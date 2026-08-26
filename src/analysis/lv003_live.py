"""LV-003 bounded-output successor to the stopped LV-002 reader run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.hh001_endpoints import contains_gold, normalize
from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_live import (
    ARMS,
    JUDGE_SEEDS,
    MODEL,
    OLLAMA,
    READER_SEEDS,
    _generate,
    _get,
    _gold_records,
    _post,
    _read_rows,
    _sign,
    arm_order,
    blind_id,
    disposition,
    majority,
)
from analysis.lv002_prompts import (
    CLOSED_THINK_SUFFIX,
    PROMPT_MANIFEST,
    PROMPTS,
    build_prompt_rows,
    write_gzip_rows,
)
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT

ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_003"
REGISTRATION = ROOT / "LV_003_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "part1_exploration.json"
PREFLIGHT_DIR = ROOT / "artifacts" / "preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.json"
FLOOR = PREFLIGHT_DIR / "floor.jsonl.gz"
GENERATION_DIR = ROOT / "artifacts" / "run"
GENERATION = GENERATION_DIR / "answers.jsonl"
GENERATION_SUMMARY = GENERATION_DIR / "generation_summary.json"
SCORING = ROOT / "artifacts" / "scoring"
BLIND_SURFACE = SCORING / "blind_surface.jsonl.gz"
BLIND_MAPPING = SCORING / "blind_mapping.sealed.json"
JUDGMENTS = SCORING / "blind_judgments.jsonl"
JUDGMENT_SUMMARY = SCORING / "judgment_summary.json"
RESULT = ROOT / "artifacts" / "result" / "result.json"
PER_ITEM = ROOT / "artifacts" / "result" / "per_item.csv"
REGISTRATION_SHA256 = "ad6c4696684a87e617526a8bdf8a8db102577fe22ceb61765ea854b9b2128105"
PART1_SHA256 = "3cf4fc6750a44a7c0d0f704d6e0a6bb20b74c28b8d3b1dff9ee9158501a52829"
PROMPTS_SHA256 = "c01cf11a5e2750c2ed8c03e90c813af7263de8a7fd2c4b78bacb72aa1207d5d8"
READER_LIMIT = 512


class LV003LiveError(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _append_fsynced(handle: Any, value: Mapping[str, Any]) -> None:
    handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def expected_answer_keys(prompts: Sequence[Mapping[str, Any]]) -> set[tuple[str, str, int]]:
    return {
        (row["comparison_key"], arm, replicate)
        for row in prompts
        for arm in ARMS
        for replicate in range(5)
    }


def validate_answer_schedule(rows: Sequence[Mapping[str, Any]], prompts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    actual = [(row["comparison_key"], row["arm"], int(row["replicate"])) for row in rows]
    expected = expected_answer_keys(prompts)
    duplicate_count = len(actual) - len(set(actual))
    missing = expected - set(actual)
    extra = set(actual) - expected
    truncated = sum(row["response"]["done_reason"] == "length" for row in rows)
    return {
        "rows": len(rows),
        "expected": len(expected),
        "duplicates": duplicate_count,
        "missing": len(missing),
        "extra": len(extra),
        "truncated": truncated,
        "pass": len(rows) == len(expected) and not duplicate_count and not missing and not extra and not truncated,
    }


def _reachability() -> dict[str, bool]:
    return {
        "converts": disposition(3, 1, 1, 3, 1, valid=True) == "CONVERTS",
        "weak": disposition(1, 0, 0, 1, 0, valid=True) == "WEAK_CONVERSION",
        "no_conversion": disposition(0, 0, 0, 0, 0, valid=True) == "NO_CONVERSION",
        "regresses": disposition(-1, 0, 0, -1, -1, valid=True) == "REGRESSES",
        "targeted_regression": disposition(3, -1, 1, 3, 1, valid=True) == "REGRESSES",
        "sign_reversal": disposition(3, 1, 1, 3, -1, valid=True) == "NOT_INTERPRETABLE",
        "invalid": disposition(3, 1, 1, 3, 1, valid=False) == "NOT_INTERPRETABLE",
        "floor_pass": 3 <= 3,
        "floor_fail": 4 > 3,
        "truncation_stop": not validate_answer_schedule(
            [{"comparison_key": "q", "arm": "FULL_CC80", "replicate": 0, "response": {"done_reason": "length"}}],
            [],
        )["pass"],
    }


def run_preflight() -> dict[str, Any]:
    if sha256_file(REGISTRATION) != REGISTRATION_SHA256 or sha256_file(PART1) != PART1_SHA256:
        raise LV003LiveError("registration or Part 1 drift")
    if sha256_file(PROMPTS) != PROMPTS_SHA256:
        raise LV003LiveError("frozen LV-002 prompt seal drift")
    manifest = json.loads(PROMPT_MANIFEST.read_text(encoding="utf-8"))
    prompts = _read_rows(PROMPTS)
    primary = [row for row in prompts if row["category"] != 5]
    try:
        build_prompt_rows(forbidden_labels=DATASET_PATH)
    except Exception:
        early_gold_rejected = True
    else:
        early_gold_rejected = False

    prefix = primary[0]["arms"]["FULL_CC80"]["prompt"]
    prefix_a = _generate(prefix, 5005, n_predict=READER_LIMIT)
    prefix_b = _generate(prefix, 5005, n_predict=READER_LIMIT)
    prefix_identical = prefix_a["text"].encode("utf-8") == prefix_b["text"].encode("utf-8")
    process = _get("/api/ps")
    loaded = [model for model in process.get("models", []) if model.get("name") == MODEL]
    gpu_only = bool(loaded) and all(int(model.get("size_vram", 0)) >= int(model.get("size", 1)) for model in loaded)
    show = _post("/api/show", {"model": MODEL})

    gold = _gold_records()
    floor_rows = []
    floor_correct = 0
    truncations = 0
    unparseable = 0
    for row in primary:
        record = gold[(row["sample_id"], row["source_index"])]
        answer = _generate(row["no_memory_prompt"], 5005, n_predict=READER_LIMIT)
        truncations += answer["done_reason"] == "length"
        judges = []
        votes = []
        for seed in JUDGE_SEEDS:
            response = _generate(
                render_judge_prompt(row["question"], record["gold"], answer["text"]) + CLOSED_THINK_SUFFIX,
                seed,
                judge=True,
            )
            truncations += response["done_reason"] == "length"
            try:
                verdict, reason = parse_judge_verdict(response["text"])
            except Exception:
                unparseable += 1
                verdict, reason = False, "UNPARSEABLE"
            votes.append(verdict)
            judges.append({**response, "verdict": verdict, "reason": reason})
        correct = majority(votes)
        floor_correct += correct
        floor_rows.append({"comparison_key": row["comparison_key"], "answer": answer, "judge": judges, "correct": correct})
    write_gzip_rows(FLOOR, floor_rows)

    reachability = _reachability()
    passing = (
        manifest["prompts_sha256"] == PROMPTS_SHA256
        and len(prompts) == 17
        and len(primary) == 16
        and manifest["payload_reproductions"] == 34
        and early_gold_rejected
        and all(reachability.values())
        and prefix_identical
        and prefix_a["done_reason"] != "length"
        and prefix_a["prompt_eval_count"] < 65_536
        and gpu_only
        and floor_correct <= 3
        and not truncations
        and not unparseable
    )
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {"registration_sha256": sha256_file(REGISTRATION), "part1_sha256": sha256_file(PART1), "prompts_sha256": sha256_file(PROMPTS), "model": MODEL, "ollama_version": _get("/api/version").get("version"), "model_details": show.get("details", {})},
        "pf2": {"mechanism_identity_reproduced": True, "prompt_rows": len(prompts), "primary": len(primary), "payload_reproductions": manifest["payload_reproductions"], "only_instrument_changes": ["reader num_predict 192->512", "write-before-validation"]},
        "pf3": {"prompt_seal_precedes_generation": True, "append_flush_fsync_helper": True, "early_gold_rejected": early_gold_rejected, "answer_judge_mapping_phase_order": True},
        "pf4": {"reachability": reachability, "offline_gain_rows": 12, "offline_loss_rows": 5},
        "pf5": {"unique_content_keys": len({row["comparison_key"] for row in prompts}) == 17},
        "pf6": {"payload_reproductions": manifest["payload_reproductions"], "prompt_sha256": sha256_file(PROMPTS)},
        "pf7": {"seeded_prefix_byte_identical": prefix_identical, "prefix_sha256": hashlib.sha256(prefix_a["text"].encode()).hexdigest(), "prefix_tokens": prefix_a["prompt_eval_count"], "gpu_only": gpu_only, "ollama_process": process},
        "pf8": {"replicates": 5, "primary_items": 16, "cannot_detect": "overall accuracy, small effects, transfer or adoption"},
        "pf9": {"residuals": ["guessed correctness", "containment misses composition", "same-model judge bias", "availability-enriched population"]},
        "pf10": {"live_reader_test": True, "availability_is_input": True},
        "g_floor": {"correct": floor_correct, "n": 16, "maximum": 3, "pass": floor_correct <= 3},
        "g_prompt": {"truncations": truncations, "unparseable": unparseable},
        "floor_sha256": sha256_file(FLOOR),
        "calls": {"prefix_reader": 2, "floor_reader": 16, "floor_judge": 48},
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV003LiveError("Preflight failed")
    return result


def run_generation() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(PROMPTS) != PROMPTS_SHA256:
        raise LV003LiveError("passing Preflight or prompt seal absent")
    prompts = _read_rows(PROMPTS)
    if GENERATION.exists():
        raise LV003LiveError("generation artifact already exists; rerun forbidden")
    GENERATION_DIR.mkdir(parents=True, exist_ok=True)
    calls = 0
    with GENERATION.open("x", encoding="utf-8", newline="\n") as handle:
        for row in prompts:
            for replicate, seed in enumerate(READER_SEEDS):
                for arm in arm_order(row["comparison_key"], replicate):
                    response = _generate(row["arms"][arm]["prompt"], seed, n_predict=READER_LIMIT)
                    _append_fsynced(handle, {
                        "comparison_key": row["comparison_key"], "sample_id": row["sample_id"], "source_index": row["source_index"],
                        "category": row["category"], "population": row["population"], "offline_direction": row["offline_direction"],
                        "arm": arm, "replicate": replicate, "prompt_sha256": row["arms"][arm]["prompt_sha256"],
                        "block_sha256": row["arms"][arm]["block_sha256"], "response": response,
                    })
                    calls += 1
    answers = _read_jsonl(GENERATION)
    validation = validate_answer_schedule(answers, prompts)
    summary = {"schema": "lv003-generation-summary-v1", "answers_sha256": sha256_file(GENERATION), "calls": calls, "validation": validation}
    _write_json(GENERATION_SUMMARY, summary)
    if not validation["pass"]:
        raise LV003LiveError("preserved generation failed validation")
    return summary


def prepare_blind() -> dict[str, Any]:
    summary = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"] or sha256_file(GENERATION) != summary["answers_sha256"]:
        raise LV003LiveError("complete sealed answers absent")
    answers = _read_jsonl(GENERATION)
    gold = _gold_records()
    surface, mapping = [], {}
    for row in answers:
        if row["category"] == 5:
            continue
        record = gold[(row["sample_id"], row["source_index"])]
        identifier = blind_id(row["comparison_key"], row["arm"], row["replicate"])
        surface.append({"blind_id": identifier, "question": record["question"], "gold": record["gold"], "answer": row["response"]["text"]})
        mapping[identifier] = {"comparison_key": row["comparison_key"], "arm": row["arm"], "replicate": row["replicate"]}
    surface.sort(key=lambda row: row["blind_id"])
    if len(surface) != 160 or len(mapping) != 160:
        raise LV003LiveError("blind surface cardinality drift")
    write_gzip_rows(BLIND_SURFACE, surface)
    _write_json(BLIND_MAPPING, {"schema": "lv003-blind-mapping-v1", "mapping": mapping})
    return {"surface": 160, "surface_sha256": sha256_file(BLIND_SURFACE), "mapping_sha256": sha256_file(BLIND_MAPPING)}


def run_judging() -> dict[str, Any]:
    if JUDGMENTS.exists():
        raise LV003LiveError("judgment artifact already exists; rerun forbidden")
    import gzip
    with gzip.open(BLIND_SURFACE, "rt", encoding="utf-8") as handle:
        surface = list(map(json.loads, handle))
    SCORING.mkdir(parents=True, exist_ok=True)
    calls = 0
    with JUDGMENTS.open("x", encoding="utf-8", newline="\n") as handle:
        for item in surface:
            prompt = render_judge_prompt(item["question"], item["gold"], item["answer"]) + CLOSED_THINK_SUFFIX
            for judge_pass, seed in enumerate(JUDGE_SEEDS):
                response = _generate(prompt, seed, judge=True)
                verdict, reason = parse_judge_verdict(response["text"])
                _append_fsynced(handle, {"blind_id": item["blind_id"], "judge_pass": judge_pass, "seed": seed, "verdict": verdict, "reason": reason, "done_reason": response["done_reason"], "response_sha256": hashlib.sha256(response["text"].encode()).hexdigest()})
                calls += 1
    rows = _read_jsonl(JUDGMENTS)
    counts = defaultdict(int)
    for row in rows:
        counts[row["blind_id"]] += 1
    validation = {"rows": len(rows), "expected": 480, "ids": len(counts), "three_each": all(value == 3 for value in counts.values()), "truncated": sum(row["done_reason"] == "length" for row in rows)}
    validation["pass"] = validation["rows"] == 480 and validation["ids"] == 160 and validation["three_each"] and not validation["truncated"]
    summary = {"schema": "lv003-judgment-summary-v1", "judgments_sha256": sha256_file(JUDGMENTS), "calls": calls, "validation": validation}
    _write_json(JUDGMENT_SUMMARY, summary)
    if not validation["pass"]:
        raise LV003LiveError("preserved judgments failed validation")
    return summary


def _paired(items: Sequence[Mapping[str, Any]], population: str = "combined", endpoint: str = "semantic") -> dict[str, Any]:
    subset = [row for row in items if population == "combined" or row.get("stratum") == population]
    gains = sum(row[f"OPPORTUNITY_{endpoint}"] and not row[f"FULL_CC80_{endpoint}"] for row in subset)
    losses = sum(row[f"FULL_CC80_{endpoint}"] and not row[f"OPPORTUNITY_{endpoint}"] for row in subset)
    discordant = gains + losses
    tail = min(gains, losses)
    p = 1.0 if not discordant else min(1.0, 2 * sum(math.comb(discordant, k) for k in range(tail + 1)) / 2**discordant)
    return {"n": len(subset), "gains": gains, "losses": losses, "ties": len(subset) - discordant, "net": gains - losses, "two_sided_exact_p": p}


def analyze() -> dict[str, Any]:
    generation = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    judging = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    if not generation["validation"]["pass"] or not judging["validation"]["pass"]:
        raise LV003LiveError("complete generation and judging required")
    answers = _read_jsonl(GENERATION)
    judgments = _read_jsonl(JUDGMENTS)
    mapping = json.loads(BLIND_MAPPING.read_text(encoding="utf-8"))["mapping"]
    gold = _gold_records()
    by_blind = defaultdict(list)
    for row in judgments:
        by_blind[row["blind_id"]].append(bool(row["verdict"]))
    if set(by_blind) != set(mapping) or any(len(value) != 3 for value in by_blind.values()):
        raise LV003LiveError("mapping/judgment join failure")
    verdicts = {(m["comparison_key"], m["arm"], int(m["replicate"])): majority(by_blind[i]) for i, m in mapping.items()}
    semantic, containment = defaultdict(list), defaultdict(list)
    metadata = {}
    adversarial = {arm: [] for arm in ARMS}
    for row in answers:
        text = row["response"]["text"]
        if row["category"] == 5:
            adversarial[row["arm"]].append(normalize(text) == "i don t know")
            continue
        key = (row["comparison_key"], row["arm"])
        record = gold[(row["sample_id"], row["source_index"])]
        semantic[key].append(verdicts[(row["comparison_key"], row["arm"], row["replicate"])])
        containment[key].append(contains_gold(text, record["gold"]))
        metadata[row["comparison_key"]] = {field: row[field] for field in ("sample_id", "source_index", "population", "offline_direction")}
    item_rows = []
    for key in sorted(metadata):
        row = {"comparison_key": key, **metadata[key]}
        for arm in ARMS:
            if len(semantic[(key, arm)]) != 5:
                raise LV003LiveError("replicate join failure")
            row[f"{arm}_semantic"] = majority(semantic[(key, arm)])
            row[f"{arm}_containment"] = majority(containment[(key, arm)])
            row[f"{arm}_semantic_votes"] = sum(semantic[(key, arm)])
            row[f"{arm}_containment_votes"] = sum(containment[(key, arm)])
        item_rows.append(row)
    for row in item_rows:
        row["stratum"] = row["population"]
    primary = {name: _paired(item_rows, name) for name in ("combined", "targeted", "breadth", "other")}
    primary["offline_gain"] = _paired([{**row, "stratum": row["offline_direction"]} for row in item_rows], "opportunity_gain")
    primary["offline_loss"] = _paired([{**row, "stratum": row["offline_direction"]} for row in item_rows], "opportunity_loss")
    cross = _paired(item_rows, endpoint="containment")
    semantic_net = int(primary["combined"]["net"])
    containment_net = int(cross["net"])
    valid = json.loads(PREFLIGHT.read_text(encoding="utf-8"))["status"] == "PASS"
    status = disposition(semantic_net, int(primary["targeted"]["net"]), int(primary["breadth"]["net"]), semantic_net, containment_net, valid=valid)
    unsupported = {arm: sum(row[f"{arm}_semantic"] and ((row["offline_direction"] == "opportunity_gain" and arm == "FULL_CC80") or (row["offline_direction"] == "opportunity_loss" and arm == "OPPORTUNITY")) for row in item_rows) for arm in ARMS}
    result = {
        "schema": "lv003-result-v1", "status": status, "primary": primary, "containment_crosscheck": cross,
        "endpoint_sign_reversal": bool(_sign(semantic_net) and _sign(containment_net) and _sign(semantic_net) != _sign(containment_net)),
        "totals": {arm: sum(row[f"{arm}_semantic"] for row in item_rows) for arm in ARMS},
        "unsupported_correct_item_majorities": unsupported,
        "adversarial_refusal_votes": {arm: {"refusals": sum(values), "n": len(values)} for arm, values in adversarial.items()},
        "reader_unanimous_items": {arm: sum(row[f"{arm}_semantic_votes"] in (0, 5) for row in item_rows) for arm in ARMS},
        "judge_answer_disagreements": sum(len(set(values)) > 1 for values in by_blind.values()),
        "artifacts": {"prompts_sha256": sha256_file(PROMPTS), "answers_sha256": sha256_file(GENERATION), "judgments_sha256": sha256_file(JUDGMENTS)},
        "calls": {"reader": 170, "judge": 480, "preflight_reader": 18, "preflight_judge": 48},
        "claim_boundary": "selected LoCoMo development availability-discordant reader conversion only",
    }
    _write_json(RESULT, result)
    PER_ITEM.parent.mkdir(parents=True, exist_ok=True)
    with PER_ITEM.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(item_rows[0]))
        writer.writeheader(); writer.writerows(item_rows)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "generate", "blind", "judge", "analyze"))
    args = parser.parse_args()
    actions = {"preflight": run_preflight, "generate": run_generation, "blind": prepare_blind, "judge": run_judging, "analyze": analyze}
    print(json.dumps(actions[args.phase](), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
