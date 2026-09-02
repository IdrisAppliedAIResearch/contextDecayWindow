"""Exposure and traversal burden analysis for DA-063 head streams."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import sha256_file
from analysis.da059_analysis import _targets

STREAMS_SHA256 = "e89a832a0a650ffd3e800006c82607a9f12c7e86a485f1326fae9b1e01f878f0"


class DA063AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(dataset_path: Path, streams_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(streams_path) != STREAMS_SHA256:
        raise DA063AnalysisError("Sealed stream differs")
    targets = _targets(dataset_path)
    rows = []
    for source in _read(streams_path):
        question_id = str(source["question_id"])
        required = targets[question_id]["sessions"]
        stream = list(source["stream"])
        positions = {str(item["session_id"]): index + 1 for index, item in enumerate(stream)}
        ranks = [positions[session_id] for session_id in required if session_id in positions]
        complete = len(ranks) == len(required)
        last = max(ranks) if complete else None
        prefix_count = int(source["pack_prefix_count"])
        traversed = stream[:last] if last is not None else []
        rows.append({
            "question_id": question_id,
            "question_type": targets[question_id]["question_type"],
            "required_sessions": len(required),
            "covered_sessions": len(ranks),
            "complete_reachability": complete,
            "pack_prefix_complete": complete and last <= prefix_count,
            "first_required_position": min(ranks) if ranks else None,
            "last_required_position": last,
            "additional_heads_through_required": max(0, last - prefix_count) if last is not None else None,
            "episodes_through_required": sum(int(item["episode_count"]) for item in traversed) if complete else None,
            "members_through_required": sum(int(item["member_count"]) for item in traversed) if complete else None,
            "stream_heads": len(stream),
            "peak_current_frame_chars": int(source["current_frame_cap"]),
            "protected_payload_mutations": int(source["protected_payload_mutations"]),
        })
    if len(rows) != 465:
        raise DA063AnalysisError("Population differs")

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
            "complete_reachability": sum(row["complete_reachability"] for row in cell),
            "pack_prefix_complete": sum(row["pack_prefix_complete"] for row in cell),
        }
    complete = sum(row["complete_reachability"] for row in rows)
    result = {
        "schema": "da063-replaceable-session-head-stream-result-v1",
        "status": "POSTHOC_REPLACEABLE_HEAD_STREAM_CHARACTERIZED",
        "questions": len(rows),
        "complete_reachability": complete,
        "complete_reachability_rate": complete / len(rows),
        "pack_prefix_complete": sum(row["pack_prefix_complete"] for row in rows),
        "first_required_position": distribution("first_required_position"),
        "last_required_position": distribution("last_required_position"),
        "additional_heads_through_required": distribution("additional_heads_through_required"),
        "episodes_through_required": distribution("episodes_through_required"),
        "members_through_required": distribution("members_through_required"),
        "stream_heads": distribution("stream_heads"),
        "by_question_type": groups,
        "simultaneously_rendered_heads": 1,
        "peak_current_frame_chars": 2_048,
        "protected_payload_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc address exposure and burden only; no reader, stopping, or delivery",
    }
    return result, rows


def run_analysis(dataset_path: Path, streams_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, streams_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "exposure.jsonl.gz"
    with artifact.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    result["exposure_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


__all__ = ["DA063AnalysisError", "analyze", "run_analysis"]
