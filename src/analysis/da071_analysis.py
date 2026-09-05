"""Posthoc reachability and burden replay for DA-071."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import sha256_file
from analysis.da064_analysis import _targets

STREAMS_SHA256 = "ae969148f1c9adb6d20f84266ee7860701fa56dd8bb7b3abafb85e6cff68f5a3"
DA066_OUTCOMES_SHA256 = "25a5dd207b54ee3d5a68dc7d0788beb5f807df88fe36a36ab7e7fc45a4a3f5ec"


class DA071AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(dataset_path: Path, streams_path: Path,
            da066_outcomes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (sha256_file(streams_path) != STREAMS_SHA256
            or sha256_file(da066_outcomes_path) != DA066_OUTCOMES_SHA256):
        raise DA071AnalysisError("Sealed input differs")
    targets = _targets(dataset_path)
    baseline = {str(row["question_id"]): row for row in _read(da066_outcomes_path)}
    rows = []
    for source in _read(streams_path):
        question_id = str(source["question_id"])
        required = targets[question_id]["episodes"]
        stream = list(source["stream"])
        positions = {str(item["episode_id"]): index + 1 for index, item in enumerate(stream)}
        ranks = [positions[episode_id] for episode_id in required if episode_id in positions]
        complete = len(ranks) == len(required)
        last = max(ranks) if complete else None
        da066_count = int(baseline[question_id]["stream_episodes"])
        da069_count = int(source["da069_prefix_count"])
        rows.append({
            "question_id": question_id,
            "question_type": targets[question_id]["question_type"],
            "required_episodes": len(required),
            "covered_episodes": len(ranks),
            "complete_reachability": complete,
            "any_reachability": bool(ranks),
            "da066_complete": bool(baseline[question_id]["complete_reachability"]),
            "first_required_position": min(ranks) if ranks else None,
            "last_required_position": last,
            "additional_episodes_beyond_da066": max(0, last - da066_count) if last is not None else None,
            "stream_episodes": len(stream),
            "additions_beyond_da069": len(stream) - da069_count,
            "protected_payload_mutations": int(source["protected_payload_mutations"]),
        })
    if len(rows) != 465:
        raise DA071AnalysisError("Population differs")

    def distribution(field: str, population: list[dict[str, Any]] = rows) -> dict[str, float | int | None]:
        values = [float(row[field]) for row in population if row[field] is not None]
        return {
            "n": len(values),
            "p10": _quantile(values, .1),
            "p50": _quantile(values, .5),
            "p90": _quantile(values, .9),
            "max": max(values, default=None),
        }

    gains = [row for row in rows if row["complete_reachability"] and not row["da066_complete"]]
    groups = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        groups[question_type] = {
            "n": len(cell),
            "complete_reachability": sum(row["complete_reachability"] for row in cell),
            "any_reachability": sum(row["any_reachability"] for row in cell),
        }
    result = {
        "schema": "da071-bounded-lattice-replay-result-v1",
        "status": "POSTHOC_BOUNDED_LATTICE_CHARACTERIZED",
        "questions": len(rows),
        "complete_reachability": sum(row["complete_reachability"] for row in rows),
        "any_reachability": sum(row["any_reachability"] for row in rows),
        "first_required_position": distribution("first_required_position"),
        "last_required_position": distribution("last_required_position"),
        "additional_episodes_beyond_da066": distribution("additional_episodes_beyond_da066"),
        "stream_episodes": distribution("stream_episodes"),
        "additions_beyond_da069": distribution("additions_beyond_da069"),
        "gain_only": {
            "questions": len(gains),
            "additional_episodes_beyond_da066": distribution(
                "additional_episodes_beyond_da066", gains
            ),
        },
        "by_question_type": groups,
        "simultaneously_rendered_episodes": 1,
        "peak_current_frame_chars": 2_048,
        "protected_payload_mutations": sum(row["protected_payload_mutations"] for row in rows),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "outcome-informed depth-three burden replay only; no transfer, reader, or delivery",
    }
    return result, rows


def run_analysis(dataset_path: Path, streams_path: Path,
                 da066_outcomes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, streams_path, da066_outcomes_path)
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


__all__ = ["DA071AnalysisError", "analyze", "run_analysis"]
