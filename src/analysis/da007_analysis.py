"""Exact evidence analysis for DA-007 immutable-prefix reserves."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from analysis.da006_reserved_links import ARMS, read_gzip
from analysis.da007_immutable_prefix import DA007Error
from analysis.nf004_anatomy_features import sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

DA004_LABEL_SHA256 = "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca"


def distribution(values: Sequence[int]) -> dict[str, int]:
    array = np.asarray(values, dtype=int)
    return {"p10": int(np.percentile(array, 10, method="nearest")),
            "p50": int(np.percentile(array, 50, method="nearest")),
            "p90": int(np.percentile(array, 90, method="nearest"))}


def run_analysis(dataset_path: Path, blind_path: Path, preflight_path: Path, g6_path: Path,
                 da004_labels_path: Path, output_dir: Path) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(blind_path) != preflight["selection_sha256"]:
        raise DA007Error("Committed DA-007 blind seal is absent or drifted")
    if sha256_file(da004_labels_path) != DA004_LABEL_SHA256:
        raise DA007Error("DA-004 labels differ")
    evidence, candidate_dialogues = {}, {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            candidate_dialogues[source.candidate.identity] = set(source.dialogue_ids)
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = set(question.resolved_dialogue_ids)
    g6 = json.loads(g6_path.read_text(encoding="utf-8"))["rows"]
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"]) for row in g6}
    old = {(row["comparison_key"], int(row["duplicate_ordinal"]), row["seed_id"], row["neighbor_id"]): row
           for row in read_gzip(da004_labels_path)}
    rows, direct_questions = [], {}
    blind_primary = []
    for row in read_gzip(blind_path):
        key = (row["comparison_key"], int(row["duplicate_ordinal"]))
        if not primary[key]:
            continue
        edge_key = (*key, row["seed_id"], row["neighbor_id"])
        gold = evidence[key]
        direct_dialogues = set().union(*(candidate_dialogues[item] for item in row["direct_ids"]))
        direct_complete = gold <= direct_dialogues
        direct_questions[key] = direct_complete
        arms = {}
        for arm in ARMS:
            blind_arm = row["arms"][arm]
            core_dialogues = set().union(*(candidate_dialogues[item] for item in blind_arm["core_ids"]))
            selected = core_dialogues | set(blind_arm["linked_dialogue_ids"])
            complete = gold <= selected
            gain, loss = complete and not direct_complete, direct_complete and not complete
            missing, lost = gold - direct_dialogues, gold & direct_dialogues - selected
            removed_dialogues = set().union(*(candidate_dialogues[item] for item in blind_arm["removed_direct_ids"]))
            if gain and (not missing or not missing <= set(blind_arm["linked_dialogue_ids"])):
                raise DA007Error("DA-007 gain lacks linked accounting")
            if loss and (not lost or not lost <= removed_dialogues):
                raise DA007Error("DA-007 loss lacks suffix accounting")
            arms[arm] = {"complete": complete, "gain": gain, "loss": loss}
        rows.append({"sample_id": row["sample_id"], "key": edge_key,
                     "da004_label": old[edge_key]["label"], "da004_carrier": old[edge_key]["benefit_carrier"], "arms": arms})
        blind_primary.append(row)
    if len(rows) != 25_941 or len(direct_questions) != 1_098 or sum(direct_questions.values()) != 935:
        raise DA007Error("DA-007 population or direct control differs")
    if Counter(row["da004_label"] for row in rows) != Counter({"BENEFIT": 57, "HARM": 40, "NEUTRAL": 25_844}):
        raise DA007Error("DA-004 labels do not reproduce")
    matrix = {}
    for arm in ARMS:
        outcomes = [row["arms"][arm] for row in rows]
        blind_arms = [row["arms"][arm] for row in blind_primary]
        gains, losses = sum(row["gain"] for row in outcomes), sum(row["loss"] for row in outcomes)
        by_conversation = {}
        for sample_id in sorted({row["sample_id"] for row in rows}):
            selected = [row for row in rows if row["sample_id"] == sample_id]
            cg, cl = sum(row["arms"][arm]["gain"] for row in selected), sum(row["arms"][arm]["loss"] for row in selected)
            by_conversation[sample_id] = {"gains": cg, "losses": cl, "net": cg - cl}
        matrix[arm] = {"complete_edge_actions": sum(row["complete"] for row in outcomes),
                       "gains": gains, "losses": losses, "net": gains - losses,
                       "link_admissions": sum(row["link_admitted"] for row in blind_arms),
                       "link_carried_gains": gains, "suffix_losses": losses,
                       "retained_da004_benefits": {carrier: sum(row["da004_label"] == "BENEFIT" and row["da004_carrier"] == carrier and row["arms"][arm]["complete"]
                                                                    for row in rows) for carrier in ("NEIGHBOR", "DOWNSTREAM")},
                       "by_conversation": by_conversation,
                       "chars": {field: distribution([int(row[field]) for row in blind_arms])
                                 for field in ("core_chars", "payload_chars", "total_chars", "unused_reserve")},
                       "status": "PROTECTED_CAPACITY_SIGNAL" if gains > losses and all(value["net"] >= 0 for value in by_conversation.values())
                       else "NO_PROTECTED_CAPACITY_SIGNAL"}
    discordance = {}
    for reserve in (256, 512, 1024, 2048):
        pair, turn = f"PAIR_R{reserve}", f"TURN_R{reserve}"
        discordance[str(reserve)] = {"turn_only_complete": sum(row["arms"][turn]["complete"] and not row["arms"][pair]["complete"] for row in rows),
                                     "pair_only_complete": sum(row["arms"][pair]["complete"] and not row["arms"][turn]["complete"] for row in rows)}
    result = {"schema": "da007-prefix-result-v1", "standing": "post-outcome representation diagnostic on spent NF-004 LoCoMo",
              "population": {"questions": len(direct_questions), "edge_actions": len(rows), "direct_complete": sum(direct_questions.values())},
              "matrix": matrix, "pair_turn_discordance": discordance,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "availability diagnostic only; no reserve, renderer, reader, or adoption"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["run_analysis"]
