"""Exact NF evidence analysis for frozen DA-022 additive allocations."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

SELECTION_SHA256 = "705a156aacb7143f7b23c9b1297701235c1b3c02ec567580f4b81c35e7114bd7"
EDGE_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"


class DA022AnalysisError(RuntimeError):
    pass


def paired(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    gains = sum(not row["CONTROL"] and row["TREATMENT"] for row in rows)
    losses = sum(row["CONTROL"] and not row["TREATMENT"] for row in rows)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / 2**n) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": len(rows) - n, "discordant": n, "two_sided_exact_p": p}


def distribution(values: Sequence[int | float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def _key(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["comparison_key"]), int(row["duplicate_ordinal"])


def _edge_key(question: tuple[str, int], action: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return (*question, str(action["seed_id"]), str(action["neighbor_id"]))


def _delivered(actions: Sequence[Mapping[str, Any]], pairs: Mapping[str, Sequence[str]]) -> set[str]:
    output = set()
    for action in actions:
        if action["kind"] == "PAIR":
            output.update(pairs[str(action["neighbor_id"])])
        elif action["kind"] == "TURN":
            output.add(pairs[str(action["neighbor_id"])][int(action["member"])])
    return output


def analyze(dataset_path: Path, selection_path: Path,
            edge_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(edge_path) != EDGE_SHA256:
        raise DA022AnalysisError("DA-022 sealed input differs")
    selections = {_key(row): row for row in read_gzip(selection_path)}
    edges = {(_key(row)[0], _key(row)[1], str(row["seed_id"]), str(row["neighbor_id"])): row
             for row in read_gzip(edge_path)}
    evidence, pairs, metadata = {}, {}, {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            pairs[source.candidate.identity] = tuple(source.dialogue_ids)
        for question in record.questions:
            key = (question.comparison_key, question.duplicate_ordinal)
            evidence[key] = set(question.resolved_dialogue_ids)
            metadata[key] = (question.sample_id, question.source_index)
    if len(selections) != 1_098 or not set(selections) < set(evidence):
        raise DA022AnalysisError("DA-022 evidence join differs")
    rows = []
    decisive = []
    all_admitted = []
    for key in sorted(selections):
        selection = selections[key]
        direct = set().union(*(pairs[value] for value in selection["direct_ids"]))
        control_links = _delivered(selection["baseline_actions"], pairs)
        admitted = [action for action in selection["treatment"]["additions"]
                    if action["kind"] in {"PAIR", "TURN"}]
        added_links = _delivered(admitted, pairs)
        gold = evidence[key]
        direct_complete = gold <= direct
        control_complete = gold <= direct | control_links
        treatment_complete = gold <= direct | control_links | added_links
        if control_complete and not treatment_complete:
            raise DA022AnalysisError("DA-022 immutable control loss")
        missing = gold - (direct | control_links)
        if treatment_complete and not control_complete and not missing <= added_links:
            raise DA022AnalysisError("DA-022 gain lacks added-carrier accounting")
        action_rows = []
        for action in admitted:
            edge = edges[_edge_key(key, action)]
            carried = set(pairs[str(action["neighbor_id"])]) if action["kind"] == "PAIR" else {
                pairs[str(action["neighbor_id"])][int(action["member"])]}
            item = {"kind": action["kind"], "cost": int(action["cost"]),
                    "position": int(action["position"]),
                    "seed_rank": int(edge["features"]["seed_rank"]),
                    "neighbor_id": str(action["neighbor_id"]),
                    "carries_missing": bool(carried & missing)}
            action_rows.append(item)
            all_admitted.append(item)
            if item["carries_missing"]:
                decisive.append(item)
        rows.append({"comparison_key": key[0], "duplicate_ordinal": key[1],
                     "sample_id": metadata[key][0], "source_index": metadata[key][1],
                     "DIRECT": direct_complete, "CONTROL": control_complete,
                     "TREATMENT": treatment_complete,
                     "recovered_chars": int(selection["treatment"]["recovered_chars"]),
                     "missing_control": sorted(missing), "carried_missing": sorted(missing & added_links),
                     "admitted": action_rows})
    totals = {arm: sum(row[arm] for row in rows) for arm in ("DIRECT", "CONTROL", "TREATMENT")}
    if totals["DIRECT"] != 935 or totals["CONTROL"] != 970:
        raise DA022AnalysisError("DA-022 control anchors differ")
    contrast = paired(rows)
    by_conversation = {}
    for sample_id in sorted({row["sample_id"] for row in rows}):
        cell = [row for row in rows if row["sample_id"] == sample_id]
        by_conversation[sample_id] = {"n": len(cell),
                                      "complete": {arm: sum(row[arm] for row in cell) for arm in totals},
                                      "contrast": paired(cell)}
    mechanism = {"recovered_chars": distribution([row["recovered_chars"] for row in rows]),
                 "admitted_actions": len(all_admitted), "decisive_actions": len(decisive),
                 "admitted_cost": distribution([row["cost"] for row in all_admitted]),
                 "decisive_cost": distribution([row["cost"] for row in decisive]),
                 "admitted_seed_rank": distribution([row["seed_rank"] for row in all_admitted]),
                 "decisive_seed_rank": distribution([row["seed_rank"] for row in decisive]),
                 "admitted_order_position": distribution([row["position"] for row in all_admitted]),
                 "decisive_order_position": distribution([row["position"] for row in decisive])}
    signal = contrast["gains"] >= 5 and contrast["losses"] == 0 and all(
        cell["contrast"]["net"] >= 0 for cell in by_conversation.values())
    result = {"schema": "da022-nf-immutable-pack-result-v1",
              "status": "NF_IMMUTABLE_PACK_CAPACITY_SIGNAL" if signal else "NO_NF_IMMUTABLE_PACK_CAPACITY_SIGNAL",
              "population": len(rows), "complete": totals, "contrast": contrast,
              "by_conversation": by_conversation, "mechanism": mechanism,
              "one_hop_ceiling": 986,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent NF exact availability; joint dictionary reader use untested"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, selection_path: Path, edge_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, selection_path, edge_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da022-result-") as directory:
        replay_result, replay_rows = analyze(dataset_path, selection_path, edge_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA022AnalysisError("DA-022 result replay differs")
    return result


__all__ = ["DA022AnalysisError", "analyze", "paired", "run_analysis"]

