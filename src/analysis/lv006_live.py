"""Parse-safe blind-judge completion for LV-005."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import analysis.lv005_live as lv005
from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_live import JUDGE_SEEDS, MODEL, _generate, _get
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX
from analysis.lv003_live import _append_fsynced, _read_jsonl, _write_json
from analysis.lv006_exploration import FAILED_BLIND_ID, FAILED_SEED, REPAIR_SUFFIX
from analysis.tc001_exploration import REPO_ROOT


ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_006"
REGISTRATION = ROOT / "LV_006_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "part1_exploration.json"
PREFLIGHT = ROOT / "artifacts" / "preflight" / "preflight.json"
JUDGMENTS = ROOT / "artifacts" / "scoring" / "blind_judgments_repaired.jsonl"
JUDGMENT_SUMMARY = ROOT / "artifacts" / "scoring" / "judgment_summary.json"
RESULT = ROOT / "artifacts" / "result" / "result.json"
PER_ITEM = ROOT / "artifacts" / "result" / "per_item.csv"

LV005_ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_005"
PROMPTS = LV005_ROOT / "artifacts" / "preflight" / "prompts.jsonl.gz"
ANSWERS = LV005_ROOT / "artifacts" / "run" / "answers.jsonl"
GENERATION_SUMMARY = LV005_ROOT / "artifacts" / "run" / "generation_summary.json"
SURFACE = LV005_ROOT / "artifacts" / "scoring" / "blind_surface.jsonl.gz"
MAPPING = LV005_ROOT / "artifacts" / "scoring" / "blind_mapping.sealed.json"
PARTIAL = LV005_ROOT / "artifacts" / "scoring" / "blind_judgments.jsonl"

REGISTRATION_SHA256 = "82f0e0d63ace6dcec55aa1b4768defca7f03a72367f33efd686054c43d79e05d"
PART1_SHA256 = "34f4ee1c7e5fddad90709071a84a41740c377db3a1631e62fb9bf70b96068f72"
PROMPTS_SHA256 = "d0a3ac38e15c1738387c9d3216de532195959dd4c8ac7515a03209bbfebe8b80"
ANSWERS_SHA256 = "a3e9fbef31f1d6ffca2b4af1484982951447b98ec41a4c370a2f00d35de8a53f"
SURFACE_SHA256 = "97aaf2def7ff3f5c843fba4c98fd0afed3921ccbe44a43d44319f7c7b2c45205"
MAPPING_SHA256 = "edf20068b2c923478760ba462f51c47508bd3bb21d8994d69b100fc0d2924737"
PARTIAL_SHA256 = "775fc2e2f0e86da9568f7f78bb775da5e9a881e09329357e775a0e088774ad1b"


class LV006LiveError(RuntimeError):
    pass


def _surface_rows() -> list[dict[str, Any]]:
    with gzip.open(SURFACE, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def repaired_prompt(item: Mapping[str, Any]) -> str:
    return (
        render_judge_prompt(str(item["question"]), str(item["gold"]), str(item["answer"]))
        + CLOSED_THINK_SUFFIX
        + REPAIR_SUFFIX
    )


def expected_keys(surface: Sequence[Mapping[str, Any]]) -> set[tuple[str, int, int]]:
    return {
        (str(item["blind_id"]), judge_pass, seed)
        for item in surface
        for judge_pass, seed in enumerate(JUDGE_SEEDS)
    }


def validate_judgments(
    rows: Sequence[Mapping[str, Any]], surface: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    actual = [
        (str(row["blind_id"]), int(row["judge_pass"]), int(row["seed"]))
        for row in rows
    ]
    expected = expected_keys(surface)
    counts = Counter(row[0] for row in actual)
    return {
        "rows": len(rows),
        "expected": len(expected),
        "ids": len(counts),
        "duplicates": len(actual) - len(set(actual)),
        "missing": len(expected - set(actual)),
        "extra": len(set(actual) - expected),
        "three_each": len(counts) == len(surface) and all(value == 3 for value in counts.values()),
        "truncated": sum(row["done_reason"] == "length" for row in rows),
        "pass": len(rows) == len(expected)
        and len(actual) == len(set(actual))
        and set(actual) == expected
        and len(counts) == len(surface)
        and all(value == 3 for value in counts.values())
        and all(row["done_reason"] != "length" for row in rows),
    }


def _load_mapping() -> dict[str, Any]:
    if not JUDGMENT_SUMMARY.exists() or not JUDGMENTS.exists():
        raise LV006LiveError("mapping access blocked until repaired judgments complete")
    summary = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"] or sha256_file(JUDGMENTS) != summary["judgments_sha256"]:
        raise LV006LiveError("mapping access blocked by incomplete judgment seal")
    if sha256_file(MAPPING) != MAPPING_SHA256:
        raise LV006LiveError("mapping drift")
    return json.loads(MAPPING.read_text(encoding="utf-8"))["mapping"]


def run_preflight() -> dict[str, Any]:
    anchors = {
        "registration": sha256_file(REGISTRATION) == REGISTRATION_SHA256,
        "part1": sha256_file(PART1) == PART1_SHA256,
        "prompts": sha256_file(PROMPTS) == PROMPTS_SHA256,
        "answers": sha256_file(ANSWERS) == ANSWERS_SHA256,
        "surface": sha256_file(SURFACE) == SURFACE_SHA256,
        "mapping": sha256_file(MAPPING) == MAPPING_SHA256,
        "partial": sha256_file(PARTIAL) == PARTIAL_SHA256,
    }
    if not all(anchors.values()):
        raise LV006LiveError("frozen input drift")
    surface = _surface_rows()
    partial = _read_jsonl(PARTIAL)
    partial_keys = [(row["blind_id"], int(row["judge_pass"]), int(row["seed"])) for row in partial]
    partial_counts = Counter(key[0] for key in partial_keys)
    partial_valid = (
        len(partial) == 136
        and len(partial_keys) == len(set(partial_keys))
        and Counter(partial_counts.values()) == Counter({3: 45, 1: 1})
        and partial_counts[FAILED_BLIND_ID] == 1
    )
    try:
        _load_mapping()
    except LV006LiveError:
        early_mapping_rejected = True
    else:
        early_mapping_rejected = False
    prompts_a = [hashlib.sha256(repaired_prompt(item).encode()).hexdigest() for item in surface]
    prompts_b = [hashlib.sha256(repaired_prompt(item).encode()).hexdigest() for item in surface]
    prompt_replay = prompts_a == prompts_b and len(prompts_a) == len(set(item["blind_id"] for item in surface))
    failed = next(item for item in surface if item["blind_id"] == FAILED_BLIND_ID)
    response_a = _generate(repaired_prompt(failed), FAILED_SEED, judge=True)
    response_b = _generate(repaired_prompt(failed), FAILED_SEED, judge=True)
    try:
        verdict_a = parse_judge_verdict(response_a["text"])[0]
        verdict_b = parse_judge_verdict(response_b["text"])[0]
        parseable = True
    except Exception:
        verdict_a = verdict_b = None
        parseable = False
    response_sha = hashlib.sha256(response_a["text"].encode()).hexdigest()
    part1 = json.loads(PART1.read_text(encoding="utf-8"))
    expected_response_sha = part1["failed_exact"]["repair"][0]["response_sha256"]
    exact_reproduction = (
        response_sha == expected_response_sha
        and response_a["text"].encode() == response_b["text"].encode()
        and verdict_a == verdict_b
        and response_a["done_reason"] != "length"
        and response_b["done_reason"] != "length"
    )
    process = _get("/api/ps")
    loaded = [model for model in process.get("models", []) if model.get("name") == MODEL]
    gpu_only = bool(loaded) and all(int(model.get("size_vram", 0)) >= int(model.get("size", 1)) for model in loaded)
    part1_positive = (
        part1["degenerate_states"]["original_unparseable"] == 2
        and part1["degenerate_states"]["repair_unparseable"] == 0
        and part1["degenerate_states"]["sample_unparseable"] == 0
        and part1["blinded_sample"]["parseable"] == 36
        and part1["blinded_sample"]["naturally_stopped"] == 36
        and not part1["mapping_opened"]
    )
    generation = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    passing = (
        len(surface) == 320
        and len({item["blind_id"] for item in surface}) == 320
        and partial_valid
        and early_mapping_rejected
        and prompt_replay
        and parseable
        and exact_reproduction
        and gpu_only
        and part1_positive
        and generation["validation"]["pass"]
        and generation["answers_sha256"] == ANSWERS_SHA256
        and all(lv005._reachability().values())
    )
    result = {
        "schema": "lv006-preflight-v1",
        "status": "PASS" if passing else "FAIL",
        "pf1": {"anchors": anchors, "surface_rows": len(surface), "partial_rows": len(partial)},
        "pf2": {"exact_failed_repair_response_sha256": response_sha, "part1_response_sha256": expected_response_sha, "exact_reproduction": exact_reproduction, "repair_suffix": REPAIR_SUFFIX},
        "pf3": {"registration_before_implementation": True, "early_mapping_rejected": early_mapping_rejected, "append_flush_fsync": True},
        "pf4": {"dispositions": lv005._reachability(), "part1_positive_control": part1_positive},
        "pf5": {"surface_unique": len({item["blind_id"] for item in surface}) == 320, "partial_schedule_valid": partial_valid, "expected_repaired_judgments": len(expected_keys(surface))},
        "pf6": {"repaired_prompt_digest_replay": prompt_replay, "prompt_digest_sha256": hashlib.sha256("".join(prompts_a).encode()).hexdigest()},
        "pf7": {"byte_identical": response_a["text"].encode() == response_b["text"].encode(), "parseable": parseable, "naturally_stopped": response_a["done_reason"] != "length" and response_b["done_reason"] != "length", "gpu_only": gpu_only, "ollama_process": process},
        "pf8": {"reader_replicates": 5, "primary_items": 16, "power_unchanged": True},
        "pf9": {"residuals": ["repaired cue can alter judge verdict", "same-model judge bias"], "single_repaired_instrument_for_all": True},
        "pf10": {"sealed_live_answers": 340, "judgment_is_measurement": True},
        "calls": {"preflight_judge": 2},
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV006LiveError("Preflight failed")
    return result


def run_judging() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(SURFACE) != SURFACE_SHA256:
        raise LV006LiveError("passing Preflight and frozen surface required")
    if JUDGMENTS.exists():
        raise LV006LiveError("repaired judgments exist; rerun forbidden")
    surface = _surface_rows()
    JUDGMENTS.parent.mkdir(parents=True, exist_ok=True)
    calls = 0
    with JUDGMENTS.open("x", encoding="utf-8", newline="\n") as handle:
        for item in surface:
            prompt = repaired_prompt(item)
            for judge_pass, seed in enumerate(JUDGE_SEEDS):
                response = _generate(prompt, seed, judge=True)
                verdict, reason = parse_judge_verdict(response["text"])
                if response["done_reason"] == "length":
                    raise LV006LiveError("repaired judge truncated")
                _append_fsynced(handle, {"blind_id": item["blind_id"], "judge_pass": judge_pass, "seed": seed, "verdict": verdict, "reason": reason, "done_reason": response["done_reason"], "response_sha256": hashlib.sha256(response["text"].encode()).hexdigest()})
                calls += 1
    rows = _read_jsonl(JUDGMENTS)
    validation = validate_judgments(rows, surface)
    summary = {"schema": "lv006-judgment-summary-v1", "judgments_sha256": sha256_file(JUDGMENTS), "calls": calls, "validation": validation}
    _write_json(JUDGMENT_SUMMARY, summary)
    if not validation["pass"]:
        raise LV006LiveError("repaired judgment completeness failed")
    return summary


def analyze() -> dict[str, Any]:
    _load_mapping()
    summary = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"]:
        raise LV006LiveError("complete repaired judgments required")
    prior = {
        "JUDGMENTS": lv005.JUDGMENTS,
        "JUDGMENT_SUMMARY": lv005.JUDGMENT_SUMMARY,
        "RESULT": lv005.RESULT,
        "PER_ITEM": lv005.PER_ITEM,
    }
    try:
        lv005.JUDGMENTS = JUDGMENTS
        lv005.JUDGMENT_SUMMARY = JUDGMENT_SUMMARY
        lv005.RESULT = RESULT
        lv005.PER_ITEM = PER_ITEM
        result = lv005.analyze()
    finally:
        for name, value in prior.items():
            setattr(lv005, name, value)
    result["schema"] = "lv006-result-v1"
    result["instrument_repair"] = {"suffix": REPAIR_SUFFIX, "original_partial_reused": 0, "repaired_judgments": 960}
    result["calls"] = {"reused_reader": 340, "repaired_judge": 960, "repair_preflight_judge": 2, "repair_exploration_judge": 40}
    _write_json(RESULT, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "judge", "analyze"))
    args = parser.parse_args()
    actions = {"preflight": run_preflight, "judge": run_judging, "analyze": analyze}
    print(json.dumps(actions[args.phase](), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
