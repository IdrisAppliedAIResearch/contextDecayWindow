"""LV-005 preflight, live generation, blind judging, and analysis."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.hh001_endpoints import contains_gold, normalize
from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_live import JUDGE_SEEDS, MODEL, READER_SEEDS, _generate, _get, _gold_records, _post, majority
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX
from analysis.lv003_live import _append_fsynced, _read_jsonl, _write_json
from analysis.lv005_prompts import (
    AMENDMENT,
    AMENDMENT_SHA256,
    ARMS,
    LV004_ANSWERS,
    LV004_ANSWERS_SHA256,
    LV004_RESULT,
    LV004_RESULT_SHA256,
    PART1,
    PART1_SHA256,
    PROMPT_MANIFEST,
    PROMPTS,
    REGISTRATION,
    REGISTRATION_SHA256,
    ROOT,
    build_prompt_rows,
    write_gzip_rows,
)
from analysis.tc001_exploration import DATASET_PATH


PROMPTS_SHA256 = "d0a3ac38e15c1738387c9d3216de532195959dd4c8ac7515a03209bbfebe8b80"
READER_LIMIT = 2048
PREFLIGHT = ROOT / "artifacts" / "preflight" / "preflight.json"
FLOOR = ROOT / "artifacts" / "preflight" / "floor.jsonl.gz"
GENERATION = ROOT / "artifacts" / "run" / "answers.jsonl"
GENERATION_SUMMARY = ROOT / "artifacts" / "run" / "generation_summary.json"
SCORING = ROOT / "artifacts" / "scoring"
BLIND_SURFACE = SCORING / "blind_surface.jsonl.gz"
BLIND_MAPPING = SCORING / "blind_mapping.sealed.json"
JUDGMENTS = SCORING / "blind_judgments.jsonl"
JUDGMENT_SUMMARY = SCORING / "judgment_summary.json"
RESULT = ROOT / "artifacts" / "result" / "result.json"
PER_ITEM = ROOT / "artifacts" / "result" / "per_item.csv"

COMPARISONS = (
    ("GROUPED_vs_FLAT", "FLAT", "GROUPED"),
    ("GROUPED_CHRONO_vs_FLAT", "FLAT", "GROUPED_CHRONO"),
    ("TEMPORAL_GUIDANCE_vs_FLAT", "FLAT", "TEMPORAL_GUIDANCE"),
    ("CHRONO_INCREMENT", "GROUPED", "GROUPED_CHRONO"),
    ("GUIDANCE_INCREMENT", "GROUPED_CHRONO", "TEMPORAL_GUIDANCE"),
)


class LV005LiveError(RuntimeError):
    pass


def _prompt_rows() -> list[dict[str, Any]]:
    with gzip.open(PROMPTS, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def disposition(
    overall: int,
    targeted: int,
    breadth: int,
    semantic: int,
    containment: int,
    *,
    valid: bool,
) -> str:
    reversal = bool(_sign(semantic) and _sign(containment) and _sign(semantic) != _sign(containment))
    if not valid or reversal:
        return "NOT_INTERPRETABLE"
    if overall >= 3 and targeted >= 0 and breadth >= 0:
        return "PROMISING"
    if overall in (1, 2) and targeted >= 0 and breadth >= 0:
        return "WEAK_SIGNAL"
    if overall == 0 and targeted >= 0 and breadth >= 0:
        return "NO_SIGNAL"
    return "REGRESSES"


def _reachability() -> dict[str, bool]:
    return {
        "promising": disposition(3, 1, 1, 3, 1, valid=True) == "PROMISING",
        "weak": disposition(2, 1, 0, 2, 0, valid=True) == "WEAK_SIGNAL",
        "no_signal": disposition(0, 0, 0, 0, 0, valid=True) == "NO_SIGNAL",
        "regresses": disposition(-1, 0, 0, -1, -1, valid=True) == "REGRESSES",
        "targeted_guard": disposition(3, -1, 1, 3, 1, valid=True) == "REGRESSES",
        "breadth_guard": disposition(3, 1, -1, 3, 1, valid=True) == "REGRESSES",
        "sign_guard": disposition(3, 1, 1, 3, -1, valid=True) == "NOT_INTERPRETABLE",
        "invalid": disposition(3, 1, 1, 3, 1, valid=False) == "NOT_INTERPRETABLE",
    }


def arm_order(comparison_key: str, replicate: int) -> tuple[str, ...]:
    return tuple(
        sorted(
            ARMS,
            key=lambda arm: hashlib.sha256(
                f"{comparison_key}\0{replicate}\0{arm}".encode("utf-8")
            ).digest(),
        )
    )


def blind_id(comparison_key: str, arm: str, replicate: int) -> str:
    return hashlib.sha256(
        f"lv005-blind-v1\0{comparison_key}\0{arm}\0{replicate}".encode("utf-8")
    ).hexdigest()


def expected_answer_keys(prompts: Sequence[Mapping[str, Any]]) -> set[tuple[str, str, int]]:
    return {
        (row["comparison_key"], arm, replicate)
        for row in prompts
        for arm in ARMS
        for replicate in range(5)
    }


def validate_answer_schedule(
    rows: Sequence[Mapping[str, Any]], prompts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    actual = [(row["comparison_key"], row["arm"], int(row["replicate"])) for row in rows]
    expected = expected_answer_keys(prompts)
    return {
        "rows": len(rows),
        "expected": len(expected),
        "duplicates": len(actual) - len(set(actual)),
        "missing": len(expected - set(actual)),
        "extra": len(set(actual) - expected),
        "truncated": sum(row["response"]["done_reason"] == "length" for row in rows),
        "pass": len(rows) == len(expected)
        and len(actual) == len(set(actual))
        and set(actual) == expected
        and all(row["response"]["done_reason"] != "length" for row in rows),
    }


def _content_checks(prompts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    set_exact = order_changes = element_exact = 0
    child_earlier = child_later = singleton = paired = 0
    for row in prompts:
        flat = row["arms"]["FLAT"]
        flat_set = set(flat["selected_ids"])
        flat_hashes = flat["episode_element_sha256"]
        for arm in ARMS:
            value = row["arms"][arm]
            set_exact += set(value["emitted_ids"]) == flat_set and len(value["emitted_ids"]) == len(flat_set)
            element_exact += value["episode_element_sha256"] == flat_hashes
            if arm != "FLAT":
                order_changes += value["emitted_ids"] != flat["emitted_ids"]
        for group in row["arms"]["GROUPED_CHRONO"]["groups"]:
            if len(group["items"]) == 1:
                singleton += 1
            else:
                paired += 1
                first, second = group["items"]
                if first["role"] == "related_spread":
                    child_earlier += 1
                else:
                    child_later += 1
    return {
        "set_exact": set_exact,
        "expected_set_exact": len(prompts) * len(ARMS),
        "episode_elements_exact": element_exact,
        "expected_element_exact": len(prompts) * len(ARMS),
        "treatment_order_changes": order_changes,
        "expected_treatment_rows": len(prompts) * 3,
        "singleton_groups": singleton,
        "paired_groups": paired,
        "child_earlier_pairs": child_earlier,
        "child_later_pairs": child_later,
    }


def run_preflight() -> dict[str, Any]:
    anchors = {
        "registration": sha256_file(REGISTRATION) == REGISTRATION_SHA256,
        "amendment": sha256_file(AMENDMENT) == AMENDMENT_SHA256,
        "part1": sha256_file(PART1) == PART1_SHA256,
        "prompts": sha256_file(PROMPTS) == PROMPTS_SHA256,
        "lv004_answers": sha256_file(LV004_ANSWERS) == LV004_ANSWERS_SHA256,
        "lv004_result": sha256_file(LV004_RESULT) == LV004_RESULT_SHA256,
    }
    if not all(anchors.values()):
        raise LV005LiveError("registered input drift")
    prompts = _prompt_rows()
    manifest = json.loads(PROMPT_MANIFEST.read_text(encoding="utf-8"))
    primary = [row for row in prompts if row["category"] != 5]
    checks = _content_checks(prompts)
    try:
        build_prompt_rows(forbidden_labels=DATASET_PATH)
    except Exception:
        early_gold_rejected = True
    else:
        early_gold_rejected = False
    rebuilt, _ = build_prompt_rows()
    rebuild_identity = hashlib.sha256(
        json.dumps(rebuilt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest() == hashlib.sha256(
        json.dumps(prompts, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    prefix = primary[0]["arms"]["TEMPORAL_GUIDANCE"]["prompt"]
    prefix_a = _generate(prefix, 5005, n_predict=READER_LIMIT)
    prefix_b = _generate(prefix, 5005, n_predict=READER_LIMIT)
    prefix_identical = prefix_a["text"].encode("utf-8") == prefix_b["text"].encode("utf-8")
    process = _get("/api/ps")
    loaded = [model for model in process.get("models", []) if model.get("name") == MODEL]
    gpu_only = bool(loaded) and all(int(model.get("size_vram", 0)) >= int(model.get("size", 1)) for model in loaded)
    show = _post("/api/show", {"model": MODEL})

    gold = _gold_records()
    floor_rows = []
    floor_correct = truncations = unparseable = 0
    for row in primary:
        record = gold[(row["sample_id"], int(row["source_index"]))]
        answer = _generate(row["no_memory_prompt"], 5005, n_predict=READER_LIMIT)
        truncations += answer["done_reason"] == "length"
        votes, judges = [], []
        for seed in JUDGE_SEEDS:
            judged = _generate(
                render_judge_prompt(row["question"], record["gold"], answer["text"]) + CLOSED_THINK_SUFFIX,
                seed,
                judge=True,
            )
            truncations += judged["done_reason"] == "length"
            try:
                verdict, reason = parse_judge_verdict(judged["text"])
            except Exception:
                unparseable += 1
                verdict, reason = False, "UNPARSEABLE"
            votes.append(verdict)
            judges.append({**judged, "verdict": verdict, "reason": reason})
        correct = majority(votes)
        floor_correct += correct
        floor_rows.append({"comparison_key": row["comparison_key"], "answer": answer, "judges": judges, "correct": correct})
    write_gzip_rows(FLOOR, floor_rows)

    reachability = _reachability()
    maximum_chars = max(row["arms"][arm]["block_chars"] for row in prompts for arm in ARMS)
    passing = (
        len(prompts) == 17
        and len(primary) == 16
        and manifest["prompts"] == 68
        and manifest["control_reproductions"] == 17
        and checks["set_exact"] == checks["expected_set_exact"]
        and checks["episode_elements_exact"] == checks["expected_element_exact"]
        and checks["treatment_order_changes"] == checks["expected_treatment_rows"]
        and checks["singleton_groups"] > 0
        and checks["paired_groups"] > 0
        and checks["child_earlier_pairs"] > 0
        and checks["child_later_pairs"] > 0
        and early_gold_rejected
        and rebuild_identity
        and all(reachability.values())
        and prefix_identical
        and prefix_a["done_reason"] != "length"
        and prefix_a["prompt_eval_count"] < 65_536
        and gpu_only
        and floor_correct <= 3
        and truncations == 0
        and unparseable == 0
    )
    result = {
        "schema": "lv005-preflight-v1",
        "status": "PASS" if passing else "FAIL",
        "pf1": {"anchors": anchors, "model": MODEL, "ollama_version": _get("/api/version").get("version"), "model_details": show.get("details", {})},
        "pf2": {"prompt_rows": len(prompts), "primary": len(primary), "content_checks": checks, "control_reproductions": manifest["control_reproductions"], "maximum_block_chars": maximum_chars},
        "pf3": {"registration_before_renderer": True, "prompt_seal_before_answers": True, "append_flush_fsync": True, "early_gold_rejected": early_gold_rejected},
        "pf4": {"reachability": reachability, "singleton_groups": checks["singleton_groups"], "paired_groups": checks["paired_groups"]},
        "pf5": {"unique_questions": len({row["comparison_key"] for row in prompts}) == 17, "content_identity_sets": checks["set_exact"]},
        "pf6": {"control_reproductions": manifest["control_reproductions"], "independent_prompt_rebuild": rebuild_identity, "lv004_answers_sha256": sha256_file(LV004_ANSWERS), "lv004_result_sha256": sha256_file(LV004_RESULT)},
        "pf7": {"seeded_prefix_byte_identical": prefix_identical, "prefix_sha256": hashlib.sha256(prefix_a["text"].encode()).hexdigest(), "prompt_eval_count": prefix_a["prompt_eval_count"], "gpu_only": gpu_only, "ollama_process": process},
        "pf8": {"replicates": 5, "primary_items": 16, "cannot_detect": "overall accuracy, small effects, transfer or production behavior"},
        "pf9": {"residuals": ["related groups can join unrelated evidence", "later can be stale", "extra markup consumes prompt tokens", "complete evidence can be ignored", "same-model judge bias"]},
        "pf10": {"live_reader_probe": True, "rendering_is_not_verdict": True},
        "g_floor": {"correct": floor_correct, "n": len(primary), "maximum": 3, "pass": floor_correct <= 3, "artifact_sha256": sha256_file(FLOOR)},
        "g_complete": {"preflight_truncations": truncations, "unparseable": unparseable},
        "calls": {"determinism_reader": 2, "floor_reader": 16, "floor_judge": 48},
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV005LiveError("Preflight failed")
    return result


def run_generation() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(PROMPTS) != PROMPTS_SHA256:
        raise LV005LiveError("passing Preflight and frozen prompts required")
    if GENERATION.exists():
        raise LV005LiveError("generation artifact exists; rerun forbidden")
    prompts = _prompt_rows()
    GENERATION.parent.mkdir(parents=True, exist_ok=True)
    calls = 0
    with GENERATION.open("x", encoding="utf-8", newline="\n") as handle:
        for row in prompts:
            for replicate, seed in enumerate(READER_SEEDS):
                for arm in arm_order(row["comparison_key"], replicate):
                    response = _generate(row["arms"][arm]["prompt"], seed, n_predict=READER_LIMIT)
                    _append_fsynced(handle, {
                        "comparison_key": row["comparison_key"], "sample_id": row["sample_id"],
                        "source_index": row["source_index"], "category": row["category"],
                        "population": row["population"], "offline_direction": row["offline_direction"],
                        "arm": arm, "replicate": replicate,
                        "prompt_sha256": row["arms"][arm]["prompt_sha256"],
                        "block_sha256": row["arms"][arm]["block_sha256"], "response": response,
                    })
                    calls += 1
    answers = _read_jsonl(GENERATION)
    validation = validate_answer_schedule(answers, prompts)
    summary = {"schema": "lv005-generation-summary-v1", "answers_sha256": sha256_file(GENERATION), "calls": calls, "validation": validation}
    _write_json(GENERATION_SUMMARY, summary)
    if not validation["pass"]:
        raise LV005LiveError("generation completeness failed")
    return summary


def prepare_blind() -> dict[str, Any]:
    summary = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"] or sha256_file(GENERATION) != summary["answers_sha256"]:
        raise LV005LiveError("sealed complete answers required")
    answers = _read_jsonl(GENERATION)
    gold = _gold_records()
    surface, mapping = [], {}
    for row in answers:
        if row["category"] == 5:
            continue
        record = gold[(row["sample_id"], int(row["source_index"]))]
        identifier = blind_id(row["comparison_key"], row["arm"], int(row["replicate"]))
        surface.append({"blind_id": identifier, "question": record["question"], "gold": record["gold"], "answer": row["response"]["text"]})
        mapping[identifier] = {"comparison_key": row["comparison_key"], "arm": row["arm"], "replicate": row["replicate"]}
    surface.sort(key=lambda row: row["blind_id"])
    if len(surface) != 320 or len(mapping) != 320:
        raise LV005LiveError("blind cardinality drift")
    write_gzip_rows(BLIND_SURFACE, surface)
    _write_json(BLIND_MAPPING, {"schema": "lv005-blind-mapping-v1", "mapping": mapping})
    return {"surface": len(surface), "surface_sha256": sha256_file(BLIND_SURFACE), "mapping_sha256": sha256_file(BLIND_MAPPING)}


def run_judging() -> dict[str, Any]:
    if JUDGMENTS.exists():
        raise LV005LiveError("judgments exist; rerun forbidden")
    with gzip.open(BLIND_SURFACE, "rt", encoding="utf-8") as handle:
        surface = [json.loads(line) for line in handle if line.strip()]
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
    validation = {"rows": len(rows), "expected": 960, "ids": len(counts), "three_each": all(value == 3 for value in counts.values()), "truncated": sum(row["done_reason"] == "length" for row in rows)}
    validation["pass"] = validation["rows"] == 960 and validation["ids"] == 320 and validation["three_each"] and validation["truncated"] == 0
    summary = {"schema": "lv005-judgment-summary-v1", "judgments_sha256": sha256_file(JUDGMENTS), "calls": calls, "validation": validation}
    _write_json(JUDGMENT_SUMMARY, summary)
    if not validation["pass"]:
        raise LV005LiveError("judgment completeness failed")
    return summary


def _paired(
    items: Sequence[Mapping[str, Any]], baseline: str, treatment: str,
    population: str = "combined", endpoint: str = "semantic",
) -> dict[str, Any]:
    subset = [row for row in items if population == "combined" or row["population"] == population]
    gains = sum(row[f"{treatment}_{endpoint}"] and not row[f"{baseline}_{endpoint}"] for row in subset)
    losses = sum(row[f"{baseline}_{endpoint}"] and not row[f"{treatment}_{endpoint}"] for row in subset)
    discordant = gains + losses
    tail = min(gains, losses)
    p = 1.0 if not discordant else min(1.0, 2 * sum(math.comb(discordant, k) for k in range(tail + 1)) / 2**discordant)
    return {"n": len(subset), "gains": gains, "losses": losses, "ties": len(subset) - discordant, "net": gains - losses, "two_sided_exact_p": p}


def analyze() -> dict[str, Any]:
    generation = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    judging = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    if not generation["validation"]["pass"] or not judging["validation"]["pass"]:
        raise LV005LiveError("complete generation and judging required")
    answers = _read_jsonl(GENERATION)
    judgments = _read_jsonl(JUDGMENTS)
    mapping = json.loads(BLIND_MAPPING.read_text(encoding="utf-8"))["mapping"]
    gold = _gold_records()
    by_blind = defaultdict(list)
    for row in judgments:
        by_blind[row["blind_id"]].append(bool(row["verdict"]))
    if set(by_blind) != set(mapping) or any(len(values) != 3 for values in by_blind.values()):
        raise LV005LiveError("blind join failed")
    answer_verdict = {(value["comparison_key"], value["arm"], int(value["replicate"])): majority(by_blind[key]) for key, value in mapping.items()}
    semantic, containment = defaultdict(list), defaultdict(list)
    metadata = {}
    adversarial = {arm: [] for arm in ARMS}
    for row in answers:
        if row["category"] == 5:
            adversarial[row["arm"]].append(normalize(row["response"]["text"]) == "i don t know")
            continue
        record = gold[(row["sample_id"], int(row["source_index"]))]
        key = (row["comparison_key"], row["arm"])
        semantic[key].append(answer_verdict[(row["comparison_key"], row["arm"], int(row["replicate"]))])
        containment[key].append(contains_gold(row["response"]["text"], record["gold"]))
        metadata[row["comparison_key"]] = {field: row[field] for field in ("sample_id", "source_index", "population", "offline_direction")}
    item_rows = []
    for comparison_key in sorted(metadata):
        row = {"comparison_key": comparison_key, **metadata[comparison_key]}
        for arm in ARMS:
            if len(semantic[(comparison_key, arm)]) != 5:
                raise LV005LiveError("replicate join failed")
            row[f"{arm}_semantic"] = majority(semantic[(comparison_key, arm)])
            row[f"{arm}_semantic_votes"] = sum(semantic[(comparison_key, arm)])
            row[f"{arm}_containment"] = majority(containment[(comparison_key, arm)])
            row[f"{arm}_containment_votes"] = sum(containment[(comparison_key, arm)])
        item_rows.append(row)
    valid = json.loads(PREFLIGHT.read_text(encoding="utf-8"))["status"] == "PASS"
    comparisons = {}
    for name, baseline, treatment in COMPARISONS:
        semantic_rows = {population: _paired(item_rows, baseline, treatment, population) for population in ("combined", "targeted", "breadth", "other")}
        containment_row = _paired(item_rows, baseline, treatment, endpoint="containment")
        net = semantic_rows["combined"]["net"]
        status = disposition(net, semantic_rows["targeted"]["net"], semantic_rows["breadth"]["net"], net, containment_row["net"], valid=valid)
        comparisons[name] = {"baseline": baseline, "treatment": treatment, "status": status, "semantic": semantic_rows, "containment": containment_row, "endpoint_sign_reversal": bool(_sign(net) and _sign(containment_row["net"]) and _sign(net) != _sign(containment_row["net"]))}
    result = {
        "schema": "lv005-result-v1",
        "comparisons": comparisons,
        "totals": {arm: sum(row[f"{arm}_semantic"] for row in item_rows) for arm in ARMS},
        "adversarial_refusal_votes": {arm: {"refusals": sum(values), "n": len(values)} for arm, values in adversarial.items()},
        "reader_unanimous_items": {arm: sum(row[f"{arm}_semantic_votes"] in (0, 5) for row in item_rows) for arm in ARMS},
        "judge_answer_disagreements": sum(len(set(values)) > 1 for values in by_blind.values()),
        "artifacts": {"prompts_sha256": sha256_file(PROMPTS), "answers_sha256": sha256_file(GENERATION), "judgments_sha256": sha256_file(JUDGMENTS)},
        "calls": {"reader": 340, "judge": 960, "preflight_reader": 18, "preflight_judge": 48},
        "claim_boundary": "selected LoCoMo development rendering-only reader probe; no overall score, transfer, inferred supersession, deployment or winner selection",
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
