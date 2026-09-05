"""Blind second-hop directional continuation for DA-048."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
DA042_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
STREAM_DEPTH = 32
FRAME_CAP = 2_048
TERMINAL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
CONTINUATION = "abcdefghijklmnopqrstuvwxyz0189-_"


class DA048Error(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def encode_uint(value: int) -> str:
    if value < 0:
        raise DA048Error("Negative node ordinal")
    digits = [value & 31]
    value >>= 5
    while value:
        digits.append(value & 31)
        value >>= 5
    return "".join(CONTINUATION[digit] for digit in digits[:-1]) + TERMINAL[digits[-1]]


def render_block(sentinel: str, ordinal: int, member: Mapping[str, str]) -> str:
    if not sentinel or set(sentinel) != {"~"} or ordinal < 1:
        raise DA048Error("Invalid node rendering")
    return f"{sentinel}N{encode_uint(ordinal)}{sentinel}{member['speaker']}: {member['text']}"


def _episodes(row: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    question_id = str(row["question_id"])
    episodes: list[dict[str, Any]] = []
    by_id: dict[str, int] = {}
    for session_order, (session_id, turns) in enumerate(
        zip(row["haystack_session_ids"], row["haystack_sessions"], strict=True)
    ):
        session = identity(question_id, str(session_order), str(session_id))
        episode_order = 0
        for start in range(0, len(turns) - 1, 2):
            first, second = turns[start:start + 2]
            if first.get("role") != "user" or second.get("role") != "assistant":
                continue
            user, assistant = str(first.get("content", "")), str(second.get("content", ""))
            text = f"User: {user}\nAssistant: {assistant}"
            episode_id = identity(question_id, session, str(episode_order), "episode", text)
            by_id[episode_id] = len(episodes)
            episodes.append({"identity": episode_id, "session": session, "order": episode_order,
                             "members": ({"speaker": "User", "text": user},
                                         {"speaker": "Assistant", "text": assistant})})
            episode_order += 1
    return episodes, by_id


def _read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def build_rows(dataset_path: Path, envelope_path: Path) -> list[dict[str, Any]]:
    if sha256_file(dataset_path) != DATASET_SHA256 or sha256_file(envelope_path) != DA042_SHA256:
        raise DA048Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    envelopes = _read_gzip(envelope_path)
    output = []
    for envelope in envelopes:
        question_id = str(envelope["question_id"])
        episodes, by_id = _episodes(raw[question_id])
        direct = set(map(str, envelope["direct_ids"]))
        one_hop = {str(target[0]) for target in envelope["treatment"]["targets"]}
        seen: set[str] = set()
        continued: list[dict[str, Any]] = []
        rejections: Counter[str] = Counter()
        for edge_position, edge in enumerate(envelope["baseline_actions"]):
            direction = int(edge["direction"])
            if direction not in {-1, 1}:
                raise DA048Error("Unexpected frozen direction")
            neighbor_id = str(edge["neighbor_id"])
            source = episodes[by_id[neighbor_id]]
            candidate_index = by_id[neighbor_id] + direction
            if not 0 <= candidate_index < len(episodes):
                rejections["CORPUS_BOUNDARY"] += 1
                continue
            candidate = episodes[candidate_index]
            if candidate["session"] != source["session"]:
                rejections["SESSION_BOUNDARY"] += 1
                continue
            candidate_id = str(candidate["identity"])
            if candidate_id in direct or candidate_id in one_hop:
                rejections["PRIOR_REPRESENTATION"] += 1
                continue
            if candidate_id in seen:
                rejections["DUPLICATE"] += 1
                continue
            seen.add(candidate_id)
            continued.append({"edge_position": edge_position, "source_neighbor_id": neighbor_id,
                              "direction": direction, "neighbor_id": candidate_id,
                              "members": candidate["members"]})
        sentinel = str(envelope["da038_control"]["sentinel"])
        actions = []
        member_rows = [(episode, member_index, member)
                       for episode in continued for member_index, member in enumerate(episode["members"])]
        for ordinal, (episode, member_index, member) in enumerate(member_rows[:STREAM_DEPTH], 1):
            block = render_block(sentinel, ordinal, member)
            fits = len(block) <= FRAME_CAP
            actions.append({"ordinal": ordinal, "edge_position": episode["edge_position"],
                            "source_neighbor_id": episode["source_neighbor_id"],
                            "direction": episode["direction"], "neighbor_id": episode["neighbor_id"],
                            "member": member_index, "kind": "FRAME" if fits else "OVERFLOW",
                            "cost": len(block) if fits else 0, "attempt_cost": len(block),
                            "block": block if fits else None,
                            "block_sha256": hashlib.sha256(block.encode()).hexdigest()})
        output.append({"question_id": question_id,
                       "immutable_prompt_chars": int(envelope["da038_control"]["final_chars"]),
                       "immutable_order_sha256": str(envelope["treatment"]["immutable_order_sha256"]),
                       "one_hop_targets_sha256": hashlib.sha256(json.dumps(
                           envelope["treatment"]["targets"], separators=(",", ":")).encode()).hexdigest(),
                       "continuation_episodes": len(continued), "candidate_members": len(member_rows),
                       "depth_truncated": len(member_rows) > STREAM_DEPTH,
                       "rejections": dict(rejections), "actions": actions})
    if len(output) != 465:
        raise DA048Error("Population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, envelope_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, envelope_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_continuations.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da048-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, envelope_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    kinds = Counter(action["kind"] for row in rows for action in row["actions"])
    rejections = Counter()
    for row in rows:
        rejections.update(row["rejections"])
    actions = [action for row in rows for action in row["actions"]]
    passed = (identical and kinds["FRAME"] > 0 and sum(rejections.values()) > 0
              and all(action["attempt_cost"] > FRAME_CAP for action in actions
                      if action["kind"] == "OVERFLOW")
              and max((action["cost"] for action in actions), default=0) <= FRAME_CAP)
    result = {"schema": "da048-directional-continuation-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "continuation_episodes": sum(row["continuation_episodes"] for row in rows),
              "candidate_members": sum(row["candidate_members"] for row in rows),
              "actions": dict(kinds), "rejections": dict(rejections),
              "depth_truncated_questions": sum(row["depth_truncated"] for row in rows),
              "peak_frame_chars": max((action["cost"] for action in actions), default=0),
              "immutable_prompt_mutations": 0, "replay_byte_identical": identical,
              "artifact_sha256": sha256_file(artifact),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA048Error("Blind preflight failed")
    return result


__all__ = ["DA048Error", "build_rows", "run_preflight"]
