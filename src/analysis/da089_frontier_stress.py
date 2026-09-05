"""Blind full-frontier stress test of the DA-088 dependency envelope."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.da034_sentinel_backrefs import sentinel_for
from analysis.da044_allocation import parse_block, render_block
from analysis.da078_allocation import _protected_descriptors
from analysis.da087_anchored_slices import parse_slice, render_slice

FRAME_CAP = 2_048
CHUNK_CHARS = 1_200
DA042_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"


class DA089Error(RuntimeError):
    pass


def analyze(longmem_path: Path, population_path: Path, da042_path: Path,
            da078_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da042_path) != DA042_SHA256 or sha256_file(da078_path) != DA078_SHA256:
        raise DA089Error("Sealed input differs")
    frontiers = {str(row["question_id"]): row for row in read_gzip(da042_path)}
    selections = {str(row["question_id"]): row for row in read_gzip(da078_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
    }
    if set(frontiers) != set(selections) or len(frontiers) != 465:
        raise DA089Error("Question population differs")
    rows = []
    for question_id in sorted(frontiers):
        frontier = frontiers[question_id]
        selection = selections[question_id]
        record = records[question_id]
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        pair_for = lambda identity: by_id[identity].members
        da038_row = {**selection, "treatment": selection["da038_control"]}
        descriptors = _protected_descriptors(da038_row, pair_for)
        for action in selection["treatment"]["actions"]:
            if action["kind"] == "MEMBER":
                descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
        prompt_members = {
            (identity, index)
            for identity, members in descriptors
            for index in members
        }
        prompt_episodes = {identity for identity, _ in prompt_members}
        first_parent: dict[str, Mapping[str, Any]] = {}
        for edge in frontier["baseline_actions"]:
            first_parent.setdefault(str(edge["neighbor_id"]), edge)
        all_texts = [
            str(member["text"])
            for episode in record.episodes
            for member in episode.members
        ]
        sentinel = sentinel_for(all_texts)
        for target_position, raw_target in enumerate(frontier["treatment"]["targets"], start=1):
            target = (str(raw_target[0]), int(raw_target[1]))
            pair = pair_for(target[0])
            if not 0 <= target[1] < len(pair):
                raise DA089Error("Frontier target member differs")
            parent_edge = first_parent.get(target[0])
            if parent_edge is None:
                raise DA089Error("Frontier target has no baseline parent")
            parent = str(parent_edge["seed_id"])
            direction = int(parent_edge["direction"])
            frames: list[int] = []
            if target in prompt_members:
                route = "PROMPT_MEMBER"
                state = "COMPLETE"
            elif len(pair) == 2 and (target[0], 1 - target[1]) in prompt_members:
                route = "PROMPT_SIBLING_FRAME"
                block = render_block(sentinel, target_position, pair[target[1]])
                if parse_block(block, sentinel) != (
                    target_position, str(pair[target[1]]["speaker"]), str(pair[target[1]]["text"])
                ):
                    raise DA089Error("Sibling child frame decode differs")
                frames = [len(block)]
                state = "COMPLETE" if len(block) <= FRAME_CAP else "FULL_CHILD_OVERFLOW"
            elif parent in prompt_episodes:
                route = "PROMPT_LINKED_FRAME"
                block = render_block(sentinel, target_position, pair[target[1]])
                if parse_block(block, sentinel) != (
                    target_position, str(pair[target[1]]["speaker"]), str(pair[target[1]]["text"])
                ):
                    raise DA089Error("Linked child frame decode differs")
                frames = [len(block)]
                state = "COMPLETE" if len(block) <= FRAME_CAP else "FULL_CHILD_OVERFLOW"
            else:
                route = "ANCHORED_EDGE_SLICES"
                parent_members = pair_for(parent)
                if len(parent_members) != 2:
                    raise DA089Error("Anchored parent arity differs")
                assistant_text = str(parent_members[1]["text"])
                chunks = [
                    assistant_text[start:start + CHUNK_CHARS]
                    for start in range(0, len(assistant_text), CHUNK_CHARS)
                ] or [""]
                decoded = []
                for index, chunk in enumerate(chunks, start=1):
                    block = render_slice(
                        sentinel, direction, index, len(chunks),
                        parent_members[0], str(parent_members[1]["speaker"]),
                        chunk, pair[target[1]],
                    )
                    parsed = parse_slice(block, sentinel)
                    if parsed[6] != chunk:
                        raise DA089Error("Anchored slice decode differs")
                    decoded.append(parsed[6])
                    frames.append(len(block))
                if "".join(decoded) != assistant_text:
                    raise DA089Error("Anchored parent context differs")
                state = (
                    "COMPLETE" if all(chars <= FRAME_CAP for chars in frames)
                    else "ANCHORED_SLICE_OVERFLOW"
                )
            rows.append({
                "question_id": question_id,
                "question_type": record.question_type,
                "target_position": target_position,
                "neighbor_id": target[0],
                "member": target[1],
                "parent_id": parent,
                "direction": direction,
                "route": route,
                "state": state,
                "frames": len(frames),
                "peak_frame_chars": max(frames, default=0),
                "cumulative_frame_chars": sum(frames),
                "prompt_char_delta": 0,
            })
    if len(rows) != 8_055:
        raise DA089Error("Frontier target count differs")
    routes = Counter(row["route"] for row in rows)
    states = Counter(row["state"] for row in rows)
    complete = states["COMPLETE"]
    result = {
        "schema": "da089-full-frontier-envelope-stress-v1",
        "status": (
            "FULL_FRONTIER_ENVELOPE_SIGNAL"
            if complete == len(rows) else "PARTIAL_FRONTIER_ENVELOPE_SIGNAL"
        ),
        "targets": len(rows),
        "complete": complete,
        "complete_rate": complete / len(rows),
        "routes": dict(routes),
        "states": dict(states),
        "frames": distribution([row["frames"] for row in rows]),
        "peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows]),
        "cumulative_frame_chars": distribution([
            row["cumulative_frame_chars"] for row in rows
        ]),
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "blind full-frontier structural exposure stress only; no reader, retention, stopping, delivery, runtime, outcomes, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(longmem_path: Path, population_path: Path, da042_path: Path,
                 da078_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da042_path, da078_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "targets.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da089-") as directory:
        replay_result, replay_rows = analyze(
            longmem_path, population_path, da042_path, da078_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["targets_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA089Error("DA-089 replay differs")
    return result


__all__ = ["DA089Error", "analyze", "run_analysis"]
