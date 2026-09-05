"""Oracle far-directional cursor capacity analysis for DA-050."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _delivered, _paired, _quantile, _records
from analysis.da048_continuation import sha256_file

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
CURSOR_SHA256 = "40c8b768e80c8b0c80e1b310f7abe3e2f3cc6066362f6b59a8aa436bfcfae490"
DA048_OUTCOMES_SHA256 = "335c4bbceb57e8ae98a4cbb030cc044813aa6ba8e3cbe4aecc01f94fa65b5b36"


class DA050AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(dataset_path: Path, envelope_path: Path, cursor_path: Path,
            da048_outcomes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((envelope_path, ENVELOPE_SHA256), (cursor_path, CURSOR_SHA256),
             (da048_outcomes_path, DA048_OUTCOMES_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA050AnalysisError("Sealed input differs")
    records = _records(dataset_path)
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    cursors = {str(row["question_id"]): row for row in _read(cursor_path)}
    prior = {str(row["question_id"]): row for row in _read(da048_outcomes_path)}
    rows = []
    for question_id in sorted(envelopes):
        envelope, cursor, record = envelopes[question_id], cursors[question_id], records[question_id]
        episodes, gold = record["episodes"], record["gold"]
        direct = set().union(*(episodes[value] for value in envelope["direct_ids"]))
        base = (direct | _delivered(envelope["baseline_actions"], episodes)
                | _delivered(envelope["da023"]["additions"], episodes)
                | _delivered(envelope["control"]["actions"], episodes)
                | _delivered(envelope["da031_control"]["actions"], episodes)
                | _delivered(envelope["da033_control"]["actions"], episodes)
                | _delivered(envelope["da038_control"]["actions"], episodes))
        control = bool(prior[question_id]["TREATMENT"])
        missing = gold - base
        matches = []
        if not control:
            for action in cursor["actions"]:
                if action["kind"] != "FRAME":
                    continue
                member_id = episodes[str(action["neighbor_id"])][int(action["member"])]
                if missing <= {member_id}:
                    matches.append(action)
        chosen = matches[0] if matches else None
        cumulative = (sum(int(action["cost"]) for action in cursor["actions"]
                          if int(action["ordinal"]) <= int(chosen["ordinal"]))
                      if chosen else None)
        rows.append({"question_id": question_id, "question_type": record["question_type"],
                     "CONTROL": control, "TREATMENT": control or chosen is not None,
                     "oracle_action": ({key: chosen[key] for key in
                                        ("ordinal", "distance", "direction", "neighbor_id", "member", "cost")}
                                       | {"cumulative_chars": cumulative} if chosen else None)})
    if len(rows) != 465 or sum(row["CONTROL"] for row in rows) != 295:
        raise DA050AnalysisError("DA-048 anchor differs")
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    contrast = _paired(rows)
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell)
                                                       for arm in complete},
                         "contrast": _paired(cell)}
    nonnegative = all(cell["contrast"]["losses"] == 0 for cell in groups.values())
    if contrast["gains"] >= 10 and contrast["losses"] == 0 and nonnegative:
        status = "FAR_DIRECTIONAL_CAPACITY_SIGNAL"
    elif contrast["gains"] >= 1 and contrast["losses"] == 0 and nonnegative:
        status = "WEAK_FAR_DIRECTIONAL_CAPACITY_SIGNAL"
    else:
        status = "NO_FAR_DIRECTIONAL_CAPACITY_SIGNAL"
    gains = [row["oracle_action"] for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    result = {"schema": "da050-far-directional-cursor-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "by_question_type": groups,
              "oracle_gains": {"n": len(gains),
                               "distance": dict(sorted(__import__("collections").Counter(
                                   int(row["distance"]) for row in gains).items())),
                               "ordinal": {"p10": _quantile([int(row["ordinal"]) for row in gains], .1),
                                           "p50": _quantile([int(row["ordinal"]) for row in gains], .5),
                                           "p90": _quantile([int(row["ordinal"]) for row in gains], .9)},
                               "frame_chars": {"p10": _quantile([int(row["cost"]) for row in gains], .1),
                                               "p50": _quantile([int(row["cost"]) for row in gains], .5),
                                               "p90": _quantile([int(row["cost"]) for row in gains], .9)},
                               "cumulative_chars": {
                                   "p10": _quantile([int(row["cumulative_chars"]) for row in gains], .1),
                                   "p50": _quantile([int(row["cumulative_chars"]) for row in gains], .5),
                                   "p90": _quantile([int(row["cumulative_chars"]) for row in gains], .9)}},
              "protected_payload_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware one-frame oracle over frozen distance-3-to-5 cursor"}
    return result, rows


def run_analysis(dataset_path: Path, envelope_path: Path, cursor_path: Path,
                 da048_outcomes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, envelope_path, cursor_path, da048_outcomes_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "outcomes.jsonl.gz"
    with artifact.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    with tempfile.TemporaryDirectory(prefix="da050-result-") as directory:
        replay_result, replay_rows = analyze(dataset_path, envelope_path, cursor_path, da048_outcomes_path)
        replay = Path(directory) / artifact.name
        with replay.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
                for row in replay_rows:
                    handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(artifact)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    if not identical:
        raise DA050AnalysisError("Analysis replay differs")
    return result


__all__ = ["DA050AnalysisError", "analyze", "run_analysis"]
