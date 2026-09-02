"""Opened exact-evidence analysis for frozen DA-013 allocations."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.nf005_measurement import adapt_population

ALLOCATION_SHA256 = "58eda0276af9a97056e4b38fdaf8b8d1def346f52a1e9afa2b37eb025347475a"
NF005_OUTCOMES_SHA256 = "a95d4e1f17d0d14e6814b2f6a3e44106b1e822027d745b2ad05ec6c106391e4f"


class DA013AnalysisError(RuntimeError):
    pass


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA013AnalysisError("NF-003 population artifact differs")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in payload["rows"])


def _paired(rows: Sequence[Mapping[str, Any]], left: str, right: str) -> dict[str, Any]:
    gains = sum(not row[left] and row[right] for row in rows)
    losses = sum(row[left] and not row[right] for row in rows)
    discordant = gains + losses
    tail = min(gains, losses)
    two_sided = min(1.0, 2 * sum(math.comb(discordant, k) for k in range(tail + 1)) / (2**discordant)) if discordant else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses, "ties": len(rows) - discordant,
            "discordant": discordant, "two_sided_exact_p": two_sided}


def analyze(
    dataset_path: Path,
    population_path: Path,
    nf005_outcomes_path: Path,
    allocation_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(nf005_outcomes_path) != NF005_OUTCOMES_SHA256:
        raise DA013AnalysisError("NF-005 evidence artifact differs")
    if sha256_file(allocation_path) != ALLOCATION_SHA256:
        raise DA013AnalysisError("DA-013 frozen allocation differs")
    records = adapt_population(dataset_path, _population_ids(population_path))
    allocations = {row["question_id"]: row for row in read_gzip(allocation_path)}
    if len(records) != 465 or set(allocations) != {record.question_id for record in records}:
        raise DA013AnalysisError("DA-013 evidence join differs")
    rows = []
    for record in records:
        allocation = allocations[record.question_id]
        episodes = {episode.candidate.identity: episode.turn_identities for episode in record.episodes}
        targets = {turn.candidate.identity for turn in record.turns if turn.is_target}
        direct_ids = set(allocation["direct_ids"])
        direct_turns = set().union(*(episodes[value] for value in direct_ids)) if direct_ids else set()
        edge_neighbors = {edge["neighbor_id"] for edge in allocation["edges"]}
        oracle_turns = direct_turns | set().union(*(episodes[value] for value in edge_neighbors))
        outcome: dict[str, Any] = {
            "question_id": record.question_id,
            "question_type": record.question_type,
            "target_count": len(targets),
            "DIRECT_ORIGINAL": targets <= direct_turns,
            "COMPACT_DIRECT": targets <= direct_turns,
            "ONE_HOP_ORACLE": targets <= oracle_turns,
        }
        arm_details = {}
        for arm in ("TEMPORAL_ORDER", "TRANSFER_BENEFIT"):
            delivered = set(direct_turns)
            link_turns = set()
            admitted = []
            for action in allocation[arm]["actions"]:
                if action["kind"] == "PAIR":
                    carried = set(episodes[action["neighbor_id"]])
                elif action["kind"] == "TURN":
                    carried = {episodes[action["neighbor_id"]][int(action["member"])]}
                else:
                    continue
                delivered.update(carried)
                link_turns.update(carried)
                admitted.append({**action, "carried_turns": sorted(carried)})
            complete = targets <= delivered
            gain = complete and not outcome["DIRECT_ORIGINAL"]
            if gain and not (targets - direct_turns) <= link_turns:
                raise DA013AnalysisError("Link gain lacks exact carrier accounting")
            outcome[arm] = complete
            arm_details[arm] = {
                "complete": complete,
                "gain": gain,
                "missing_direct": sorted(targets - direct_turns),
                "admitted": admitted,
                "carried_missing": sorted((targets - direct_turns) & link_turns),
            }
        outcome["arms"] = arm_details
        rows.append(outcome)
    if any(row["DIRECT_ORIGINAL"] != row["COMPACT_DIRECT"] for row in rows):
        raise DA013AnalysisError("Compact direct evidence identity differs")
    for arm in ("TEMPORAL_ORDER", "TRANSFER_BENEFIT"):
        if any(row["DIRECT_ORIGINAL"] and not row[arm] for row in rows):
            raise DA013AnalysisError("Protected direct context lost evidence")
    totals = {arm: sum(row[arm] for row in rows) for arm in
              ("DIRECT_ORIGINAL", "COMPACT_DIRECT", "TEMPORAL_ORDER", "TRANSFER_BENEFIT", "ONE_HOP_ORACLE")}
    contrasts = {
        "temporal_vs_direct": _paired(rows, "DIRECT_ORIGINAL", "TEMPORAL_ORDER"),
        "benefit_vs_direct": _paired(rows, "DIRECT_ORIGINAL", "TRANSFER_BENEFIT"),
        "benefit_vs_temporal": _paired(rows, "TEMPORAL_ORDER", "TRANSFER_BENEFIT"),
    }
    by_type = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        by_type[question_type] = {"n": len(cell), **{arm: sum(row[arm] for row in cell) for arm in totals},
                                  "benefit_vs_direct": _paired(cell, "DIRECT_ORIGINAL", "TRANSFER_BENEFIT")}
    bar = (contrasts["benefit_vs_direct"]["gains"] >= 5 and not contrasts["benefit_vs_direct"]["losses"]
           and all(cell["benefit_vs_direct"]["net"] >= 0 for cell in by_type.values())
           and totals["TRANSFER_BENEFIT"] > totals["TEMPORAL_ORDER"])
    result = {
        "schema": "da013-cross-corpus-result-v1",
        "standing": "spent LongMemEval cross-corpus availability stress test",
        "population": {"questions": len(rows), "target_turns": sum(row["target_count"] for row in rows)},
        "complete": totals,
        "contrasts": contrasts,
        "by_question_type": by_type,
        "status": "CROSS_CORPUS_CAPACITY_SIGNAL" if bar else "NO_CROSS_CORPUS_CAPACITY_SIGNAL",
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "spent-corpus exact availability only; no reader, fresh-validation, safety, or adoption claim",
    }
    return result, rows


def _write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, population_path: Path, nf005_outcomes_path: Path,
                 allocation_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, population_path, nf005_outcomes_path, allocation_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "outcomes.jsonl.gz"
    _write_rows(rows_path, rows)
    with tempfile.TemporaryDirectory(prefix="da013-analysis-") as directory:
        replay_result, replay_rows = analyze(dataset_path, population_path, nf005_outcomes_path, allocation_path)
        replay_path = Path(directory) / rows_path.name
        _write_rows(replay_path, replay_rows)
        identical = result == replay_result and rows_path.read_bytes() == replay_path.read_bytes()
    result["replay_byte_identical"] = identical
    result["outcomes_sha256"] = sha256_file(rows_path)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA013AnalysisError("DA-013 result replay differs")
    return result


__all__ = ["DA013AnalysisError", "analyze", "run_analysis"]
