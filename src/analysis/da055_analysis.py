"""Exact session-directory addressability analysis for DA-055."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import sha256_file

DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
DA053_RESIDUAL_SHA256 = "559f610177d6e4e9f499a3fe9ee4a7bd844b96d3e84558a2b5ccd634dd827560"


class DA055AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(directory_path: Path, residual_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (sha256_file(directory_path) != DIRECTORY_SHA256
            or sha256_file(residual_path) != DA053_RESIDUAL_SHA256):
        raise DA055AnalysisError("Sealed input differs")
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    residuals = _read(residual_path)
    rows = []
    ambiguities = 0
    for residual in residuals:
        question_id = str(residual["question_id"])
        directory = directories[question_id]
        session_order = {str(node["session_id"]): int(node["session_order"])
                         for node in directory["sessions"]}
        matches: dict[str, list[dict[str, Any]]] = {}
        for episode in directory["episodes"]:
            for member in episode["members"]:
                matches.setdefault(str(member["member_id"]), []).append(
                    {"session_id": str(episode["session_id"]),
                     "session_order": session_order[str(episode["session_id"])],
                     "episode_order": int(episode["episode_order"]),
                     "member_offset": int(member["offset"])})
        resolved = []
        for member in residual["members"]:
            if member["state"] != "ABSENT":
                continue
            found = matches.get(str(member["member_id"]), [])
            if len(found) != 1:
                ambiguities += 1
                continue
            coordinate = found[0]
            resolved.append({"member_id": str(member["member_id"]), **coordinate,
                             "pointer_hops": int(coordinate["episode_order"]) + 3})
        rows.append({"question_id": question_id, "question_type": residual["question_type"],
                     "absent_members": sum(member["state"] == "ABSENT" for member in residual["members"]),
                     "resolved_members": len(resolved), "coordinates": resolved})
    absent = sum(row["absent_members"] for row in rows)
    resolved = sum(row["resolved_members"] for row in rows)
    coordinates = [coordinate for row in rows for coordinate in row["coordinates"]]
    status = ("SESSION_DIRECTORY_ADDRESSABILITY_SIGNAL"
              if absent == resolved == 134 and ambiguities == 0 else "NO_SESSION_DIRECTORY_ADDRESSABILITY_SIGNAL")
    types = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        types[question_type] = {"questions": len(cell),
                                "absent_members": sum(row["absent_members"] for row in cell),
                                "resolved_members": sum(row["resolved_members"] for row in cell)}
    def distribution(field: str) -> dict[str, float | int | None]:
        values = [int(row[field]) for row in coordinates]
        return {"p10": _quantile(values, .1), "p50": _quantile(values, .5),
                "p90": _quantile(values, .9), "max": max(values, default=None)}
    result = {"schema": "da055-session-directory-addressability-result-v1", "status": status,
              "questions": len(rows), "absent_members": absent, "resolved_members": resolved,
              "ambiguities": ambiguities,
              "session_order": distribution("session_order"),
              "episode_order": distribution("episode_order"),
              "pointer_hops": distribution("pointer_hops"),
              "by_question_type": types, "rendered_char_delta": 0,
              "payload_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "exact control-plane addressability only; no payload delivery"}
    return result, rows


def run_analysis(directory_path: Path, residual_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(directory_path, residual_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "resolved_members.jsonl.gz"
    with artifact.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    result["resolved_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    return result


__all__ = ["DA055AnalysisError", "analyze", "run_analysis"]
