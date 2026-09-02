"""Exact evidence analysis for frozen DA-016 allocations."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.nf005_measurement import adapt_population

ALLOCATION_SHA256 = "8ab71c95ee4cea7c78149e344ea704243cfbfa2acbfc9eddd70b105e32d39a64"
DA013_OUTCOMES_SHA256 = "832b85bff370fdfb0de619df2b4b280f5b50e375ebfee0190fb22bfa488c2f49"


class DA016AnalysisError(RuntimeError):
    pass


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA016AnalysisError("NF-003 population differs")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in payload["rows"])


def _paired(rows: Sequence[Mapping[str, Any]], left: str, right: str) -> dict[str, Any]:
    gains = sum(not row[left] and row[right] for row in rows)
    losses = sum(row[left] and not row[right] for row in rows)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / (2**n)) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses, "ties": len(rows) - n,
            "discordant": n, "two_sided_exact_p": p}


def analyze(dataset_path: Path, population_path: Path, allocation_path: Path,
            da013_outcomes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(allocation_path) != ALLOCATION_SHA256 or sha256_file(da013_outcomes_path) != DA013_OUTCOMES_SHA256:
        raise DA016AnalysisError("DA-016 sealed input differs")
    records = {record.question_id: record for record in adapt_population(dataset_path, _ids(population_path))}
    allocations = {row["question_id"]: row for row in read_gzip(allocation_path)}
    controls = {row["question_id"]: row for row in read_gzip(da013_outcomes_path)}
    if set(records) != set(allocations) or set(records) != set(controls):
        raise DA016AnalysisError("DA-016 evidence join differs")
    rows = []
    for question_id in sorted(records):
        record, allocation, control = records[question_id], allocations[question_id], controls[question_id]
        episode_turns = {episode.candidate.identity: episode.turn_identities for episode in record.episodes}
        targets = {turn.candidate.identity for turn in record.turns if turn.is_target}
        direct_turns = set().union(*(episode_turns[value] for value in allocation["direct_ids"]))
        delivered = set(direct_turns)
        link_turns = set()
        admitted = []
        for action in allocation["actions"]:
            if action["kind"] == "PAIR":
                carried = set(episode_turns[action["neighbor_id"]])
            elif action["kind"] == "TURN":
                carried = {episode_turns[action["neighbor_id"]][int(action["member"])]}
            else:
                continue
            delivered.update(carried)
            link_turns.update(carried)
            admitted.append({"neighbor_id": action["neighbor_id"], "kind": action["kind"],
                             "member": action["member"], "carried_turns": sorted(carried)})
        direct_complete = targets <= direct_turns
        treatment = targets <= delivered
        missing = targets - direct_turns
        if treatment and not direct_complete and not missing <= link_turns:
            raise DA016AnalysisError("DA-016 gain lacks exact carrier accounting")
        if direct_complete and not treatment:
            raise DA016AnalysisError("DA-016 lost protected direct evidence")
        rows.append({"question_id": question_id, "question_type": record.question_type,
                     "DIRECT": direct_complete, "DA013_TEMPORAL": bool(control["TEMPORAL_ORDER"]),
                     "DA016_PHRASE_LINKS": treatment, "missing_direct": sorted(missing),
                     "carried_missing": sorted(missing & link_turns), "admitted": admitted})
    totals = {arm: sum(row[arm] for row in rows) for arm in ("DIRECT", "DA013_TEMPORAL", "DA016_PHRASE_LINKS")}
    contrast = _paired(rows, "DA013_TEMPORAL", "DA016_PHRASE_LINKS")
    by_type = {}
    for kind in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == kind]
        by_type[kind] = {"n": len(cell), **{arm: sum(row[arm] for row in cell) for arm in totals},
                         "contrast": _paired(cell, "DA013_TEMPORAL", "DA016_PHRASE_LINKS")}
    passed = contrast["gains"] >= 10 and not contrast["losses"] and all(cell["contrast"]["net"] >= 0 for cell in by_type.values())
    result = {"schema": "da016-phrase-link-result-v1",
              "status": "PHRASE_LINK_DELIVERY_SIGNAL" if passed else "NO_PHRASE_LINK_DELIVERY_SIGNAL",
              "population": len(rows), "complete": totals, "contrast": contrast,
              "by_question_type": by_type, "one_hop_ceiling": 250,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent-corpus exact availability only; dictionary reader use untested"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, population_path: Path, allocation_path: Path,
                 da013_outcomes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, population_path, allocation_path, da013_outcomes_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da016-") as directory:
        replay_result, replay_rows = analyze(dataset_path, population_path, allocation_path, da013_outcomes_path)
        replay_path = Path(directory) / path.name
        _write(replay_path, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay_path.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA016AnalysisError("DA-016 result replay differs")
    return result


__all__ = ["DA016AnalysisError", "analyze", "run_analysis"]
