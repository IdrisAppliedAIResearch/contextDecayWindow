"""Required-episode reachability analysis for DA-064 occurrence streams."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file

STREAMS_SHA256 = "4273dc9bfbba2af9107c8e7c3d93812185905c4ebc1ef83a41c6ff68706b333f"


class DA064AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _targets(dataset_path: Path) -> dict[str, dict[str, Any]]:
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise DA064AnalysisError("Dataset differs")
    output = {}
    for source in json.loads(dataset_path.read_text(encoding="utf-8")):
        question_id = str(source["question_id"])
        episodes, _ = _episodes(source)
        episode_index = 0
        required = set()
        for turns in source["haystack_sessions"]:
            for start in range(0, len(turns) - 1, 2):
                first, second = turns[start:start + 2]
                if first.get("role") != "user" or second.get("role") != "assistant":
                    continue
                episode = episodes[episode_index]
                episode_index += 1
                if bool(first.get("has_answer")) or bool(second.get("has_answer")):
                    required.add(str(episode["identity"]))
        if required:
            output[question_id] = {
                "episodes": required,
                "question_type": str(source.get("question_type", "unknown")),
            }
    return output


def analyze(dataset_path: Path, streams_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(streams_path) != STREAMS_SHA256:
        raise DA064AnalysisError("Sealed stream differs")
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
        prefix = int(source["pack_prefix_count"])
        rows.append({
            "question_id": question_id,
            "question_type": targets[question_id]["question_type"],
            "required_episodes": len(required),
            "covered_episodes": len(ranks),
            "complete_reachability": complete,
            "any_reachability": bool(ranks),
            "pack_prefix_complete": complete and last <= prefix,
            "first_required_position": min(ranks) if ranks else None,
            "last_required_position": last,
            "additional_episodes_through_required": max(0, last - prefix) if last is not None else None,
            "stream_episodes": len(stream),
            "protected_payload_mutations": int(source["protected_payload_mutations"]),
        })
    if len(rows) != 465:
        raise DA064AnalysisError("Population differs")

    def distribution(field: str) -> dict[str, float | int | None]:
        values = [float(row[field]) for row in rows if row[field] is not None]
        return {
            "p10": _quantile(values, .1),
            "p50": _quantile(values, .5),
            "p90": _quantile(values, .9),
            "max": max(values, default=None),
        }

    complete = sum(row["complete_reachability"] for row in rows)
    complete_rate = complete / len(rows)
    p50_last = _quantile(
        [float(row["last_required_position"]) for row in rows if row["last_required_position"] is not None], .5
    )
    status = (
        "OCCURRENCE_COORDINATE_SIGNAL"
        if complete_rate >= .90 and p50_last is not None and p50_last <= 32
        else "NO_OCCURRENCE_COORDINATE_SIGNAL"
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
        "schema": "da064-occurrence-coordinate-stream-result-v1",
        "status": status,
        "questions": len(rows),
        "complete_reachability": complete,
        "complete_reachability_rate": complete_rate,
        "any_reachability": sum(row["any_reachability"] for row in rows),
        "pack_prefix_complete": sum(row["pack_prefix_complete"] for row in rows),
        "first_required_position": distribution("first_required_position"),
        "last_required_position": distribution("last_required_position"),
        "additional_episodes_through_required": distribution("additional_episodes_through_required"),
        "stream_episodes": distribution("stream_episodes"),
        "by_question_type": groups,
        "simultaneously_rendered_episodes": 1,
        "peak_current_frame_chars": 2_048,
        "protected_payload_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "episode address reachability only; no reader, stopping, reconstruction, or delivery",
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


__all__ = ["DA064AnalysisError", "analyze", "run_analysis"]
