"""Dialogue-level evidence join for DA-006 reserved compact links."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da006_reserved_links import ARMS, DA006Error
from analysis.nf004_anatomy_features import sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

DA004_LABEL_SHA256 = "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca"


def read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def distribution(values: Sequence[int]) -> dict[str, int]:
    array = np.asarray(values, dtype=int)
    return {"p10": int(np.percentile(array, 10, method="nearest")),
            "p50": int(np.percentile(array, 50, method="nearest")),
            "p90": int(np.percentile(array, 90, method="nearest"))}


def run_analysis(dataset_path: Path, blind_path: Path, preflight_path: Path, g6_path: Path,
                 da004_labels_path: Path, output_dir: Path) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(blind_path) != preflight["selection_sha256"]:
        raise DA006Error("Committed DA-006 blind seal is absent or drifted")
    if sha256_file(da004_labels_path) != DA004_LABEL_SHA256:
        raise DA006Error("DA-004 edge labels differ")
    records = adapt_split(dataset_path, HOLDOUT_IDS)
    evidence, candidate_dialogues = {}, {}
    for record in records:
        for source in record.candidates:
            candidate_dialogues[source.candidate.identity] = set(source.dialogue_ids)
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = set(question.resolved_dialogue_ids)
    g6 = json.loads(g6_path.read_text(encoding="utf-8"))["rows"]
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"]) for row in g6}
    old_labels = {(row["comparison_key"], int(row["duplicate_ordinal"]), row["seed_id"], row["neighbor_id"]): row
                  for row in read_gzip(da004_labels_path)}
    joined, direct_questions = [], {}
    for row in read_gzip(blind_path):
        key = (row["comparison_key"], int(row["duplicate_ordinal"]))
        if not primary[key]:
            continue
        edge_key = (*key, row["seed_id"], row["neighbor_id"])
        if edge_key not in old_labels:
            raise DA006Error("DA-006 edge lacks DA-004 label")
        gold = evidence[key]
        direct_dialogues = set().union(*(candidate_dialogues[item] for item in row["direct_ids"]))
        direct_complete = gold <= direct_dialogues
        direct_questions[key] = direct_complete
        arms = {}
        for arm in ARMS:
            blind_arm = row["arms"][arm]
            selected = set(blind_arm["selected_dialogue_ids"])
            complete = gold <= selected
            missing_direct, lost_direct = gold - direct_dialogues, gold & direct_dialogues - selected
            gain, loss = complete and not direct_complete, direct_complete and not complete
            removed_dialogues = set().union(*(candidate_dialogues[item] for item in blind_arm["removed_direct_ids"])) if blind_arm["removed_direct_ids"] else set()
            if gain and (not missing_direct or not missing_direct <= set(blind_arm["linked_dialogue_ids"])):
                raise DA006Error("DA-006 gain lacks linked-dialogue accounting")
            if loss and (not lost_direct or not lost_direct <= removed_dialogues):
                raise DA006Error("DA-006 loss lacks reservation accounting")
            arms[arm] = {"complete": complete, "gain": gain, "loss": loss,
                         "link_carried_gain": gain, "reservation_loss": loss}
        joined.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": row["sample_id"],
                       "source_index": row["source_index"], "seed_id": row["seed_id"], "neighbor_id": row["neighbor_id"],
                       "da004_label": old_labels[edge_key]["label"],
                       "da004_carrier": old_labels[edge_key]["benefit_carrier"], "arms": arms})
    if len(joined) != 25_941 or len(direct_questions) != 1_098 or sum(direct_questions.values()) != 935:
        raise DA006Error("DA-006 primary or direct reproduction differs")
    old_counts = Counter(row["da004_label"] for row in joined)
    if old_counts != Counter({"BENEFIT": 57, "HARM": 40, "NEUTRAL": 25_844}):
        raise DA006Error("DA-004 transition reproduction differs")
    blind_by_key = {(row["comparison_key"], int(row["duplicate_ordinal"]), row["seed_id"], row["neighbor_id"]): row
                    for row in read_gzip(blind_path)}
    matrix = {}
    for arm in ARMS:
        arm_rows = [row["arms"][arm] for row in joined]
        blind_rows = [blind_by_key[(row["comparison_key"], row["duplicate_ordinal"], row["seed_id"], row["neighbor_id"])]["arms"][arm]
                      for row in joined]
        gains, losses = sum(row["gain"] for row in arm_rows), sum(row["loss"] for row in arm_rows)
        by_conversation = {}
        for sample_id in sorted({row["sample_id"] for row in joined}):
            selected = [row for row in joined if row["sample_id"] == sample_id]
            cg = sum(row["arms"][arm]["gain"] for row in selected)
            cl = sum(row["arms"][arm]["loss"] for row in selected)
            by_conversation[sample_id] = {"gains": cg, "losses": cl, "net": cg - cl}
        retained = {carrier: sum(row["da004_label"] == "BENEFIT" and row["da004_carrier"] == carrier and row["arms"][arm]["complete"]
                                 for row in joined) for carrier in ("NEIGHBOR", "DOWNSTREAM")}
        nonnegative = all(value["net"] >= 0 for value in by_conversation.values())
        matrix[arm] = {
            "complete_edge_actions": sum(row["complete"] for row in arm_rows), "gains": gains, "losses": losses,
            "net": gains - losses, "link_admissions": sum(row["link_admitted"] for row in blind_rows),
            "link_carried_gains": sum(row["link_carried_gain"] for row in arm_rows),
            "reservation_losses": sum(row["reservation_loss"] for row in arm_rows),
            "retained_da004_benefits": retained, "by_conversation": by_conversation,
            "chars": {field: distribution([int(row[field]) for row in blind_rows])
                      for field in ("core_chars", "payload_chars", "total_chars", "unused_reserve")},
            "status": "PROTECTED_CAPACITY_SIGNAL" if gains > losses and nonnegative else "NO_PROTECTED_CAPACITY_SIGNAL",
        }
    pair_turn = {}
    for reserve in (256, 512, 1024, 2048):
        pair, turn = f"PAIR_R{reserve}", f"TURN_R{reserve}"
        pair_turn[str(reserve)] = {
            "turn_only_complete": sum(row["arms"][turn]["complete"] and not row["arms"][pair]["complete"] for row in joined),
            "pair_only_complete": sum(row["arms"][pair]["complete"] and not row["arms"][turn]["complete"] for row in joined),
        }
    result = {"schema": "da006-reserved-link-result-v1", "standing": "post-outcome representation diagnostic on spent NF-004 LoCoMo",
              "population": {"questions": len(direct_questions), "edge_actions": len(joined), "direct_complete": sum(direct_questions.values())},
              "matrix": matrix, "pair_turn_discordance": pair_turn,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "availability representation diagnostic only; no reserve, renderer, reader, or adoption"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["run_analysis"]
