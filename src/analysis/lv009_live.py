"""Registered LV-009 preflight and reader generation runner."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import time
import urllib.error
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.locomo_nf_development import sha256_file
from analysis.lv009_exploration import ARMS, PROMPTS, ROOT, SELECTIONS, ordered_schedule, load_blind_population
from analysis.lv009_runtime import SERVER, complete


REGISTRATION = ROOT / "LV_009_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "part1" / "part1.json"
TOKEN_AUDIT = ROOT / "artifacts" / "part1" / "token_audit.json"
READER_PROBES = ROOT / "artifacts" / "part1" / "reader_probes.json"
JUDGE_PROBES = ROOT / "artifacts" / "part1" / "judge_probes.json"
PREFLIGHT = ROOT / "artifacts" / "preflight" / "preflight.json"
ANSWERS = ROOT / "artifacts" / "run" / "answers.jsonl"
GENERATION_SUMMARY = ROOT / "artifacts" / "run" / "generation_summary.json"
MODEL_SOURCE = Path(r"C:\Users\muzaf\.cache\huggingface\hub\models--unsloth--Qwen3.8-27B-GGUF\snapshots\f1bfb127c64f7072bdd2cad55f258b9c8b2910fe\Qwen3.8-27B-UD-Q4_K_XL.gguf")
SERVER_BINARY = Path(r"C:\Users\muzaf\.unsloth\llama.cpp\build\bin\Release\llama-server.exe")
MODEL_SOURCE_SHA256 = "bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372"
SERVER_BINARY_SHA256 = "125e0938a280cba46c803a60178e51826203e030abacce03367a22108720f7ac"
REGISTRATION_SHA256 = "b0b6c7806ecdf8dd9be6f070ff4595d749a72feab1eb3add8e851d05eb7cf8bb"
PART1_SHA256 = "4a2a275d2658ee05eeefd4887706fedcf398e75ba08d83732ad5be192230da13"
PROMPTS_SHA256 = "98a0d0a3e00f78dfa222bd6d2cb6c49093dd7ae5f5f005b2a8de1412d14fc454"
SELECTIONS_SHA256 = "35ab1fd17299163dfd11b1b6d84f583203982f9325e2e56bc38ed08129802315"
READER_LIMIT = 8_192


class LV009LiveError(RuntimeError):
    pass


def _read_prompts() -> list[dict[str, Any]]:
    with gzip.open(PROMPTS, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _append_fsynced(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _get(path: str) -> dict[str, Any]:
    import urllib.request
    with urllib.request.urlopen(SERVER + path, timeout=30.0) as response:
        return json.loads(response.read().decode("utf-8"))


def _gpu_record() -> dict[str, Any]:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
        text=True, capture_output=True, check=True,
    )
    fields = [value.strip() for value in result.stdout.strip().split(",")]
    if len(fields) != 4:
        raise LV009LiveError("unexpected nvidia-smi output")
    record = {"name": fields[0], "total_mib": int(fields[1]), "used_mib": int(fields[2]), "free_mib": int(fields[3])}
    record["resident"] = record["name"] == "NVIDIA GeForce RTX 5090" and record["used_mib"] >= 20_000
    return record


def validate_answer_schedule(rows: Sequence[Mapping[str, Any]], prompts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = {(row["comparison_key"], arm) for row in prompts for arm in ARMS}
    actual = [(row["comparison_key"], row["arm"]) for row in rows]
    completed = {
        (row["comparison_key"], row["arm"])
        for row in rows
        if row.get("response", {}).get("complete") and row.get("response", {}).get("response_bytes", 0) > 0
    }
    return {
        "rows": len(rows), "expected": len(expected),
        "duplicates": len(actual) - len(set(actual)),
        "missing": len(expected - set(actual)), "extra": len(set(actual) - expected),
        "completed": len(completed),
        "length_stops": sum(row.get("response", {}).get("stop_type") == "limit" for row in rows),
        "pass": len(rows) == len(expected) and len(actual) == len(set(actual)) and set(actual) == expected and completed == expected,
    }


def _structural_checks(prompts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    set_exact = element_exact = reminders = qeach_active = 0
    for row in prompts:
        selected = set(row["selected_ids"])
        baseline_hashes = row["arms"]["PAIRWISE"]["episode_element_sha256"]
        groups = len(row["arms"]["COMMUNITY_QB"]["groups"])
        reminder = f"<question_reminder>Question to answer: {row['question']}</question_reminder>"
        for arm in ARMS:
            value = row["arms"][arm]
            set_exact += len(value["emitted_ids"]) == len(selected) and set(value["emitted_ids"]) == selected
            element_exact += value["episode_element_sha256"] == baseline_hashes
        count = row["arms"]["COMMUNITY_QEACH"]["prompt"].count(reminder)
        reminders += count == groups - 1
        qeach_active += groups >= 2 and row["arms"]["COMMUNITY_QEACH"]["prompt_sha256"] != row["arms"]["COMMUNITY_QB"]["prompt_sha256"]
    return {
        "set_exact": set_exact, "expected_set_exact": len(prompts) * len(ARMS),
        "element_exact": element_exact, "expected_element_exact": len(prompts) * len(ARMS),
        "reminder_rows": reminders, "qeach_active_rows": qeach_active,
    }


def run_preflight() -> dict[str, Any]:
    anchors = {
        "registration": sha256_file(REGISTRATION) == REGISTRATION_SHA256,
        "part1": sha256_file(PART1) == PART1_SHA256,
        "prompts": sha256_file(PROMPTS) == PROMPTS_SHA256,
        "selections": sha256_file(SELECTIONS) == SELECTIONS_SHA256,
        "model_source": sha256_file(MODEL_SOURCE) == MODEL_SOURCE_SHA256,
        "server_binary": sha256_file(SERVER_BINARY) == SERVER_BINARY_SHA256,
        "registration_ancestor": subprocess.run(
            ["git", "merge-base", "--is-ancestor", "950a17f1", "HEAD"],
            cwd=ROOT.parents[2], capture_output=True,
        ).returncode == 0,
    }
    if not all(anchors.values()):
        raise LV009LiveError(f"registered anchor drift: {anchors}")
    prompts = _read_prompts()
    if len(prompts) != 1_986 or len({row["comparison_key"] for row in prompts}) != 1_986:
        raise LV009LiveError("prompt population drift")
    primary = [row for row in prompts if row["category"] in (1, 2, 3, 4)]
    checks = _structural_checks(prompts)
    token_audit = json.loads(TOKEN_AUDIT.read_text(encoding="utf-8"))
    reader_probes = json.loads(READER_PROBES.read_text(encoding="utf-8"))
    judge_probes = json.loads(JUDGE_PROBES.read_text(encoding="utf-8"))
    props = _get("/props")
    params = props["default_generation_settings"]["params"]
    gpu = _gpu_record()
    passing = (
        len(primary) == 1_540
        and checks["set_exact"] == checks["expected_set_exact"]
        and checks["element_exact"] == checks["expected_element_exact"]
        and checks["reminder_rows"] == 1_986
        and checks["qeach_active_rows"] >= 1_540
        and token_audit["rows"] == 7_944
        and token_audit["all_context_safe_at_reader_cap"]
        and reader_probes["all_nonempty"] and reader_probes["all_context_safe"]
        and judge_probes["all_nonempty"] and all(row["parseable_surface"] for row in judge_probes["rows"])
        and int(props["total_slots"]) == 1
        and int(props["default_generation_settings"]["n_ctx"]) == 65_536
        and params["speculative.types"] == "none"
        and gpu["resident"]
    )
    result = {
        "schema": "lv009-preflight-v1", "status": "PASS" if passing else "FAIL",
        "anchors": anchors, "population": {"rows": len(prompts), "primary": len(primary), "prompts": len(prompts) * len(ARMS)},
        "checks": checks, "token_audit": token_audit, "reader_probes": reader_probes,
        "judge_probes": judge_probes, "server": {"props": props, "gpu": gpu},
        "registration_commit": "950a17f1",
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV009LiveError("LV-009 Preflight failed")
    return result


def run_generation() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8")) if PREFLIGHT.exists() else run_preflight()
    if preflight.get("status") != "PASS":
        raise LV009LiveError("generation requires passing Preflight")
    prompts = _read_prompts()
    by_key = {row["comparison_key"]: row for row in prompts}
    existing = _read_jsonl(ANSWERS)
    validation = validate_answer_schedule(existing, prompts)
    if validation["duplicates"] or validation["extra"]:
        raise LV009LiveError("existing answer ledger has duplicate or extra keys")
    completed = {(row["comparison_key"], row["arm"]) for row in existing}
    schedule = ordered_schedule(load_blind_population())
    started = time.time()
    for comparison_key, arm, seed in schedule:
        if (comparison_key, arm) in completed:
            continue
        prompt_row = by_key[comparison_key]
        prompt = prompt_row["arms"][arm]["prompt"]
        attempts = []
        for attempt in range(2):
            try:
                response = complete(prompt, seed=seed, n_predict=READER_LIMIT)
            except (OSError, TimeoutError, urllib.error.URLError) as error:
                attempts.append({"attempt": attempt + 1, "transport_error": repr(error)})
                if attempt == 0:
                    continue
                raise LV009LiveError("unresolved mechanical transport failure") from error
            text = response.pop("_text")
            response["complete"] = True
            response["text"] = text
            attempts.append({"attempt": attempt + 1, "transport_error": None})
            break
        if response["prompt_tokens"] + READER_LIMIT >= 65_536:
            raise LV009LiveError("reader context overflow")
        gpu = _gpu_record()
        if not gpu["resident"]:
            raise LV009LiveError("GPU residency lost")
        _append_fsynced(ANSWERS, {
            "comparison_key": comparison_key, "sample_id": prompt_row["sample_id"],
            "source_index": prompt_row["source_index"], "category": prompt_row["category"],
            "arm": arm, "seed": seed, "prompt_sha256": prompt_row["arms"][arm]["prompt_sha256"],
            "attempts": attempts, "response": response,
        })
        completed.add((comparison_key, arm))
    rows = _read_jsonl(ANSWERS)
    validation = validate_answer_schedule(rows, prompts)
    summary = {
        "schema": "lv009-generation-summary-v1", "validation": validation,
        "answers_sha256": sha256_file(ANSWERS), "wall_seconds": round(time.time() - started, 3),
        "gpu_after": _gpu_record(), "server_after": _get("/props"),
    }
    _write_json(GENERATION_SUMMARY, summary)
    if not validation["pass"]:
        raise LV009LiveError("generation schedule incomplete")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "generate"))
    args = parser.parse_args()
    if args.phase == "preflight":
        run_preflight()
    else:
        run_generation()


if __name__ == "__main__":
    main()
