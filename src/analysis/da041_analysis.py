"""Exact frontier-head resolver reachability analysis for DA-041."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.da041_allocation import parse_head
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "dff352250a1f969caa7c1f1545d919bbd43cad61b09580ece0b7a8b1382a8e18"
AUDIT_SHA256 = "b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727"


class DA041AnalysisError(RuntimeError):
    pass


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA041AnalysisError("Population differs")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in data["rows"])


def analyze(longmem_path: Path, population_path: Path, selection_path: Path,
            audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA041AnalysisError("Sealed input differs")
    selections = {str(row["question_id"]): row for row in read_gzip(selection_path)}
    residuals = {str(row["key"]): row for row in read_gzip(audit_path)}
    records = {record.question_id: record for record in adapt_population(longmem_path, _ids(population_path))}
    rows = []
    for question_id, residual in residuals.items():
        selection, record = selections[question_id], records[question_id]
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        treatment = selection["treatment"]
        referenced: set[str] = set()
        if treatment["kind"] == "HEAD":
            parse_head(str(treatment["code"]), str(treatment["sentinel"]))
            for neighbor, member in treatment["targets"]:
                referenced.add(identities[str(neighbor)][int(member)])
        missing = set(map(str, residual["remaining_missing"]))
        reachable = missing <= referenced
        rows.append({"question_id": question_id, "question_type": record.question_type,
                     "blocker": residual["blocker"], "head_admitted": treatment["kind"] == "HEAD",
                     "remaining_missing": sorted(missing), "reachable": reachable,
                     "resolved_targets": len(treatment["targets"]) if treatment["kind"] == "HEAD" else 0})
    if len(rows) != 18:
        raise DA041AnalysisError("Residual cardinality differs")
    reached = sum(row["reachable"] for row in rows)
    by_type = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        by_type[question_type] = {"n": len(cell), "reachable": sum(row["reachable"] for row in cell)}
    if reached >= 12:
        status = "FRONTIER_HEAD_SIGNAL"
    elif reached >= 5:
        status = "WEAK_FRONTIER_HEAD_SIGNAL"
    else:
        status = "NO_FRONTIER_HEAD_SIGNAL"
    result = {"schema": "da041-frontier-head-result-v1", "status": status,
              "residuals": len(rows), "newly_reachable": reached,
              "remaining_unreachable": len(rows) - reached,
              "heads_admitted": sum(row["head_admitted"] for row in rows),
              "by_question_type": by_type,
              "by_blocker": {name: {"n": sum(row["blocker"] == name for row in rows),
                                    "reachable": sum(row["blocker"] == name and row["reachable"] for row in rows)}
                             for name in sorted({row["blocker"] for row in rows})},
              "protected_da038_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "exact external-resolver reachability only; head is not delivered evidence"}
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
    with tempfile.TemporaryDirectory(prefix="da041-result-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, selection_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "reachability_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA041AnalysisError("Result replay differs")
    return result


__all__ = ["DA041AnalysisError", "analyze", "run_analysis"]
