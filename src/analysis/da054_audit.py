"""Session-entry anatomy for absent DA-053 evidence members."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.da048_continuation import sha256_file
from analysis.da049_audit import _positions

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
DA053_RESIDUAL_SHA256 = "559f610177d6e4e9f499a3fe9ee4a7bd844b96d3e84558a2b5ccd634dd827560"
SEEDS = 16


class DA054Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _distribution(values: list[int]) -> dict[str, float | int] | None:
    if not values:
        return None
    ordered = sorted(values)
    def nearest(fraction: float) -> int:
        return ordered[round((len(ordered) - 1) * fraction)]
    return {"min": ordered[0], "p50": nearest(.5), "p90": nearest(.9), "max": ordered[-1]}


def audit(dataset_path: Path, envelope_path: Path,
          residual_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (sha256_file(envelope_path) != ENVELOPE_SHA256
            or sha256_file(residual_path) != DA053_RESIDUAL_SHA256):
        raise DA054Error("Sealed input differs")
    positions = _positions(dataset_path)
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    residuals = _read(residual_path)
    rows = []
    absent_count = 0
    for residual in residuals:
        question_id = str(residual["question_id"])
        envelope, position = envelopes[question_id], positions[question_id]
        direct_ids = list(map(str, envelope["direct_ids"]))
        top_ids = direct_ids[:SEEDS]
        top_by_session: dict[str, list[int]] = {}
        tail_by_session: dict[str, list[int]] = {}
        for episode_id in top_ids:
            episode = position["episodes"][episode_id]
            top_by_session.setdefault(str(episode["session"]), []).append(int(episode["order"]))
        for episode_id in direct_ids[SEEDS:]:
            episode = position["episodes"][episode_id]
            tail_by_session.setdefault(str(episode["session"]), []).append(int(episode["order"]))
        members = []
        for member in residual["members"]:
            if member["state"] != "ABSENT":
                continue
            absent_count += 1
            target = position["episodes"][str(member["episode_id"])]
            session, order = str(target["session"]), int(target["order"])
            if session in top_by_session:
                address = "TOP16_SESSION"
                distance = min(abs(order - value) for value in top_by_session[session])
            elif session in tail_by_session:
                address = "DIRECT_TAIL_SESSION"
                distance = min(abs(order - value) for value in tail_by_session[session])
            else:
                address = "UNTOUCHED_SESSION"
                distance = None
            members.append({"member_id": str(member["member_id"]),
                            "episode_id": str(member["episode_id"]),
                            "address": address, "minimum_distance": distance})
        combination = ("+".join(sorted(set(member["address"] for member in members)))
                       if members else "NO_ABSENT_MEMBER")
        rows.append({"question_id": question_id, "question_type": residual["question_type"],
                     "absent_members": len(members), "address_combination": combination,
                     "members": members})
    if len(rows) != 102 or absent_count != 134:
        raise DA054Error("DA-053 absent population differs")
    addresses = Counter(member["address"] for row in rows for member in row["members"])
    combinations = Counter(row["address_combination"] for row in rows)
    distance_by_address = {address: _distribution([
        int(member["minimum_distance"]) for row in rows for member in row["members"]
        if member["address"] == address and member["minimum_distance"] is not None])
        for address in ("TOP16_SESSION", "DIRECT_TAIL_SESSION")}
    types = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        types[question_type] = {"n": len(cell),
                                "combinations": dict(Counter(row["address_combination"] for row in cell))}
    result = {"schema": "da054-session-addressability-audit-v1", "status": "COMPLETE",
              "questions": len(rows), "absent_members": absent_count,
              "member_addresses": dict(addresses), "question_combinations": dict(combinations),
              "distance_by_address": distance_by_address, "by_question_type": types,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware session-entry anatomy only"}
    return result, rows


def run_audit(dataset_path: Path, envelope_path: Path,
              residual_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(dataset_path, envelope_path, residual_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "session_addresses.jsonl.gz"
    with artifact.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    result["addresses_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    return result


__all__ = ["DA054Error", "audit", "run_audit"]
