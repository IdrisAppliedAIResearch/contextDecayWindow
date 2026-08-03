"""Generate EC-001 Tier 2 answers after Tier 1 scores are committed."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.analysis.ec001_longmemeval import (  # noqa: E402
    AMENDMENT_004_SHA,
    EC001Error,
    assert_repository_ready,
    load_adaptation_record,
    load_longmemeval,
    sha256_file,
    validate_subset_manifest,
)
from src.analysis.ec001_tier2 import (  # noqa: E402
    EC001Tier2Error,
    prepare_reader_prompt,
    reduce_scoreable_response,
)


SCORE_ARTIFACTS = (
    "tier1_scores.jsonl",
    "tier1_summary.json",
    "instrument_audit.json",
    "source_integrity.json",
    "run_header.json",
)
MECHANISM_ARTIFACT = "SEALED_MECHANISM_DO_NOT_OPEN.jsonl"


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _last_commit(path: Path) -> str:
    relative = path.resolve().relative_to(REPO.resolve())
    commit = _git("log", "-1", "--format=%H", "--", str(relative))
    if not commit:
        raise EC001Tier2Error(f"Artifact is not committed: {relative}")
    return commit


def assert_score_before_log_order(tier1_dir: Path) -> dict:
    score_commits = {
        name: _last_commit(tier1_dir / name) for name in SCORE_ARTIFACTS
    }
    mechanism_commit = _last_commit(tier1_dir / MECHANISM_ARTIFACT)
    for name, score_commit in score_commits.items():
        if score_commit == mechanism_commit:
            raise EC001Tier2Error(
                f"{name} and the sealed mechanism log share one commit"
            )
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor",
             score_commit, mechanism_commit],
            cwd=REPO,
            check=False,
            capture_output=True,
        )
        if completed.returncode:
            raise EC001Tier2Error(
                f"{name} was not committed before the mechanism log"
            )
    return {
        "score_commits": score_commits,
        "mechanism_commit": mechanism_commit,
        "status": "PASS",
    }


def _request_json(url: str, payload: dict | None = None) -> dict:
    if payload is None:
        request = Request(url, method="GET")
    else:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    with urlopen(request, timeout=900) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise EC001Tier2Error(f"Non-object response from {url}")
    return value


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _validate_reader_runtime(record: dict, server_url: str) -> dict:
    if record.get("amendment_004_sha") != AMENDMENT_004_SHA:
        raise EC001Tier2Error("Runtime record predates scoring Amendment 004")
    reader = record.get("reader")
    if not isinstance(reader, dict):
        raise EC001Tier2Error("Runtime record has no reader")
    model_path = Path(str(reader["model_path"]))
    server_path = Path(str(reader["server_binary"]))
    if sha256_file(model_path) != reader.get("model_sha256"):
        raise EC001Tier2Error("Reader model hash mismatch")
    if sha256_file(server_path) != reader.get("server_sha256"):
        raise EC001Tier2Error("llama.cpp server hash mismatch")

    props = _request_json(f"{server_url.rstrip('/')}/props")
    if props.get("total_slots") != 1:
        raise EC001Tier2Error("Reader server must expose exactly one slot")
    if props.get("model_alias") != reader.get("model_alias"):
        raise EC001Tier2Error("Reader server model alias mismatch")
    if props.get("build_info") != reader.get("server_build_info"):
        raise EC001Tier2Error("Reader server build mismatch")
    params = props.get("default_generation_settings", {}).get("params", {})
    if params.get("speculative.types") != "none":
        raise EC001Tier2Error("Speculative decoding is not disabled")
    return props


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--subset", type=Path, required=True)
    parser.add_argument("--tier1-dir", type=Path, required=True)
    parser.add_argument("--runtime-record", type=Path, required=True)
    parser.add_argument("--server-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = assert_repository_ready(require_clean=True)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite output: {args.output}")
    order_gate = assert_score_before_log_order(args.tier1_dir)

    adaptation = load_adaptation_record()
    benchmark = adaptation["benchmark"]
    dataset = load_longmemeval(
        args.data,
        expected_sha256=str(benchmark["dataset_sha256"]),
    )
    subset = json.loads(args.subset.read_text(encoding="utf-8"))
    selected_ids = validate_subset_manifest(subset, dataset)
    runtime = json.loads(args.runtime_record.read_text(encoding="utf-8"))
    props = _validate_reader_runtime(runtime, args.server_url)

    mechanisms = {
        row["question_id"]: row
        for row in _load_jsonl(args.tier1_dir / MECHANISM_ARTIFACT)
    }
    if set(selected_ids) - set(mechanisms):
        raise EC001Tier2Error("Tier 1 mechanism log misses selected questions")

    response_budget = int(runtime["reader"]["response_budget_tokens"])
    script_sha = sha256_file(Path(__file__).resolve())
    dataset_sha = dataset.source_sha256
    started = time.time()
    rows: list[dict] = []
    for index, question_id in enumerate(selected_ids, 1):
        bundle = dataset.by_id[question_id]
        block = str(mechanisms[question_id]["block"])
        prompt = prepare_reader_prompt(
            block,
            bundle.measurement.question_date,
            bundle.mechanism.question,
        )
        exact_prompt = f"{prompt}\n<think>\n</think>\n"
        result = _request_json(
            f"{args.server_url.rstrip('/')}/completion",
            {
                "prompt": exact_prompt,
                "n_predict": response_budget,
                "reasoning_format": "none",
                "stream": False,
            },
        )
        raw = str(result.get("content", ""))
        reduced = reduce_scoreable_response(raw)
        stop_type = str(result.get("stop_type", ""))
        hit_limit = stop_type == "limit" or bool(result.get("truncated"))
        completeness = (
            "TRUNCATED_GENERATION_LIMIT"
            if hit_limit
            else reduced.completeness_status
        )
        rows.append(
            {
                "question_id": question_id,
                "question_type": bundle.measurement.question_type,
                "stratum": bundle.measurement.stratum,
                "prompt_sha256": hashlib.sha256(
                    exact_prompt.encode("utf-8")
                ).hexdigest(),
                "retrieval_block_sha256": mechanisms[question_id][
                    "block_sha256"
                ],
                "raw_response": raw,
                "scoreable_response": reduced.scoreable_text,
                "no_answer": reduced.no_answer,
                "reasoning_blocks_balanced": (
                    reduced.reasoning_blocks_balanced
                ),
                "completeness_status": completeness,
                "tokens_predicted": result.get("tokens_predicted"),
                "stop_type": stop_type,
                "response_model": result.get("model"),
            }
        )
        if index % 10 == 0 or index == len(selected_ids):
            print(f"{index:3d}/{len(selected_ids)} Tier 2 answers")

    if sha256_file(args.data) != dataset_sha:
        raise EC001Error("Dataset changed during Tier 2 generation")
    if sha256_file(Path(__file__).resolve()) != script_sha:
        raise EC001Error("Generation script changed during Tier 2")

    args.output.mkdir(parents=True)
    answers = args.output / "tier2_answers.jsonl"
    with answers.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (args.output / "generation_header.json").write_text(
        json.dumps(
            {
                "record": "EC-001 Tier 2 reader generation",
                "head": repository["head"],
                "amendment_004_sha": repository["amendment_004_sha"],
                "launch_command": shlex.join(sys.argv),
                "tier1_commit_order": order_gate,
                "subset_sha256": sha256_file(args.subset),
                "runtime_record_sha256": sha256_file(args.runtime_record),
                "dataset_sha256": dataset_sha,
                "script_sha256": script_sha,
                "server_props": props,
                "reader_reference_fields_received": False,
                "question_count": len(rows),
                "started_utc": datetime.fromtimestamp(
                    started, timezone.utc
                ).isoformat(),
                "finished_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(time.time() - started, 3),
                "answers_sha256": sha256_file(answers),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Tier 2 generation complete at {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
