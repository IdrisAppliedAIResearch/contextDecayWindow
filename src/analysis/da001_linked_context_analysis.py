"""Exact-evidence join for the DA-001 linked-context exploration."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da001_linked_context import ARMS, DA001Error
from analysis.nf004_anatomy_features import sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split


def _read_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _distribution(values: Sequence[int]) -> dict[str, int]:
    ordered = sorted(values)
    at = lambda fraction: ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction)))]
    return {"min": ordered[0], "p10": at(.1), "p50": at(.5), "p90": at(.9), "max": ordered[-1]}


def run_analysis(
    dataset_path: Path, blind_path: Path, preflight_path: Path, outcome_path: Path, output_dir: Path
) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(blind_path) != preflight["selection_sha256"]:
        raise DA001Error("Committed passing blind selection anchor is absent or drifted")
    blind_rows = _read_rows(blind_path)
    records = adapt_split(dataset_path, HOLDOUT_IDS)
    evidence_by_key = {}
    for record in records:
        dialogue_to_candidate = {
            dialogue_id: source.candidate.identity
            for source in record.candidates for dialogue_id in source.dialogue_ids
        }
        for question in record.questions:
            evidence_by_key[(question.comparison_key, question.duplicate_ordinal)] = {
                dialogue_to_candidate[item] for item in question.resolved_dialogue_ids
            }
    g6_rows = json.loads(outcome_path.read_text(encoding="utf-8"))["rows"]
    g6_by_key = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in g6_rows}
    joined = []
    for row in blind_rows:
        key = (row["comparison_key"], int(row["duplicate_ordinal"]))
        gold = evidence_by_key[key]
        g6 = g6_by_key[key]
        arms = {}
        direct_selected = set(row["arms"]["DIRECT"]["selected_ids"])
        direct_complete = gold <= direct_selected
        if direct_complete != bool(g6["arms"]["P_PAIR_RANK"]["all_evidence"]):
            raise DA001Error("DIRECT exact-evidence replay differs from NF-004")
        for arm in ARMS:
            selected = set(row["arms"][arm]["selected_ids"])
            linked = set(row["arms"][arm]["linked_selected_ids"])
            displaced = set(row["arms"][arm]["displaced_direct_ids"])
            complete = gold <= selected
            missing_direct = gold - direct_selected
            lost_direct = gold & direct_selected - selected
            arms[arm] = {
                "complete": complete, "any": bool(gold & selected),
                "gain": complete and not direct_complete,
                "loss": direct_complete and not complete,
                "gain_carried_by_link": complete and not direct_complete and bool(missing_direct) and missing_direct <= linked,
                "loss_is_displacement": direct_complete and not complete and bool(lost_direct) and lost_direct <= displaced,
            }
        original_class = (
            "PAIR_GAIN" if g6["arms"]["P_PAIR_RANK"]["all_evidence"] and not g6["arms"]["S_SESSION_RANK"]["all_evidence"]
            else "SESSION_RESCUE" if g6["arms"]["S_SESSION_RANK"]["all_evidence"] and not g6["arms"]["P_PAIR_RANK"]["all_evidence"]
            else "CONCORDANT"
        )
        joined.append({
            "comparison_key": row["comparison_key"], "duplicate_ordinal": row["duplicate_ordinal"],
            "sample_id": row["sample_id"], "source_index": row["source_index"],
            "primary_eligible": bool(g6["primary_eligible"]), "original_class": original_class,
            "arms": arms,
        })
    primary = [row for row in joined if row["primary_eligible"]]
    if len(primary) != 1_098:
        raise DA001Error("Primary population differs")
    original = Counter(row["original_class"] for row in primary)
    if original != Counter({"PAIR_GAIN": 140, "SESSION_RESCUE": 48, "CONCORDANT": 910}):
        raise DA001Error("Original NF-004 discordance reproduction differs")
    matrix = {}
    blind_by_key = {(row["comparison_key"], row["duplicate_ordinal"]): row for row in blind_rows}
    for arm in ARMS:
        arm_rows = [row["arms"][arm] for row in primary]
        blind_arm_rows = [blind_by_key[(row["comparison_key"], row["duplicate_ordinal"])] ["arms"][arm] for row in primary]
        matrix[arm] = {
            "complete": sum(row["complete"] for row in arm_rows),
            "any": sum(row["any"] for row in arm_rows),
            "gains_vs_direct": sum(row["gain"] for row in arm_rows),
            "losses_vs_direct": sum(row["loss"] for row in arm_rows),
            "net_vs_direct": sum(row["gain"] for row in arm_rows) - sum(row["loss"] for row in arm_rows),
            "link_carried_gains": sum(row["gain_carried_by_link"] for row in arm_rows),
            "displacement_losses": sum(row["loss_is_displacement"] for row in arm_rows),
            "original_pair_gains_retained": sum(
                row["original_class"] == "PAIR_GAIN" and row["arms"][arm]["complete"] for row in primary
            ),
            "original_session_rescues_recovered": sum(
                row["original_class"] == "SESSION_RESCUE" and row["arms"][arm]["complete"] for row in primary
            ),
            "linked_admissions": _distribution([int(row["linked_admissions"]) for row in blind_arm_rows]),
            "linked_chars": _distribution([int(row["linked_chars"]) for row in blind_arm_rows]),
            "displaced_count": _distribution([int(row["displaced_count"]) for row in blind_arm_rows]),
            "by_conversation": {
                sample_id: {
                    "complete": sum(
                        row["arms"][arm]["complete"] for row in primary if row["sample_id"] == sample_id
                    ),
                    "gains": sum(
                        row["arms"][arm]["gain"] for row in primary if row["sample_id"] == sample_id
                    ),
                    "losses": sum(
                        row["arms"][arm]["loss"] for row in primary if row["sample_id"] == sample_id
                    ),
                    "linked_admissions": _distribution([
                        int(blind_by_key[(row["comparison_key"], row["duplicate_ordinal"])]["arms"][arm]["linked_admissions"])
                        for row in primary if row["sample_id"] == sample_id
                    ]),
                    "linked_chars": _distribution([
                        int(blind_by_key[(row["comparison_key"], row["duplicate_ordinal"])]["arms"][arm]["linked_chars"])
                        for row in primary if row["sample_id"] == sample_id
                    ]),
                    "displaced_count": _distribution([
                        int(blind_by_key[(row["comparison_key"], row["duplicate_ordinal"])]["arms"][arm]["displaced_count"])
                        for row in primary if row["sample_id"] == sample_id
                    ]),
                }
                for sample_id in sorted({row["sample_id"] for row in primary})
            },
        }
    result = {
        "schema": "da001-linked-context-result-v1",
        "standing": "post-outcome light exploration on spent NF-004 LoCoMo holdout",
        "population": {"primary": len(primary), "original_classes": dict(sorted(original.items()))},
        "matrix": matrix,
        "calls": {"embedding": 0, "model": 0, "cache_misses": 0},
        "claim_boundary": "availability architecture feasibility only; no selector, reader, or adoption",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["run_analysis"]
