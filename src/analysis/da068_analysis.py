"""Reachability and marginal burden analysis for DA-068 pair witnesses."""

from __future__ import annotations

import gzip
import json
import statistics
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import sha256_file
from analysis.da064_analysis import _targets

STREAMS_SHA256 = "9c254cb065614e69a823f8d996bff24da209a84e1d5f275b418807ea696d1464"
DA067_GAIN_MEDIAN = 62


class DA068AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(dataset_path: Path, streams_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(streams_path) != STREAMS_SHA256:
        raise DA068AnalysisError("Sealed stream differs")
    targets = _targets(dataset_path)
    rows = []
    for source in _read(streams_path):
        question_id = str(source["question_id"])
        required = targets[question_id]["episodes"]
        stream = list(source["stream"])
        positions = {str(item["episode_id"]): index + 1 for index, item in enumerate(stream)}
        ranks = [positions[episode_id] for episode_id in required if episode_id in positions]
        complete = len(ranks) == len(required)
        last = max(ranks) if complete else None
        prefix = int(source["da066_prefix_count"])
        rows.append({
            "question_id": question_id,
            "question_type": targets[question_id]["question_type"],
            "required_episodes": len(required),
            "covered_episodes": len(ranks),
            "complete_reachability": complete,
            "any_reachability": bool(ranks),
            "da066_prefix_complete": complete and last <= prefix,
            "first_required_position": min(ranks) if ranks else None,
            "last_required_position": last,
            "additional_episodes_through_required": max(0, last - prefix) if last is not None else None,
            "stream_episodes": len(stream),
            "protected_payload_mutations": int(source["protected_payload_mutations"]),
        })
    if len(rows) != 465:
        raise DA068AnalysisError("Population differs")

    def distribution(field: str, population: list[dict[str, Any]] = rows) -> dict[str, float | int | None]:
        values = [float(row[field]) for row in population if row[field] is not None]
        return {
            "n": len(values),
            "p10": _quantile(values, .1),
            "p50": _quantile(values, .5),
            "p90": _quantile(values, .9),
            "max": max(values, default=None),
        }

    complete = sum(row["complete_reachability"] for row in rows)
    complete_rate = complete / len(rows)
    mutations = sum(row["protected_payload_mutations"] for row in rows)
    gains = [row for row in rows if row["complete_reachability"] and not row["da066_prefix_complete"]]
    gain_additions = [int(row["additional_episodes_through_required"]) for row in gains]
    gain_median = statistics.median(gain_additions) if gain_additions else None
    status = (
        "MINIMUM_PAIR_WITNESS_SIGNAL"
        if complete_rate >= .98 and mutations == 0
        and gain_median is not None and gain_median < DA067_GAIN_MEDIAN
        else "NO_MINIMUM_PAIR_WITNESS_SIGNAL"
    )
    groups = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        groups[question_type] = {
            "n": len(cell),
            "complete_reachability": sum(row["complete_reachability"] for row in cell),
            "any_reachability": sum(row["any_reachability"] for row in cell),
        }
    result = {
        "schema": "da068-minimum-pair-witness-result-v1",
        "status": status,
        "questions": len(rows),
        "complete_reachability": complete,
        "complete_reachability_rate": complete_rate,
        "any_reachability": sum(row["any_reachability"] for row in rows),
        "da066_prefix_complete": sum(row["da066_prefix_complete"] for row in rows),
        "first_required_position": distribution("first_required_position"),
        "last_required_position": distribution("last_required_position"),
        "additional_episodes_through_required": distribution("additional_episodes_through_required"),
        "stream_episodes": distribution("stream_episodes"),
        "gain_only": {
            "questions": len(gains),
            "additional_episodes_through_required": distribution(
                "additional_episodes_through_required", gains
            ),
            "da067_reference_median": DA067_GAIN_MEDIAN,
        },
        "by_question_type": groups,
        "simultaneously_rendered_episodes": 1,
        "peak_current_frame_chars": 2_048,
        "protected_payload_mutations": mutations,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "pair-witness reachability and burden only; no reader, stopping, reconstruction, or delivery",
    }
    return result, rows


def run_analysis(dataset_path: Path, streams_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, streams_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "reachability.jsonl.gz"
    with artifact.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    result["reachability_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


__all__ = ["DA068AnalysisError", "analyze", "run_analysis"]
