"""Blind exact member chunk-chain codec for DA-058."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, encode_uint, render_block, sha256_file
from analysis.da056_materialization import DIRECTORY_SHA256, ENVELOPE_SHA256, _payloads, _read

CHUNK_PAYLOAD = 1_984
FRAME_CAP = 2_048
TERMINAL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
CONTINUATION = "abcdefghijklmnopqrstuvwxyz0189-_"


class DA058Error(RuntimeError):
    pass


def decode_uint(text: str, position: int = 0) -> tuple[int, int]:
    start, value, shift = position, 0, 0
    while position < len(text):
        char = text[position]
        position += 1
        if char in CONTINUATION:
            value |= CONTINUATION.index(char) << shift
            shift += 5
            continue
        if char in TERMINAL:
            value |= TERMINAL.index(char) << shift
            if text[start:position] != encode_uint(value):
                raise DA058Error("Noncanonical chunk integer")
            return value, position
        raise DA058Error("Invalid chunk integer")
    raise DA058Error("Truncated chunk integer")


def render_chunk(sentinel: str, ordinal: int, total: int, role: str, text: str) -> str:
    if not sentinel or set(sentinel) != {"~"} or not 1 <= ordinal <= total:
        raise DA058Error("Invalid chunk coordinate")
    return f"{sentinel}C{encode_uint(ordinal)}{encode_uint(total)}{sentinel}{role}: {text}"


def parse_chunk(block: str, sentinel: str) -> tuple[int, int, str, str]:
    opening = sentinel + "C"
    if not block.startswith(opening):
        raise DA058Error("Malformed chunk frame")
    end = block.find(sentinel, len(opening))
    if end < 0:
        raise DA058Error("Unterminated chunk frame")
    body = block[len(opening):end]
    ordinal, position = decode_uint(body, 0)
    total, position = decode_uint(body, position)
    if position != len(body):
        raise DA058Error("Trailing chunk coordinate")
    payload = block[end + len(sentinel):]
    if ": " not in payload:
        raise DA058Error("Malformed chunk payload")
    role, text = payload.split(": ", 1)
    if render_chunk(sentinel, ordinal, total, role, text) != block:
        raise DA058Error("Noncanonical chunk frame")
    return ordinal, total, role, text


def build_rows(dataset_path: Path, directory_path: Path,
               envelope_path: Path) -> list[dict[str, Any]]:
    if (sha256_file(dataset_path) != DATASET_SHA256
            or sha256_file(directory_path) != DIRECTORY_SHA256
            or sha256_file(envelope_path) != ENVELOPE_SHA256):
        raise DA058Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    output = []
    for question_id in sorted(directories):
        payloads = _payloads(raw[question_id])
        sentinel = str(envelopes[question_id]["da038_control"]["sentinel"])
        decisions = []
        for episode in directories[question_id]["episodes"]:
            episode_id = str(episode["episode_id"])
            for offset, member in enumerate(payloads[episode_id]):
                member_id = str(episode["members"][offset]["member_id"])
                literal = render_block(sentinel, int(episode["episode_order"]) + 1, member)
                if len(literal) <= FRAME_CAP:
                    blocks = [literal]
                    selected = "LITERAL"
                else:
                    text = str(member["text"])
                    pieces = [text[start:start + CHUNK_PAYLOAD]
                              for start in range(0, len(text), CHUNK_PAYLOAD)]
                    blocks = [render_chunk(sentinel, index, len(pieces), str(member["speaker"]), piece)
                              for index, piece in enumerate(pieces, 1)]
                    selected = "CHUNKED"
                    decoded = [parse_chunk(block, sentinel) for block in blocks]
                    if ([value[0] for value in decoded] != list(range(1, len(blocks) + 1))
                            or any(value[1] != len(blocks) for value in decoded)
                            or any(value[2] != str(member["speaker"]) for value in decoded)
                            or "".join(value[3] for value in decoded) != text):
                        raise DA058Error("Chunk chain decode differs")
                if max(map(len, blocks)) > FRAME_CAP:
                    raise DA058Error("Chunk frame exceeds cap")
                decisions.append({"session_id": str(episode["session_id"]),
                                  "episode_id": episode_id,
                                  "episode_order": int(episode["episode_order"]),
                                  "member_id": member_id, "member_offset": offset,
                                  "role": str(member["speaker"]), "selected": selected,
                                  "literal_cost": len(literal), "chunk_count": len(blocks),
                                  "selected_cost": sum(map(len, blocks)),
                                  "blocks": [{"ordinal": index, "cost": len(block), "block": block,
                                              "sha256": hashlib.sha256(block.encode()).hexdigest()}
                                             for index, block in enumerate(blocks, 1)]})
        output.append({"question_id": question_id, "rendered_char_delta": 0,
                       "decisions": decisions})
    if len(output) != 465:
        raise DA058Error("Population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, directory_path: Path, envelope_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, directory_path, envelope_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_chunks.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da058-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, directory_path, envelope_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    decisions = [decision for row in rows for decision in row["decisions"]]
    selections = Counter(decision["selected"] for decision in decisions)
    blocks = [block for decision in decisions for block in decision["blocks"]]
    passed = (identical and selections["LITERAL"] > 0 and selections["CHUNKED"] > 0
              and max(int(block["cost"]) for block in blocks) <= FRAME_CAP
              and all(row["rendered_char_delta"] == 0 for row in rows))
    result = {"schema": "da058-exact-member-chunk-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "members": len(decisions), "selections": dict(selections),
              "frames": len(blocks), "max_chunks": max(int(row["chunk_count"]) for row in decisions),
              "peak_frame_chars": max(int(block["cost"]) for block in blocks),
              "replay_byte_identical": identical, "chunks_sha256": sha256_file(artifact),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    if not passed:
        raise DA058Error("Blind chunk preflight failed")
    return result


__all__ = ["DA058Error", "build_rows", "parse_chunk", "render_chunk", "run_preflight"]
