"""LV-007 Preflight, live generation, blind judging, and analysis."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from analysis.hh001_endpoints import contains_gold, normalize
from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_live import JUDGE_SEEDS, MODEL, READER_SEEDS, _generate, _get, _gold_records, _post, majority
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX
from analysis.lv003_live import _append_fsynced, _read_jsonl, _write_json
from analysis.lv007_prompts import (
    ARMS,
    CAP,
    LV005_PROMPTS,
    PART1,
    PROMPT_MANIFEST,
    PROMPTS,
    REGISTRATION,
    ROOT,
    build_prompt_rows,
    write_gzip_rows,
)
from analysis.tc001_exploration import DATASET_PATH


PREFLIGHT = ROOT / "artifacts" / "preflight" / "preflight.json"
GENERATION = ROOT / "artifacts" / "run" / "answers.jsonl"
GENERATION_SUMMARY = ROOT / "artifacts" / "run" / "generation_summary.json"
BLIND_SURFACE = ROOT / "artifacts" / "scoring" / "blind_surface.jsonl.gz"
BLIND_MAPPING = ROOT / "artifacts" / "scoring" / "blind_mapping.sealed.json"
JUDGMENTS = ROOT / "artifacts" / "scoring" / "blind_judgments.jsonl"
JUDGMENT_SUMMARY = ROOT / "artifacts" / "scoring" / "judgment_summary.json"
RESULT = ROOT / "artifacts" / "result" / "result.json"
PER_ITEM = ROOT / "artifacts" / "result" / "per_item.csv"
LV006_RESULT = (
    ROOT.parent / "live_validation_006" / "artifacts" / "result" / "result.json"
)

REGISTRATION_SHA256 = "2898f8cfde7b06ebfdf6638f63a1a210557f0b4cdcde232444fa46a6dd37dc9f"
PART1_SHA256 = "acd6a783a8ffd949b35ebe28788ea88a9b08de3c9b19ba7139da9547d815d78f"
PROMPTS_SHA256 = "dc40d134e0e281fd0a064371620ce2a9a99f8f4a39855d3f32072ca9a844e9d9"
LV005_PROMPTS_SHA256 = "d0a3ac38e15c1738387c9d3216de532195959dd4c8ac7515a03209bbfebe8b80"
LV006_RESULT_SHA256 = "011d0a3cf49d781f99a14327c3189b5260c1eec3e44e206ff84be8ce783f76ee"
READER_LIMIT = 2048
REPAIR_SUFFIX = "VERDICT:"
COMPARISONS = (
    ("COMMUNITY_vs_PAIRWISE", "PAIRWISE", "COMMUNITY"),
    ("QUESTION_REPEAT_INCREMENT", "COMMUNITY", "COMMUNITY_QB"),
    ("FULL_vs_PAIRWISE", "PAIRWISE", "COMMUNITY_QB"),
)


class LV007LiveError(RuntimeError):
    pass


def _prompt_rows() -> list[dict[str, Any]]:
    with gzip.open(PROMPTS, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _lv005_rows() -> dict[tuple[str, int], dict[str, Any]]:
    with gzip.open(LV005_PROMPTS, "rt", encoding="utf-8") as handle:
        return {
            (row["sample_id"], int(row["source_index"])): row
            for row in map(json.loads, handle)
        }


def arm_order(comparison_key: str, replicate: int) -> tuple[str, ...]:
    return tuple(
        sorted(
            ARMS,
            key=lambda arm: hashlib.sha256(
                f"lv007-order-v1\0{comparison_key}\0{replicate}\0{arm}".encode("utf-8")
            ).digest(),
        )
    )


def blind_id(comparison_key: str, arm: str, replicate: int) -> str:
    return hashlib.sha256(
        f"lv007-blind-v1\0{comparison_key}\0{arm}\0{replicate}".encode("utf-8")
    ).hexdigest()


def expected_answer_keys(prompts: Sequence[Mapping[str, Any]]) -> set[tuple[str, str, int]]:
    return {
        (str(row["comparison_key"]), arm, replicate)
        for row in prompts
        for arm in ARMS
        for replicate in range(5)
    }


def validate_answer_schedule(
    rows: Sequence[Mapping[str, Any]], prompts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    actual = [
        (str(row["comparison_key"]), str(row["arm"]), int(row["replicate"]))
        for row in rows
    ]
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


def repaired_judge_prompt(item: Mapping[str, Any]) -> str:
    return (
        render_judge_prompt(str(item["question"]), str(item["gold"]), str(item["answer"]))
        + CLOSED_THINK_SUFFIX
        + REPAIR_SUFFIX
    )


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def disposition(
    combined: int,
    targeted: int,
    breadth: int,
    semantic: int,
    containment: int,
    *,
    valid: bool,
) -> str:
    reversal = bool(
        _sign(semantic)
        and _sign(containment)
        and _sign(semantic) != _sign(containment)
    )
    if not valid or reversal:
        return "NOT_INTERPRETABLE"
    if combined >= 3 and targeted >= 0 and breadth >= 0:
        return "PROMISING"
    if combined in (1, 2) and targeted >= 0 and breadth >= 0:
        return "WEAK_SIGNAL"
    if combined == 0 and targeted >= 0 and breadth >= 0:
        return "NO_SIGNAL"
    return "REGRESSES"


def _reachability() -> dict[str, bool]:
    return {
        "promising": disposition(3, 1, 1, 3, 1, valid=True) == "PROMISING",
        "weak": disposition(1, 0, 1, 1, 0, valid=True) == "WEAK_SIGNAL",
        "no_signal": disposition(0, 0, 0, 0, 0, valid=True) == "NO_SIGNAL",
        "combined_regression": disposition(-1, 0, 0, -1, -1, valid=True) == "REGRESSES",
        "targeted_regression": disposition(3, -1, 1, 3, 1, valid=True) == "REGRESSES",
        "breadth_regression": disposition(3, 1, -1, 3, 1, valid=True) == "REGRESSES",
        "sign_reversal": disposition(3, 1, 1, 3, -1, valid=True) == "NOT_INTERPRETABLE",
        "invalid": disposition(3, 1, 1, 3, 1, valid=False) == "NOT_INTERPRETABLE",
    }


def _load_mapping() -> dict[str, Any]:
    if not JUDGMENT_SUMMARY.exists() or not JUDGMENTS.exists():
        raise LV007LiveError("mapping access blocked until blind judgments complete")
    summary = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"] or sha256_file(JUDGMENTS) != summary["judgments_sha256"]:
        raise LV007LiveError("mapping access blocked by incomplete judgment seal")
    return json.loads(BLIND_MAPPING.read_text(encoding="utf-8"))["mapping"]


def _distribution(values: Sequence[int]) -> dict[str, int | float]:
    return {
        "min": min(values),
        "median": median(values),
        "max": max(values),
    }


def _structural_checks(prompts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    prior = _lv005_rows()
    set_exact = 0
    element_exact = 0
    pairwise_exact = 0
    compact = 0
    same_community_block = 0
    order_changes = 0
    chronological_groups = 0
    total_groups = 0
    group_counts = []
    group_sizes = []
    singleton_counts = []
    cap_bound_counts = []
    mixed_counts = []
    join_decisions = 0
    new_decisions = 0
    question_top_exact = 0
    absorbing_singleton = 0
    absorbing_capacity = 0
    for row in prompts:
        key = (str(row["sample_id"]), int(row["source_index"]))
        baseline = row["arms"]["PAIRWISE"]
        expected = prior[key]["arms"]["TEMPORAL_GUIDANCE"]
        pairwise_exact += baseline["prompt"] == expected["prompt"] and baseline["prompt_sha256"] == expected["prompt_sha256"]
        selected = set(row["selected_ids"])
        for arm in ARMS:
            value = row["arms"][arm]
            set_exact += len(value["emitted_ids"]) == len(selected) and set(value["emitted_ids"]) == selected
            element_exact += value["episode_element_sha256"] == baseline["episode_element_sha256"]
        community = row["arms"]["COMMUNITY"]
        repeated = row["arms"]["COMMUNITY_QB"]
        compact += community["block_chars"] < baseline["block_chars"]
        same_community_block += community["block"] == repeated["block"] and community["block_sha256"] == repeated["block_sha256"]
        order_changes += community["emitted_ids"] != baseline["emitted_ids"]
        question_top_exact += (
            community["prompt"].count("Question to answer:") == 0
            and repeated["prompt"].count(f"Question to answer: {row['question']}") == 1
            and repeated["prompt"].count(f"\nQuestion: {row['question']}") == 1
        )
        groups = community["groups"]
        group_counts.append(len(groups))
        singleton_counts.append(sum(len(group["items"]) == 1 for group in groups))
        cap_bound_counts.append(sum(len(group["items"]) == CAP for group in groups))
        mixed_counts.append(sum(len({item["route"] for item in group["items"]}) == 2 for group in groups))
        for group in groups:
            turns = [int(item["turn"]) for item in group["items"]]
            group_sizes.append(len(turns))
            chronological_groups += turns == sorted(turns)
            total_groups += 1
        join_decisions += sum(item["decision"] == "join" for item in community["assignment_trace"])
        new_decisions += sum(item["decision"] == "new" for item in community["assignment_trace"])
        controls = community["absorbing_controls"]
        absorbing_singleton += all(size == 1 for size in controls["all_singleton_group_sizes"])
        capacity_sizes = controls["capacity_partition_group_sizes"]
        absorbing_capacity += (
            all(size == CAP for size in capacity_sizes[:-1])
            and 1 <= capacity_sizes[-1] <= CAP
        )
    return {
        "set_exact": set_exact,
        "expected_set_exact": len(prompts) * len(ARMS),
        "episode_elements_exact": element_exact,
        "expected_element_exact": len(prompts) * len(ARMS),
        "pairwise_exact": pairwise_exact,
        "compact_rows": compact,
        "same_community_block": same_community_block,
        "community_order_changes": order_changes,
        "chronological_groups": chronological_groups,
        "total_groups": total_groups,
        "groups_per_prompt": _distribution(group_counts),
        "group_size": _distribution(group_sizes),
        "singletons_per_prompt": _distribution(singleton_counts),
        "cap_bound_per_prompt": _distribution(cap_bound_counts),
        "mixed_groups_per_prompt": _distribution(mixed_counts),
        "join_decisions": join_decisions,
        "new_decisions": new_decisions,
        "question_top_exact": question_top_exact,
        "absorbing_singleton_rows": absorbing_singleton,
        "absorbing_capacity_rows": absorbing_capacity,
    }


def run_preflight() -> dict[str, Any]:
    anchors = {
        "registration": sha256_file(REGISTRATION) == REGISTRATION_SHA256,
        "part1": sha256_file(PART1) == PART1_SHA256,
        "prompts": sha256_file(PROMPTS) == PROMPTS_SHA256,
        "lv005_prompts": sha256_file(LV005_PROMPTS) == LV005_PROMPTS_SHA256,
        "lv006_result": sha256_file(LV006_RESULT) == LV006_RESULT_SHA256,
    }
    if not all(anchors.values()):
        raise LV007LiveError("registered input drift")
    prompts = _prompt_rows()
    manifest = json.loads(PROMPT_MANIFEST.read_text(encoding="utf-8"))
    primary = [row for row in prompts if int(row["category"]) != 5]
    checks = _structural_checks(prompts)
    try:
        build_prompt_rows(forbidden_labels=DATASET_PATH)
    except Exception:
        early_gold_rejected = True
    else:
        early_gold_rejected = False
    try:
        _load_mapping()
    except LV007LiveError:
        early_mapping_rejected = True
    else:
        early_mapping_rejected = False
    rebuilt_a, _ = build_prompt_rows()
    rebuilt_b, _ = build_prompt_rows()
    canonical = lambda value: hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    rebuild_identity = canonical(rebuilt_a) == canonical(prompts) == canonical(rebuilt_b)
    part1 = json.loads(PART1.read_text(encoding="utf-8"))
    selected = part1["selected_configuration"]
    part1_reproduced = (
        checks["groups_per_prompt"] == {
            "min": int(selected["groups_per_prompt"]["min"]),
            "median": selected["groups_per_prompt"]["median"],
            "max": int(selected["groups_per_prompt"]["max"]),
        }
        and checks["group_size"] == {
            "min": int(selected["group_size"]["min"]),
            "median": selected["group_size"]["median"],
            "max": int(selected["group_size"]["max"]),
        }
        and checks["singletons_per_prompt"] == {
            "min": int(selected["singletons_per_prompt"]["min"]),
            "median": selected["singletons_per_prompt"]["median"],
            "max": int(selected["singletons_per_prompt"]["max"]),
        }
        and checks["cap_bound_per_prompt"] == {
            "min": int(selected["cap_bound_per_prompt"]["min"]),
            "median": selected["cap_bound_per_prompt"]["median"],
            "max": int(selected["cap_bound_per_prompt"]["max"]),
        }
    )
    prefix = primary[0]["arms"]["COMMUNITY_QB"]["prompt"]
    prefix_a = _generate(prefix, 5005, n_predict=READER_LIMIT)
    prefix_b = _generate(prefix, 5005, n_predict=READER_LIMIT)
    prefix_identical = prefix_a["text"].encode("utf-8") == prefix_b["text"].encode("utf-8")
    process = _get("/api/ps")
    loaded = [model for model in process.get("models", []) if model.get("name") == MODEL]
    gpu_only = bool(loaded) and all(
        int(model.get("size_vram", 0)) >= int(model.get("size", 1)) for model in loaded
    )
    show = _post("/api/show", {"model": MODEL})
    reachability = _reachability()
    passing = (
        len(prompts) == 17
        and len(primary) == 16
        and manifest["prompts"] == 51
        and manifest["selected_episode_occurrences"] == 1686
        and checks["set_exact"] == checks["expected_set_exact"]
        and checks["episode_elements_exact"] == checks["expected_element_exact"]
        and checks["pairwise_exact"] == 17
        and checks["compact_rows"] == 17
        and checks["same_community_block"] == 17
        and checks["community_order_changes"] == 17
        and checks["chronological_groups"] == checks["total_groups"]
        and checks["join_decisions"] > 0
        and checks["new_decisions"] > 0
        and checks["cap_bound_per_prompt"]["max"] > 0
        and checks["mixed_groups_per_prompt"]["min"] > 0
        and checks["question_top_exact"] == 17
        and checks["absorbing_singleton_rows"] == 17
        and checks["absorbing_capacity_rows"] == 17
        and early_gold_rejected
        and early_mapping_rejected
        and rebuild_identity
        and part1_reproduced
        and all(reachability.values())
        and prefix_identical
        and prefix_a["done_reason"] != "length"
        and prefix_a["prompt_eval_count"] < 65_536
        and gpu_only
    )
    result = {
        "schema": "lv007-preflight-v1",
        "status": "PASS" if passing else "FAIL",
        "pf1": {
            "anchors": anchors,
            "prompts": len(prompts),
            "primary": len(primary),
            "model": MODEL,
            "ollama_version": _get("/api/version").get("version"),
            "model_details": show.get("details", {}),
            "cache": manifest["cache"],
            "parser": manifest["parser"],
        },
        "pf2": {"structural_checks": checks, "parameters": manifest["parameters"]},
        "pf3": {
            "registration_before_implementation": True,
            "early_gold_rejected": early_gold_rejected,
            "early_mapping_rejected": early_mapping_rejected,
            "append_flush_fsync": True,
        },
        "pf4": {"reachability": reachability, "real_trace_alternatives": {"join": checks["join_decisions"], "new": checks["new_decisions"], "cap_bound_max": checks["cap_bound_per_prompt"]["max"]}},
        "pf5": {"unique_questions": len({row["comparison_key"] for row in prompts}) == 17, "content_keyed": True},
        "pf6": {"pairwise_reproductions": checks["pairwise_exact"], "independent_rebuild": rebuild_identity, "part1_reproduced": part1_reproduced, "lv006_result_sha256": sha256_file(LV006_RESULT)},
        "pf7": {"all_singleton_rows": checks["absorbing_singleton_rows"], "capacity_partition_rows": checks["absorbing_capacity_rows"], "seeded_prefix_byte_identical": prefix_identical, "prefix_sha256": hashlib.sha256(prefix_a["text"].encode("utf-8")).hexdigest(), "prompt_eval_count": prefix_a["prompt_eval_count"], "gpu_only": gpu_only, "ollama_process": process},
        "pf8": {"replicates": 5, "primary_items": 16, "cannot_detect": "overall accuracy, small effects, transfer, production behavior or globally optimal grouping"},
        "pf9": {"residuals": ["affinity can group unrelated passages", "shared facets can be generic", "compactness can improve without correctness", "question repetition can change verbosity", "same-model judge bias"]},
        "pf10": {"live_reader_probe": True, "structure_is_not_verdict": True},
        "g_content": {"pass": checks["set_exact"] == checks["expected_set_exact"] and checks["episode_elements_exact"] == checks["expected_element_exact"]},
        "g_compact": {"pass": checks["compact_rows"] == 17, "rows": checks["compact_rows"], "expected": 17},
        "g_context": {"pass": prefix_a["prompt_eval_count"] < 65_536, "prompt_eval_count": prefix_a["prompt_eval_count"]},
        "calls": {"preflight_reader": 2, "embedding": 0, "llm_judge": 0},
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV007LiveError("Preflight failed")
    return result


def run_generation() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(PROMPTS) != PROMPTS_SHA256:
        raise LV007LiveError("passing Preflight and frozen prompts required")
    if GENERATION.exists():
        raise LV007LiveError("generation artifact exists; rerun forbidden")
    prompts = _prompt_rows()
    GENERATION.parent.mkdir(parents=True, exist_ok=True)
    calls = 0
    with GENERATION.open("x", encoding="utf-8", newline="\n") as handle:
        for row in prompts:
            for replicate, seed in enumerate(READER_SEEDS):
                for arm in arm_order(row["comparison_key"], replicate):
                    response = _generate(row["arms"][arm]["prompt"], seed, n_predict=READER_LIMIT)
                    _append_fsynced(
                        handle,
                        {
                            "comparison_key": row["comparison_key"],
                            "sample_id": row["sample_id"],
                            "source_index": row["source_index"],
                            "category": row["category"],
                            "population": row["population"],
                            "offline_direction": row["offline_direction"],
                            "arm": arm,
                            "replicate": replicate,
                            "prompt_sha256": row["arms"][arm]["prompt_sha256"],
                            "block_sha256": row["arms"][arm]["block_sha256"],
                            "response": response,
                        },
                    )
                    calls += 1
    answers = _read_jsonl(GENERATION)
    validation = validate_answer_schedule(answers, prompts)
    summary = {
        "schema": "lv007-generation-summary-v1",
        "answers_sha256": sha256_file(GENERATION),
        "calls": calls,
        "validation": validation,
        "prompt_tokens": {
            arm: _distribution(
                [int(row["response"]["prompt_eval_count"]) for row in answers if row["arm"] == arm]
            )
            for arm in ARMS
        },
    }
    _write_json(GENERATION_SUMMARY, summary)
    if not validation["pass"]:
        raise LV007LiveError("generation completeness failed")
    return summary


def prepare_blind() -> dict[str, Any]:
    summary = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"] or sha256_file(GENERATION) != summary["answers_sha256"]:
        raise LV007LiveError("sealed complete answers required")
    answers = _read_jsonl(GENERATION)
    gold = _gold_records()
    surface: list[dict[str, Any]] = []
    mapping: dict[str, Any] = {}
    for row in answers:
        if int(row["category"]) == 5:
            continue
        record = gold[(row["sample_id"], int(row["source_index"]))]
        identifier = blind_id(row["comparison_key"], row["arm"], int(row["replicate"]))
        surface.append(
            {
                "blind_id": identifier,
                "question": record["question"],
                "gold": record["gold"],
                "answer": row["response"]["text"],
            }
        )
        mapping[identifier] = {
            "comparison_key": row["comparison_key"],
            "arm": row["arm"],
            "replicate": row["replicate"],
        }
    surface.sort(key=lambda row: row["blind_id"])
    if len(surface) != 240 or len(mapping) != 240:
        raise LV007LiveError("blind cardinality drift")
    write_gzip_rows(BLIND_SURFACE, surface)
    _write_json(BLIND_MAPPING, {"schema": "lv007-blind-mapping-v1", "mapping": mapping})
    return {
        "surface": len(surface),
        "surface_sha256": sha256_file(BLIND_SURFACE),
        "mapping_sha256": sha256_file(BLIND_MAPPING),
    }


def _surface_rows() -> list[dict[str, Any]]:
    with gzip.open(BLIND_SURFACE, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_judgments(
    rows: Sequence[Mapping[str, Any]], surface: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    actual = [
        (str(row["blind_id"]), int(row["judge_pass"]), int(row["seed"]))
        for row in rows
    ]
    expected = {
        (str(item["blind_id"]), judge_pass, seed)
        for item in surface
        for judge_pass, seed in enumerate(JUDGE_SEEDS)
    }
    counts = Counter(key[0] for key in actual)
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


def run_judging() -> dict[str, Any]:
    if JUDGMENTS.exists():
        raise LV007LiveError("judgments exist; rerun forbidden")
    surface = _surface_rows()
    JUDGMENTS.parent.mkdir(parents=True, exist_ok=True)
    calls = 0
    with JUDGMENTS.open("x", encoding="utf-8", newline="\n") as handle:
        for item in surface:
            prompt = repaired_judge_prompt(item)
            for judge_pass, seed in enumerate(JUDGE_SEEDS):
                response = _generate(prompt, seed, judge=True)
                verdict, reason = parse_judge_verdict(response["text"])
                if response["done_reason"] == "length":
                    raise LV007LiveError("judge response truncated")
                _append_fsynced(
                    handle,
                    {
                        "blind_id": item["blind_id"],
                        "judge_pass": judge_pass,
                        "seed": seed,
                        "verdict": verdict,
                        "reason": reason,
                        "done_reason": response["done_reason"],
                        "response_sha256": hashlib.sha256(response["text"].encode("utf-8")).hexdigest(),
                    },
                )
                calls += 1
    rows = _read_jsonl(JUDGMENTS)
    validation = validate_judgments(rows, surface)
    summary = {
        "schema": "lv007-judgment-summary-v1",
        "judgments_sha256": sha256_file(JUDGMENTS),
        "calls": calls,
        "validation": validation,
    }
    _write_json(JUDGMENT_SUMMARY, summary)
    if not validation["pass"]:
        raise LV007LiveError("judgment completeness failed")
    return summary


def _paired(
    items: Sequence[Mapping[str, Any]],
    baseline: str,
    treatment: str,
    population: str = "combined",
    endpoint: str = "semantic",
) -> dict[str, Any]:
    subset = [row for row in items if population == "combined" or row["population"] == population]
    gains = sum(row[f"{treatment}_{endpoint}"] and not row[f"{baseline}_{endpoint}"] for row in subset)
    losses = sum(row[f"{baseline}_{endpoint}"] and not row[f"{treatment}_{endpoint}"] for row in subset)
    discordant = gains + losses
    tail = min(gains, losses)
    p = 1.0 if not discordant else min(
        1.0,
        2 * sum(math.comb(discordant, value) for value in range(tail + 1)) / 2**discordant,
    )
    return {
        "n": len(subset),
        "gains": gains,
        "losses": losses,
        "ties": len(subset) - discordant,
        "net": gains - losses,
        "two_sided_exact_p": p,
    }


def analyze() -> dict[str, Any]:
    mapping = _load_mapping()
    generation = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    judging = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    if not generation["validation"]["pass"] or not judging["validation"]["pass"]:
        raise LV007LiveError("complete generation and judging required")
    answers = _read_jsonl(GENERATION)
    judgments = _read_jsonl(JUDGMENTS)
    gold = _gold_records()
    by_blind: dict[str, list[bool]] = defaultdict(list)
    for row in judgments:
        by_blind[row["blind_id"]].append(bool(row["verdict"]))
    if set(by_blind) != set(mapping) or any(len(values) != 3 for values in by_blind.values()):
        raise LV007LiveError("blind join failed")
    answer_verdict = {
        (value["comparison_key"], value["arm"], int(value["replicate"])): majority(by_blind[key])
        for key, value in mapping.items()
    }
    semantic: dict[tuple[str, str], list[bool]] = defaultdict(list)
    containment: dict[tuple[str, str], list[bool]] = defaultdict(list)
    metadata: dict[str, Any] = {}
    adversarial = {arm: [] for arm in ARMS}
    for row in answers:
        if int(row["category"]) == 5:
            adversarial[row["arm"]].append(normalize(row["response"]["text"]) == "i don t know")
            continue
        record = gold[(row["sample_id"], int(row["source_index"]))]
        key = (row["comparison_key"], row["arm"])
        semantic[key].append(answer_verdict[(row["comparison_key"], row["arm"], int(row["replicate"]))])
        containment[key].append(contains_gold(row["response"]["text"], record["gold"]))
        metadata[row["comparison_key"]] = {
            field: row[field]
            for field in ("sample_id", "source_index", "population", "offline_direction")
        }
    item_rows = []
    for comparison_key in sorted(metadata):
        row = {"comparison_key": comparison_key, **metadata[comparison_key]}
        for arm in ARMS:
            if len(semantic[(comparison_key, arm)]) != 5:
                raise LV007LiveError("replicate join failed")
            row[f"{arm}_semantic"] = majority(semantic[(comparison_key, arm)])
            row[f"{arm}_semantic_votes"] = sum(semantic[(comparison_key, arm)])
            row[f"{arm}_containment"] = majority(containment[(comparison_key, arm)])
            row[f"{arm}_containment_votes"] = sum(containment[(comparison_key, arm)])
        item_rows.append(row)
    valid = json.loads(PREFLIGHT.read_text(encoding="utf-8"))["status"] == "PASS"
    comparisons: dict[str, Any] = {}
    for name, baseline, treatment in COMPARISONS:
        semantic_rows = {
            population: _paired(item_rows, baseline, treatment, population)
            for population in ("combined", "targeted", "breadth", "other")
        }
        containment_row = _paired(item_rows, baseline, treatment, endpoint="containment")
        net = int(semantic_rows["combined"]["net"])
        status = disposition(
            net,
            int(semantic_rows["targeted"]["net"]),
            int(semantic_rows["breadth"]["net"]),
            net,
            int(containment_row["net"]),
            valid=valid,
        )
        comparisons[name] = {
            "baseline": baseline,
            "treatment": treatment,
            "status": status,
            "semantic": semantic_rows,
            "containment": containment_row,
            "endpoint_sign_reversal": bool(
                _sign(net)
                and _sign(int(containment_row["net"]))
                and _sign(net) != _sign(int(containment_row["net"]))
            ),
        }
    prompts = _prompt_rows()
    result = {
        "schema": "lv007-result-v1",
        "comparisons": comparisons,
        "totals": {arm: sum(row[f"{arm}_semantic"] for row in item_rows) for arm in ARMS},
        "adversarial_refusal_votes": {
            arm: {"refusals": sum(values), "n": len(values)} for arm, values in adversarial.items()
        },
        "reader_unanimous_items": {
            arm: sum(row[f"{arm}_semantic_votes"] in (0, 5) for row in item_rows) for arm in ARMS
        },
        "judge_answer_disagreements": sum(len(set(values)) > 1 for values in by_blind.values()),
        "block_chars": {
            arm: _distribution([int(row["arms"][arm]["block_chars"]) for row in prompts])
            for arm in ARMS
        },
        "prompt_tokens": generation["prompt_tokens"],
        "artifacts": {
            "prompts_sha256": sha256_file(PROMPTS),
            "answers_sha256": sha256_file(GENERATION),
            "surface_sha256": sha256_file(BLIND_SURFACE),
            "mapping_sha256": sha256_file(BLIND_MAPPING),
            "judgments_sha256": sha256_file(JUDGMENTS),
        },
        "calls": {"reader": 255, "judge": 720, "preflight_reader": 2, "embedding": 0},
        "claim_boundary": "selected LoCoMo development fixed-evidence rendering probe; no overall score, deployable fixed-32k renderer, transfer, optimal clustering, model generality, adoption or production claim",
    }
    _write_json(RESULT, result)
    PER_ITEM.parent.mkdir(parents=True, exist_ok=True)
    with PER_ITEM.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(item_rows[0]))
        writer.writeheader()
        writer.writerows(item_rows)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "generate", "blind", "judge", "analyze"))
    args = parser.parse_args()
    actions = {
        "preflight": run_preflight,
        "generate": run_generation,
        "blind": prepare_blind,
        "judge": run_judging,
        "analyze": analyze,
    }
    print(json.dumps(actions[args.phase](), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
