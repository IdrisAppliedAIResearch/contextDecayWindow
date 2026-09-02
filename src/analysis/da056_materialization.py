"""Blind session-local materialization contract for DA-056."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, identity, render_block, sha256_file

DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
FRAME_CAP = 2_048
RETAINED_SLOTS = 5
GENERAL_CAP = 12_288


class DA056Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _payloads(row: Mapping[str, Any]) -> dict[str, list[dict[str, str]]]:
    question_id = str(row["question_id"])
    output = {}
    for session_order, (source_id, turns) in enumerate(
        zip(row["haystack_session_ids"], row["haystack_sessions"], strict=True)
    ):
        session_id = identity(question_id, str(session_order), str(source_id))
        episode_order = 0
        for start in range(0, len(turns) - 1, 2):
            first, second = turns[start:start + 2]
            if first.get("role") != "user" or second.get("role") != "assistant":
                continue
            user, assistant = str(first.get("content", "")), str(second.get("content", ""))
            episode_text = f"User: {user}\nAssistant: {assistant}"
            episode_id = identity(question_id, session_id, str(episode_order), "episode", episode_text)
            output[episode_id] = [{"speaker": "User", "text": user},
                                  {"speaker": "Assistant", "text": assistant}]
            episode_order += 1
    return output


def build_rows(dataset_path: Path, directory_path: Path,
               envelope_path: Path) -> list[dict[str, Any]]:
    if (sha256_file(dataset_path) != DATASET_SHA256
            or sha256_file(directory_path) != DIRECTORY_SHA256
            or sha256_file(envelope_path) != ENVELOPE_SHA256):
        raise DA056Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    output = []
    for question_id in sorted(directories):
        directory = directories[question_id]
        payloads = _payloads(raw[question_id])
        sentinel = str(envelopes[question_id]["da038_control"]["sentinel"])
        ledger = []
        session_order = {str(node["session_id"]): int(node["session_order"])
                         for node in directory["sessions"]}
        for episode in directory["episodes"]:
            episode_id = str(episode["episode_id"])
            members = payloads[episode_id]
            for offset, member in enumerate(members):
                block = render_block(sentinel, int(episode["episode_order"]) + 1, member)
                cost = len(block)
                ledger.append({"session_id": str(episode["session_id"]),
                               "session_order": session_order[str(episode["session_id"])],
                               "episode_id": episode_id,
                               "episode_order": int(episode["episode_order"]),
                               "member_id": str(episode["members"][offset]["member_id"]),
                               "member_offset": offset, "kind": "FRAME" if cost <= FRAME_CAP else "OVERFLOW",
                               "cost": cost if cost <= FRAME_CAP else 0, "attempt_cost": cost,
                               "block": block if cost <= FRAME_CAP else None,
                               "block_sha256": hashlib.sha256(block.encode()).hexdigest()})
        output.append({"question_id": question_id,
                       "directory_root_sha256": hashlib.sha256(json.dumps(
                           directory["directory_root"], sort_keys=True,
                           separators=(",", ":")).encode()).hexdigest(),
                       "rendered_char_delta": 0, "ledger": ledger})
    if len(output) != 465:
        raise DA056Error("Population differs")
    return output


@dataclass
class SessionLocalMachine:
    sessions: Mapping[str, Sequence[Mapping[str, Any]]]
    current_session: str | None = None
    episode_index: int | None = None
    current: str | None = None
    retained: list[str] = field(default_factory=list)
    peak_chars: int = 0

    def _measure(self) -> None:
        total = sum(map(len, self.retained)) + (len(self.current) if self.current else 0)
        if len(self.retained) > RETAINED_SLOTS or total > GENERAL_CAP:
            raise DA056Error("Auxiliary cap exceeded")
        self.peak_chars = max(self.peak_chars, total)

    def open_session(self, head: str) -> bool:
        if head not in self.sessions or not self.sessions[head]:
            return False
        self.current_session, self.episode_index, self.current = head, 0, None
        return True

    def next_episode(self) -> bool:
        if self.current_session is None or self.episode_index is None:
            return False
        if self.episode_index + 1 >= len(self.sessions[self.current_session]):
            return False
        self.episode_index += 1
        self.current = None
        return True

    def materialize(self, offset: int) -> bool:
        if self.current_session is None or self.episode_index is None or offset not in (0, 1):
            return False
        action = self.sessions[self.current_session][self.episode_index][offset]
        if action["kind"] != "FRAME":
            self.current = None
            return False
        block = action.get("block")
        if not isinstance(block, str) or hashlib.sha256(block.encode()).hexdigest() != action["block_sha256"]:
            raise DA056Error("Materialized payload differs")
        self.current = block
        self._measure()
        return True

    def keep(self) -> bool:
        if self.current is None or self.current in self.retained or len(self.retained) >= RETAINED_SLOTS:
            return False
        self.retained.append(self.current)
        self.current = None
        self._measure()
        return True


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def _catalog(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[list[Mapping[str, Any]]]]:
    sessions: dict[str, dict[int, dict[int, Mapping[str, Any]]]] = {}
    for row in rows:
        for action in row["ledger"]:
            sessions.setdefault(str(action["session_id"]), {}).setdefault(
                int(action["episode_order"]), {})[int(action["member_offset"])] = action
    output = {}
    for session_id, episodes in sessions.items():
        if sorted(episodes) != list(range(len(episodes))):
            raise DA056Error("Noncontiguous session episodes")
        output[session_id] = []
        for episode_order in range(len(episodes)):
            if set(episodes[episode_order]) != {0, 1}:
                raise DA056Error("Episode member coordinates differ")
            output[session_id].append([episodes[episode_order][0], episodes[episode_order][1]])
    return output


def _exercise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    sessions = _catalog(rows)
    machine = SessionLocalMachine(sessions)
    unknown_head_rejected = not machine.open_session("0" * 64)
    frames = [item for row in rows for item in row["ledger"] if item["kind"] == "FRAME"]
    overflow = next(item for row in rows for item in row["ledger"] if item["kind"] == "OVERFLOW")
    unique = []
    hashes = set()
    for item in frames:
        if item["block_sha256"] not in hashes:
            hashes.add(item["block_sha256"])
            unique.append(item)
        if len(unique) == 6:
            break
    if len(unique) != 6:
        raise DA056Error("Insufficient distinct planted frames")
    bad_offset_rejected = False
    for item in unique[:5]:
        machine.open_session(str(item["session_id"]))
        for _ in range(int(item["episode_order"])):
            if not machine.next_episode():
                raise DA056Error("Planted local traversal failed")
        bad_offset_rejected |= not machine.materialize(2)
        if not machine.materialize(int(item["member_offset"])) or not machine.keep():
            raise DA056Error("Planted fitting frame failed")
    retained = list(machine.retained)
    first = unique[0]
    machine.open_session(str(first["session_id"]))
    for _ in range(int(first["episode_order"])):
        machine.next_episode()
    machine.materialize(int(first["member_offset"]))
    duplicate_rejected = not machine.keep() and machine.retained == retained
    sixth = unique[5]
    machine.open_session(str(sixth["session_id"]))
    for _ in range(int(sixth["episode_order"])):
        machine.next_episode()
    machine.materialize(int(sixth["member_offset"]))
    full_rejected = not machine.keep() and machine.retained == retained
    machine.open_session(str(overflow["session_id"]))
    for _ in range(int(overflow["episode_order"])):
        machine.next_episode()
    overflow_rejected = not machine.materialize(int(overflow["member_offset"]))
    retained_survives_overflow = machine.retained == retained
    session = str(first["session_id"])
    machine.open_session(session)
    while machine.next_episode():
        pass
    boundary_rejected = not machine.next_episode()
    return {"unknown_head_rejected": unknown_head_rejected,
            "bad_offset_rejected": bad_offset_rejected,
            "boundary_rejected": boundary_rejected,
            "overflow_rejected": overflow_rejected,
            "duplicate_rejected": duplicate_rejected,
            "full_rejected": full_rejected,
            "retained_survives_overflow": retained_survives_overflow,
            "retained_slots": len(machine.retained), "peak_chars": machine.peak_chars}


def run_preflight(dataset_path: Path, directory_path: Path, envelope_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, directory_path, envelope_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_materializations.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da056-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, directory_path, envelope_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    ledgers = [item for row in rows for item in row["ledger"]]
    kinds = Counter(item["kind"] for item in ledgers)
    exercise = _exercise(rows)
    valid = (identical and kinds["FRAME"] > 0 and kinds["OVERFLOW"] > 0
             and max(item["cost"] for item in ledgers) <= FRAME_CAP
             and all(row["rendered_char_delta"] == 0 for row in rows)
             and all(exercise[name] for name in
                     ("unknown_head_rejected", "bad_offset_rejected", "boundary_rejected",
                      "overflow_rejected", "duplicate_rejected", "full_rejected",
                      "retained_survives_overflow"))
             and exercise["peak_chars"] <= GENERAL_CAP)
    result = {"schema": "da056-session-local-materialization-preflight-v1",
              "status": "PASS" if valid else "FAIL", "questions": len(rows),
              "members": len(ledgers), "actions": dict(kinds),
              "peak_frame_chars": max(item["cost"] for item in ledgers),
              "transition_exercise": exercise,
              "rendered_char_delta": 0, "replay_byte_identical": identical,
              "catalog_sha256": sha256_file(artifact),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    if not valid:
        raise DA056Error("Blind materialization preflight failed")
    return result


__all__ = ["DA056Error", "SessionLocalMachine", "build_rows", "run_preflight"]
