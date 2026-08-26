"""Part 1 exploration for live validation of TC-014 opportunity admission."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any, Sequence

import numpy as np

from analysis.hh001_endpoints import contains_gold
from analysis.hh001_prompt import render_reader_prompt, template_manifest
from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from episodic._render import render_stm_payload

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
TC014_SELECTIONS = ROOT / "artifacts" / "tc014" / "preflight" / "selections.jsonl.gz"
TC014_OUTCOMES = ROOT / "artifacts" / "tc014" / "result" / "per_question.csv"
OUTPUT_ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_002"
OUTPUT = OUTPUT_ROOT / "artifacts" / "part1_exploration.json"
TC014_SELECTIONS_SHA256 = "32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7"
TC014_OUTCOMES_SHA256 = "ce73bfcb0b3c9a1d7d94e89023ce7ef7b9fbf928eb44a1669699ec3f37324bb0"
BUDGET = 32_000


class LV002ExplorationError(RuntimeError):
    pass


def _rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(map(json.loads, handle))


def _distribution(values: Sequence[int | float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "min": float(min(values)) if values else None,
        "median": float(median(values)) if values else None,
        "max": float(max(values)) if values else None,
    }


def _gold_rows() -> dict[tuple[str, int], dict[str, Any]]:
    raw = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    result = {}
    for conversation in raw:
        sample_id = str(conversation["sample_id"])
        for source_index, qa in enumerate(conversation["qa"]):
            result[(sample_id, source_index)] = {
                "question": str(qa["question"]),
                "category": int(qa["category"]),
                "gold": str(qa.get("answer") or qa.get("adversarial_answer") or ""),
                "answerable": "answer" in qa,
            }
    return result


def _payload(episodes: Sequence[Any], selected_ids: Sequence[str]) -> str:
    by_id = {episode.identity: episode.record for episode in episodes}
    if len(selected_ids) != len(set(selected_ids)) or not set(selected_ids) <= set(by_id):
        raise LV002ExplorationError("frozen selected identity join failed")
    return render_stm_payload([], [by_id[identifier] for identifier in selected_ids])


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if sha256_file(TC014_SELECTIONS) != TC014_SELECTIONS_SHA256:
        raise LV002ExplorationError("TC-014 selection anchor drift")
    if sha256_file(TC014_OUTCOMES) != TC014_OUTCOMES_SHA256:
        raise LV002ExplorationError("TC-014 outcome anchor drift")

    cases = adapt_development(DATASET_PATH)
    prepared = {}
    for case in cases:
        dummy = np.zeros(1, dtype=np.float32)
        prepared[case.sample_id] = build_episodes(
            case, {pair.text: dummy for pair in case.pairs}
        )
    frozen = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _rows(TC014_SELECTIONS)
    }
    gold = _gold_rows()
    with TC014_OUTCOMES.open(encoding="utf-8", newline="") as handle:
        outcomes = list(csv.DictReader(handle))

    selected: list[dict[str, Any]] = []
    prompt_chars = {"cc80": [], "opportunity": []}
    block_chars = {"cc80": [], "opportunity": []}
    selected_counts = {"cc80": [], "opportunity": []}
    shared_counts: list[int] = []
    symmetric_differences: list[int] = []
    digest_reproductions = 0
    for row in outcomes:
        cc80_complete = row[f"cc80_{BUDGET}_complete"] == "True"
        opportunity_complete = row[f"opportunity_{BUDGET}_complete"] == "True"
        if cc80_complete == opportunity_complete:
            continue
        key = (row["sample_id"], int(row["source_index"]))
        source = frozen[key]["budgets"][str(BUDGET)]
        episodes = prepared[row["sample_id"]]
        payloads = {}
        ids = {}
        prompts = {}
        qa = gold[key]
        for arm in ("cc80", "opportunity"):
            allocation = source[arm]
            ids[arm] = tuple(allocation["selected_ids"])
            payloads[arm] = _payload(episodes, ids[arm])
            digest = hashlib.sha256(payloads[arm].encode("utf-8")).hexdigest()
            if digest != allocation["payload_sha256"] or len(payloads[arm]) != allocation["payload_chars"]:
                raise LV002ExplorationError("frozen payload reproduction failed")
            digest_reproductions += 1
            prompts[arm] = render_reader_prompt(qa["question"], payloads[arm])
            prompt_chars[arm].append(len(prompts[arm]))
            block_chars[arm].append(len(payloads[arm]))
            selected_counts[arm].append(len(ids[arm]))
        shared = set(ids["cc80"]) & set(ids["opportunity"])
        shared_counts.append(len(shared))
        symmetric_differences.append(len(set(ids["cc80"]) ^ set(ids["opportunity"])))
        selected.append(
            {
                "comparison_key": row["question_id"],
                "sample_id": row["sample_id"],
                "source_index": int(row["source_index"]),
                "category": int(qa["category"]),
                "population": row["population"],
                "offline_direction": "opportunity_gain" if opportunity_complete else "opportunity_loss",
                "answerable": bool(qa["answerable"]),
                "question_sha256": hashlib.sha256(qa["question"].encode("utf-8")).hexdigest(),
                "gold_sha256": hashlib.sha256(qa["gold"].encode("utf-8")).hexdigest(),
                "cc80_block_sha256": hashlib.sha256(payloads["cc80"].encode("utf-8")).hexdigest(),
                "opportunity_block_sha256": hashlib.sha256(payloads["opportunity"].encode("utf-8")).hexdigest(),
                "cc80_prompt_sha256": hashlib.sha256(prompts["cc80"].encode("utf-8")).hexdigest(),
                "opportunity_prompt_sha256": hashlib.sha256(prompts["opportunity"].encode("utf-8")).hexdigest(),
                "cc80_gold_contained": contains_gold(payloads["cc80"], qa["gold"]),
                "opportunity_gold_contained": contains_gold(payloads["opportunity"], qa["gold"]),
                "cc80_selected": len(ids["cc80"]),
                "opportunity_selected": len(ids["opportunity"]),
                "shared_selected": len(shared),
                "symmetric_difference": symmetric_differences[-1],
            }
        )

    if len(selected) != 17:
        raise LV002ExplorationError("discordant population drift")
    primary = [row for row in selected if row["answerable"]]
    result = {
        "schema": "lv002-part1-exploration-v1",
        "mechanism_identity": (
            "C0 renders TC-014 full-budget CC80; T1 renders TC-014's 50/50 "
            "CC80-parent fan-out after exact opportunity admission. Only the frozen memory block differs."
        ),
        "anchors": {
            "dataset_sha256": sha256_file(DATASET_PATH),
            "tc014_selections_sha256": sha256_file(TC014_SELECTIONS),
            "tc014_outcomes_sha256": sha256_file(TC014_OUTCOMES),
            "reader_templates": template_manifest().as_dict(),
        },
        "population": {
            "discordant": len(selected),
            "primary_answerable": len(primary),
            "adversarial_secondary": len(selected) - len(primary),
            "offline_opportunity_gains": sum(row["offline_direction"] == "opportunity_gain" for row in selected),
            "offline_opportunity_losses": sum(row["offline_direction"] == "opportunity_loss" for row in selected),
            "primary_by_population": {
                population: sum(row["population"] == population for row in primary)
                for population in ("targeted", "breadth", "other")
            },
        },
        "distributions": {
            "block_chars": {arm: _distribution(values) for arm, values in block_chars.items()},
            "prompt_chars": {arm: _distribution(values) for arm, values in prompt_chars.items()},
            "selected_candidates": {arm: _distribution(values) for arm, values in selected_counts.items()},
            "shared_candidates": _distribution(shared_counts),
            "symmetric_difference": _distribution(symmetric_differences),
        },
        "degenerate_states": {
            "identical_selected_sets": sum(value == 0 for value in symmetric_differences),
            "identical_prompt_digests": sum(row["cc80_prompt_sha256"] == row["opportunity_prompt_sha256"] for row in selected),
            "both_gold_containment_same": sum(row["cc80_gold_contained"] == row["opportunity_gold_contained"] for row in selected),
            "neither_contains_gold": sum(not row["cc80_gold_contained"] and not row["opportunity_gold_contained"] for row in selected),
        },
        "checks": {"payload_digest_reproductions": digest_reproductions, "expected": 34},
        "rows": selected,
        "calls": {"embedding": 0, "reader": 0, "judge": 0},
        "boundary": "Part 1 prompt characterization; no new generation or scoring",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
