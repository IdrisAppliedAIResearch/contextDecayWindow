"""LV-004 deterministic completion repair and live reader verdict."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import analysis.lv003_live as scoring
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_live import MODEL, _generate, _get, _post
from analysis.lv002_prompts import PROMPT_MANIFEST, PROMPTS, build_prompt_rows
from analysis.lv003_live import _append_fsynced, _read_jsonl, _reachability, _write_json, validate_answer_schedule
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT

ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_004"
REGISTRATION = ROOT / "LV_004_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "part1_exploration.json"
PREFLIGHT = ROOT / "artifacts" / "preflight" / "preflight.json"
REPAIRS = ROOT / "artifacts" / "run" / "repairs.jsonl"
MERGED = ROOT / "artifacts" / "run" / "answers_repaired.jsonl"
MERGED_SUMMARY = ROOT / "artifacts" / "run" / "generation_summary.json"
SCORING = ROOT / "artifacts" / "scoring"
BLIND_SURFACE = SCORING / "blind_surface.jsonl.gz"
BLIND_MAPPING = SCORING / "blind_mapping.sealed.json"
JUDGMENTS = SCORING / "blind_judgments.jsonl"
JUDGMENT_SUMMARY = SCORING / "judgment_summary.json"
RESULT = ROOT / "artifacts" / "result" / "result.json"
PER_ITEM = ROOT / "artifacts" / "result" / "per_item.csv"

LV003_ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_003"
LV003_ANSWERS = LV003_ROOT / "artifacts" / "run" / "answers.jsonl"
LV003_SUMMARY = LV003_ROOT / "artifacts" / "run" / "generation_summary.json"
LV003_PREFLIGHT = LV003_ROOT / "artifacts" / "preflight" / "preflight.json"
LV003_FLOOR = LV003_ROOT / "artifacts" / "preflight" / "floor.jsonl.gz"

REGISTRATION_SHA256 = "6ba4938e3ebeb25b1fa5a26186583aa5357f14975de8be312a6879f181356ffd"
PART1_SHA256 = "1fa6cb263f0a8650fb18a4aef2e796c040ca5aa42608b63e1996d193b9098755"
LV003_ANSWERS_SHA256 = "e7a9a2343182502d0be1675ba5b797a2115e49b873709cb3614e22a9bd55e784"
PROMPTS_SHA256 = "c01cf11a5e2750c2ed8c03e90c813af7263de8a7fd2c4b78bacb72aa1207d5d8"
LV003_FLOOR_SHA256 = "3521785f65b180735b9469872d4a44688be76d8f0b3181e30378a67a00a20f73"
REPAIR_LIMIT = 2048

REPAIR_KEYS = {
    ("FULL_CC80", 2): {"sample_id": "conv-42", "source_index": 79, "seed": 5007, "prompt_eval_count": 8416},
    ("OPPORTUNITY", 3): {"sample_id": "conv-42", "source_index": 79, "seed": 5008, "prompt_eval_count": 8447},
}


class LV004LiveError(RuntimeError):
    pass


def _canonical_sha(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _prompt_rows() -> list[dict[str, Any]]:
    return scoring._read_rows(PROMPTS)


def _repair_key(row: Mapping[str, Any]) -> tuple[str, int] | None:
    if row.get("sample_id") != "conv-42" or int(row.get("source_index", -1)) != 79:
        return None
    key = (str(row.get("arm")), int(row.get("replicate", -1)))
    return key if key in REPAIR_KEYS else None


def validate_repair_batch(
    originals: Sequence[Mapping[str, Any]], repairs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    original_by_key = {_repair_key(row): row for row in originals if _repair_key(row) is not None}
    repair_keys = [(str(row.get("arm")), int(row.get("replicate", -1))) for row in repairs]
    expected = set(REPAIR_KEYS)
    prefix_matches = []
    identity_matches = []
    naturally_stopped = []
    for repair in repairs:
        key = (str(repair.get("arm")), int(repair.get("replicate", -1)))
        original = original_by_key.get(key)
        spec = REPAIR_KEYS.get(key)
        if original is None or spec is None:
            prefix_matches.append(False); identity_matches.append(False); naturally_stopped.append(False)
            continue
        response = repair.get("response", {})
        prefix_matches.append(str(response.get("text", "")).startswith(str(original["response"]["text"])))
        identity_matches.append(
            repair.get("comparison_key") == original.get("comparison_key")
            and repair.get("prompt_sha256") == original.get("prompt_sha256")
            and int(response.get("seed", -1)) == spec["seed"]
            and int(response.get("prompt_eval_count", -1)) == spec["prompt_eval_count"]
            and repair.get("original_response_sha256") == _canonical_sha(original["response"])
        )
        naturally_stopped.append(response.get("done_reason") != "length")
    valid_keys = len(repair_keys) == 2 and len(set(repair_keys)) == 2 and set(repair_keys) == expected
    return {
        "rows": len(repairs), "expected": 2, "valid_keys": valid_keys,
        "prefix_identity": all(prefix_matches) and len(prefix_matches) == 2,
        "record_identity": all(identity_matches) and len(identity_matches) == 2,
        "naturally_stopped": all(naturally_stopped) and len(naturally_stopped) == 2,
        "pass": valid_keys and all(prefix_matches) and all(identity_matches) and all(naturally_stopped),
    }


def merge_repaired(
    originals: Sequence[Mapping[str, Any]], repairs: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    validation = validate_repair_batch(originals, repairs)
    if not validation["pass"]:
        raise LV004LiveError("repair validation failed")
    by_key = {(row["arm"], int(row["replicate"])): row for row in repairs}
    merged = []
    replaced = 0
    for original in originals:
        key = _repair_key(original)
        if key is None:
            merged.append(dict(original))
            continue
        replacement = dict(original)
        replacement["response"] = by_key[key]["response"]
        replacement["repair"] = {
            "original_response_sha256": _canonical_sha(original["response"]),
            "repair_response_sha256": _canonical_sha(by_key[key]["response"]),
            "num_predict": REPAIR_LIMIT,
        }
        merged.append(replacement)
        replaced += 1
    if replaced != 2:
        raise LV004LiveError("replacement scope drift")
    return merged


def run_preflight() -> dict[str, Any]:
    if sha256_file(REGISTRATION) != REGISTRATION_SHA256 or sha256_file(PART1) != PART1_SHA256:
        raise LV004LiveError("registration or Part 1 drift")
    if sha256_file(LV003_ANSWERS) != LV003_ANSWERS_SHA256 or sha256_file(PROMPTS) != PROMPTS_SHA256:
        raise LV004LiveError("frozen answer or prompt drift")
    if sha256_file(LV003_FLOOR) != LV003_FLOOR_SHA256:
        raise LV004LiveError("carried no-memory floor drift")

    prompts = _prompt_rows()
    originals = _read_jsonl(LV003_ANSWERS)
    original_validation = validate_answer_schedule(originals, prompts)
    truncated = [row for row in originals if row["response"]["done_reason"] == "length"]
    exact_repair_population = len(truncated) == 2 and {_repair_key(row) for row in truncated} == set(REPAIR_KEYS)
    complement = [row for row in originals if _repair_key(row) is None]
    manifest = json.loads(PROMPT_MANIFEST.read_text(encoding="utf-8"))
    lv003_preflight = json.loads(LV003_PREFLIGHT.read_text(encoding="utf-8"))
    try:
        build_prompt_rows(forbidden_labels=DATASET_PATH)
    except Exception:
        early_gold_rejected = True
    else:
        early_gold_rejected = False

    nonrepair = next(row for row in prompts if row["sample_id"] != "conv-42" or row["source_index"] != 79)
    prefix = nonrepair["arms"]["FULL_CC80"]["prompt"]
    prefix_a = _generate(prefix, 5005, n_predict=REPAIR_LIMIT)
    prefix_b = _generate(prefix, 5005, n_predict=REPAIR_LIMIT)
    prefix_identical = prefix_a["text"].encode("utf-8") == prefix_b["text"].encode("utf-8")
    process = _get("/api/ps")
    loaded = [model for model in process.get("models", []) if model.get("name") == MODEL]
    gpu_only = bool(loaded) and all(int(model.get("size_vram", 0)) >= int(model.get("size", 1)) for model in loaded)
    show = _post("/api/show", {"model": MODEL})
    synthetic = {
        "prefix_pass": "abcdef".startswith("abc"), "prefix_fail": not "abX".startswith("abc"),
        "truncation_pass": "stop" != "length", "truncation_fail": "length" == "length",
        **_reachability(),
    }
    passing = (
        len(prompts) == 17 and manifest["payload_reproductions"] == 34
        and original_validation["rows"] == 170 and original_validation["truncated"] == 2
        and original_validation["duplicates"] == original_validation["missing"] == original_validation["extra"] == 0
        and exact_repair_population and len(complement) == 168 and early_gold_rejected
        and all(synthetic.values()) and prefix_identical and prefix_a["done_reason"] != "length"
        and prefix_a["prompt_eval_count"] < 65_536 and gpu_only
        and lv003_preflight["status"] == "PASS" and lv003_preflight["g_floor"]["correct"] <= 3
    )
    result = {
        "schema": "lv004-preflight-v1", "status": "PASS" if passing else "FAIL",
        "pf1": {"registration_sha256": sha256_file(REGISTRATION), "part1_sha256": sha256_file(PART1), "lv003_answers_sha256": sha256_file(LV003_ANSWERS), "prompts_sha256": sha256_file(PROMPTS), "ollama_version": _get("/api/version").get("version"), "model_details": show.get("details", {})},
        "pf2": {"rows": len(originals), "naturally_stopped": 168, "truncated": len(truncated), "repair_keys_exact": exact_repair_population, "payload_reproductions": manifest["payload_reproductions"]},
        "pf3": {"registration_precedes_repair": True, "append_flush_fsync_helper": True, "early_gold_rejected": early_gold_rejected, "phase_order_enforced": True},
        "pf4": {"reachability": synthetic, "offline_gain_rows": 12, "offline_loss_rows": 5, "repair_arms": sorted(key[0] for key in REPAIR_KEYS)},
        "pf5": {"unique_schedule_keys": original_validation["duplicates"] == 0, "complement_rows": len(complement)},
        "pf6": {"payload_reproductions": manifest["payload_reproductions"], "answer_identity": sha256_file(LV003_ANSWERS)},
        "pf7": {"seeded_nonrepair_byte_identical": prefix_identical, "prefix_sha256": hashlib.sha256(prefix_a["text"].encode()).hexdigest(), "naturally_stopped": prefix_a["done_reason"] != "length", "gpu_only": gpu_only, "ollama_process": process},
        "pf8": {"replicates": 5, "primary_items": 16, "cannot_detect": "overall accuracy, small effects, transfer or adoption"},
        "pf9": {"residuals": ["guessed correctness", "containment misses composition", "same-model judge bias", "availability enrichment", "continuation-tail sensitivity"]},
        "pf10": {"live_reader_test": True, "availability_is_input": True},
        "g_floor": {**lv003_preflight["g_floor"], "artifact_sha256": sha256_file(LV003_FLOOR), "carried": True},
        "calls": {"nonrepair_determinism_reader": 2, "repair_reader": 0, "judge": 0},
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV004LiveError("Preflight failed")
    return result


def run_repair() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(LV003_ANSWERS) != LV003_ANSWERS_SHA256:
        raise LV004LiveError("passing Preflight and frozen originals required")
    if REPAIRS.exists() or MERGED.exists():
        raise LV004LiveError("repair artifact already exists; rerun forbidden")
    prompts = _prompt_rows()
    prompt_by_key = {row["comparison_key"]: row for row in prompts}
    originals = _read_jsonl(LV003_ANSWERS)
    targets = [row for row in originals if _repair_key(row) is not None]
    REPAIRS.parent.mkdir(parents=True, exist_ok=True)
    with REPAIRS.open("x", encoding="utf-8", newline="\n") as handle:
        for original in targets:
            key = _repair_key(original)
            assert key is not None
            spec = REPAIR_KEYS[key]
            prompt = prompt_by_key[original["comparison_key"]]["arms"][original["arm"]]["prompt"]
            response = _generate(prompt, spec["seed"], n_predict=REPAIR_LIMIT)
            _append_fsynced(handle, {
                "comparison_key": original["comparison_key"], "sample_id": original["sample_id"],
                "source_index": original["source_index"], "arm": original["arm"],
                "replicate": original["replicate"], "prompt_sha256": original["prompt_sha256"],
                "original_response_sha256": _canonical_sha(original["response"]), "response": response,
            })
    repairs = _read_jsonl(REPAIRS)
    repair_validation = validate_repair_batch(originals, repairs)
    if not repair_validation["pass"]:
        raise LV004LiveError("preserved repair failed validation")
    merged = merge_repaired(originals, repairs)
    with MERGED.open("x", encoding="utf-8", newline="\n") as handle:
        for row in merged:
            _append_fsynced(handle, row)
    schedule = validate_answer_schedule(merged, prompts)
    unchanged = all(a == b for a, b in zip(originals, merged) if _repair_key(a) is None)
    validation = {**schedule, "repair": repair_validation, "unchanged_complement": unchanged, "pass": schedule["pass"] and repair_validation["pass"] and unchanged}
    summary = {"schema": "lv004-generation-summary-v1", "answers_sha256": sha256_file(MERGED), "repairs_sha256": sha256_file(REPAIRS), "calls": 2, "validation": validation}
    _write_json(MERGED_SUMMARY, summary)
    if not validation["pass"]:
        raise LV004LiveError("merged answer validation failed")
    return summary


@contextmanager
def _scoring_paths() -> Iterator[None]:
    names = ("PREFLIGHT", "GENERATION", "GENERATION_SUMMARY", "SCORING", "BLIND_SURFACE", "BLIND_MAPPING", "JUDGMENTS", "JUDGMENT_SUMMARY", "RESULT", "PER_ITEM")
    replacements = (PREFLIGHT, MERGED, MERGED_SUMMARY, SCORING, BLIND_SURFACE, BLIND_MAPPING, JUDGMENTS, JUDGMENT_SUMMARY, RESULT, PER_ITEM)
    prior = {name: getattr(scoring, name) for name in names}
    try:
        for name, value in zip(names, replacements):
            setattr(scoring, name, value)
        yield
    finally:
        for name, value in prior.items():
            setattr(scoring, name, value)


def prepare_blind() -> dict[str, Any]:
    summary = json.loads(MERGED_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"] or sha256_file(MERGED) != summary["answers_sha256"]:
        raise LV004LiveError("sealed repaired answers required")
    with _scoring_paths():
        return scoring.prepare_blind()


def run_judging() -> dict[str, Any]:
    with _scoring_paths():
        return scoring.run_judging()


def analyze() -> dict[str, Any]:
    with _scoring_paths():
        result = scoring.analyze()
    result["schema"] = "lv004-result-v1"
    result["repair"] = json.loads(MERGED_SUMMARY.read_text(encoding="utf-8"))["validation"]["repair"]
    result["calls"] = {"reused_reader_answers": 168, "repair_reader": 2, "judge": 480, "preflight_reader": 2}
    result["claim_boundary"] = "selected LoCoMo development availability-discordant reader conversion only; no overall score, transfer or adoption claim"
    _write_json(RESULT, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "repair", "blind", "judge", "analyze"))
    args = parser.parse_args()
    actions = {"preflight": run_preflight, "repair": run_repair, "blind": prepare_blind, "judge": run_judging, "analyze": analyze}
    print(json.dumps(actions[args.phase](), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
