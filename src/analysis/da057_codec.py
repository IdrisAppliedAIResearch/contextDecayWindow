"""Blind exact episode-local derivative codec for DA-057."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, encode_uint, sha256_file
from analysis.da056_materialization import DIRECTORY_SHA256, ENVELOPE_SHA256, _payloads, _read

TERMINAL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
CONTINUATION = "abcdefghijklmnopqrstuvwxyz0189-_"


class DA057Error(RuntimeError):
    pass


def prefix_for(texts: Sequence[str]) -> str:
    prefix = "~"
    while any(prefix + marker in text for text in texts for marker in ("r", "q", "v")):
        prefix += "~"
    return prefix


def reference_code(prefix: str, start: int, length: int) -> str:
    if start < 0 or length <= 0:
        raise DA057Error("Invalid local backreference")
    return f"{prefix}v{encode_uint(1)}{encode_uint(start)}{encode_uint(length)}{prefix}"


def encode_assistant(user: str, assistant: str, prefix: str) -> list[dict[str, Any]]:
    index: dict[str, list[int]] = {}
    for start in range(max(0, len(user) - 3)):
        index.setdefault(user[start:start + 4], []).append(start)
    segments: list[dict[str, Any]] = []
    position = 0
    while position < len(assistant):
        starts = index.get(assistant[position:position + 4], ()) if position + 4 <= len(assistant) else ()
        best_length, best_start = 0, None
        for start in starts:
            limit = min(len(assistant) - position, len(user) - start)
            length = 4
            while length < limit and assistant[position + length] == user[start + length]:
                length += 1
            if length > best_length or (length == best_length and best_start is not None and start < best_start):
                best_length, best_start = length, start
        if best_start is not None and best_length > len(reference_code(prefix, best_start, best_length)):
            segments.append({"start": best_start, "length": best_length})
            position += best_length
            continue
        if segments and "literal" in segments[-1]:
            segments[-1]["literal"] += assistant[position]
        else:
            segments.append({"literal": assistant[position]})
        position += 1
    return segments


def encoded_text(segments: Sequence[Mapping[str, Any]], prefix: str) -> str:
    return "".join(str(segment["literal"]) if "literal" in segment else
                   reference_code(prefix, int(segment["start"]), int(segment["length"]))
                   for segment in segments)


def decode_assistant(user: str, segments: Sequence[Mapping[str, Any]]) -> str:
    chunks = []
    for segment in segments:
        if "literal" in segment:
            chunks.append(str(segment["literal"]))
        else:
            start, length = int(segment["start"]), int(segment["length"])
            if start < 0 or length <= 0 or start + length > len(user):
                raise DA057Error("Backreference exceeds user premise")
            chunks.append(user[start:start + length])
    return "".join(chunks)


def build_rows(dataset_path: Path, directory_path: Path,
               envelope_path: Path) -> list[dict[str, Any]]:
    if (sha256_file(dataset_path) != DATASET_SHA256
            or sha256_file(directory_path) != DIRECTORY_SHA256
            or sha256_file(envelope_path) != ENVELOPE_SHA256):
        raise DA057Error("Sealed input differs")
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
            user, assistant = payloads[episode_id][0]["text"], payloads[episode_id][1]["text"]
            prefix = prefix_for((user, assistant))
            segments = encode_assistant(user, assistant, prefix)
            if decode_assistant(user, segments) != assistant:
                raise DA057Error("Episode derivative decode differs")
            marker = f"{sentinel}N{encode_uint(int(episode['episode_order']) + 1)}{sentinel}"
            literal = f"{marker}User: {user}\nAssistant: {assistant}"
            coded = f"{marker}User: {user}\nAssistant: {encoded_text(segments, prefix)}"
            selected = "CODED" if len(coded) < len(literal) else "LITERAL"
            block = coded if selected == "CODED" else literal
            decisions.append({"session_id": str(episode["session_id"]),
                              "episode_id": episode_id,
                              "episode_order": int(episode["episode_order"]),
                              "user_member_id": str(episode["members"][0]["member_id"]),
                              "assistant_member_id": str(episode["members"][1]["member_id"]),
                              "prefix": prefix, "segments": segments, "selected": selected,
                              "literal_cost": len(literal), "coded_cost": len(coded),
                              "selected_cost": len(block),
                              "selected_block": block,
                              "selected_sha256": hashlib.sha256(block.encode()).hexdigest()})
        output.append({"question_id": question_id, "rendered_char_delta": 0,
                       "decisions": decisions})
    if len(output) != 465:
        raise DA057Error("Population differs")
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
    artifact = output_dir / "blind_codec.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da057-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, directory_path, envelope_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    decisions = [decision for row in rows for decision in row["decisions"]]
    selections = Counter(decision["selected"] for decision in decisions)
    savings = [int(decision["literal_cost"]) - int(decision["selected_cost"]) for decision in decisions]
    passed = (identical and selections["CODED"] > 0 and selections["LITERAL"] > 0
              and min(savings) >= 0 and all(row["rendered_char_delta"] == 0 for row in rows))
    result = {"schema": "da057-episode-derivative-codec-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "episodes": len(decisions), "selections": dict(selections),
              "saved_chars": sum(savings), "max_saved_chars": max(savings),
              "replay_byte_identical": identical, "codec_sha256": sha256_file(artifact),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    if not passed:
        raise DA057Error("Blind codec preflight failed")
    return result


__all__ = ["DA057Error", "build_rows", "decode_assistant", "encode_assistant",
           "run_preflight"]
