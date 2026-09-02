"""Grouped dependency topology audit for DA-051."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _delivered, _records
from analysis.da048_continuation import render_block, sha256_file
from analysis.da049_audit import _positions

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
DA050_OUTCOMES_SHA256 = "32d93e6c3653ace8c3933eeb421b907937fcef2f168e584b5dc61e15dac14f6a"
FRAME_CAP = 2_048


class DA051Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def audit(dataset_path: Path, envelope_path: Path,
          da050_outcomes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (sha256_file(envelope_path) != ENVELOPE_SHA256
            or sha256_file(da050_outcomes_path) != DA050_OUTCOMES_SHA256):
        raise DA051Error("Sealed input differs")
    records = _records(dataset_path)
    positions = _positions(dataset_path)
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    outcomes = {str(row["question_id"]): row for row in _read(da050_outcomes_path)}
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
        episode_ids = {position["member_to_episode"][member] for member in missing}
        sessions = {position["episodes"][episode]["session"] for episode in episode_ids}
        if len(missing) == 1:
            topology = "ONE_MEMBER"
        elif len(episode_ids) == 1:
            topology = "ONE_EPISODE_MULTI_MEMBER"
        elif len(sessions) == 1:
            topology = "ONE_SESSION_MULTI_EPISODE"
        else:
            topology = "MULTI_SESSION"
        frame_chars = fits = None
        if topology == "ONE_EPISODE_MULTI_MEMBER":
            episode = position["episodes"][next(iter(episode_ids))]
            first, second = episode["members"]
            member = {"speaker": first["speaker"],
                      "text": f"{first['text']}\n{second['speaker']}: {second['text']}"}
            frame_chars = len(render_block(str(envelope["da038_control"]["sentinel"]), 1, member))
            fits = frame_chars <= FRAME_CAP
        rows.append({"question_id": question_id, "question_type": record["question_type"],
                     "topology": topology, "members": len(missing),
                     "episodes": len(episode_ids), "sessions": len(sessions),
                     "grouped_frame_chars": frame_chars, "grouped_fits": fits})
    if len(rows) != 133:
        raise DA051Error("DA-050 residual population differs")
    topology = Counter(row["topology"] for row in rows)
    grouped = [row for row in rows if row["topology"] == "ONE_EPISODE_MULTI_MEMBER"]
    types = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        types[question_type] = {"n": len(cell),
                                "topology": dict(Counter(row["topology"] for row in cell))}
    result = {"schema": "da051-grouped-residual-audit-v1", "status": "COMPLETE",
              "residuals": len(rows), "topology": dict(topology),
              "grouped_episode_fit_2048": sum(bool(row["grouped_fits"]) for row in grouped),
              "grouped_episode_overflow": sum(row["grouped_fits"] is False for row in grouped),
              "by_question_type": types, "anchor": {"da050": 332},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware dependency topology only"}
    return result, rows


def run_audit(dataset_path: Path, envelope_path: Path,
              da050_outcomes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(dataset_path, envelope_path, da050_outcomes_path)
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


__all__ = ["DA051Error", "audit", "run_audit"]
