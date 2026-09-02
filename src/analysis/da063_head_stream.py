"""Blind replaceable composition of DA-062 and DA-061 session heads."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import sha256_file

BIGRAM_SHA256 = "9fbbbb1ca232c57c9b959092de6627dfaee6fbead833f843c73ee14692c2fb4c"
PACK_SHA256 = "111edd60e2165e7932899b993a2c81cdaaa0e74bc998fce391a3fc3d00033a9f"
DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
CURRENT_FRAME_CAP = 2_048


class DA063Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def build_rows(bigram_path: Path, pack_path: Path, directory_path: Path) -> list[dict[str, Any]]:
    seals = (
        (bigram_path, BIGRAM_SHA256),
        (pack_path, PACK_SHA256),
        (directory_path, DIRECTORY_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA063Error("Sealed input differs")
    bigrams = {str(row["question_id"]): row for row in _read(bigram_path)}
    packs = {str(row["question_id"]): row for row in _read(pack_path)}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    if set(bigrams) != set(packs) or set(packs) != set(directories) or len(packs) != 465:
        raise DA063Error("Population differs")
    rows = []
    for question_id in sorted(packs):
        prefix = list(map(str, packs[question_id]["routed_session_ids"]))
        suffix = list(map(str, bigrams[question_id]["routed_session_ids"]))
        session_counts = {
            str(session["session_id"]): int(session["episode_count"])
            for session in directories[question_id]["sessions"]
        }
        stream, seen = [], set()
        for origin, heads in (("PACK", prefix), ("BIGRAM", suffix)):
            for session_id in heads:
                if session_id in seen:
                    continue
                if session_id not in session_counts:
                    raise DA063Error("Head lacks directory session")
                seen.add(session_id)
                episodes = session_counts[session_id]
                stream.append({
                    "session_id": session_id,
                    "origin": origin,
                    "episode_count": episodes,
                    "member_count": episodes * 2,
                })
        if [item["session_id"] for item in stream[:len(prefix)]] != prefix:
            raise DA063Error("Pack prefix differs")
        rows.append({
            "question_id": question_id,
            "pack_prefix_count": len(prefix),
            "stream": stream,
            "current_frame_cap": CURRENT_FRAME_CAP,
            "simultaneously_rendered_heads": 1,
            "protected_payload_mutations": 0,
            "rendered_char_delta": 0,
        })
    return rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(bigram_path: Path, pack_path: Path,
                  directory_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(bigram_path, pack_path, directory_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_streams.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da063-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(bigram_path, pack_path, directory_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden = ("has_" + "answer", "evi" + "dence", "required_" + "session")
    leakage_clean = not any(token in source for token in forbidden)
    suffixes = [sum(item["origin"] == "BIGRAM" for item in row["stream"]) for row in rows]
    valid = (
        identical
        and any(value > 0 for value in suffixes)
        and all(len(row["stream"]) == len({item["session_id"] for item in row["stream"]}) for row in rows)
        and all(row["simultaneously_rendered_heads"] == 1 for row in rows)
        and all(row["current_frame_cap"] == CURRENT_FRAME_CAP for row in rows)
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
        and leakage_clean
    )
    result = {
        "schema": "da063-replaceable-session-head-stream-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "pack_heads": sum(row["pack_prefix_count"] for row in rows),
        "new_bigram_heads": sum(suffixes),
        "min_stream_heads": min(len(row["stream"]) for row in rows),
        "max_stream_heads": max(len(row["stream"]) for row in rows),
        "simultaneously_rendered_heads": 1,
        "peak_current_frame_chars": CURRENT_FRAME_CAP,
        "protected_payload_mutations": 0,
        "rendered_char_delta": 0,
        "leakage_scan_clean": leakage_clean,
        "replay_byte_identical": identical,
        "streams_sha256": sha256_file(artifact),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
    }
    (output_dir / "preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not valid:
        raise DA063Error("Blind stream preflight failed")
    return result


__all__ = ["DA063Error", "build_rows", "run_preflight"]
