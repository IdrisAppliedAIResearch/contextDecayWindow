"""Required-session coverage analysis for DA-059 sparse routes."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import DATASET_SHA256, identity, sha256_file

ROUTES_SHA256 = "c8f8bd7af9e82fc54a75bda855bd164bce6a21356ce0a29c591e99ad9ea475e3"


class DA059AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _targets(dataset_path: Path) -> dict[str, dict[str, Any]]:
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise DA059AnalysisError("Dataset differs")
    output = {}
    for row in json.loads(dataset_path.read_text(encoding="utf-8")):
        question_id = str(row["question_id"])
        sessions = set()
        for session_order, (source_id, turns) in enumerate(
            zip(row["haystack_session_ids"], row["haystack_sessions"], strict=True)
        ):
            session_id = identity(question_id, str(session_order), str(source_id))
            for start in range(0, len(turns) - 1, 2):
                first, second = turns[start:start + 2]
                if first.get("role") != "user" or second.get("role") != "assistant":
                    continue
                if bool(first.get("has_answer")) or bool(second.get("has_answer")):
                    sessions.add(session_id)
        if sessions:
            output[question_id] = {"sessions": sessions,
                                   "question_type": str(row.get("question_type", "unknown"))}
    return output


def analyze(dataset_path: Path, routes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(routes_path) != ROUTES_SHA256:
        raise DA059AnalysisError("Sealed routes differ")
    targets = _targets(dataset_path)
    routes = _read(routes_path)
    rows = []
    for route in routes:
        question_id = str(route["question_id"])
        required = targets[question_id]["sessions"]
        routed = list(map(str, route["routed_session_ids"]))
        position = {session_id: index + 1 for index, session_id in enumerate(routed)}
        covered = required & set(routed)
        ranks = [position[session_id] for session_id in required if session_id in position]
        rows.append({"question_id": question_id,
                     "question_type": targets[question_id]["question_type"],
                     "required_sessions": len(required), "covered_sessions": len(covered),
                     "complete_coverage": required <= set(routed), "any_coverage": bool(covered),
                     "routed_sessions": len(routed), "total_sessions": int(route["total_sessions"]),
                     "routed_fraction": len(routed) / int(route["total_sessions"]),
                     "first_required_rank": min(ranks) if ranks else None,
                     "last_required_rank": max(ranks) if ranks else None})
    if len(rows) != 465:
        raise DA059AnalysisError("Population differs")
    complete = sum(row["complete_coverage"] for row in rows)
    any_coverage = sum(row["any_coverage"] for row in rows)
    fractions = [float(row["routed_fraction"]) for row in rows]
    complete_rate = complete / len(rows)
    p50_fraction = _quantile(fractions, .5)
    if complete_rate >= .90 and p50_fraction is not None and p50_fraction <= .25:
        status = "SELECTIVE_SPARSE_SESSION_SIGNAL"
    elif complete_rate >= .90:
        status = "BROAD_SPARSE_SESSION_SIGNAL"
    else:
        status = "NO_SPARSE_SESSION_SIGNAL"
    def distribution(field: str) -> dict[str, float | int | None]:
        values = [float(row[field]) for row in rows if row[field] is not None]
        return {"p10": _quantile(values, .1), "p50": _quantile(values, .5),
                "p90": _quantile(values, .9), "max": max(values, default=None)}
    types = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        types[question_type] = {"n": len(cell),
                                "complete_coverage": sum(row["complete_coverage"] for row in cell),
                                "any_coverage": sum(row["any_coverage"] for row in cell)}
    result = {"schema": "da059-sparse-session-postings-result-v1", "status": status,
              "questions": len(rows), "complete_coverage": complete,
              "complete_coverage_rate": complete_rate, "any_coverage": any_coverage,
              "routed_sessions": distribution("routed_sessions"),
              "routed_fraction": distribution("routed_fraction"),
              "first_required_rank": distribution("first_required_rank"),
              "last_required_rank": distribution("last_required_rank"),
              "by_question_type": types,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "exact-token session address coverage only; no delivery"}
    return result, rows


def run_analysis(dataset_path: Path, routes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, routes_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "coverage.jsonl.gz"
    with artifact.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    result["coverage_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    return result


__all__ = ["DA059AnalysisError", "analyze", "run_analysis"]
