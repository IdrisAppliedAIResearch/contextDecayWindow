"""Exact parent-user and required-child endpoint coframes for DA-085."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.da034_sentinel_backrefs import sentinel_for

FRAME_CAP = 2_048
DA085_SHA256 = "defe4e35e507ebe7de6832c2318457106626333d3f429c5468707f5c50ec8e3f"


class DA086Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def render_coframe(sentinel: str, direction: int,
                   parent: Mapping[str, str], child: Mapping[str, str]) -> str:
    if direction not in (-1, 1) or any(
        sentinel in str(member["text"]) for member in (parent, child)
    ):
        raise DA086Error("Invalid endpoint coframe")
    marker = "P" if direction == 1 else "M"
    return (
        f"{sentinel}E{marker}{sentinel}"
        f"PARENT {parent['speaker']}: {parent['text']}\n"
        f"CHILD {child['speaker']}: {child['text']}"
    )


def parse_coframe(block: str, sentinel: str) -> tuple[int, str, str, str, str]:
    opening = sentinel + "E"
    if not block.startswith(opening):
        raise DA086Error("Malformed endpoint coframe")
    end = block.find(sentinel, len(opening))
    if end != len(opening) + 1:
        raise DA086Error("Malformed endpoint direction")
    marker = block[len(opening):end]
    if marker not in {"P", "M"}:
        raise DA086Error("Unknown endpoint direction")
    payload = block[end + len(sentinel):]
    if "\nCHILD " not in payload or not payload.startswith("PARENT "):
        raise DA086Error("Malformed endpoint payload")
    parent_part, child_part = payload.split("\nCHILD ", 1)
    parent_part = parent_part[len("PARENT "):]
    if ": " not in parent_part or ": " not in child_part:
        raise DA086Error("Malformed endpoint member")
    parent_role, parent_text = parent_part.split(": ", 1)
    child_role, child_text = child_part.split(": ", 1)
    direction = 1 if marker == "P" else -1
    if render_coframe(
        sentinel, direction,
        {"speaker": parent_role, "text": parent_text},
        {"speaker": child_role, "text": child_text},
    ) != block:
        raise DA086Error("Noncanonical endpoint coframe")
    return direction, parent_role, parent_text, child_role, child_text


def analyze(longmem_path: Path, population_path: Path,
            da085_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da085_path) != DA085_SHA256:
        raise DA086Error("Sealed DA-085 bridge differs")
    bridges = {str(row["key"]): row for row in _read(da085_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in bridges
    }
    if len(bridges) != len(records) or len(records) != 5:
        raise DA086Error("Coframe population differs")
    rows = []
    for question_id in sorted(bridges):
        bridge, record = bridges[question_id], records[question_id]
        if bridge["state"] != "COMPLETE_CHUNKED_BRIDGE":
            raise DA086Error("DA-085 bridge is incomplete")
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        parent = by_id[str(bridge["parent"])].members[0]
        child_index = int(bridge["edge"]["member"])
        child = by_id[str(bridge["child"])].members[child_index]
        all_texts = [
            str(member["text"])
            for episode in record.episodes
            for member in episode.members
        ]
        sentinel = sentinel_for(all_texts)
        direction = int(bridge["direction"])
        coframe = render_coframe(sentinel, direction, parent, child)
        decoded = parse_coframe(coframe, sentinel)
        expected = (
            direction,
            str(parent["speaker"]), str(parent["text"]),
            str(child["speaker"]), str(child["text"]),
        )
        if decoded != expected or len(coframe) > FRAME_CAP:
            raise DA086Error("Endpoint coframe gate fails")
        prior_actions = list(bridge["actions"][:-1])
        if len(prior_actions) != 3 or any(action["kind"] != "FRAME" for action in prior_actions):
            raise DA086Error("DA-085 parent frames differ")
        prior_child = bridge["actions"][-1]
        if prior_child["relation"] != "CHILD" or prior_child["kind"] != "FRAME":
            raise DA086Error("DA-085 child frame differs")
        prior_chars = sum(int(action["chars"]) for action in bridge["actions"])
        parent_chars = sum(int(action["chars"]) for action in prior_actions)
        final_chars = parent_chars + len(coframe)
        rows.append({
            "key": question_id,
            "question_type": str(bridge["question_type"]),
            "parent": str(bridge["parent"]),
            "child": str(bridge["child"]),
            "direction": direction,
            "state": "EXACT_ENDPOINT_COFRAME",
            "retained_parent_frames": len(prior_actions),
            "frames": len(prior_actions) + 1,
            "coframe_chars": len(coframe),
            "peak_frame_chars": max(
                len(coframe), max(int(action["chars"]) for action in prior_actions)
            ),
            "cumulative_frame_chars": final_chars,
            "incremental_chars_vs_da085": final_chars - prior_chars,
            "prompt_char_delta": 0,
            "edge": dict(bridge["edge"]),
        })
    exact = sum(row["state"] == "EXACT_ENDPOINT_COFRAME" for row in rows)
    result = {
        "schema": "da086-parent-child-endpoint-coframe-v1",
        "status": "ENDPOINT_COFRAME_SIGNAL" if exact == 5 else "NO_ENDPOINT_COFRAME_SIGNAL",
        "bridges": len(rows),
        "exact_coframes": exact,
        "frames": distribution([row["frames"] for row in rows]),
        "coframe_chars": distribution([row["coframe_chars"] for row in rows]),
        "peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows]),
        "cumulative_frame_chars": distribution([
            row["cumulative_frame_chars"] for row in rows
        ]),
        "incremental_chars_vs_da085": distribution([
            row["incremental_chars_vs_da085"] for row in rows
        ]),
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "exact simultaneous endpoint exposure only; no reader, retention, stopping, transfer, delivery, runtime, or adoption",
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
                 da085_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da085_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "coframes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da086-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da085_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["coframes_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA086Error("DA-086 replay differs")
    return result


__all__ = ["DA086Error", "analyze", "parse_coframe", "render_coframe", "run_analysis"]
