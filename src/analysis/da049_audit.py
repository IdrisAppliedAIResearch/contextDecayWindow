"""Evidence-aware directional distance residual audit for DA-049."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _delivered, _records
from analysis.da048_continuation import identity, render_block, sha256_file

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
DA048_OUTCOMES_SHA256 = "335c4bbceb57e8ae98a4cbb030cc044813aa6ba8e3cbe4aecc01f94fa65b5b36"
FRAME_CAP = 2_048


class DA049Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _positions(dataset_path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    output = {}
    for row in json.loads(dataset_path.read_text(encoding="utf-8")):
        question_id = str(row["question_id"])
        episodes = {}
        member_to_episode = {}
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
                members = []
                for offset, turn in enumerate((first, second)):
                    role = str(turn.get("role", "")).strip().capitalize()
                    rendered = f"{role}: {turn.get('content', '')}"
                    member_id = identity(question_id, session, str(episode_order), str(offset),
                                         str(turn["role"]), rendered)
                    members.append({"identity": member_id, "speaker": role,
                                    "text": str(turn.get("content", ""))})
                    member_to_episode[member_id] = episode_id
                episodes[episode_id] = {"session": session, "order": episode_order,
                                        "members": members}
                episode_order += 1
        output[question_id] = {"episodes": episodes, "member_to_episode": member_to_episode}
    return output


def audit(dataset_path: Path, envelope_path: Path,
          da048_outcomes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (sha256_file(envelope_path) != ENVELOPE_SHA256
            or sha256_file(da048_outcomes_path) != DA048_OUTCOMES_SHA256):
        raise DA049Error("Sealed input differs")
    records = _records(dataset_path)
    positions = _positions(dataset_path)
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    outcomes = {str(row["question_id"]): row for row in _read(da048_outcomes_path)}
    rows = []
    for question_id in sorted(envelopes):
        if outcomes[question_id]["TREATMENT"]:
            continue
        envelope, record, position = envelopes[question_id], records[question_id], positions[question_id]
        episodes, gold = record["episodes"], record["gold"]
        direct = set().union(*(episodes[value] for value in envelope["direct_ids"]))
        base = (direct | _delivered(envelope["baseline_actions"], episodes)
                | _delivered(envelope["da023"]["additions"], episodes)
                | _delivered(envelope["control"]["actions"], episodes)
                | _delivered(envelope["da031_control"]["actions"], episodes)
                | _delivered(envelope["da033_control"]["actions"], episodes)
                | _delivered(envelope["da038_control"]["actions"], episodes))
        missing = gold - base
        if len(missing) != 1:
            rows.append({"question_id": question_id, "question_type": record["question_type"],
                         "class": "MULTI_MEMBER", "missing_members": len(missing),
                         "minimum_distance": None, "frame_chars": None, "fits": None})
            continue
        member_id = next(iter(missing))
        target_id = position["member_to_episode"][member_id]
        target = position["episodes"][target_id]
        distances = []
        for edge in envelope["baseline_actions"]:
            seed = position["episodes"][str(edge["seed_id"])]
            direction = int(edge["direction"])
            if seed["session"] != target["session"]:
                continue
            distance = (int(target["order"]) - int(seed["order"])) * direction
            if distance > 2:
                distances.append(distance)
        if not distances:
            rows.append({"question_id": question_id, "question_type": record["question_type"],
                         "class": "NO_DIRECTIONAL_RAY", "missing_members": 1,
                         "minimum_distance": None, "frame_chars": None, "fits": None})
            continue
        member = next(member for member in target["members"] if member["identity"] == member_id)
        frame_chars = len(render_block(str(envelope["da038_control"]["sentinel"]), 1, member))
        rows.append({"question_id": question_id, "question_type": record["question_type"],
                     "class": "SINGLE_DIRECTIONAL", "missing_members": 1,
                     "minimum_distance": min(distances), "frame_chars": frame_chars,
                     "fits": frame_chars <= FRAME_CAP})
    if len(rows) != 170:
        raise DA049Error("DA-048 residual population differs")
    classes = Counter(row["class"] for row in rows)
    directional = [row for row in rows if row["class"] == "SINGLE_DIRECTIONAL"]
    distances = Counter(int(row["minimum_distance"]) for row in directional)
    types = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        types[question_type] = {"n": len(cell), "classes": dict(Counter(row["class"] for row in cell))}
    result = {"schema": "da049-directional-residual-audit-v1", "status": "COMPLETE",
              "residuals": len(rows), "classes": dict(classes),
              "directional_distance": {str(key): distances[key] for key in sorted(distances)},
              "directional_fit_2048": sum(bool(row["fits"]) for row in directional),
              "directional_overflow": sum(row["fits"] is False for row in directional),
              "by_question_type": types,
              "anchors": {"da038": 232, "da046": 250, "da048": 295},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware residual anatomy only"}
    return result, rows


def run_audit(dataset_path: Path, envelope_path: Path,
              da048_outcomes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(dataset_path, envelope_path, da048_outcomes_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "residuals.jsonl.gz"
    with artifact.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    result["residuals_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    return result


__all__ = ["DA049Error", "audit", "run_audit"]
