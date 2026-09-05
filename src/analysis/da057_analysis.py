"""Protected residual overflow analysis for DA-057."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _paired, _quantile
from analysis.da048_continuation import sha256_file

CODEC_SHA256 = "209d9f1c121f024e86d135316ceff7e8ab4d1faa2c73cb966a592e073c6e3eba"
DA056_OUTCOMES_SHA256 = "6ccec9bf69e13fb5503e8b43f9482bab4be2c1b2d50b1b30e4b8682b98d876ee"
DA052_OUTCOMES_SHA256 = "c2f0359eedfe4460979634e1bd0d9038329895c4a6f208f9c80e354df65010dd"
DA053_RESIDUAL_SHA256 = "559f610177d6e4e9f499a3fe9ee4a7bd844b96d3e84558a2b5ccd634dd827560"
FRAME_CAP = 2_048
RETAINED_SLOTS = 5
GENERAL_CAP = 12_288


class DA057AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _codec_rows(path: Path, wanted: set[str]) -> dict[str, dict[str, Any]]:
    output = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            question_id = str(row["question_id"])
            if question_id in wanted:
                output[question_id] = row
    if set(output) != wanted:
        raise DA057AnalysisError("Residual codec join differs")
    return output


def analyze(codec_path: Path, da056_outcomes_path: Path, da052_outcomes_path: Path,
            residual_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((codec_path, CODEC_SHA256), (da056_outcomes_path, DA056_OUTCOMES_SHA256),
             (da052_outcomes_path, DA052_OUTCOMES_SHA256), (residual_path, DA053_RESIDUAL_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA057AnalysisError("Sealed input differs")
    prior = {str(row["question_id"]): row for row in _read(da056_outcomes_path)}
    retained = {str(row["question_id"]): row for row in _read(da052_outcomes_path)}
    residuals = {str(row["question_id"]): row for row in _read(residual_path)}
    remaining = {question_id for question_id, row in prior.items() if not row["TREATMENT"]}
    if len(remaining) != 6:
        raise DA057AnalysisError("DA-056 residual population differs")
    codecs = _codec_rows(codec_path, remaining)
    rows = []
    for question_id in sorted(prior):
        control = bool(prior[question_id]["TREATMENT"])
        if control:
            rows.append({"question_id": question_id, "question_type": prior[question_id]["question_type"],
                         "CONTROL": True, "TREATMENT": True, "episode_frames": 0,
                         "selected_cost": 0, "saved_chars": 0,
                         "retained_slots": 0, "retained_chars": int(prior[question_id]["retained_chars"]),
                         "peak_auxiliary_chars": int(prior[question_id]["peak_auxiliary_chars"])})
            continue
        residual = residuals[question_id]
        missing = {str(member["member_id"]) for member in residual["members"]}
        decisions = []
        for decision in codecs[question_id]["decisions"]:
            delivered = {str(decision["user_member_id"]), str(decision["assistant_member_id"])}
            if missing & delivered:
                decisions.append(decision)
        unique = {str(decision["episode_id"]): decision for decision in decisions}
        delivered = set()
        for decision in unique.values():
            delivered.update((str(decision["user_member_id"]), str(decision["assistant_member_id"])))
        prior_slots = int(retained[question_id]["retained_members"]) + int(prior[question_id]["new_frames"])
        costs = [int(decision["selected_cost"]) for decision in unique.values()]
        fits = all(cost <= FRAME_CAP for cost in costs)
        treatment = missing <= delivered and fits and prior_slots + len(costs) <= RETAINED_SLOTS
        retained_chars = int(prior[question_id]["retained_chars"])
        peak = int(prior[question_id]["peak_auxiliary_chars"])
        for cost in costs:
            peak = max(peak, retained_chars + cost)
            retained_chars += cost
        if peak > GENERAL_CAP:
            treatment = False
        rows.append({"question_id": question_id, "question_type": residual["question_type"],
                     "CONTROL": False, "TREATMENT": treatment,
                     "episode_frames": len(costs), "selected_cost": sum(costs),
                     "saved_chars": sum(int(decision["literal_cost"]) - int(decision["selected_cost"])
                                        for decision in unique.values()),
                     "retained_slots": prior_slots + len(costs),
                     "retained_chars": retained_chars, "peak_auxiliary_chars": peak})
    if len(rows) != 465 or sum(row["CONTROL"] for row in rows) != 459:
        raise DA057AnalysisError("DA-056 anchor differs")
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    contrast = _paired(rows)
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell)
                                                       for arm in complete},
                         "contrast": _paired(cell)}
    nonnegative = all(cell["contrast"]["losses"] == 0 for cell in groups.values())
    status = ("EPISODE_DERIVATIVE_CAPACITY_SIGNAL" if contrast["gains"] >= 3
              and contrast["losses"] == 0 and nonnegative else "NO_EPISODE_DERIVATIVE_CAPACITY_SIGNAL")
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    result = {"schema": "da057-episode-derivative-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "by_question_type": groups,
              "oracle_gains": {"n": len(gains),
                               "episode_frames": dict(Counter(int(row["episode_frames"]) for row in gains)),
                               "selected_cost": {"p50": _quantile([int(row["selected_cost"]) for row in gains], .5),
                                                 "max": max((int(row["selected_cost"]) for row in gains), default=None)},
                               "saved_chars": {"p50": _quantile([int(row["saved_chars"]) for row in gains], .5),
                                               "max": max((int(row["saved_chars"]) for row in gains), default=None)},
                               "peak_auxiliary_chars": {
                                   "p50": _quantile([int(row["peak_auxiliary_chars"]) for row in gains], .5),
                                   "max": max((int(row["peak_auxiliary_chars"]) for row in gains), default=None)}},
              "remaining_overflow": sum(not row["TREATMENT"] for row in rows),
              "protected_payload_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "exact episode-local codec availability; reader interpretation untested"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(codec_path: Path, da056_outcomes_path: Path, da052_outcomes_path: Path,
                 residual_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(codec_path, da056_outcomes_path, da052_outcomes_path, residual_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "outcomes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da057-result-") as directory:
        replay_result, replay_rows = analyze(codec_path, da056_outcomes_path,
                                             da052_outcomes_path, residual_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(artifact)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    if not identical:
        raise DA057AnalysisError("Analysis replay differs")
    return result


__all__ = ["DA057AnalysisError", "analyze", "run_analysis"]
