"""Sequential exact evidence-exposure analysis for DA-045 streams."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.da032_audit import distribution
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"
AUDIT_SHA256 = "b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727"


class DA045AnalysisError(RuntimeError):
    pass


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA045AnalysisError("Population differs")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in data["rows"])


def analyze(longmem_path: Path, population_path: Path, selection_path: Path,
            audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA045AnalysisError("Sealed input differs")
    selections = {str(row["question_id"]): row for row in read_gzip(selection_path)}
    residuals = {str(row["key"]): row for row in read_gzip(audit_path)}
    records = {record.question_id: record for record in adapt_population(longmem_path, _ids(population_path))}
    rows = []
    for question_id, residual in residuals.items():
        selection, record = selections[question_id], records[question_id]
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        action_identity = {}
        for action in selection["treatment"]["actions"]:
            identity = identities[str(action["neighbor_id"])][int(action["member"])]
            if identity in action_identity:
                raise DA045AnalysisError("Stream identity appears twice")
            action_identity[identity] = action
        required_actions = []
        for identity in map(str, residual["remaining_missing"]):
            if identity not in action_identity:
                raise DA045AnalysisError("Required identity is outside stream")
            required_actions.append(action_identity[identity])
        exposed = all(action["kind"] == "FRAME" for action in required_actions)
        last_ordinal = max(int(action["ordinal"]) for action in required_actions)
        traversed = [action for action in selection["treatment"]["actions"]
                     if int(action["ordinal"]) <= last_ordinal]
        rows.append({"question_id": question_id, "question_type": record.question_type,
                     "blocker": residual["blocker"], "exposed": exposed,
                     "required_nodes": len(required_actions), "last_required_ordinal": last_ordinal,
                     "frames_through_requirement": sum(action["kind"] == "FRAME" for action in traversed),
                     "overflows_through_requirement": sum(action["kind"] == "OVERFLOW" for action in traversed),
                     "cumulative_chars_through_requirement": sum(int(action["cost"]) for action in traversed),
                     "peak_frame_chars": max((int(action["cost"]) for action in traversed), default=0)})
    if len(rows) != 18:
        raise DA045AnalysisError("Residual cardinality differs")
    exposed = sum(row["exposed"] for row in rows)
    by_type = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        by_type[question_type] = {"n": len(cell), "exposed": sum(row["exposed"] for row in cell)}
    if exposed >= 17:
        status = "REPLACEABLE_NODE_STREAM_SIGNAL"
    elif exposed >= 12:
        status = "WEAK_REPLACEABLE_NODE_STREAM_SIGNAL"
    else:
        status = "NO_REPLACEABLE_NODE_STREAM_SIGNAL"
    reached = [row for row in rows if row["exposed"]]
    result = {"schema": "da045-replaceable-node-stream-result-v1", "status": status,
              "residuals": len(rows), "exposed": exposed, "not_exposed": len(rows) - exposed,
              "by_question_type": by_type,
              "by_blocker": {name: {"n": sum(row["blocker"] == name for row in rows),
                                    "exposed": sum(row["blocker"] == name and row["exposed"] for row in rows)}
                             for name in sorted({row["blocker"] for row in rows})},
              "peak_frame_chars": distribution([row["peak_frame_chars"] for row in reached]),
              "cumulative_chars_through_requirement": distribution(
                  [row["cumulative_chars_through_requirement"] for row in reached]),
              "frames_through_requirement": distribution([row["frames_through_requirement"] for row in reached]),
              "overflows_through_requirement": distribution([row["overflows_through_requirement"] for row in reached]),
              "protected_da038_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "sequential exact payload exposure only; no simultaneous delivery or reader use"}
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
    path = output_dir / "exposure.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da045-result-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, selection_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "exposure_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA045AnalysisError("Result replay differs")
    return result


__all__ = ["DA045AnalysisError", "analyze", "run_analysis"]
