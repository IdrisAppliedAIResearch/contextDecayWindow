"""Registered LV-008 Preflight, generation, blind judging, and analysis."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from analysis.hh001_endpoints import contains_gold, normalize
from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_live import JUDGE_SEEDS, READER_SEEDS, _get, _gold_records, _post, majority
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX
from analysis.lv003_live import _append_fsynced, _read_jsonl, _write_json
from analysis.lv007_live import _paired, _sign, _structural_checks, disposition
from analysis.lv007_prompts import ARMS, PROMPTS as LV007_PROMPTS
from analysis.tc001_exploration import REPO_ROOT


ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_008"
REGISTRATION = ROOT / "LV_008_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "part1_exploration.json"
LV007_STOP = ROOT.parent / "live_validation_007" / "LV_007_STOP.md"
LV007_ERRATUM = ROOT.parent / "live_validation_007" / "LV_007_ERRATUM_001.md"
PROMPTS = ROOT / "artifacts" / "preflight" / "prompts.jsonl.gz"
PREFLIGHT = ROOT / "artifacts" / "preflight" / "preflight.json"
GENERATION = ROOT / "artifacts" / "run" / "answers.jsonl"
GENERATION_SUMMARY = ROOT / "artifacts" / "run" / "generation_summary.json"
BLIND_SURFACE = ROOT / "artifacts" / "scoring" / "blind_surface.jsonl.gz"
BLIND_MAPPING = ROOT / "artifacts" / "scoring" / "blind_mapping.sealed.json"
JUDGMENTS = ROOT / "artifacts" / "scoring" / "blind_judgments.jsonl"
JUDGMENT_SUMMARY = ROOT / "artifacts" / "scoring" / "judgment_summary.json"
RESULT = ROOT / "artifacts" / "result" / "result.json"
PER_ITEM = ROOT / "artifacts" / "result" / "per_item.csv"
MODEL_MANIFEST = Path(
    r"C:\Users\muzaf\.ollama\models\manifests\registry.ollama.ai\library\lv008-qwen38-q4\latest"
)
MODEL_SOURCE = Path(
    r"C:\Users\muzaf\.cache\huggingface\hub\models--unsloth--Qwen3.8-27B-GGUF\snapshots\f1bfb127c64f7072bdd2cad55f258b9c8b2910fe\Qwen3.8-27B-UD-Q4_K_XL.gguf"
)

REGISTRATION_SHA256 = "8b19ee2b922731f34802e250b8100d113dc9099f33bdee6b0d02ebddf4d0cd62"
PART1_SHA256 = "6092121c1459be2516f3e7a2fde1557541c00d93c7fce199e65ef4def65e77e1"
LV007_PROMPTS_SHA256 = "dc40d134e0e281fd0a064371620ce2a9a99f8f4a39855d3f32072ca9a844e9d9"
LV007_STOP_SHA256 = "d1497d7aadc47f6f4afb67361d5f3face895dc6d07142dffefbfbb9412b74957"
MODEL_MANIFEST_SHA256 = "281d02f0ad1a4b4928fcf1450e6bd1bb88e0d57c0051df03a993265ec6662adc"
MODEL_SOURCE_SHA256 = "bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372"
PART1_KEY = "7fd147b3cb2deb3677b72ea650c8453b67ff7f6a2e84e36d1d887c7a14608c85"
PART1_RESPONSE_SHA256 = "d993af43c78fee1775ba2f2d3f864c71a8d1dbc4615119307ce4f43dc875bdef"
MODEL = "lv008-qwen38-q4:latest"
READER_LIMIT = 4096
REPAIR_SUFFIX = "VERDICT:"
COMPARISONS = (
    ("COMMUNITY_vs_PAIRWISE", "PAIRWISE", "COMMUNITY"),
    ("QUESTION_REPEAT_INCREMENT", "COMMUNITY", "COMMUNITY_QB"),
    ("FULL_vs_PAIRWISE", "PAIRWISE", "COMMUNITY_QB"),
)


class LV008LiveError(RuntimeError):
    pass


def _prompt_rows(path: Path = LV007_PROMPTS) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _distribution(values: Sequence[int]) -> dict[str, int | float]:
    return {"min": min(values), "median": median(values), "max": max(values)}


def _generate(
    prompt: str,
    seed: int,
    *,
    judge: bool = False,
    n_predict: int | None = None,
) -> dict[str, Any]:
    options = {
        "seed": seed,
        "num_ctx": 65_536,
        "num_predict": n_predict if n_predict is not None else (128 if judge else READER_LIMIT),
        "temperature": 0.2 if judge else 0.6,
        "top_p": 0.9 if judge else 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "repeat_penalty": 1.0,
    }
    started = time.perf_counter()
    payload = _post(
        "/api/generate",
        {
            "model": MODEL,
            "prompt": prompt,
            "raw": True,
            "think": False,
            "stream": False,
            "keep_alive": "30m",
            "options": options,
        },
    )
    text = str(payload.get("response", "")).strip()
    if not payload.get("done") or not text:
        raise LV008LiveError("Ollama returned an incomplete or empty response")
    return {
        "text": text,
        "seed": seed,
        "prompt_eval_count": int(payload.get("prompt_eval_count", 0) or 0),
        "eval_count": int(payload.get("eval_count", 0) or 0),
        "done_reason": str(payload.get("done_reason", "")),
        "total_duration_ns": int(payload.get("total_duration", 0) or 0),
        "load_duration_ns": int(payload.get("load_duration", 0) or 0),
        "wall_seconds": round(time.perf_counter() - started, 3),
    }


def arm_order(comparison_key: str, replicate: int) -> tuple[str, ...]:
    return tuple(
        sorted(
            ARMS,
            key=lambda arm: hashlib.sha256(
                f"lv008-order-v1\0{comparison_key}\0{replicate}\0{arm}".encode("utf-8")
            ).digest(),
        )
    )


def blind_id(comparison_key: str, arm: str, replicate: int) -> str:
    return hashlib.sha256(
        f"lv008-blind-v1\0{comparison_key}\0{arm}\0{replicate}".encode("utf-8")
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
    actual = [(str(row["comparison_key"]), str(row["arm"]), int(row["replicate"])) for row in rows]
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


def _reachability() -> dict[str, bool]:
    cases = {
        "promising": (3, 1, 1, 3, 1, True, "PROMISING"),
        "weak": (1, 0, 1, 1, 0, True, "WEAK_SIGNAL"),
        "no_signal": (0, 0, 0, 0, 0, True, "NO_SIGNAL"),
        "combined_regression": (-1, 0, 0, -1, -1, True, "REGRESSES"),
        "targeted_regression": (3, -1, 1, 3, 1, True, "REGRESSES"),
        "breadth_regression": (3, 1, -1, 3, 1, True, "REGRESSES"),
        "sign_reversal": (3, 1, 1, 3, -1, True, "NOT_INTERPRETABLE"),
        "invalid": (3, 1, 1, 3, 1, False, "NOT_INTERPRETABLE"),
    }
    return {
        name: disposition(*values[:5], valid=values[5]) == values[6]
        for name, values in cases.items()
    }


def _gpu_process() -> tuple[dict[str, Any], bool]:
    process = _get("/api/ps")
    loaded = [row for row in process.get("models", []) if row.get("name") == MODEL]
    gpu_only = bool(loaded) and all(
        int(row.get("size_vram", 0)) == int(row.get("size", -1)) for row in loaded
    )
    return process, gpu_only


def _load_mapping() -> dict[str, Any]:
    if not JUDGMENT_SUMMARY.exists() or not JUDGMENTS.exists():
        raise LV008LiveError("mapping access blocked until blind judgments complete")
    summary = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"] or sha256_file(JUDGMENTS) != summary["judgments_sha256"]:
        raise LV008LiveError("mapping access blocked by incomplete judgment seal")
    return json.loads(BLIND_MAPPING.read_text(encoding="utf-8"))["mapping"]


def run_preflight() -> dict[str, Any]:
    anchors = {
        "registration": sha256_file(REGISTRATION) == REGISTRATION_SHA256,
        "part1": sha256_file(PART1) == PART1_SHA256,
        "lv007_prompts": sha256_file(LV007_PROMPTS) == LV007_PROMPTS_SHA256,
        "lv007_stop": sha256_file(LV007_STOP) == LV007_STOP_SHA256,
        "lv007_erratum": LV007_ERRATUM.exists(),
        "model_manifest": sha256_file(MODEL_MANIFEST) == MODEL_MANIFEST_SHA256,
        "model_source": sha256_file(MODEL_SOURCE) == MODEL_SOURCE_SHA256,
    }
    if not all(anchors.values()):
        raise LV008LiveError("registered input drift")
    prompts = _prompt_rows()
    primary = [row for row in prompts if int(row["category"]) != 5]
    checks = _structural_checks(prompts)
    if PROMPTS.exists():
        raise LV008LiveError("LV-008 prompt seal already exists")
    PROMPTS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LV007_PROMPTS, PROMPTS)
    prompt_copy_exact = sha256_file(PROMPTS) == LV007_PROMPTS_SHA256
    early_mapping_rejected = False
    try:
        _load_mapping()
    except LV008LiveError:
        early_mapping_rejected = True

    part1_row = next(row for row in prompts if row["comparison_key"] == PART1_KEY)
    part1_response = _generate(part1_row["arms"]["COMMUNITY"]["prompt"], 5005)
    part1_reproduced = (
        hashlib.sha256(part1_response["text"].encode("utf-8")).hexdigest() == PART1_RESPONSE_SHA256
        and part1_response["eval_count"] == 12
        and part1_response["done_reason"] != "length"
    )
    cap_response = _generate(primary[0]["arms"]["COMMUNITY_QB"]["prompt"], 5005, n_predict=1)
    cap_reachable = cap_response["done_reason"] == "length" and cap_response["eval_count"] == 1
    prefix = primary[0]["arms"]["COMMUNITY_QB"]["prompt"]
    prefix_a = _generate(prefix, 5005)
    prefix_b = _generate(prefix, 5005)
    prefix_identical = prefix_a["text"].encode("utf-8") == prefix_b["text"].encode("utf-8")
    process, gpu_only = _gpu_process()
    show = _post("/api/show", {"model": MODEL})
    reachability = _reachability()
    max_prompt_bytes = max(len(row["arms"][arm]["prompt"].encode("utf-8")) for row in prompts for arm in ARMS)
    context_safe = max_prompt_bytes < 65_536 and prefix_a["prompt_eval_count"] < 65_536
    passing = (
        len(prompts) == 17
        and len(primary) == 16
        and prompt_copy_exact
        and checks["set_exact"] == checks["expected_set_exact"]
        and checks["episode_elements_exact"] == checks["expected_element_exact"]
        and checks["pairwise_exact"] == 17
        and checks["same_community_block"] == 17
        and checks["question_top_exact"] == 17
        and early_mapping_rejected
        and all(reachability.values())
        and part1_reproduced
        and cap_reachable
        and prefix_identical
        and prefix_a["done_reason"] != "length"
        and context_safe
        and gpu_only
    )
    result = {
        "schema": "lv008-preflight-v1",
        "status": "PASS" if passing else "FAIL",
        "pf1": {
            "anchors": anchors,
            "prompts": len(prompts),
            "primary": len(primary),
            "model": MODEL,
            "ollama_version": _get("/api/version").get("version"),
            "model_details": show.get("details", {}),
        },
        "pf2": {"structural_checks": checks, "frozen_prompt_copy_exact": prompt_copy_exact},
        "pf3": {
            "registration_before_implementation": True,
            "early_gold_forbidden_by_phase": True,
            "early_mapping_rejected": early_mapping_rejected,
            "append_flush_fsync": True,
        },
        "pf4": {"reachability": reachability, "cap_reachable": cap_reachable},
        "pf5": {
            "unique_questions": len({row["comparison_key"] for row in prompts}) == 17,
            "content_keyed": True,
        },
        "pf6": {
            "prompt_seal_reproduced": prompt_copy_exact,
            "part1_response_reproduced": part1_reproduced,
            "part1_response_sha256": hashlib.sha256(part1_response["text"].encode("utf-8")).hexdigest(),
        },
        "pf7": {
            "cap_absorbing_state": cap_reachable,
            "seeded_prefix_byte_identical": prefix_identical,
            "prefix_sha256": hashlib.sha256(prefix_a["text"].encode("utf-8")).hexdigest(),
            "prompt_eval_count": prefix_a["prompt_eval_count"],
            "gpu_only": gpu_only,
            "ollama_process": process,
        },
        "pf8": {
            "replicates": 5,
            "primary_items": 16,
            "cannot_detect": "overall accuracy, small effects, transfer, production behavior or optimal rendering",
        },
        "pf9": {
            "residuals": [
                "compactness can improve without correctness",
                "question repetition can change verbosity",
                "exact evidence preservation can coexist with reader failure",
                "same-model judge bias",
            ]
        },
        "pf10": {"live_reader_probe": True, "structure_is_not_verdict": True},
        "g_prompts": {"pass": prompt_copy_exact, "sha256": sha256_file(PROMPTS)},
        "g_context": {"pass": context_safe, "max_prompt_utf8_bytes": max_prompt_bytes},
        "g_gpu": {"pass": gpu_only},
        "calls": {"preflight_reader": 4, "embedding": 0, "judge": 0},
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV008LiveError("Preflight failed")
    return result


def run_generation() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(PROMPTS) != LV007_PROMPTS_SHA256:
        raise LV008LiveError("passing Preflight and frozen prompts required")
    if GENERATION.exists():
        raise LV008LiveError("generation artifact exists; rerun forbidden")
    prompts = _prompt_rows(PROMPTS)
    GENERATION.parent.mkdir(parents=True, exist_ok=True)
    calls = 0
    with GENERATION.open("x", encoding="utf-8", newline="\n") as handle:
        for row in prompts:
            for replicate, seed in enumerate(READER_SEEDS):
                for arm in arm_order(row["comparison_key"], replicate):
                    response = _generate(row["arms"][arm]["prompt"], seed)
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
    process, gpu_only = _gpu_process()
    validation["gpu_only_after"] = gpu_only
    validation["pass"] = validation["pass"] and gpu_only
    summary = {
        "schema": "lv008-generation-summary-v1",
        "answers_sha256": sha256_file(GENERATION),
        "calls": calls,
        "validation": validation,
        "prompt_tokens": {
            arm: _distribution([int(row["response"]["prompt_eval_count"]) for row in answers if row["arm"] == arm])
            for arm in ARMS
        },
        "ollama_process_after": process,
    }
    _write_json(GENERATION_SUMMARY, summary)
    if not validation["pass"]:
        raise LV008LiveError("generation completeness failed")
    return summary


def _poststop_generation_complete(summary: Mapping[str, Any]) -> bool:
    validation = summary["validation"]
    return (
        int(validation["rows"]) == 255
        and int(validation["expected"]) == 255
        and int(validation["duplicates"]) == 0
        and int(validation["missing"]) == 0
        and int(validation["extra"]) == 0
        and int(validation["truncated"]) == 1
        and bool(validation["gpu_only_after"])
    )


def prepare_blind(*, poststop: bool = False) -> dict[str, Any]:
    summary = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    generation_valid = bool(summary["validation"]["pass"]) or (
        poststop and _poststop_generation_complete(summary)
    )
    if not generation_valid or sha256_file(GENERATION) != summary["answers_sha256"]:
        raise LV008LiveError("sealed complete answers required")
    answers = _read_jsonl(GENERATION)
    gold = _gold_records()
    surface: list[dict[str, Any]] = []
    mapping: dict[str, Any] = {}
    for row in answers:
        if int(row["category"]) == 5:
            continue
        record = gold[(row["sample_id"], int(row["source_index"]))]
        identifier = blind_id(row["comparison_key"], row["arm"], int(row["replicate"]))
        surface.append({"blind_id": identifier, "question": record["question"], "gold": record["gold"], "answer": row["response"]["text"]})
        mapping[identifier] = {"comparison_key": row["comparison_key"], "arm": row["arm"], "replicate": row["replicate"]}
    surface.sort(key=lambda row: row["blind_id"])
    if len(surface) != 240 or len(mapping) != 240:
        raise LV008LiveError("blind cardinality drift")
    from analysis.lv007_prompts import write_gzip_rows

    write_gzip_rows(BLIND_SURFACE, surface)
    _write_json(BLIND_MAPPING, {"schema": "lv008-blind-mapping-v1", "mapping": mapping})
    return {
        "surface": len(surface),
        "surface_sha256": sha256_file(BLIND_SURFACE),
        "mapping_sha256": sha256_file(BLIND_MAPPING),
        "poststop": poststop,
    }


def _surface_rows() -> list[dict[str, Any]]:
    with gzip.open(BLIND_SURFACE, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_judgments(rows: Sequence[Mapping[str, Any]], surface: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    actual = [(str(row["blind_id"]), int(row["judge_pass"]), int(row["seed"])) for row in rows]
    expected = {(str(item["blind_id"]), judge_pass, seed) for item in surface for judge_pass, seed in enumerate(JUDGE_SEEDS)}
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
        raise LV008LiveError("judgments exist; rerun forbidden")
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
                    raise LV008LiveError("judge response truncated")
                _append_fsynced(handle, {"blind_id": item["blind_id"], "judge_pass": judge_pass, "seed": seed, "verdict": verdict, "reason": reason, "done_reason": response["done_reason"], "prompt_eval_count": response["prompt_eval_count"], "response_sha256": hashlib.sha256(response["text"].encode("utf-8")).hexdigest()})
                calls += 1
    rows = _read_jsonl(JUDGMENTS)
    validation = validate_judgments(rows, surface)
    process, gpu_only = _gpu_process()
    validation["gpu_only_after"] = gpu_only
    validation["pass"] = validation["pass"] and gpu_only and all(int(row["prompt_eval_count"]) < 65_536 for row in rows)
    summary = {"schema": "lv008-judgment-summary-v1", "judgments_sha256": sha256_file(JUDGMENTS), "calls": calls, "validation": validation, "ollama_process_after": process}
    _write_json(JUDGMENT_SUMMARY, summary)
    if not validation["pass"]:
        raise LV008LiveError("judgment completeness failed")
    return summary


def analyze(*, poststop: bool = False) -> dict[str, Any]:
    mapping = _load_mapping()
    generation = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    judging = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    generation_valid = bool(generation["validation"]["pass"]) or (
        poststop and _poststop_generation_complete(generation)
    )
    if not generation_valid or not judging["validation"]["pass"]:
        raise LV008LiveError("complete generation and judging required")
    answers = _read_jsonl(GENERATION)
    judgments = _read_jsonl(JUDGMENTS)
    gold = _gold_records()
    by_blind: dict[str, list[bool]] = defaultdict(list)
    for row in judgments:
        by_blind[row["blind_id"]].append(bool(row["verdict"]))
    if set(by_blind) != set(mapping) or any(len(values) != 3 for values in by_blind.values()):
        raise LV008LiveError("blind join failed")
    answer_verdict = {(value["comparison_key"], value["arm"], int(value["replicate"])): majority(by_blind[key]) for key, value in mapping.items()}
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
        metadata[row["comparison_key"]] = {field: row[field] for field in ("sample_id", "source_index", "population", "offline_direction")}
    item_rows = []
    for comparison_key in sorted(metadata):
        row = {"comparison_key": comparison_key, **metadata[comparison_key]}
        for arm in ARMS:
            if len(semantic[(comparison_key, arm)]) != 5:
                raise LV008LiveError("replicate join failed")
            row[f"{arm}_semantic"] = majority(semantic[(comparison_key, arm)])
            row[f"{arm}_semantic_votes"] = sum(semantic[(comparison_key, arm)])
            row[f"{arm}_containment"] = majority(containment[(comparison_key, arm)])
            row[f"{arm}_containment_votes"] = sum(containment[(comparison_key, arm)])
        item_rows.append(row)
    valid = json.loads(PREFLIGHT.read_text(encoding="utf-8"))["status"] == "PASS"
    comparisons: dict[str, Any] = {}
    for name, baseline, treatment in COMPARISONS:
        semantic_rows = {population: _paired(item_rows, baseline, treatment, population) for population in ("combined", "targeted", "breadth", "other")}
        containment_row = _paired(item_rows, baseline, treatment, endpoint="containment")
        net = int(semantic_rows["combined"]["net"])
        status = disposition(net, int(semantic_rows["targeted"]["net"]), int(semantic_rows["breadth"]["net"]), net, int(containment_row["net"]), valid=valid)
        comparisons[name] = {"baseline": baseline, "treatment": treatment, "status": status, "semantic": semantic_rows, "containment": containment_row, "endpoint_sign_reversal": bool(_sign(net) and _sign(int(containment_row["net"])) and _sign(net) != _sign(int(containment_row["net"])))}
    prompts = _prompt_rows(PROMPTS)
    result = {
        "schema": "lv008-result-v1",
        "registered_result": not poststop,
        "analysis_type": "POSTSTOP_USER_AUTHORIZED" if poststop else "REGISTERED",
        "comparisons": comparisons,
        "totals": {arm: sum(row[f"{arm}_semantic"] for row in item_rows) for arm in ARMS},
        "adversarial_refusal_votes": {arm: {"refusals": sum(values), "n": len(values)} for arm, values in adversarial.items()},
        "reader_unanimous_items": {arm: sum(row[f"{arm}_semantic_votes"] in (0, 5) for row in item_rows) for arm in ARMS},
        "judge_answer_disagreements": sum(len(set(values)) > 1 for values in by_blind.values()),
        "block_chars": {arm: _distribution([int(row["arms"][arm]["block_chars"]) for row in prompts]) for arm in ARMS},
        "prompt_tokens": generation["prompt_tokens"],
        "artifacts": {"prompts_sha256": sha256_file(PROMPTS), "answers_sha256": sha256_file(GENERATION), "surface_sha256": sha256_file(BLIND_SURFACE), "mapping_sha256": sha256_file(BLIND_MAPPING), "judgments_sha256": sha256_file(JUDGMENTS)},
        "calls": {"reader": 255, "judge": 720, "preflight_reader": 4, "embedding": 0},
        "claim_boundary": "post-stop descriptive scoring of the sealed Qwen3.8 answers; the registered LV-008 result remains stopped and this is not an adoption claim" if poststop else "selected LoCoMo development fixed-prompt Qwen3.8 rendering probe; no overall score, transfer, optimal renderer, model generality, adoption or production claim",
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
    parser.add_argument("phase", choices=("preflight", "generate", "blind", "blind-poststop", "judge", "analyze", "analyze-poststop"))
    args = parser.parse_args()
    actions = {
        "preflight": run_preflight,
        "generate": run_generation,
        "blind": prepare_blind,
        "blind-poststop": lambda: prepare_blind(poststop=True),
        "judge": run_judging,
        "analyze": analyze,
        "analyze-poststop": lambda: analyze(poststop=True),
    }
    print(json.dumps(actions[args.phase](), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
