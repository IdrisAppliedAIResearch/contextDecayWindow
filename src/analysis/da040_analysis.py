"""Exact dependency-reference reachability analysis for DA-040."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.da040_allocation import parse_reference
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "fb88b0276b20dadd084c0c1080de5c6532711addcb42488e909b5c2f8458c1c3"
AUDIT_SHA256 = "b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727"


class DA040AnalysisError(RuntimeError):
    pass


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA040AnalysisError("Population differs")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in data["rows"])


def distribution(values: Sequence[int | float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def analyze(longmem_path: Path, population_path: Path, selection_path: Path,
            audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA040AnalysisError("Sealed input differs")
    selections = {str(row["question_id"]): row for row in read_gzip(selection_path)}
    residuals = {str(row["key"]): row for row in read_gzip(audit_path)}
    records = {record.question_id: record for record in adapt_population(longmem_path, _ids(population_path))}
    rows = []
    for question_id, residual in residuals.items():
        selection, record = selections[question_id], records[question_id]
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        referenced: set[str] = set()
        positions = []
        for action in selection["treatment"]["actions"]:
            if action["kind"] != "REF":
                continue
            position, member = parse_reference(str(action["code"]), str(selection["treatment"]["sentinel"]))
            neighbor = str(selection["baseline_actions"][position]["neighbor_id"])
            if neighbor != str(action["neighbor_id"]) or member != int(action["member"]):
                raise DA040AnalysisError("Sealed reference resolution differs")
            referenced.add(identities[neighbor][member])
            positions.append(position)
        missing = set(map(str, residual["remaining_missing"]))
        reachable = missing <= referenced
        rows.append({"question_id": question_id, "question_type": record.question_type,
                     "blocker": residual["blocker"], "remaining_missing": sorted(missing),
                     "reachable": reachable, "referenced_identities": len(referenced),
                     "reference_positions": positions})
    if len(rows) != 18:
        raise DA040AnalysisError("Residual cardinality differs")
    gains = sum(row["reachable"] for row in rows)
    by_type = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        by_type[question_type] = {"n": len(cell), "reachable": sum(row["reachable"] for row in cell)}
    if gains >= 5:
        status = "COMPACT_DEPENDENCY_FRONTIER_SIGNAL"
    elif gains >= 2:
        status = "WEAK_COMPACT_DEPENDENCY_FRONTIER_SIGNAL"
    else:
        status = "NO_COMPACT_DEPENDENCY_FRONTIER_SIGNAL"
    reached = [row for row in rows if row["reachable"]]
    result = {"schema": "da040-compact-dependency-frontier-result-v1", "status": status,
              "residuals": len(rows), "newly_reachable": gains,
              "remaining_unreachable": len(rows) - gains, "by_question_type": by_type,
              "by_blocker": {name: {"n": sum(row["blocker"] == name for row in rows),
                                    "reachable": sum(row["blocker"] == name and row["reachable"] for row in rows)}
                             for name in sorted({row["blocker"] for row in rows})},
              "referenced_identities": distribution([row["referenced_identities"] for row in rows]),
              "reachable_reference_position": distribution([position for row in reached
                                                               for position in row["reference_positions"]]),
              "protected_da038_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "exact external-resolver reachability only; references are not delivered facts"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(longmem_path: Path, population_path: Path, selection_path: Path,
                 audit_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, selection_path, audit_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "reachability.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da040-result-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, selection_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "reachability_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA040AnalysisError("Result replay differs")
    return result


__all__ = ["DA040AnalysisError", "analyze", "run_analysis"]
