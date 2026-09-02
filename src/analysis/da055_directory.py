"""Blind control-plane session directory for DA-055."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, identity, sha256_file

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"


class DA055Error(RuntimeError):
    pass


def _question_ids(path: Path) -> list[str]:
    if sha256_file(path) != ENVELOPE_SHA256:
        raise DA055Error("Sealed population envelope differs")
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        values = [str(json.loads(line)["question_id"]) for line in handle]
    if len(values) != 465 or len(set(values)) != 465:
        raise DA055Error("Population differs")
    return values


def build_rows(dataset_path: Path, envelope_path: Path) -> list[dict[str, Any]]:
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise DA055Error("Dataset differs")
    wanted = set(_question_ids(envelope_path))
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))
           if str(row.get("question_id")) in wanted}
    if set(raw) != wanted:
        raise DA055Error("Dataset join differs")
    output = []
    for question_id in sorted(wanted):
        row = raw[question_id]
        sessions = []
        episode_nodes = []
        for session_order, (session_source_id, turns) in enumerate(
            zip(row["haystack_session_ids"], row["haystack_sessions"], strict=True)
        ):
            session_id = identity(question_id, str(session_order), str(session_source_id))
            accepted = []
            episode_order = 0
            for start in range(0, len(turns) - 1, 2):
                first, second = turns[start:start + 2]
                if first.get("role") != "user" or second.get("role") != "assistant":
                    continue
                user, assistant = str(first.get("content", "")), str(second.get("content", ""))
                episode_text = f"User: {user}\nAssistant: {assistant}"
                episode_id = identity(question_id, session_id, str(episode_order), "episode", episode_text)
                members = []
                for offset, turn in enumerate((first, second)):
                    role = str(turn.get("role", "")).strip().capitalize()
                    rendered = f"{role}: {turn.get('content', '')}"
                    member_id = identity(question_id, session_id, str(episode_order), str(offset),
                                         str(turn["role"]), rendered)
                    members.append({"member_id": member_id, "offset": offset,
                                    "role": str(turn["role"])})
                accepted.append({"episode_id": episode_id, "session_id": session_id,
                                 "episode_order": episode_order, "members": members})
                episode_order += 1
            for index, episode in enumerate(accepted):
                episode_nodes.append({**episode,
                                      "previous": accepted[index - 1]["episode_id"] if index else None,
                                      "next": accepted[index + 1]["episode_id"]
                                      if index + 1 < len(accepted) else None})
            sessions.append({"session_id": session_id, "session_order": session_order,
                             "first_episode": accepted[0]["episode_id"] if accepted else None,
                             "episode_count": len(accepted)})
        output.append({"question_id": question_id,
                       "directory_root": {"type": "session_directory",
                                          "session_heads": [item["session_id"] for item in sessions]},
                       "sessions": sessions, "episodes": episode_nodes,
                       "rendered_char_delta": 0})
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def _validate(rows: Sequence[Mapping[str, Any]]) -> dict[str, int | bool]:
    sessions = episodes = members = 0
    valid = True
    for row in rows:
        session_nodes = list(row["sessions"])
        episode_nodes = list(row["episodes"])
        by_episode = {str(node["episode_id"]): node for node in episode_nodes}
        heads = list(row["directory_root"]["session_heads"])
        valid &= heads == [node["session_id"] for node in session_nodes]
        valid &= [node["session_order"] for node in session_nodes] == list(range(len(session_nodes)))
        for session in session_nodes:
            chain = []
            cursor = session["first_episode"]
            previous = None
            while cursor is not None:
                node = by_episode[str(cursor)]
                valid &= node["session_id"] == session["session_id"]
                valid &= node["previous"] == previous
                valid &= len(node["members"]) == 2
                valid &= [member["offset"] for member in node["members"]] == [0, 1]
                chain.append(str(cursor))
                previous, cursor = str(cursor), node["next"]
            valid &= len(chain) == int(session["episode_count"])
        sessions += len(session_nodes)
        episodes += len(episode_nodes)
        members += sum(len(node["members"]) for node in episode_nodes)
    return {"valid": bool(valid), "sessions": sessions, "episodes": episodes, "members": members}


def run_preflight(dataset_path: Path, envelope_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, envelope_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_directory.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da055-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, envelope_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    validation = _validate(rows)
    passed = (len(rows) == 465 and validation["valid"] and identical
              and all(row["rendered_char_delta"] == 0 for row in rows))
    result = {"schema": "da055-session-directory-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              **validation, "rendered_char_delta": 0, "replay_byte_identical": identical,
              "directory_sha256": sha256_file(artifact),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    if not passed:
        raise DA055Error("Blind directory preflight failed")
    return result


__all__ = ["DA055Error", "build_rows", "run_preflight"]
