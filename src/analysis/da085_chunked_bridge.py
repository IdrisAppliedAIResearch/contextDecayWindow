"""Exact fixed-chunk materialization of DA-084 orphan parent bridges."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da031_varint_backrefs import decode_uint, encode_uint
from analysis.da032_audit import distribution
from analysis.da034_sentinel_backrefs import sentinel_for
from analysis.da044_allocation import parse_block, render_block

FRAME_CAP = 2_048
CHUNK_CHARS = 1_900
DA084_SHA256 = "c041a806b7a33025018e8fc03b4f6a5b8a8fb9b234adb06b07214b06beaa2f4b"


class DA085Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def render_chunk(sentinel: str, index: int, total: int,
                 speaker: str, payload: str) -> str:
    if not 1 <= index <= total or sentinel in payload or not speaker:
        raise DA085Error("Invalid exact chunk")
    return (
        f"{sentinel}C{encode_uint(index)}{encode_uint(total)}{sentinel}"
        f"{speaker}: {payload}"
    )


def parse_chunk(block: str, sentinel: str) -> tuple[int, int, str, str]:
    opening = sentinel + "C"
    if not block.startswith(opening):
        raise DA085Error("Malformed exact chunk")
    end = block.find(sentinel, len(opening))
    if end < 0:
        raise DA085Error("Unterminated exact chunk")
    index, cursor = decode_uint(block[len(opening):end], 0)
    total, cursor = decode_uint(block[len(opening):end], cursor)
    if cursor != end - len(opening):
        raise DA085Error("Trailing exact chunk header")
    body = block[end + len(sentinel):]
    if ": " not in body:
        raise DA085Error("Malformed exact chunk payload")
    speaker, payload = body.split(": ", 1)
    if render_chunk(sentinel, index, total, speaker, payload) != block:
        raise DA085Error("Noncanonical exact chunk")
    return index, total, speaker, payload


def analyze(longmem_path: Path, population_path: Path,
            da084_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da084_path) != DA084_SHA256:
        raise DA085Error("Sealed DA-084 bridge differs")
    bridges = {str(row["key"]): row for row in _read(da084_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in bridges
    }
    if len(bridges) != len(records) or len(records) != 5:
        raise DA085Error("Bridge population differs")
    rows = []
    for question_id in sorted(bridges):
        bridge, record = bridges[question_id], records[question_id]
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        all_texts = [
            str(member["text"])
            for episode in record.episodes
            for member in episode.members
        ]
        sentinel = sentinel_for(all_texts)
        parent = str(bridge["parent"])
        child = str(bridge["child"])
        parent_members = by_id[parent].members
        child_member = by_id[child].members[int(bridge["required_child_member"])]
        actions = []

        user_block = render_block(sentinel, 1, parent_members[0])
        if parse_block(user_block, sentinel) != (
            1, str(parent_members[0]["speaker"]), str(parent_members[0]["text"])
        ):
            raise DA085Error("Parent user decode differs")
        actions.append({
            "relation": "PARENT_USER",
            "kind": "FRAME" if len(user_block) <= FRAME_CAP else "OVERFLOW",
            "chars": len(user_block),
        })

        assistant_text = str(parent_members[1]["text"])
        chunks = [
            assistant_text[start:start + CHUNK_CHARS]
            for start in range(0, len(assistant_text), CHUNK_CHARS)
        ]
        decoded = []
        for index, payload in enumerate(chunks, start=1):
            block = render_chunk(
                sentinel, index, len(chunks), str(parent_members[1]["speaker"]), payload
            )
            parsed_index, parsed_total, speaker, parsed_payload = parse_chunk(block, sentinel)
            if (parsed_index, parsed_total, speaker) != (
                index, len(chunks), str(parent_members[1]["speaker"])
            ):
                raise DA085Error("Parent assistant chunk header differs")
            decoded.append(parsed_payload)
            actions.append({
                "relation": "PARENT_ASSISTANT_CHUNK",
                "chunk": index,
                "chunks": len(chunks),
                "kind": "FRAME" if len(block) <= FRAME_CAP else "OVERFLOW",
                "chars": len(block),
            })
        if "".join(decoded) != assistant_text:
            raise DA085Error("Parent assistant exact decode differs")

        child_ordinal = len(chunks) + 2
        child_block = render_block(sentinel, child_ordinal, child_member)
        if parse_block(child_block, sentinel) != (
            child_ordinal, str(child_member["speaker"]), str(child_member["text"])
        ):
            raise DA085Error("Required child decode differs")
        actions.append({
            "relation": "CHILD",
            "kind": "FRAME" if len(child_block) <= FRAME_CAP else "OVERFLOW",
            "chars": len(child_block),
        })
        complete = all(action["kind"] == "FRAME" for action in actions)
        rows.append({
            "key": question_id,
            "question_type": str(bridge["question_type"]),
            "blocker": str(bridge["blocker"]),
            "parent": parent,
            "child": child,
            "direction": int(bridge["direction"]),
            "state": "COMPLETE_CHUNKED_BRIDGE" if complete else "INCOMPLETE_CHUNKED_BRIDGE",
            "assistant_chunks": len(chunks),
            "frames": sum(action["kind"] == "FRAME" for action in actions),
            "overflows": sum(action["kind"] == "OVERFLOW" for action in actions),
            "peak_frame_chars": max(action["chars"] for action in actions if action["kind"] == "FRAME"),
            "cumulative_frame_chars": sum(action["chars"] for action in actions if action["kind"] == "FRAME"),
            "parent_new_vs_prompt": int(bridge["parent_new_vs_prompt"]),
            "prompt_char_delta": 0,
            "edge": dict(bridge["edge"]),
            "actions": actions,
        })

    complete = sum(row["state"] == "COMPLETE_CHUNKED_BRIDGE" for row in rows)
    result = {
        "schema": "da085-exact-chunked-parent-bridge-v1",
        "status": "CHUNKED_PARENT_BRIDGE_SIGNAL" if complete == 5 else "NO_CHUNKED_PARENT_BRIDGE_SIGNAL",
        "bridges": len(rows),
        "complete": complete,
        "states": dict(Counter(row["state"] for row in rows)),
        "assistant_chunks": distribution([row["assistant_chunks"] for row in rows]),
        "frames": distribution([row["frames"] for row in rows]),
        "peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows]),
        "cumulative_frame_chars": distribution([
            row["cumulative_frame_chars"] for row in rows
        ]),
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "exact chunked parent-child exposure only; no reader, stopping, transfer, delivery, runtime, or adoption",
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
                 da084_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da084_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "bridges.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da085-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da084_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["bridges_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA085Error("DA-085 replay differs")
    return result


__all__ = ["DA085Error", "analyze", "parse_chunk", "render_chunk", "run_analysis"]
