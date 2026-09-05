"""Residual member reachability audit after DA-052."""

from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _delivered, _records
from analysis.da048_continuation import sha256_file
from analysis.da049_audit import _positions

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
DA045_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"
DA048_SHA256 = "8ea82cc737b65bf457e05bf921043907d70f0f82f0e878b340ab6c7f04c41bd3"
DA050_SHA256 = "40c8b768e80c8b0c80e1b310f7abe3e2f3cc6066362f6b59a8aa436bfcfae490"
DA052_OUTCOMES_SHA256 = "c2f0359eedfe4460979634e1bd0d9038329895c4a6f208f9c80e354df65010dd"


class DA053Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _member_occurrences(actions: Sequence[Mapping[str, Any]],
                        episodes: Mapping[str, Sequence[str]], source: str,
                        output: dict[str, list[dict[str, Any]]]) -> None:
    for action in actions:
        member_id = episodes[str(action["neighbor_id"])][int(action["member"])]
        output[member_id].append({"source": source, "kind": str(action["kind"]),
                                  "attempt_cost": int(action["attempt_cost"])})


def audit(dataset_path: Path, envelope_path: Path, da045_path: Path, da048_path: Path,
          da050_path: Path, da052_outcomes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((envelope_path, ENVELOPE_SHA256), (da045_path, DA045_SHA256),
             (da048_path, DA048_SHA256), (da050_path, DA050_SHA256),
             (da052_outcomes_path, DA052_OUTCOMES_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA053Error("Sealed input differs")
    records = _records(dataset_path)
    positions = _positions(dataset_path)
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    one_hop = {str(row["question_id"]): row["treatment"]["actions"] for row in _read(da045_path)}
    distance_2 = {str(row["question_id"]): row["actions"] for row in _read(da048_path)}
    distance_3_5 = {str(row["question_id"]): row["actions"] for row in _read(da050_path)}
    outcomes = {str(row["question_id"]): row for row in _read(da052_outcomes_path)}
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
        occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
        _member_occurrences(one_hop[question_id], episodes, "ONE_HOP", occurrences)
        _member_occurrences(distance_2[question_id], episodes, "DISTANCE_2", occurrences)
        _member_occurrences(distance_3_5[question_id], episodes, "DISTANCE_3_5", occurrences)
        originally_missing = gold - base
        retained = {member for member in originally_missing
                    if any(item["kind"] == "FRAME" for item in occurrences.get(member, []))}
        residual = originally_missing - retained
        if len(retained) != int(outcomes[question_id]["retained_members"]):
            raise DA053Error("DA-052 retained-member replay differs")
        member_rows = []
        for member in sorted(residual):
            seen = occurrences.get(member, [])
            if any(item["kind"] == "FRAME" for item in seen):
                state = "FRAME"
            elif seen:
                state = "OVERFLOW_ONLY"
            else:
                state = "ABSENT"
            episode_id = position["member_to_episode"][member]
            member_rows.append({"member_id": member, "episode_id": episode_id,
                                "session_id": position["episodes"][episode_id]["session"],
                                "state": state,
                                "sources": sorted({item["source"] for item in seen}),
                                "minimum_attempt_cost": min((item["attempt_cost"] for item in seen), default=None)})
        states = Counter(item["state"] for item in member_rows)
        if set(states) == {"ABSENT"}:
            question_class = "ALL_ABSENT"
        elif set(states) == {"OVERFLOW_ONLY"}:
            question_class = "ALL_OVERFLOW"
        elif "FRAME" in states and "OVERFLOW_ONLY" in states:
            question_class = "FRAME_PLUS_OVERFLOW"
        elif "FRAME" in states:
            question_class = "PARTIAL_FRAME"
        else:
            question_class = "+".join(sorted(states))
        rows.append({"question_id": question_id, "question_type": record["question_type"],
                     "class": question_class, "originally_missing": len(originally_missing),
                     "retained_before_residual": len(retained), "residual_members": len(residual),
                     "residual_episodes": len({item["episode_id"] for item in member_rows}),
                     "residual_sessions": len({item["session_id"] for item in member_rows}),
                     "member_states": dict(states), "members": member_rows})
    if len(rows) != 102:
        raise DA053Error("DA-052 residual population differs")
    classes = Counter(row["class"] for row in rows)
    states = Counter()
    sources = Counter()
    for row in rows:
        states.update(row["member_states"])
        for member in row["members"]:
            sources.update(member["sources"])
    types = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        types[question_type] = {"n": len(cell), "classes": dict(Counter(row["class"] for row in cell))}
    result = {"schema": "da053-retained-set-residual-audit-v1", "status": "COMPLETE",
              "residuals": len(rows), "question_classes": dict(classes),
              "member_states": dict(states), "represented_sources": dict(sources),
              "by_question_type": types, "anchor": {"da052": 363},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware residual reachability anatomy only"}
    return result, rows


def run_audit(dataset_path: Path, envelope_path: Path, da045_path: Path, da048_path: Path,
              da050_path: Path, da052_outcomes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(dataset_path, envelope_path, da045_path, da048_path,
                         da050_path, da052_outcomes_path)
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


__all__ = ["DA053Error", "audit", "run_audit"]
