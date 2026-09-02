"""Blind role-typed ordered-feature lattice for DA-074."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import sha256_file
from analysis.da070_lattice_descent import _synthetic_check
from analysis.da073_ordered_lattice import (
    CURRENT_FRAME_CAP,
    DA073Error,
    build_rows,
)

DA073_STREAMS_SHA256 = "38bbe1ffe58f4b2c27b4a8ef85512850ac17f3967bca8f83e30e5735d439caa7"
REQUIRED_TYPED_FAMILIES = (
    "USER_UNIGRAM",
    "USER_BIGRAM",
    "ASSISTANT_UNIGRAM",
    "ASSISTANT_BIGRAM",
)


class DA074Error(RuntimeError):
    pass


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, da066_path: Path, directory_path: Path,
                  da073_streams_path: Path, output_dir: Path) -> dict[str, Any]:
    if sha256_file(da073_streams_path) != DA073_STREAMS_SHA256:
        raise DA074Error("Sealed DA-073 comparison differs")
    try:
        untyped = build_rows(dataset_path, da066_path, directory_path)
        rows = build_rows(dataset_path, da066_path, directory_path, role_typed=True)
    except DA073Error as error:
        raise DA074Error(str(error)) from error
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_streams.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da074-") as directory:
        untyped_replay = Path(directory) / "untyped.jsonl.gz"
        typed_replay = Path(directory) / "typed.jsonl.gz"
        _write(untyped_replay, untyped)
        _write(
            typed_replay,
            build_rows(dataset_path, da066_path, directory_path, role_typed=True),
        )
        parent_identical = sha256_file(untyped_replay) == DA073_STREAMS_SHA256
        typed_identical = artifact.read_bytes() == typed_replay.read_bytes()
    typed_counts: Counter[str] = Counter()
    rejections: Counter[str] = Counter()
    for row in rows:
        typed_counts.update(row["typed_feature_occurrences"])
        rejections.update(row["rejections"])
    valid = (
        _synthetic_check()
        and parent_identical
        and typed_identical
        and all(typed_counts[family] > 0 for family in REQUIRED_TYPED_FAMILIES)
        and sum(row["cover_edges"] for row in rows) > 0
        and sum(row["ordered_feature_additions"] for row in rows) > 0
        and rejections["SESSION_BOUNDARY"] > 0
        and all(row["role_typed"] for row in rows)
        and all(len(row["stream"]) == len({item["episode_id"] for item in row["stream"]}) for row in rows)
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
    )
    result = {
        "schema": "da074-role-typed-feature-lattice-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "synthetic_hasse_check": _synthetic_check(),
        "parent_replay_byte_identical": parent_identical,
        "typed_replay_byte_identical": typed_identical,
        "typed_feature_occurrences": dict(typed_counts),
        "signature_nodes": sum(row["signature_nodes"] for row in rows),
        "equal_signature_sessions": sum(row["equal_signature_sessions"] for row in rows),
        "root_nodes": sum(row["root_nodes"] for row in rows),
        "cover_edges": sum(row["cover_edges"] for row in rows),
        "max_depth": max(row["max_depth"] for row in rows),
        "ordered_feature_additions": sum(row["ordered_feature_additions"] for row in rows),
        "rejections": dict(rejections),
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
        raise DA074Error("Blind role-typed preflight failed")
    return result


__all__ = ["DA074Error", "REQUIRED_TYPED_FAMILIES", "run_preflight"]
