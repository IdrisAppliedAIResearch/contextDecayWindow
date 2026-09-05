"""Required-session coverage analysis for DA-062 pack-activated heads."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import sha256_file
from analysis.da059_analysis import _targets

ROUTES_SHA256 = "111edd60e2165e7932899b993a2c81cdaaa0e74bc998fce391a3fc3d00033a9f"


class DA062AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(dataset_path: Path, routes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(routes_path) != ROUTES_SHA256:
        raise DA062AnalysisError("Sealed routes differ")
    targets = _targets(dataset_path)
    rows = []
    for route in _read(routes_path):
        question_id = str(route["question_id"])
        required = targets[question_id]["sessions"]
        routed = list(map(str, route["routed_session_ids"]))
        routed_set = set(routed)
        positions = {session_id: index + 1 for index, session_id in enumerate(routed)}
        ranks = [positions[session_id] for session_id in required if session_id in positions]
        rows.append({
            "question_id": question_id,
            "question_type": targets[question_id]["question_type"],
            "required_sessions": len(required),
            "covered_sessions": len(required & routed_set),
            "complete_coverage": required <= routed_set,
            "any_coverage": bool(required & routed_set),
            "routed_sessions": len(routed),
            "total_sessions": int(route["total_sessions"]),
            "routed_fraction": len(routed) / int(route["total_sessions"]),
            "first_required_rank": min(ranks) if ranks else None,
            "last_required_rank": max(ranks) if ranks else None,
        })
    if len(rows) != 465:
        raise DA062AnalysisError("Population differs")
    complete = sum(row["complete_coverage"] for row in rows)
    any_coverage = sum(row["any_coverage"] for row in rows)
    complete_rate = complete / len(rows)
    p50_fraction = _quantile([float(row["routed_fraction"]) for row in rows], .5)
    if complete_rate >= .90 and p50_fraction is not None and p50_fraction <= .25:
        status = "SELECTIVE_PACK_ACTIVATED_HEAD_SIGNAL"
    elif complete_rate >= .90:
        status = "BROAD_PACK_ACTIVATED_HEAD_SIGNAL"
    else:
        status = "NO_PACK_ACTIVATED_HEAD_SIGNAL"

    def distribution(field: str) -> dict[str, float | int | None]:
        values = [float(row[field]) for row in rows if row[field] is not None]
        return {
            "p10": _quantile(values, .1),
            "p50": _quantile(values, .5),
            "p90": _quantile(values, .9),
            "max": max(values, default=None),
        }

    groups = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        groups[question_type] = {
            "n": len(cell),
            "complete_coverage": sum(row["complete_coverage"] for row in cell),
            "any_coverage": sum(row["any_coverage"] for row in cell),
        }
    result = {
        "schema": "da062-pack-activated-session-heads-result-v1",
        "status": status,
        "questions": len(rows),
        "complete_coverage": complete,
        "complete_coverage_rate": complete_rate,
        "any_coverage": any_coverage,
        "routed_sessions": distribution("routed_sessions"),
        "routed_fraction": distribution("routed_fraction"),
        "first_required_rank": distribution("first_required_rank"),
        "last_required_rank": distribution("last_required_rank"),
        "by_question_type": groups,
        "protected_payload_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "pack-activated session address coverage only; no traversal or delivery",
    }
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
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


__all__ = ["DA062AnalysisError", "analyze", "run_analysis"]
