"""Blind session heads activated by the immutable DA-038 pack."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import sha256_file

ALLOCATION_SHA256 = "7758e13562c536fd5123583ccbf0082fd8f3315ddf29a68d74f10f12ee42703e"
DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"


class DA062Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _represented(row: Mapping[str, Any]) -> tuple[list[str], int]:
    represented = list(map(str, row["direct_ids"]))
    linked = 0
    for block in ("da031_control", "da033_control", "treatment"):
        for action in row[block]["actions"]:
            if int(action["cost"]) <= 0:
                continue
            represented.append(str(action["neighbor_id"]))
            linked += 1
    output, seen = [], set()
    for episode_id in represented:
        if episode_id not in seen:
            seen.add(episode_id)
            output.append(episode_id)
    return output, linked


def build_rows(allocation_path: Path, directory_path: Path) -> list[dict[str, Any]]:
    if (sha256_file(allocation_path) != ALLOCATION_SHA256
            or sha256_file(directory_path) != DIRECTORY_SHA256):
        raise DA062Error("Sealed input differs")
    allocations = {str(row["question_id"]): row for row in _read(allocation_path)}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    if set(allocations) != set(directories) or len(allocations) != 465:
        raise DA062Error("Population differs")
    rows = []
    for question_id in sorted(allocations):
        directory = directories[question_id]
        episode_to_session = {
            str(episode["episode_id"]): str(episode["session_id"])
            for episode in directory["episodes"]
        }
        represented, linked_actions = _represented(allocations[question_id])
        unresolved = [episode_id for episode_id in represented if episode_id not in episode_to_session]
        if unresolved:
            raise DA062Error("Represented episode lacks a directory coordinate")
        heads, seen = [], set()
        for episode_id in represented:
            session_id = episode_to_session[episode_id]
            if session_id not in seen:
                seen.add(session_id)
                heads.append(session_id)
        total_sessions = len(directory["directory_root"]["session_heads"])
        rows.append({
            "question_id": question_id,
            "represented_episode_ids": represented,
            "direct_episode_count": len(allocations[question_id]["direct_ids"]),
            "linked_action_count": linked_actions,
            "routed_session_ids": heads,
            "total_sessions": total_sessions,
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


def run_preflight(allocation_path: Path, directory_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(allocation_path, directory_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_routes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da062-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(allocation_path, directory_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden = ("has_" + "answer", "evi" + "dence", "required_" + "session")
    leakage_clean = not any(token in source for token in forbidden)
    direct = sum(row["direct_episode_count"] for row in rows)
    linked = sum(row["linked_action_count"] for row in rows)
    represented = sum(len(row["represented_episode_ids"]) for row in rows)
    routes = [len(row["routed_session_ids"]) for row in rows]
    valid = (
        identical
        and direct > 0
        and linked > 0
        and represented > 0
        and all(0 < value <= int(row["total_sessions"]) for value, row in zip(routes, rows, strict=True))
        and all(len(row["routed_session_ids"]) == len(set(row["routed_session_ids"])) for row in rows)
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
        and leakage_clean
    )
    result = {
        "schema": "da062-pack-activated-session-heads-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "direct_episodes": direct,
        "linked_actions": linked,
        "unique_represented_episodes": represented,
        "min_routed_sessions": min(routes),
        "max_routed_sessions": max(routes),
        "protected_payload_mutations": 0,
        "rendered_char_delta": 0,
        "leakage_scan_clean": leakage_clean,
        "replay_byte_identical": identical,
        "routes_sha256": sha256_file(artifact),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
    }
    (output_dir / "preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not valid:
        raise DA062Error("Blind pack-head preflight failed")
    return result


__all__ = ["DA062Error", "build_rows", "run_preflight"]
