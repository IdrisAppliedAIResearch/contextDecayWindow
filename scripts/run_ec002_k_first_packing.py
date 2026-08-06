"""Run EC-002's registered A0 replay gate or A1 K-first counterfactual."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "episodic" / "src"))

from episodic import EmbeddingCache, EpisodeStore, EpisodicConfig  # noqa: E402
from src.analysis.ec001_longmemeval import (  # noqa: E402
    aggregate_tier1,
    load_adaptation_record,
    load_longmemeval,
    parse_delivered_block,
    score_retrieval,
    session_cosine_ranking,
    sha256_file,
)
from src.analysis.ec002_k_first_packing import (  # noqa: E402
    EC002Error,
    build_k_first_context,
    check_reproduction_row,
    compare_score_rows,
    evaluate_reproduction,
    normalized_report,
)
from src.retrieval_bakeoff.embedding import CarriedEmbedder  # noqa: E402

REGISTRATION_SHA = "8c75d7e2"
AMENDMENT_001_SHA = "2a675eef"
AMENDMENT_002_SHA = "1e2410c4"
REQUIRED_BRANCH = "ec/002-k-first-packing"
DEFAULT_ORIGINAL_RUN = (
    REPO / "experiments" / "external" / "longmemeval" / "runs" / "tier1_001"
)
DEFAULT_CACHE_ADOPTION = (
    REPO
    / "experiments"
    / "components"
    / "embedding_cache"
    / "artifacts"
    / "cc006"
    / "ec002_legacy_adoption.json"
)


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def repository_gate() -> dict:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != REQUIRED_BRANCH:
        raise EC002Error(
            f"EC-002 must run on {REQUIRED_BRANCH}, found {branch}"
        )
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", REGISTRATION_SHA, "HEAD"],
        cwd=REPO,
        check=False,
    ).returncode:
        raise EC002Error("EC-002 registration is not an ancestor of HEAD")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", AMENDMENT_001_SHA, "HEAD"],
        cwd=REPO,
        check=False,
    ).returncode:
        raise EC002Error("EC-002 amendment is not an ancestor of HEAD")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", AMENDMENT_002_SHA, "HEAD"],
        cwd=REPO,
        check=False,
    ).returncode:
        raise EC002Error("EC-002 amendment 002 is not an ancestor of HEAD")
    status = _git("status", "--porcelain")
    if status:
        raise EC002Error(f"EC-002 refuses a dirty worktree:\n{status}")
    return {
        "branch": branch,
        "head": _git("rev-parse", "HEAD"),
        "registration_sha": _git("rev-parse", REGISTRATION_SHA),
        "amendment_001_sha": _git("rev-parse", AMENDMENT_001_SHA),
        "amendment_002_sha": _git("rev-parse", AMENDMENT_002_SHA),
        "worktree_clean": True,
    }


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="\n") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def load_original(run_dir: Path) -> dict:
    paths = {
        "scores": run_dir / "tier1_scores.jsonl",
        "summary": run_dir / "tier1_summary.json",
        "mechanism": run_dir / "SEALED_MECHANISM_DO_NOT_OPEN.jsonl",
        "integrity": run_dir / "source_integrity.json",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise EC002Error(f"Original EC-001 artifacts missing: {missing}")
    integrity = json.loads(paths["integrity"].read_text(encoding="utf-8"))
    expected = {
        "scores": integrity["scores_sha256"],
        "mechanism": integrity["sealed_mechanism_sha256"],
    }
    for name, expected_hash in expected.items():
        observed = sha256_file(paths[name])
        if observed != expected_hash:
            raise EC002Error(
                f"Original {name} hash drifted: {observed} != {expected_hash}"
            )
    return {
        "paths": paths,
        "scores": read_jsonl(paths["scores"]),
        "summary": json.loads(paths["summary"].read_text(encoding="utf-8")),
        "mechanisms": read_jsonl(paths["mechanism"]),
        "integrity": integrity,
    }


def committed_gate(path: Path) -> dict:
    if not path.is_file():
        raise EC002Error(f"A0 gate artifact does not exist: {path}")
    relative = path.resolve().relative_to(REPO.resolve()).as_posix()
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    if _git("status", "--porcelain", "--", relative):
        raise EC002Error("A0 gate artifact is dirty")
    gate_commit = _git("log", "-1", "--format=%H", "--", relative)
    if not gate_commit:
        raise EC002Error("A0 gate artifact has no commit")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", gate_commit, "HEAD"],
        cwd=REPO,
        check=False,
    ).returncode:
        raise EC002Error("A0 gate commit is not an ancestor of HEAD")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise EC002Error("A0 reproduction gate did not pass")
    if gate.get("registration_sha") != _git("rev-parse", REGISTRATION_SHA):
        raise EC002Error("A0 gate registration anchor differs")
    cache = gate.get("embedding_cache")
    cache_source = "a0_reproduction_gate.json"
    if not isinstance(cache, dict):
        integrity_path = path.parent / "source_integrity.json"
        if not integrity_path.is_file():
            raise EC002Error(
                "A0 gate omits its cache and sibling source integrity is missing"
            )
        integrity_relative = (
            integrity_path.resolve().relative_to(REPO.resolve()).as_posix()
        )
        subprocess.run(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                "--",
                integrity_relative,
            ],
            cwd=REPO,
            check=True,
            capture_output=True,
        )
        if _git("status", "--porcelain", "--", integrity_relative):
            raise EC002Error("A0 source-integrity artifact is dirty")
        integrity_commit = _git(
            "log", "-1", "--format=%H", "--", integrity_relative
        )
        if integrity_commit != gate_commit:
            raise EC002Error(
                "A0 gate and source integrity were not committed together"
            )
        integrity = json.loads(
            integrity_path.read_text(encoding="utf-8")
        )
        if integrity.get("status") != "PASS":
            raise EC002Error("A0 source integrity did not pass")
        if integrity.get("mode") != "reproduce":
            raise EC002Error("A0 source integrity has the wrong mode")
        if integrity.get("registration_sha") != _git(
            "rev-parse", REGISTRATION_SHA
        ):
            raise EC002Error(
                "A0 source-integrity registration anchor differs"
            )
        if (
            integrity.get("script_sha256_before")
            != integrity.get("script_sha256_after")
        ):
            raise EC002Error("A0 script changed during reproduction")
        if integrity.get("embedding_model_sha256") != (
            "06507c7b42688469c4e7298b0a1e16de"
            "ff06caf291cf0a5b278c308249c3e439"
        ):
            raise EC002Error("A0 source-integrity model hash differs")
        cache = integrity.get("embedding_cache")
        if not isinstance(cache, dict):
            raise EC002Error("A0 source integrity omits its cache")
        expected_cache = {
            "bytes": 1_050_013_696,
            "entries": 96_585,
            "misses": 0,
            "call_shape": "solo",
            "sha256": (
                "e8a31513700a0a5d1cfe34b4703bbe3c"
                "8c85dc3ca29188d7cc480c2e2417a7ad"
            ),
        }
        for key, expected in expected_cache.items():
            if cache.get(key) != expected:
                raise EC002Error(
                    f"A0 source-integrity cache {key} differs: "
                    f"{cache.get(key)!r} != {expected!r}"
                )
        expected_path = (
            REPO
            / "experiments"
            / "external"
            / "longmemeval"
            / "runs"
            / "ec002_k_first"
            / "ec002_exact_solo_embeddings.db"
        ).resolve()
        if Path(str(cache.get("path"))).resolve() != expected_path:
            raise EC002Error("A0 source-integrity cache path differs")
        cache_source = integrity_relative
    return {
        "path": relative,
        "sha256": sha256_file(path),
        "commit": gate_commit,
        "embedding_cache": cache,
        "embedding_cache_source": cache_source,
    }


def committed_cache_adoption(path: Path) -> dict:
    """Load CC-006's committed binding for the retained EC-002 cache."""

    if not path.is_file():
        raise EC002Error(f"CC-006 cache adoption is missing: {path}")
    relative = path.resolve().relative_to(REPO.resolve()).as_posix()
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    if _git("status", "--porcelain", "--", relative):
        raise EC002Error("CC-006 cache adoption artifact is dirty")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("status") != "PASS":
        raise EC002Error("CC-006 cache adoption did not pass")
    adoption = record.get("adoption")
    if not isinstance(adoption, dict):
        raise EC002Error("CC-006 cache adoption record is malformed")
    return {
        "path": relative,
        "sha256": sha256_file(path),
        "commit": _git("log", "-1", "--format=%H", "--", relative),
        "adoption": adoption,
    }


def build_store(bundle, path: Path, embedder, config: EpisodicConfig):
    store = EpisodeStore(path, config=config, embedder=embedder)
    for episode in bundle.mechanism.episodes:
        store.append("user", episode.user_message)
        store.append("assistant", episode.assistant_message)
    return store


def run_reproduction(
    *,
    dataset,
    original: dict,
    embedder,
    config: EpisodicConfig,
    budget: int,
    output: Path,
) -> dict:
    original_scores = {
        str(row["question_id"]): row for row in original["scores"]
    }
    original_mechanisms = {
        str(row["question_id"]): row for row in original["mechanisms"]
    }
    checks: list[dict] = []
    reproduced_scores: list[dict] = []
    reproduced_mechanisms: list[dict] = []
    started = time.time()

    with tempfile.TemporaryDirectory(prefix="ec002-a0-") as temporary:
        stores = Path(temporary)
        for index, bundle in enumerate(dataset.instances, 1):
            question_id = bundle.mechanism.question_id
            with build_store(
                bundle,
                stores / f"{question_id}.db",
                embedder,
                config,
            ) as store:
                block, report = store.context(
                    bundle.mechanism.question, budget
                )
            delivered = parse_delivered_block(block)
            ranking = session_cosine_ranking(
                bundle.mechanism, bundle.measurement, embedder
            )
            score = {
                "question_id": question_id,
                "question_type": bundle.measurement.question_type,
                "stratum": bundle.measurement.stratum,
                **score_retrieval(
                    bundle.measurement, delivered, ranking
                ),
            }
            reproduced_scores.append(score)
            reproduced_mechanisms.append(
                {
                    "question_id": question_id,
                    "block": block,
                    "block_sha256": hashlib.sha256(
                        block.encode("utf-8")
                    ).hexdigest(),
                    "report": asdict(report),
                    "delivered_turn_numbers": sorted(delivered),
                    "session_cosine_ranking": ranking,
                    "reproduction_label": (
                        "reproduction under recomputed embeddings"
                    ),
                }
            )
            checks.append(
                check_reproduction_row(
                    original_score=original_scores[question_id],
                    original_mechanism=original_mechanisms[question_id],
                    reproduced_score=score,
                    reproduced_block=block,
                    reproduced_report=report,
                )
            )
            _progress(index, len(dataset.instances), started)

    summary = aggregate_tier1(reproduced_scores)
    gate = evaluate_reproduction(
        checks=checks,
        reproduced_summary=summary,
        original_summary=original["summary"],
    )
    gate["registration_sha"] = _git("rev-parse", REGISTRATION_SHA)
    gate["amendment_001_sha"] = _git("rev-parse", AMENDMENT_001_SHA)
    write_jsonl(output / "a0_reproduction_checks.jsonl", checks)
    write_json(output / "a0_reproduction_gate.json", gate)
    write_jsonl(output / "a0_reproduced_scores.jsonl", reproduced_scores)
    write_jsonl(
        output / "a0_reproduced_mechanism.jsonl", reproduced_mechanisms
    )
    write_json(output / "a0_reproduced_summary.json", summary)
    return gate


def run_counterfactual(
    *,
    dataset,
    original: dict,
    embedder,
    config: EpisodicConfig,
    budget: int,
    output: Path,
) -> dict:
    original_scores = {
        str(row["question_id"]): row for row in original["scores"]
    }
    original_mechanisms = {
        str(row["question_id"]): row for row in original["mechanisms"]
    }
    baseline_scores: list[dict] = []
    baseline_mechanisms: list[dict] = []
    baseline_checks: list[dict] = []
    treatment_scores: list[dict] = []
    treatment_mechanisms: list[dict] = []
    started = time.time()

    with tempfile.TemporaryDirectory(prefix="ec002-a1-") as temporary:
        stores = Path(temporary)
        for index, bundle in enumerate(dataset.instances, 1):
            question_id = bundle.mechanism.question_id
            with build_store(
                bundle,
                stores / f"{question_id}.db",
                embedder,
                config,
            ) as store:
                baseline_block, baseline_report = store.context(
                    bundle.mechanism.question, budget
                )
                baseline_rerun_block, baseline_rerun_report = store.context(
                    bundle.mechanism.question, budget
                )
                if baseline_block != baseline_rerun_block:
                    raise EC002Error(
                        f"{question_id}: same-store A0 block rerun drifted"
                    )
                if normalized_report(
                    baseline_report
                ) != normalized_report(baseline_rerun_report):
                    raise EC002Error(
                        f"{question_id}: same-store A0 report rerun drifted"
                    )
                episodes = store._all_episodes()
                query = embedder(bundle.mechanism.question)
                block, report, diagnostics = build_k_first_context(
                    episodes=episodes,
                    query_embedding=query,
                    budget=budget,
                    config=config,
                )
                rerun_block, rerun_report, rerun_diagnostics = (
                    build_k_first_context(
                        episodes=episodes,
                        query_embedding=query,
                        budget=budget,
                        config=config,
                    )
                )
            if block != rerun_block:
                raise EC002Error(
                    f"{question_id}: K-first byte-identical rerun failed"
                )
            if normalized_report(report) != normalized_report(rerun_report):
                raise EC002Error(
                    f"{question_id}: K-first report rerun drifted"
                )
            if diagnostics != rerun_diagnostics:
                raise EC002Error(
                    f"{question_id}: K-first diagnostics rerun drifted"
                )

            ranking = session_cosine_ranking(
                bundle.mechanism, bundle.measurement, embedder
            )
            baseline_delivered = parse_delivered_block(baseline_block)
            baseline_score = {
                "question_id": question_id,
                "question_type": bundle.measurement.question_type,
                "stratum": bundle.measurement.stratum,
                **score_retrieval(
                    bundle.measurement, baseline_delivered, ranking
                ),
            }
            baseline_scores.append(baseline_score)
            baseline_mechanisms.append(
                {
                    "question_id": question_id,
                    "block": baseline_block,
                    "block_sha256": hashlib.sha256(
                        baseline_block.encode("utf-8")
                    ).hexdigest(),
                    "report": asdict(baseline_report),
                    "delivered_turn_numbers": sorted(baseline_delivered),
                    "session_cosine_ranking": ranking,
                    "same_store_as_a1": True,
                    "determinism_rerun": "PASS",
                }
            )
            baseline_checks.append(
                check_reproduction_row(
                    original_score=original_scores[question_id],
                    original_mechanism=original_mechanisms[question_id],
                    reproduced_score=baseline_score,
                    reproduced_block=baseline_block,
                    reproduced_report=baseline_report,
                )
            )

            delivered = parse_delivered_block(block)
            score = {
                "question_id": question_id,
                "question_type": bundle.measurement.question_type,
                "stratum": bundle.measurement.stratum,
                **score_retrieval(
                    bundle.measurement, delivered, ranking
                ),
            }
            treatment_scores.append(score)
            treatment_mechanisms.append(
                {
                    "question_id": question_id,
                    "block": block,
                    "block_sha256": hashlib.sha256(
                        block.encode("utf-8")
                    ).hexdigest(),
                    "report": asdict(report),
                    "delivered_turn_numbers": sorted(delivered),
                    "session_cosine_ranking": ranking,
                    "packing_diagnostics": diagnostics,
                    "same_store_as_a0": True,
                    "determinism_rerun": "PASS",
                }
            )
            _progress(index, len(dataset.instances), started)

    baseline_summary = aggregate_tier1(baseline_scores)
    baseline_gate = evaluate_reproduction(
        checks=baseline_checks,
        reproduced_summary=baseline_summary,
        original_summary=original["summary"],
    )
    baseline_gate["same_store_as_a1"] = True
    baseline_gate["registration_sha"] = _git("rev-parse", REGISTRATION_SHA)
    baseline_gate["amendment_001_sha"] = _git(
        "rev-parse", AMENDMENT_001_SHA
    )
    baseline_gate["amendment_002_sha"] = _git(
        "rev-parse", AMENDMENT_002_SHA
    )
    write_jsonl(output / "a1_same_store_a0_scores.jsonl", baseline_scores)
    write_jsonl(
        output / "a1_same_store_a0_mechanism.jsonl", baseline_mechanisms
    )
    write_json(
        output / "a1_same_store_a0_summary.json", baseline_summary
    )
    write_json(output / "a1_same_store_a0_gate.json", baseline_gate)
    if baseline_gate["status"] != "PASS":
        raise EC002Error(
            "Same-store A0 failed the amended reproduction gate; "
            "A1 output remains unwritten"
        )

    summary = aggregate_tier1(treatment_scores)
    comparison = compare_score_rows(
        baseline_rows=baseline_scores,
        treatment_rows=treatment_scores,
        treatment_mechanisms=treatment_mechanisms,
    )
    write_jsonl(output / "a1_scores.jsonl", treatment_scores)
    write_jsonl(output / "a1_mechanism.jsonl", treatment_mechanisms)
    write_json(output / "a1_summary.json", summary)
    write_json(output / "paired_comparison.json", comparison)
    return comparison


def _progress(index: int, total: int, started: float) -> None:
    if index % 10 == 0 or index == total:
        elapsed = time.time() - started
        print(
            f"{index:3d}/{total} questions; {elapsed / index:.2f}s/question",
            flush=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("reproduce", "counterfactual"), required=True
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--embedding-model", type=Path, required=True)
    parser.add_argument("--embedding-cache", type=Path, required=True)
    parser.add_argument(
        "--reuse-a0-cache",
        action="store_true",
        help=(
            "Open an existing failed-A0 cache read-only for the amended "
            "reproduction; no new embedding calls are allowed."
        ),
    )
    parser.add_argument(
        "--original-run", type=Path, default=DEFAULT_ORIGINAL_RUN
    )
    parser.add_argument("--gate", type=Path)
    parser.add_argument(
        "--cache-adoption", type=Path, default=DEFAULT_CACHE_ADOPTION
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    script_before = sha256_file(script_path)
    repository = repository_gate()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite output: {args.output}")
    if args.mode == "counterfactual" and args.gate is None:
        raise EC002Error("Counterfactual mode requires --gate")
    gate_record = (
        committed_gate(args.gate)
        if args.mode == "counterfactual"
        else None
    )
    adoption_record = (
        committed_cache_adoption(args.cache_adoption)
        if args.mode == "counterfactual" or args.reuse_a0_cache
        else None
    )

    record = load_adaptation_record()
    benchmark = record["benchmark"]
    if args.data.stat().st_size != int(benchmark["dataset_bytes"]):
        raise EC002Error("Dataset byte size differs from EC-001 pin")
    dataset = load_longmemeval(
        args.data,
        expected_sha256=str(benchmark["dataset_sha256"]),
    )
    original = load_original(args.original_run)

    config = EpisodicConfig()
    decisions = record["decisions"]
    budget = int(decisions["budget"]["budget_chars"])
    if budget != 32_000:
        raise EC002Error("Registered budget is not 32,000 characters")

    expected_model_sha = str(config.embedder_sha256)
    observed_model_sha = sha256_file(args.embedding_model)
    if observed_model_sha != expected_model_sha:
        raise EC002Error(
            "Embedding model artifact differs from the pinned configuration"
        )
    carried = None
    if args.mode == "reproduce" and not args.reuse_a0_cache:
        carried = CarriedEmbedder(args.embedding_model)
        carried.assert_carried_model()
    if args.mode == "counterfactual":
        registered_cache = gate_record["embedding_cache"]
        adoption = adoption_record["adoption"]
        if args.embedding_cache.resolve() != Path(
            registered_cache["path"]
        ).resolve():
            raise EC002Error("A1 cache path differs from the A0 gate")
        if args.embedding_cache.resolve() != Path(adoption["path"]).resolve():
            raise EC002Error("A1 cache path differs from CC-006 adoption")
        if adoption["file_sha256"] != registered_cache["sha256"]:
            raise EC002Error("CC-006 file hash differs from the A0 gate")
        if adoption["entries"] != registered_cache["entries"]:
            raise EC002Error("CC-006 entry count differs from the A0 gate")
        if adoption["model_sha256"] != expected_model_sha:
            raise EC002Error("CC-006 model hash differs from EC-002")
        if adoption["content_sha256"] != (
            "d60d723dea787b0d5bbd25a3c89f2a1c"
            "20b92a2a79813f34688a12e7c346a180"
        ):
            raise EC002Error("CC-006 canonical content hash differs")
        observed_cache_sha = sha256_file(args.embedding_cache)
        if observed_cache_sha != adoption["file_sha256"]:
            raise EC002Error("A1 embedding cache hash differs from A0")

    args.output.mkdir(parents=True)
    started = time.time()
    cache_arguments = {
        "mode": (
            "reuse"
            if args.mode == "counterfactual" or args.reuse_a0_cache
            else "populate"
        ),
        "embedder": carried,
    }
    if cache_arguments["mode"] == "reuse":
        adoption = adoption_record["adoption"]
        cache_arguments.update(
            {
                "expected_file_sha256": adoption["file_sha256"],
                "expected_content_sha256": adoption["content_sha256"],
                "expected_model_sha256": expected_model_sha,
                "legacy_v0": True,
            }
        )
    with EmbeddingCache(
        args.embedding_cache,
        **cache_arguments,
    ) as embedder:
        if args.mode == "reproduce":
            result = run_reproduction(
                dataset=dataset,
                original=original,
                embedder=embedder,
                config=config,
                budget=budget,
                output=args.output,
            )
        else:
            result = run_counterfactual(
                dataset=dataset,
                original=original,
                embedder=embedder,
                config=config,
                budget=budget,
                output=args.output,
            )
        cache_entries = embedder.cache_size
        cache_hits = embedder.hits
        cache_misses = embedder.misses
        public_cache_record = embedder.record()

    cache_record = {
        **public_cache_record,
        # Compatibility with the locked A0 artifact's field name.
        "sha256": public_cache_record["file_sha256"],
    }
    if args.mode == "counterfactual":
        if cache_misses != 0:
            raise EC002Error("A1 made a new embedding call")
        if cache_record["sha256"] != gate_record["embedding_cache"]["sha256"]:
            raise EC002Error("Read-only A1 changed the embedding cache")
        if (
            cache_record["content_sha256"]
            != adoption_record["adoption"]["content_sha256"]
        ):
            raise EC002Error("Read-only A1 changed cache content")
    elif args.reuse_a0_cache:
        if cache_misses != 0:
            raise EC002Error("Amended A0 made a new embedding call")
    else:
        gate_path = args.output / "a0_reproduction_gate.json"
        gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
        gate_payload["embedding_cache"] = cache_record
        write_json(gate_path, gate_payload)
        result = gate_payload

    script_after = sha256_file(script_path)
    if script_after != script_before:
        raise EC002Error("Runner changed during replay")
    if sha256_file(args.data) != dataset.source_sha256:
        raise EC002Error("Dataset changed during replay")

    integrity = {
        "status": "PASS",
        "mode": args.mode,
        "registration_sha": repository["registration_sha"],
        "dataset_sha256": dataset.source_sha256,
        "embedding_model_sha256": embedder.model_sha256,
        "script_sha256_before": script_before,
        "script_sha256_after": script_after,
        "original_scores_sha256": sha256_file(
            original["paths"]["scores"]
        ),
        "original_mechanism_sha256": sha256_file(
            original["paths"]["mechanism"]
        ),
        "original_summary_sha256": sha256_file(
            original["paths"]["summary"]
        ),
        "a0_gate": gate_record,
        "cc006_cache_adoption": adoption_record,
        "embedding_cache": cache_record,
    }
    write_json(args.output / "source_integrity.json", integrity)
    write_json(
        args.output / "run_header.json",
        {
            "record": f"EC-002 {args.mode}",
            **repository,
            "launch_command": shlex.join(sys.argv),
            "parallel": 1,
            "seed": config.seed,
            "speculative_decoding": False,
            "inference_server": None,
            "server_build_hash": None,
            "question_count": len(dataset.instances),
            "budget_chars": budget,
            "episodic_config": json.loads(config.to_json()),
            "packing_order": (
                "recency, K, A3 coverage"
                if args.mode == "reproduce"
                else "K, recency, A3 coverage"
            ),
            "started_utc": datetime.fromtimestamp(
                started, timezone.utc
            ).isoformat(),
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - started, 3),
            "embedding_cache_entries": cache_entries,
            "embedding_cache": cache_record,
            "result_status": result.get("status"),
        },
    )
    print(f"EC-002 {args.mode}: {result.get('status', 'COMPLETE')}")
    if args.mode == "reproduce" and result["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
