"""Exact fixed component-packet fallback for DA-089 overflow rows."""

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

FRAME_CAP = 2_048
CHUNK_CHARS = 1_800
DA089_SHA256 = "ec67f7f0e7ae44db2369f986571935061f52f4c33e8dff8c7ea63222c00ec26d"
COMPONENT_CODES = {
    "PARENT_USER": "U",
    "PARENT_ASSISTANT": "A",
    "CHILD": "C",
}
CODE_COMPONENTS = {value: key for key, value in COMPONENT_CODES.items()}


class DA090Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def render_packet(sentinel: str, component: str, index: int, total: int,
                  speaker: str, payload: str) -> str:
    code = COMPONENT_CODES.get(component)
    if code is None or not 1 <= index <= total or sentinel in payload or not speaker:
        raise DA090Error("Invalid exact component packet")
    return (
        f"{sentinel}K{code}{encode_uint(index)}{encode_uint(total)}{sentinel}"
        f"{speaker}: {payload}"
    )


def parse_packet(block: str, sentinel: str) -> tuple[str, int, int, str, str]:
    opening = sentinel + "K"
    if not block.startswith(opening):
        raise DA090Error("Malformed exact component packet")
    end = block.find(sentinel, len(opening))
    if end < 0:
        raise DA090Error("Unterminated exact component packet")
    header = block[len(opening):end]
    if not header or header[0] not in CODE_COMPONENTS:
        raise DA090Error("Unknown exact component packet")
    index, cursor = decode_uint(header, 1)
    total, cursor = decode_uint(header, cursor)
    if cursor != len(header):
        raise DA090Error("Trailing exact packet header")
    body = block[end + len(sentinel):]
    if ": " not in body:
        raise DA090Error("Malformed exact packet payload")
    speaker, payload = body.split(": ", 1)
    component = CODE_COMPONENTS[header[0]]
    if render_packet(sentinel, component, index, total, speaker, payload) != block:
        raise DA090Error("Noncanonical exact packet")
    return component, index, total, speaker, payload


def analyze(longmem_path: Path, population_path: Path,
            da089_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da089_path) != DA089_SHA256:
        raise DA090Error("Sealed DA-089 targets differ")
    controls = _read(da089_path)
    wanted = {str(row["question_id"]) for row in controls}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in wanted
    }
    if len(controls) != 8_055 or len(records) != 461:
        raise DA090Error("Packet population differs")
    rows = []
    preserved = 0
    for control in controls:
        question_id = str(control["question_id"])
        if control["state"] == "COMPLETE":
            preserved += 1
            rows.append({
                **control,
                "control_state": "COMPLETE",
                "fallback": "NONE",
            })
            continue
        record = records[question_id]
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        child_id = str(control["neighbor_id"])
        child_member = int(control["member"])
        child = by_id[child_id].members[child_member]
        if control["state"] == "FULL_CHILD_OVERFLOW":
            components = [("CHILD", child_id, child_member, child)]
            fallback = "CHILD_PACKET_STREAM"
        elif control["state"] == "ANCHORED_SLICE_OVERFLOW":
            parent_id = str(control["parent_id"])
            parent = by_id[parent_id].members
            components = [
                ("PARENT_USER", parent_id, 0, parent[0]),
                ("PARENT_ASSISTANT", parent_id, 1, parent[1]),
                ("CHILD", child_id, child_member, child),
            ]
            fallback = "EDGE_COMPONENT_PACKET_STREAM"
        else:
            raise DA090Error("Unknown DA-089 failure state")
        all_texts = [
            str(member["text"])
            for episode in record.episodes
            for member in episode.members
        ]
        sentinel = sentinel_for(all_texts)
        manifest, frame_chars = [], []
        for component, episode_id, member_index, member in components:
            text = str(member["text"])
            chunks = [
                text[start:start + CHUNK_CHARS]
                for start in range(0, len(text), CHUNK_CHARS)
            ] or [""]
            decoded = []
            for index, chunk in enumerate(chunks, start=1):
                block = render_packet(
                    sentinel, component, index, len(chunks),
                    str(member["speaker"]), chunk,
                )
                parsed = parse_packet(block, sentinel)
                expected = (
                    component, index, len(chunks), str(member["speaker"]), chunk
                )
                if parsed != expected or len(block) > FRAME_CAP:
                    raise DA090Error("Exact packet gate fails")
                decoded.append(parsed[4])
                frame_chars.append(len(block))
                manifest.append({
                    "component": component,
                    "episode_id": episode_id,
                    "member": member_index,
                    "index": index,
                    "total": len(chunks),
                    "chars": len(block),
                })
            if "".join(decoded) != text:
                raise DA090Error("Exact packet component decode differs")
        rows.append({
            **control,
            "control_state": str(control["state"]),
            "route": fallback,
            "state": "COMPLETE",
            "fallback": fallback,
            "frames": len(frame_chars),
            "peak_frame_chars": max(frame_chars),
            "cumulative_frame_chars": sum(frame_chars),
            "prompt_char_delta": 0,
            "packet_manifest": manifest,
        })
    if len(rows) != len(controls) or preserved != 4_556:
        raise DA090Error("Preserved-row population differs")
    for control, treatment in zip(controls, rows, strict=True):
        if control["state"] == "COMPLETE":
            for field in (
                "route", "frames", "peak_frame_chars",
                "cumulative_frame_chars", "prompt_char_delta",
            ):
                if treatment[field] != control[field]:
                    raise DA090Error("DA-089 complete row changed")
    fallbacks = Counter(row["fallback"] for row in rows)
    complete = sum(row["state"] == "COMPLETE" for row in rows)
    fallback_rows = [row for row in rows if row["fallback"] != "NONE"]
    result = {
        "schema": "da090-exact-component-packet-fallback-v1",
        "status": (
            "EXACT_PACKET_FALLBACK_SIGNAL"
            if complete == 8_055 else "NO_EXACT_PACKET_FALLBACK_SIGNAL"
        ),
        "targets": len(rows),
        "complete": complete,
        "preserved_da089_complete": preserved,
        "fallbacks": dict(fallbacks),
        "frames": distribution([row["frames"] for row in rows]),
        "peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows]),
        "cumulative_frame_chars": distribution([
            row["cumulative_frame_chars"] for row in rows
        ]),
        "fallback_only": {
            "targets": len(fallback_rows),
            "frames": distribution([row["frames"] for row in fallback_rows]),
            "peak_frame_chars": distribution([
                row["peak_frame_chars"] for row in fallback_rows
            ]),
            "cumulative_frame_chars": distribution([
                row["cumulative_frame_chars"] for row in fallback_rows
            ]),
        },
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "blind exact packet exposure only; no reader, retention, stopping, delivery, runtime, outcomes, or adoption",
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
                 da089_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da089_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "targets.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da090-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da089_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["targets_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA090Error("DA-090 replay differs")
    return result


__all__ = ["DA090Error", "analyze", "parse_packet", "render_packet", "run_analysis"]
