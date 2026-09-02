"""Typed-edge provenance with exact child-only packet exposure for DA-091."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.da034_sentinel_backrefs import sentinel_for
from analysis.da090_packet_fallback import CHUNK_CHARS, FRAME_CAP, parse_packet, render_packet

DA090_SHA256 = "76a07552baaf87504cb130bb45f706263c5c2a9d961223bd5c779dd1d3375923"
ELIGIBLE_ROUTE = "EDGE_COMPONENT_PACKET_STREAM"


class DA091Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(longmem_path: Path, population_path: Path,
            da090_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da090_path) != DA090_SHA256:
        raise DA091Error("Sealed DA-090 targets differ")
    controls = _read(da090_path)
    wanted = {str(row["question_id"]) for row in controls}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in wanted
    }
    if len(controls) != 8_055 or len(records) != 461:
        raise DA091Error("Typed-edge population differs")

    rows: list[dict[str, Any]] = []
    eligible = 0
    savings: list[int] = []
    for control in controls:
        if control["route"] != ELIGIBLE_ROUTE:
            rows.append({**control, "typed_edge_substitution": False})
            continue

        eligible += 1
        question_id = str(control["question_id"])
        record = records[question_id]
        by_id = {episode.candidate.identity: episode for episode in record.episodes}
        child_id = str(control["neighbor_id"])
        member_index = int(control["member"])
        child = by_id[child_id].members[member_index]
        all_texts = [
            str(member["text"])
            for episode in record.episodes
            for member in episode.members
        ]
        sentinel = sentinel_for(all_texts)
        text = str(child["text"])
        chunks = [
            text[start:start + CHUNK_CHARS]
            for start in range(0, len(text), CHUNK_CHARS)
        ] or [""]
        decoded: list[str] = []
        manifest: list[dict[str, Any]] = []
        frame_chars: list[int] = []
        for index, chunk in enumerate(chunks, start=1):
            block = render_packet(
                sentinel, "CHILD", index, len(chunks),
                str(child["speaker"]), chunk,
            )
            parsed = parse_packet(block, sentinel)
            expected = ("CHILD", index, len(chunks), str(child["speaker"]), chunk)
            if parsed != expected or len(block) > FRAME_CAP:
                raise DA091Error("Exact child packet gate fails")
            decoded.append(parsed[4])
            frame_chars.append(len(block))
            manifest.append({
                "component": "CHILD",
                "episode_id": child_id,
                "member": member_index,
                "index": index,
                "total": len(chunks),
                "chars": len(block),
            })
        if "".join(decoded) != text:
            raise DA091Error("Exact child decode differs")

        cumulative = sum(frame_chars)
        peak = max(frame_chars)
        saved = int(control["cumulative_frame_chars"]) - cumulative
        if saved <= 0 or peak > int(control["peak_frame_chars"]):
            raise DA091Error("Typed edge does not strictly dominate payload replay")
        savings.append(saved)
        rows.append({
            **control,
            "route": "TYPED_EDGE_CHILD_PACKET_STREAM",
            "frames": len(frame_chars),
            "peak_frame_chars": peak,
            "cumulative_frame_chars": cumulative,
            "typed_edge_substitution": True,
            "typed_edge": {
                "parent_id": str(control["parent_id"]),
                "child_id": child_id,
                "member": member_index,
                "direction": int(control["direction"]),
            },
            "packet_manifest": manifest,
            "saved_cumulative_chars": saved,
        })

    if eligible != 798 or len(rows) != len(controls):
        raise DA091Error("Eligible typed-edge count differs")
    protected_fields = (
        "route", "frames", "peak_frame_chars", "cumulative_frame_chars",
        "prompt_char_delta", "state", "neighbor_id", "member", "parent_id",
        "direction",
    )
    for control, treatment in zip(controls, rows, strict=True):
        if control["route"] != ELIGIBLE_ROUTE:
            for field in protected_fields:
                if treatment[field] != control[field]:
                    raise DA091Error("Noneligible DA-090 row changed")

    result = {
        "schema": "da091-typed-edge-child-stream-v1",
        "status": "TYPED_EDGE_CHILD_STREAM_SIGNAL",
        "targets": len(rows),
        "eligible_substitutions": eligible,
        "preserved_noneligible": len(rows) - eligible,
        "routes": dict(Counter(row["route"] for row in rows)),
        "eligible_savings_chars": distribution(savings),
        "eligible_frames": distribution([
            row["frames"] for row in rows if row["typed_edge_substitution"]
        ]),
        "eligible_peak_frame_chars": distribution([
            row["peak_frame_chars"] for row in rows if row["typed_edge_substitution"]
        ]),
        "eligible_cumulative_frame_chars": distribution([
            row["cumulative_frame_chars"]
            for row in rows if row["typed_edge_substitution"]
        ]),
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "blind typed dependency representation only; reader use and delivery untested",
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
                 da090_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da090_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "targets.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da091-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da090_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["targets_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA091Error("DA-091 replay differs")
    return result


__all__ = ["DA091Error", "analyze", "run_analysis"]
