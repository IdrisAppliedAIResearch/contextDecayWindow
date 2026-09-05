"""Self-contained parent-assistant-child edge slices for DA-086 bridges."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da031_varint_backrefs import decode_uint, encode_uint
from analysis.da032_audit import distribution
from analysis.da034_sentinel_backrefs import sentinel_for

FRAME_CAP = 2_048
CHUNK_CHARS = 1_200
DA086_SHA256 = "a4643d8d60cc450cb1e08afd5f182f2617529d9589eb83bcaa52e3df7df8ad63"


class DA087Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def render_slice(sentinel: str, direction: int, index: int, total: int,
                 parent: Mapping[str, str], assistant_role: str,
                 chunk: str, child: Mapping[str, str]) -> str:
    if direction not in (-1, 1) or not 1 <= index <= total:
        raise DA087Error("Invalid anchored edge slice")
    if any(sentinel in value for value in (
        str(parent["text"]), chunk, str(child["text"])
    )):
        raise DA087Error("Sentinel occurs in anchored slice")
    marker = "P" if direction == 1 else "M"
    return (
        f"{sentinel}S{marker}{encode_uint(index)}{encode_uint(total)}{sentinel}"
        f"PARENT {parent['speaker']}: {parent['text']}\n"
        f"CONTEXT {assistant_role}: {chunk}\n"
        f"CHILD {child['speaker']}: {child['text']}"
    )


def parse_slice(block: str, sentinel: str) -> tuple[int, int, int, str, str, str, str, str, str]:
    opening = sentinel + "S"
    if not block.startswith(opening):
        raise DA087Error("Malformed anchored slice")
    end = block.find(sentinel, len(opening))
    if end < 0:
        raise DA087Error("Unterminated anchored slice")
    header = block[len(opening):end]
    if not header or header[0] not in {"P", "M"}:
        raise DA087Error("Malformed anchored direction")
    index, cursor = decode_uint(header, 1)
    total, cursor = decode_uint(header, cursor)
    if cursor != len(header):
        raise DA087Error("Trailing anchored header")
    payload = block[end + len(sentinel):]
    if not payload.startswith("PARENT ") or "\nCONTEXT " not in payload or "\nCHILD " not in payload:
        raise DA087Error("Malformed anchored payload")
    parent_part, remainder = payload[len("PARENT "):].split("\nCONTEXT ", 1)
    context_part, child_part = remainder.split("\nCHILD ", 1)
    if any(": " not in part for part in (parent_part, context_part, child_part)):
        raise DA087Error("Malformed anchored member")
    parent_role, parent_text = parent_part.split(": ", 1)
    context_role, chunk = context_part.split(": ", 1)
    child_role, child_text = child_part.split(": ", 1)
    direction = 1 if header[0] == "P" else -1
    if render_slice(
        sentinel, direction, index, total,
        {"speaker": parent_role, "text": parent_text}, context_role, chunk,
        {"speaker": child_role, "text": child_text},
    ) != block:
        raise DA087Error("Noncanonical anchored slice")
    return (
        direction, index, total, parent_role, parent_text,
        context_role, chunk, child_role, child_text,
    )


def analyze(longmem_path: Path, population_path: Path,
            da086_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da086_path) != DA086_SHA256:
        raise DA087Error("Sealed DA-086 coframe differs")
    bridges = {str(row["key"]): row for row in _read(da086_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in bridges
    }
    if len(bridges) != len(records) or len(records) != 5:
        raise DA087Error("Anchored-slice population differs")
    rows = []
    for question_id in sorted(bridges):
        bridge, record = bridges[question_id], records[question_id]
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        parent_members = by_id[str(bridge["parent"])].members
        child = by_id[str(bridge["child"])].members[int(bridge["edge"]["member"])]
        all_texts = [
            str(member["text"])
            for episode in record.episodes
            for member in episode.members
        ]
        sentinel = sentinel_for(all_texts)
        assistant_text = str(parent_members[1]["text"])
        chunks = [
            assistant_text[start:start + CHUNK_CHARS]
            for start in range(0, len(assistant_text), CHUNK_CHARS)
        ]
        frames, decoded_chunks = [], []
        for index, chunk in enumerate(chunks, start=1):
            block = render_slice(
                sentinel, int(bridge["direction"]), index, len(chunks),
                parent_members[0], str(parent_members[1]["speaker"]), chunk, child,
            )
            decoded = parse_slice(block, sentinel)
            expected = (
                int(bridge["direction"]), index, len(chunks),
                str(parent_members[0]["speaker"]), str(parent_members[0]["text"]),
                str(parent_members[1]["speaker"]), chunk,
                str(child["speaker"]), str(child["text"]),
            )
            if decoded != expected or len(block) > FRAME_CAP:
                raise DA087Error("Anchored slice gate fails")
            decoded_chunks.append(decoded[6])
            frames.append({"index": index, "total": len(chunks), "chars": len(block)})
        if "".join(decoded_chunks) != assistant_text:
            raise DA087Error("Anchored assistant decode differs")
        cumulative = sum(frame["chars"] for frame in frames)
        da086_cumulative = int(bridge["cumulative_frame_chars"])
        da085_cumulative = da086_cumulative - int(bridge["incremental_chars_vs_da085"])
        rows.append({
            "key": question_id,
            "question_type": str(bridge["question_type"]),
            "parent": str(bridge["parent"]),
            "child": str(bridge["child"]),
            "direction": int(bridge["direction"]),
            "state": "COMPLETE_ANCHORED_EDGE_SLICES",
            "frames": len(frames),
            "peak_frame_chars": max(frame["chars"] for frame in frames),
            "cumulative_frame_chars": cumulative,
            "delta_frames_vs_da086": len(frames) - int(bridge["frames"]),
            "delta_chars_vs_da086": cumulative - da086_cumulative,
            "delta_chars_vs_da085": cumulative - da085_cumulative,
            "prompt_char_delta": 0,
            "edge": dict(bridge["edge"]),
            "frame_manifest": frames,
        })
    complete = sum(row["state"] == "COMPLETE_ANCHORED_EDGE_SLICES" for row in rows)
    result = {
        "schema": "da087-anchored-edge-slices-v1",
        "status": "ANCHORED_EDGE_SLICE_SIGNAL" if complete == 5 else "NO_ANCHORED_EDGE_SLICE_SIGNAL",
        "bridges": len(rows),
        "complete": complete,
        "frames": distribution([row["frames"] for row in rows]),
        "peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows]),
        "cumulative_frame_chars": distribution([
            row["cumulative_frame_chars"] for row in rows
        ]),
        "delta_frames_vs_da086": distribution([
            row["delta_frames_vs_da086"] for row in rows
        ]),
        "delta_chars_vs_da086": distribution([
            row["delta_chars_vs_da086"] for row in rows
        ]),
        "delta_chars_vs_da085": distribution([
            row["delta_chars_vs_da085"] for row in rows
        ]),
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "exact self-contained edge-slice exposure only; no reader, retention, stopping, transfer, delivery, runtime, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(longmem_path: Path, population_path: Path,
                 da086_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da086_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "slices.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da087-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da086_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["slices_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA087Error("DA-087 replay differs")
    return result


__all__ = ["DA087Error", "analyze", "parse_slice", "render_slice", "run_analysis"]
