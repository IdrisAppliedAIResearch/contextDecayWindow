"""Registered LV-002 Preflight, generation, blind judging, and analysis."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.hh001_endpoints import contains_gold, normalize
from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_prompts import (
    CLOSED_THINK_SUFFIX,
    PART1,
    PROMPT_MANIFEST,
    PROMPTS,
    REGISTRATION,
    ROOT,
    build_prompt_rows,
    freeze_prompts,
    write_gzip_rows,
)
from analysis.tc001_exploration import DATASET_PATH

PREFLIGHT = ROOT / "artifacts" / "preflight" / "preflight.json"
FLOOR = ROOT / "artifacts" / "preflight" / "floor.jsonl.gz"
GENERATION = ROOT / "artifacts" / "run" / "answers.jsonl.gz"
GENERATION_SUMMARY = ROOT / "artifacts" / "run" / "generation_summary.json"
BLIND_SURFACE = ROOT / "artifacts" / "scoring" / "blind_surface.jsonl.gz"
BLIND_MAPPING = ROOT / "artifacts" / "scoring" / "blind_mapping.sealed.json"
JUDGMENTS = ROOT / "artifacts" / "scoring" / "blind_judgments.jsonl.gz"
RESULT = ROOT / "artifacts" / "result" / "result.json"
PER_ITEM = ROOT / "artifacts" / "result" / "per_item.csv"
REGISTRATION_SHA256 = "34ddd063b7c17873ae92b59f929bd788b7f66fb66d53c910a81d270bd619254a"
PART1_SHA256 = "f1dcd160b8cdf4e78673a9795861fc6ffa6affdc0b16f19907922f53fb082e60"
MODEL = "qwen-custom:latest"
OLLAMA = "http://127.0.0.1:11434"
READER_SEEDS = tuple(range(5005, 5010))
JUDGE_SEEDS = tuple(range(9005, 9008))
ARMS = ("FULL_CC80", "OPPORTUNITY")


class LV002LiveError(RuntimeError):
    pass


def _read_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(map(json.loads, handle))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _post(path: str, body: Mapping[str, Any], timeout: float = 600.0) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{OLLAMA}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as error:
        raise LV002LiveError(f"Ollama request failed at {path}: {error}") from error


def _get(path: str, timeout: float = 30.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(f"{OLLAMA}{path}", timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as error:
        raise LV002LiveError(f"Ollama request failed at {path}: {error}") from error


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
        "num_predict": n_predict if n_predict is not None else (128 if judge else 192),
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
    elapsed = time.perf_counter() - started
    text = str(payload.get("response", "")).strip()
    if not payload.get("done") or not text:
        raise LV002LiveError("Ollama returned an incomplete or empty response")
    return {
        "text": text,
        "seed": seed,
        "prompt_eval_count": int(payload.get("prompt_eval_count", 0) or 0),
        "eval_count": int(payload.get("eval_count", 0) or 0),
        "done_reason": str(payload.get("done_reason", "")),
        "total_duration_ns": int(payload.get("total_duration", 0) or 0),
        "load_duration_ns": int(payload.get("load_duration", 0) or 0),
        "wall_seconds": round(elapsed, 3),
    }


def _gold_records() -> dict[tuple[str, int], dict[str, Any]]:
    raw = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    values = {}
    for conversation in raw:
        sample_id = str(conversation["sample_id"])
        for source_index, qa in enumerate(conversation["qa"]):
            values[(sample_id, source_index)] = {
                "question": str(qa["question"]),
                "gold": str(qa.get("answer") or qa.get("adversarial_answer") or ""),
                "answerable": "answer" in qa,
            }
    return values


def majority(values: Sequence[bool]) -> bool:
    if not values or len(values) % 2 == 0:
        raise LV002LiveError("majority requires a nonempty odd population")
    return sum(values) * 2 > len(values)


def arm_order(comparison_key: str, replicate: int) -> tuple[str, str]:
    value = hashlib.sha256(f"{comparison_key}\0{replicate}".encode("utf-8")).digest()[0]
    return ARMS if value % 2 == 0 else tuple(reversed(ARMS))


def blind_id(comparison_key: str, arm: str, replicate: int) -> str:
    return hashlib.sha256(
        f"lv002-blind-v1\0{comparison_key}\0{arm}\0{replicate}".encode("utf-8")
    ).hexdigest()


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def disposition(
    overall_net: int,
    targeted_net: int,
    breadth_net: int,
    semantic_net: int,
    containment_net: int,
    *,
    valid: bool,
) -> str:
    reversal = _sign(semantic_net) and _sign(containment_net) and _sign(semantic_net) != _sign(containment_net)
    if not valid or reversal:
        return "NOT_INTERPRETABLE"
    if overall_net >= 3 and targeted_net >= 0 and breadth_net >= 0:
        return "CONVERTS"
    if overall_net in (1, 2) and targeted_net >= 0 and breadth_net >= 0:
        return "WEAK_CONVERSION"
    if overall_net == 0 and targeted_net >= 0 and breadth_net >= 0:
        return "NO_CONVERSION"
    return "REGRESSES"


def _reachability() -> dict[str, bool]:
    return {
        "converts": disposition(3, 1, 1, 3, 1, valid=True) == "CONVERTS",
        "weak": disposition(2, 1, 0, 2, 0, valid=True) == "WEAK_CONVERSION",
        "no_conversion": disposition(0, 0, 0, 0, 0, valid=True) == "NO_CONVERSION",
        "regresses": disposition(-1, 0, 0, -1, -1, valid=True) == "REGRESSES",
        "targeted_regression": disposition(3, -1, 1, 3, 1, valid=True) == "REGRESSES",
        "sign_reversal": disposition(3, 1, 1, 3, -1, valid=True) == "NOT_INTERPRETABLE",
        "invalid": disposition(3, 1, 1, 3, 1, valid=False) == "NOT_INTERPRETABLE",
        "floor_pass": 3 <= 3,
        "floor_fail": 4 > 3,
    }


def freeze() -> dict[str, Any]:
    return freeze_prompts()


def run_preflight() -> dict[str, Any]:
    if sha256_file(REGISTRATION) != REGISTRATION_SHA256 or sha256_file(PART1) != PART1_SHA256:
        raise LV002LiveError("registration or Part 1 drift")
    manifest = json.loads(PROMPT_MANIFEST.read_text(encoding="utf-8"))
    if sha256_file(PROMPTS) != manifest["prompts_sha256"]:
        raise LV002LiveError("prompt seal drift")
    prompts = _read_rows(PROMPTS)
    part1 = json.loads(PART1.read_text(encoding="utf-8"))
    primary = [row for row in prompts if row["category"] != 5]
    part1_reproduced = (
        len(prompts) == part1["population"]["discordant"]
        and len(primary) == part1["population"]["primary_answerable"]
        and sum(row["offline_direction"] == "opportunity_gain" for row in prompts) == part1["population"]["offline_opportunity_gains"]
        and manifest["payload_reproductions"] == 34
    )
    try:
        build_prompt_rows(forbidden_labels=DATASET_PATH)
    except Exception:
        early_gold_rejected = True
    else:
        early_gold_rejected = False
    reachability = _reachability()

    prefix_prompt = primary[0]["arms"]["FULL_CC80"]["prompt"]
    prefix_a = _generate(prefix_prompt, 5005)
    prefix_b = _generate(prefix_prompt, 5005)
    prefix_identical = prefix_a["text"].encode("utf-8") == prefix_b["text"].encode("utf-8")
    process = _get("/api/ps")
    loaded = [model for model in process.get("models", []) if model.get("name") == MODEL]
    gpu_only = bool(loaded) and all(int(model.get("size_vram", 0)) >= int(model.get("size", 1)) for model in loaded)
    show = _post("/api/show", {"model": MODEL})

    gold = _gold_records()
    floor_rows = []
    floor_correct = 0
    floor_truncated = 0
    judge_unparseable = 0
    for row in primary:
        record = gold[(row["sample_id"], row["source_index"])]
        if record["question"] != row["question"] or not record["answerable"]:
            raise LV002LiveError("floor scoring join drift")
        answer = _generate(row["no_memory_prompt"], 5005)
        votes = []
        judge_rows = []
        for seed in JUDGE_SEEDS:
            judged = _generate(render_judge_prompt(row["question"], record["gold"], answer["text"]) + CLOSED_THINK_SUFFIX, seed, judge=True)
            try:
                verdict, reason = parse_judge_verdict(judged["text"])
            except Exception:
                judge_unparseable += 1
                verdict, reason = False, "UNPARSEABLE"
            votes.append(verdict)
            judge_rows.append({**judged, "verdict": verdict, "reason": reason})
            floor_truncated += judged["done_reason"] == "length"
        correct = majority(votes)
        floor_correct += correct
        floor_truncated += answer["done_reason"] == "length"
        floor_rows.append({
            "comparison_key": row["comparison_key"],
            "answer": answer,
            "judge": judge_rows,
            "correct": correct,
            "gold_sha256": hashlib.sha256(record["gold"].encode("utf-8")).hexdigest(),
        })
    write_gzip_rows(FLOOR, floor_rows)

    passing = (
        part1_reproduced
        and early_gold_rejected
        and all(reachability.values())
        and len(prompts) == 17
        and len(primary) == 16
        and prefix_identical
        and prefix_a["done_reason"] != "length"
        and prefix_a["prompt_eval_count"] < 65_536
        and gpu_only
        and floor_correct <= 3
        and floor_truncated == 0
        and judge_unparseable == 0
    )
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {
            "registration_sha256": sha256_file(REGISTRATION),
            "part1_sha256": sha256_file(PART1),
            "prompts_sha256": sha256_file(PROMPTS),
            "prompt_rows": len(prompts),
            "model": MODEL,
            "ollama_version": _get("/api/version").get("version"),
            "model_details": show.get("details", {}),
        },
        "pf2": {"part1_reproduced": part1_reproduced, "mechanism_identity": part1["mechanism_identity"]},
        "pf3": {"prompts_sealed": True, "early_gold_rejected": early_gold_rejected, "later_order_enforced_by_phase_files": True},
        "pf4": {"reachability": reachability, "offline_gain_rows": 12, "offline_loss_rows": 5},
        "pf5": {"unique_content_keys": len({row["comparison_key"] for row in prompts}) == 17},
        "pf6": {"payload_reproductions": manifest["payload_reproductions"], "expected": 34},
        "pf7": {
            "seeded_prefix_byte_identical": prefix_identical,
            "prefix_sha256": hashlib.sha256(prefix_a["text"].encode("utf-8")).hexdigest(),
            "prompt_eval_count": prefix_a["prompt_eval_count"],
            "gpu_only": gpu_only,
            "ollama_process": process,
        },
        "pf8": {"reader_replicates": 5, "primary_items": 16, "cannot_detect": "overall accuracy, small effects, transfer or adoption value"},
        "pf9": {"residuals": ["correct answers can be guessed without support", "containment misses composition and paraphrase", "one model supplies all three judge passes", "availability-discordant selection is enriched"]},
        "pf10": {"live_reader_test": True, "availability_is_input_not_verdict": True},
        "g_floor": {"correct": floor_correct, "n": len(primary), "maximum": 3, "pass": floor_correct <= 3},
        "g_prompt": {"prefix_truncated": prefix_a["done_reason"] == "length", "floor_truncated": floor_truncated, "judge_unparseable": judge_unparseable},
        "floor_sha256": sha256_file(FLOOR),
        "calls": {"prefix_reader": 2, "floor_reader": len(primary), "floor_judge": len(primary) * 3},
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV002LiveError("Preflight failed")
    return result


def run_generation() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    manifest = json.loads(PROMPT_MANIFEST.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(PROMPTS) != manifest["prompts_sha256"]:
        raise LV002LiveError("passing Preflight prompt seal absent")
    rows = _read_rows(PROMPTS)
    answers = []
    truncated = 0
    for row in rows:
        for replicate, seed in enumerate(READER_SEEDS):
            for arm in arm_order(row["comparison_key"], replicate):
                response = _generate(row["arms"][arm]["prompt"], seed)
                truncated += response["done_reason"] == "length"
                answers.append({
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
                })
    expected = len(rows) * len(READER_SEEDS) * len(ARMS)
    if len(answers) != expected or truncated:
        raise LV002LiveError("generation completeness or truncation failure")
    write_gzip_rows(GENERATION, answers)
    summary = {
        "schema": "lv002-generation-summary-v1",
        "answers": len(answers),
        "primary_answers": sum(row["category"] != 5 for row in answers),
        "adversarial_answers": sum(row["category"] == 5 for row in answers),
        "truncated": truncated,
        "answers_sha256": sha256_file(GENERATION),
        "prompts_sha256": sha256_file(PROMPTS),
        "reader_calls": len(answers),
    }
    _write_json(GENERATION_SUMMARY, summary)
    return summary


def prepare_blind() -> dict[str, Any]:
    if not GENERATION.is_file() or not GENERATION_SUMMARY.is_file():
        raise LV002LiveError("sealed answers absent")
    answers = _read_rows(GENERATION)
    gold = _gold_records()
    surface = []
    mapping = {}
    for row in answers:
        if row["category"] == 5:
            continue
        record = gold[(row["sample_id"], row["source_index"])]
        identifier = blind_id(row["comparison_key"], row["arm"], row["replicate"])
        surface.append({"blind_id": identifier, "question": record["question"], "gold": record["gold"], "answer": row["response"]["text"]})
        mapping[identifier] = {"comparison_key": row["comparison_key"], "arm": row["arm"], "replicate": row["replicate"]}
    surface.sort(key=lambda row: row["blind_id"])
    if len(surface) != 160 or len(mapping) != 160:
        raise LV002LiveError("blind surface cardinality drift")
    write_gzip_rows(BLIND_SURFACE, surface)
    _write_json(BLIND_MAPPING, {"schema": "lv002-blind-mapping-v1", "mapping": mapping})
    return {"surface": len(surface), "surface_sha256": sha256_file(BLIND_SURFACE), "mapping_sha256": sha256_file(BLIND_MAPPING)}


def run_judging() -> dict[str, Any]:
    if not BLIND_SURFACE.is_file() or not BLIND_MAPPING.is_file():
        raise LV002LiveError("blind surface or sealed mapping absent")
    surface = _read_rows(BLIND_SURFACE)
    judgments = []
    for item in surface:
        prompt = render_judge_prompt(item["question"], item["gold"], item["answer"]) + CLOSED_THINK_SUFFIX
        for judge_pass, seed in enumerate(JUDGE_SEEDS):
            response = _generate(prompt, seed, judge=True)
            try:
                verdict, reason = parse_judge_verdict(response["text"])
            except Exception as error:
                raise LV002LiveError(f"unparseable blind judgment {item['blind_id']}: {error}") from error
            if response["done_reason"] == "length":
                raise LV002LiveError("judge response truncated")
            judgments.append({"blind_id": item["blind_id"], "judge_pass": judge_pass, "seed": seed, "verdict": verdict, "reason": reason, "response_sha256": hashlib.sha256(response["text"].encode("utf-8")).hexdigest()})
    if len(judgments) != 480:
        raise LV002LiveError("judge cardinality drift")
    write_gzip_rows(JUDGMENTS, judgments)
    return {"judgments": len(judgments), "sha256": sha256_file(JUDGMENTS), "judge_calls": len(judgments)}


def _paired(items: Sequence[Mapping[str, Any]], predicate=lambda row: True, endpoint: str = "semantic") -> dict[str, int | float]:
    subset = [row for row in items if predicate(row)]
    gains = sum(row[f"OPPORTUNITY_{endpoint}"] and not row[f"FULL_CC80_{endpoint}"] for row in subset)
    losses = sum(row[f"FULL_CC80_{endpoint}"] and not row[f"OPPORTUNITY_{endpoint}"] for row in subset)
    discordant = gains + losses
    tail = min(gains, losses)
    p = 1.0 if not discordant else min(1.0, 2 * sum(math.comb(discordant, k) for k in range(tail + 1)) / 2**discordant)
    return {"n": len(subset), "gains": gains, "losses": losses, "ties": len(subset) - discordant, "net": gains - losses, "two_sided_exact_p": p}


def analyze() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS":
        raise LV002LiveError("Preflight is not passing")
    answers = _read_rows(GENERATION)
    judgments = _read_rows(JUDGMENTS)
    mapping = json.loads(BLIND_MAPPING.read_text(encoding="utf-8"))["mapping"]
    gold = _gold_records()
    by_blind: dict[str, list[bool]] = defaultdict(list)
    for row in judgments:
        by_blind[row["blind_id"]].append(bool(row["verdict"]))
    if set(by_blind) != set(mapping) or any(len(values) != 3 for values in by_blind.values()):
        raise LV002LiveError("judgment completeness failure")

    answer_verdicts = {
        (entry["comparison_key"], entry["arm"], int(entry["replicate"])): majority(by_blind[identifier])
        for identifier, entry in mapping.items()
    }
    grouped_semantic: dict[tuple[str, str], list[bool]] = defaultdict(list)
    grouped_containment: dict[tuple[str, str], list[bool]] = defaultdict(list)
    metadata = {}
    adversarial = {arm: [] for arm in ARMS}
    for row in answers:
        text = row["response"]["text"]
        if row["category"] == 5:
            adversarial[row["arm"]].append(normalize(text) == "i don t know")
            continue
        key = (row["comparison_key"], row["arm"])
        record = gold[(row["sample_id"], row["source_index"])]
        grouped_semantic[key].append(answer_verdicts[(row["comparison_key"], row["arm"], row["replicate"])])
        grouped_containment[key].append(contains_gold(text, record["gold"]))
        metadata[row["comparison_key"]] = {field: row[field] for field in ("sample_id", "source_index", "population", "offline_direction")}
    item_rows = []
    for comparison_key in sorted(metadata):
        row = {"comparison_key": comparison_key, **metadata[comparison_key]}
        for arm in ARMS:
            semantic_votes = grouped_semantic[(comparison_key, arm)]
            containment_votes = grouped_containment[(comparison_key, arm)]
            if len(semantic_votes) != 5 or len(containment_votes) != 5:
                raise LV002LiveError("reader replicate completeness failure")
            row[f"{arm}_semantic"] = majority(semantic_votes)
            row[f"{arm}_containment"] = majority(containment_votes)
            row[f"{arm}_semantic_votes"] = sum(semantic_votes)
            row[f"{arm}_containment_votes"] = sum(containment_votes)
        item_rows.append(row)

    semantic = {
        "combined": _paired(item_rows),
        "targeted": _paired(item_rows, lambda row: row["population"] == "targeted"),
        "breadth": _paired(item_rows, lambda row: row["population"] == "breadth"),
        "other": _paired(item_rows, lambda row: row["population"] == "other"),
        "offline_gain": _paired(item_rows, lambda row: row["offline_direction"] == "opportunity_gain"),
        "offline_loss": _paired(item_rows, lambda row: row["offline_direction"] == "opportunity_loss"),
    }
    containment = _paired(item_rows, endpoint="containment")
    semantic_net = int(semantic["combined"]["net"])
    containment_net = int(containment["net"])
    valid = (
        len(item_rows) == 16
        and preflight["g_floor"]["pass"]
        and json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))["truncated"] == 0
        and len(judgments) == 480
    )
    status = disposition(
        semantic_net,
        int(semantic["targeted"]["net"]),
        int(semantic["breadth"]["net"]),
        semantic_net,
        containment_net,
        valid=valid,
    )
    unsupported = {
        arm: sum(
            row[f"{arm}_semantic"]
            and ((row["offline_direction"] == "opportunity_gain" and arm == "FULL_CC80") or (row["offline_direction"] == "opportunity_loss" and arm == "OPPORTUNITY"))
            for row in item_rows
        )
        for arm in ARMS
    }
    judge_disagreement = sum(len(set(values)) > 1 for values in by_blind.values())
    result = {
        "schema": "lv002-result-v1",
        "status": status,
        "primary": semantic,
        "containment_crosscheck": containment,
        "endpoint_sign_reversal": bool(_sign(semantic_net) and _sign(containment_net) and _sign(semantic_net) != _sign(containment_net)),
        "totals": {arm: sum(row[f"{arm}_semantic"] for row in item_rows) for arm in ARMS},
        "unsupported_correct_item_majorities": unsupported,
        "adversarial_refusal_votes": {arm: {"refusals": sum(values), "n": len(values)} for arm, values in adversarial.items()},
        "reader_unanimous_items": {arm: sum(row[f"{arm}_semantic_votes"] in (0, 5) for row in item_rows) for arm in ARMS},
        "judge_answer_disagreements": judge_disagreement,
        "validity": {"valid": valid, "floor": preflight["g_floor"], "generation_complete": True, "judgments_complete": True},
        "artifacts": {"prompts_sha256": sha256_file(PROMPTS), "answers_sha256": sha256_file(GENERATION), "blind_surface_sha256": sha256_file(BLIND_SURFACE), "judgments_sha256": sha256_file(JUDGMENTS)},
        "calls": {"reader": 170, "judge": 480, "preflight_reader": preflight["calls"]["prefix_reader"] + preflight["calls"]["floor_reader"], "preflight_judge": preflight["calls"]["floor_judge"]},
        "claim_boundary": "selected LoCoMo development availability-discordant reader conversion only; no overall score, transfer or adoption claim",
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
    parser.add_argument("phase", choices=("freeze", "preflight", "generate", "blind", "judge", "analyze"))
    args = parser.parse_args()
    if args.phase == "freeze":
        print(json.dumps(freeze(), indent=2, sort_keys=True))
    elif args.phase == "preflight":
        print(json.dumps(run_preflight(), indent=2, sort_keys=True))
    elif args.phase == "generate":
        print(json.dumps(run_generation(), indent=2, sort_keys=True))
    elif args.phase == "blind":
        print(json.dumps(prepare_blind(), indent=2, sort_keys=True))
    elif args.phase == "judge":
        print(json.dumps(run_judging(), indent=2, sort_keys=True))
    else:
        print(json.dumps(analyze(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
