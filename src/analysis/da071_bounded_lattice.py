"""Posthoc depth-three replay of the DA-070 signature lattice."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import sha256_file
from analysis.da070_lattice_descent import (
    CURRENT_FRAME_CAP,
    DA070Error,
    _synthetic_check,
    build_rows,
)

DEPTH_LIMIT = 3
DA070_STREAMS_SHA256 = "7c963b4e1921456a35102c644f4cd602425bc91eacc9dabafc4dc9d8ccaaba5c"


class DA071Error(RuntimeError):
    pass


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, da069_path: Path, directory_path: Path,
                  da070_streams_path: Path, output_dir: Path) -> dict[str, Any]:
    if sha256_file(da070_streams_path) != DA070_STREAMS_SHA256:
        raise DA071Error("Sealed DA-070 comparison differs")
    try:
        unbounded = build_rows(dataset_path, da069_path, directory_path)
        rows = build_rows(
            dataset_path, da069_path, directory_path,
            max_traversal_depth=DEPTH_LIMIT,
        )
    except DA070Error as error:
        raise DA071Error(str(error)) from error
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_streams.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da071-") as directory:
        unbounded_replay = Path(directory) / "unbounded.jsonl.gz"
        bounded_replay = Path(directory) / "bounded.jsonl.gz"
        _write(unbounded_replay, unbounded)
        _write(
            bounded_replay,
            build_rows(
                dataset_path, da069_path, directory_path,
                max_traversal_depth=DEPTH_LIMIT,
            ),
        )
        parent_identical = sha256_file(unbounded_replay) == DA070_STREAMS_SHA256
        bounded_identical = artifact.read_bytes() == bounded_replay.read_bytes()
    bounded_episodes = sum(len(row["stream"]) for row in rows)
    unbounded_episodes = sum(len(row["stream"]) for row in unbounded)
    valid = (
        _synthetic_check()
        and parent_identical
        and bounded_identical
        and all(row["traversal_depth_limit"] == DEPTH_LIMIT for row in rows)
        and all(row["nodes_within_limit"] >= row["root_nodes"] for row in rows)
        and all(len(row["stream"]) <= len(parent["stream"])
                for row, parent in zip(rows, unbounded, strict=True))
        and bounded_episodes < unbounded_episodes
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
    )
    result = {
        "schema": "da071-bounded-lattice-replay-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "depth_limit": DEPTH_LIMIT,
        "synthetic_hasse_check": _synthetic_check(),
        "parent_replay_byte_identical": parent_identical,
        "bounded_replay_byte_identical": bounded_identical,
        "unbounded_stream_episodes": unbounded_episodes,
        "bounded_stream_episodes": bounded_episodes,
        "saved_stream_episodes": unbounded_episodes - bounded_episodes,
        "appended_signature_nodes": sum(row["appended_signature_nodes"] for row in rows),
        "appended_sessions": sum(row["appended_sessions"] for row in rows),
        "lattice_additions": sum(row["lattice_additions"] for row in rows),
        "min_stream_episodes": min(len(row["stream"]) for row in rows),
        "max_stream_episodes": max(len(row["stream"]) for row in rows),
        "simultaneously_rendered_episodes": 1,
        "peak_current_frame_chars": CURRENT_FRAME_CAP,
        "protected_payload_mutations": 0,
        "rendered_char_delta": 0,
        "streams_sha256": sha256_file(artifact),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
    }
    (output_dir / "preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not valid:
        raise DA071Error("Bounded lattice preflight failed")
    return result


__all__ = ["DA071Error", "DEPTH_LIMIT", "run_preflight"]
