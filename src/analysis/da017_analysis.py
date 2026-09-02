"""Exact NF-004 evidence analysis for frozen DA-017 allocations."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.nf004_anatomy_features import sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

ALLOCATION_SHA256 = "877058e2d2499bb62f3d40ac28dbe4f6f1bc168467d42b16e37b3ace934c1146"
CONTROL_SHA256 = "d69a5e1a1585f0e1988bb6599af9fd53d2d84c5d4d70e3783d96c6427839d9b8"


class DA017AnalysisError(RuntimeError):
    pass


def _qkey(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["comparison_key"]), int(row["duplicate_ordinal"])


def _paired(rows: Sequence[Mapping[str, Any]], left: str, right: str) -> dict[str, Any]:
    gains = sum(not row[left] and row[right] for row in rows)
    losses = sum(row[left] and not row[right] for row in rows)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / (2**n)) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": len(rows) - n, "discordant": n, "two_sided_exact_p": p}


def analyze(dataset_path: Path, allocation_path: Path,
            control_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(allocation_path) != ALLOCATION_SHA256 or sha256_file(control_path) != CONTROL_SHA256:
        raise DA017AnalysisError("DA-017 sealed input differs")
    allocations = {_qkey(row): row for row in read_gzip(allocation_path)}
    controls = {_qkey(row): row for row in read_gzip(control_path)}
    evidence = {}
    dialogues = {}
    metadata = {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            dialogues[source.candidate.identity] = tuple(source.dialogue_ids)
        for question in record.questions:
            key = (question.comparison_key, question.duplicate_ordinal)
            evidence[key] = set(question.resolved_dialogue_ids)
            metadata[key] = {"sample_id": question.sample_id, "source_index": question.source_index}
    if set(allocations) != set(controls) or not set(allocations) < set(evidence) or len(evidence) != 1_104:
        raise DA017AnalysisError("DA-017 evidence join differs")
    rows = []
    for key in sorted(allocations):
        allocation, control = allocations[key], controls[key]
        direct_dialogues = set().union(*(dialogues[value] for value in allocation["direct_ids"]))
        linked = set()
        admitted = []
        for action in allocation["actions"]:
            if action["kind"] == "PAIR":
                carried = set(dialogues[action["neighbor_id"]])
            elif action["kind"] == "TURN":
                carried = {dialogues[action["neighbor_id"]][int(action["member"])]}
            else:
                continue
            linked.update(carried)
            admitted.append({"neighbor_id": action["neighbor_id"], "kind": action["kind"],
                             "member": action["member"], "carried_dialogues": sorted(carried)})
        gold = evidence[key]
        direct_complete = gold <= direct_dialogues
        control_complete = bool(control["arms"]["PAIR_THEN_TURN"]["complete"])
        treatment = gold <= direct_dialogues | linked
        missing = gold - direct_dialogues
        if treatment and not direct_complete and not missing <= linked:
            raise DA017AnalysisError("DA-017 gain lacks exact carrier accounting")
        if direct_complete and not treatment:
            raise DA017AnalysisError("DA-017 lost protected direct evidence")
        rows.append({"comparison_key": key[0], "duplicate_ordinal": key[1],
                     "sample_id": metadata[key]["sample_id"], "source_index": metadata[key]["source_index"],
                     "DIRECT": direct_complete, "DA010_CONTROL": control_complete,
                     "DA017_PHRASE_LINKS": treatment, "missing_direct": sorted(missing),
                     "carried_missing": sorted(missing & linked), "admitted": admitted})
    totals = {arm: sum(row[arm] for row in rows) for arm in ("DIRECT", "DA010_CONTROL", "DA017_PHRASE_LINKS")}
    if totals["DIRECT"] != 935 or totals["DA010_CONTROL"] != 970:
        raise DA017AnalysisError("DA-017 control reproduction differs")
    contrast = _paired(rows, "DA010_CONTROL", "DA017_PHRASE_LINKS")
    by_conversation = {}
    for sample_id in sorted({row["sample_id"] for row in rows}):
        cell = [row for row in rows if row["sample_id"] == sample_id]
        by_conversation[sample_id] = {"n": len(cell), **{arm: sum(row[arm] for row in cell) for arm in totals},
                                      "contrast": _paired(cell, "DA010_CONTROL", "DA017_PHRASE_LINKS")}
    passed = contrast["gains"] >= 5 and not contrast["losses"] and all(cell["contrast"]["net"] >= 0 for cell in by_conversation.values())
    result = {"schema": "da017-nf004-phrase-link-result-v1",
              "status": "CROSS_CORPUS_PHRASE_LINK_SIGNAL" if passed else "NO_CROSS_CORPUS_PHRASE_LINK_SIGNAL",
              "population": len(rows), "complete": totals, "contrast": contrast,
              "by_conversation": by_conversation, "one_hop_ceiling": 986,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent NF-004 exact availability; phrase reader use and fresh transfer untested"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, allocation_path: Path, control_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, allocation_path, control_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da017-") as directory:
        replay_result, replay_rows = analyze(dataset_path, allocation_path, control_path)
        replay_path = Path(directory) / path.name
        _write(replay_path, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay_path.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA017AnalysisError("DA-017 result replay differs")
    return result


__all__ = ["DA017AnalysisError", "analyze", "run_analysis"]
