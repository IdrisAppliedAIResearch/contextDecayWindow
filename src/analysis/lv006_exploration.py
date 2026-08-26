"""Part 1 exploration of a parse-safe continuation for LV-005 judging."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_live import JUDGE_SEEDS, _generate
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX
from analysis.tc001_exploration import REPO_ROOT


LV005_ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_005"
ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_006"
SURFACE = LV005_ROOT / "artifacts" / "scoring" / "blind_surface.jsonl.gz"
PARTIAL = LV005_ROOT / "artifacts" / "scoring" / "blind_judgments.jsonl"
OUTPUT = ROOT / "artifacts" / "part1_exploration.json"
FAILED_BLIND_ID = "246c60b934c6ef5407667603029949b115fe9fdced33e7de67f3b15d0e5fd996"
FAILED_SEED = 9006
REPAIR_SUFFIX = "VERDICT:"


def _read_surface() -> list[dict[str, Any]]:
    with gzip.open(SURFACE, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _attempt(item: dict[str, Any], seed: int, *, repair: bool) -> dict[str, Any]:
    prompt = render_judge_prompt(item["question"], item["gold"], item["answer"]) + CLOSED_THINK_SUFFIX
    if repair:
        prompt += REPAIR_SUFFIX
    response = _generate(prompt, seed, judge=True)
    try:
        verdict, reason = parse_judge_verdict(response["text"])
    except Exception:
        parseable, verdict, reason = False, None, None
    else:
        parseable = True
    return {
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "response_sha256": hashlib.sha256(response["text"].encode("utf-8")).hexdigest(),
        "parseable": parseable,
        "verdict": verdict,
        "reason_present": bool(reason),
        "done_reason": response["done_reason"],
        "eval_count": response["eval_count"],
    }


def explore() -> dict[str, Any]:
    surface = _read_surface()
    by_id = {row["blind_id"]: row for row in surface}
    failed = by_id[FAILED_BLIND_ID]
    original = [_attempt(failed, FAILED_SEED, repair=False) for _ in range(2)]
    repaired = [_attempt(failed, FAILED_SEED, repair=True) for _ in range(2)]
    sample_ids = sorted(by_id, key=lambda value: hashlib.sha256(("lv006-part1" + value).encode()).digest())[:12]
    sample = []
    for blind_id in sample_ids:
        for seed in JUDGE_SEEDS:
            attempt = _attempt(by_id[blind_id], seed, repair=True)
            sample.append({"blind_id": blind_id, "seed": seed, **attempt})
    result = {
        "schema": "lv006-part1-exploration-v1",
        "behavioral_identity": (
            "The stopped judge prompt can omit the verdict value after the closed-think "
            "suffix; appending the already-requested literal VERDICT: cue makes the exact "
            "failed prompt and a blinded sample parseable without exposing arm mapping."
        ),
        "inputs": {"surface_sha256": sha256_file(SURFACE), "partial_sha256": sha256_file(PARTIAL), "surface_rows": len(surface)},
        "failed_exact": {
            "blind_id": FAILED_BLIND_ID,
            "seed": FAILED_SEED,
            "original": original,
            "original_byte_identical": original[0]["response_sha256"] == original[1]["response_sha256"],
            "repair": repaired,
            "repair_byte_identical": repaired[0]["response_sha256"] == repaired[1]["response_sha256"],
        },
        "blinded_sample": {
            "ids": len(sample_ids),
            "calls": len(sample),
            "parseable": sum(row["parseable"] for row in sample),
            "naturally_stopped": sum(row["done_reason"] != "length" for row in sample),
            "rows": sample,
        },
        "name_checks": {
            "repair": "append only the literal VERDICT: cue after the frozen closed-think suffix",
            "continuation": "regenerate the whole 960-judgment surface under one repaired prompt; do not mix instruments",
            "blind": "surface only; LV-005 arm mapping is not read",
        },
        "degenerate_states": {
            "original_unparseable": sum(not row["parseable"] for row in original),
            "repair_unparseable": sum(not row["parseable"] for row in repaired),
            "sample_unparseable": sum(not row["parseable"] for row in sample),
            "truncations": sum(row["done_reason"] == "length" for row in original + repaired + sample),
        },
        "calls": {"judge_original": 2, "judge_repair_exact": 2, "judge_repair_sample": len(sample)},
        "mapping_opened": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(explore(), indent=2, sort_keys=True))
