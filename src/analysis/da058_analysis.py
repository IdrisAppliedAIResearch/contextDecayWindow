"""Protected exact chunk-chain capacity analysis for DA-058."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _paired, _quantile
from analysis.da048_continuation import sha256_file

CHUNKS_SHA256 = "2d2d7d8b1327c035d41e1eea20c07d0081c0fc807068e717ece843e7586ee34f"
DA057_OUTCOMES_SHA256 = "f8cfd17f532782386f9572ed4dc1e8c610e153bd4b3601d98e7d7416eb752bbb"
DA056_OUTCOMES_SHA256 = "6ccec9bf69e13fb5503e8b43f9482bab4be2c1b2d50b1b30e4b8682b98d876ee"
DA052_OUTCOMES_SHA256 = "c2f0359eedfe4460979634e1bd0d9038329895c4a6f208f9c80e354df65010dd"
DA053_RESIDUAL_SHA256 = "559f610177d6e4e9f499a3fe9ee4a7bd844b96d3e84558a2b5ccd634dd827560"
RETAINED_SLOTS = 5
GENERAL_CAP = 12_288


class DA058AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _selected(path: Path, wanted: set[str]) -> dict[str, dict[str, Any]]:
    output = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if str(row["question_id"]) in wanted:
                output[str(row["question_id"])] = row
    if set(output) != wanted:
        raise DA058AnalysisError("Residual chunk join differs")
    return output


def analyze(chunks_path: Path, da057_outcomes_path: Path, da056_outcomes_path: Path,
            da052_outcomes_path: Path,
            residual_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((chunks_path, CHUNKS_SHA256), (da057_outcomes_path, DA057_OUTCOMES_SHA256),
             (da056_outcomes_path, DA056_OUTCOMES_SHA256),
             (da052_outcomes_path, DA052_OUTCOMES_SHA256),
             (residual_path, DA053_RESIDUAL_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA058AnalysisError("Sealed input differs")
    control_rows = {str(row["question_id"]): row for row in _read(da057_outcomes_path)}
    local = {str(row["question_id"]): row for row in _read(da056_outcomes_path)}
    retained = {str(row["question_id"]): row for row in _read(da052_outcomes_path)}
    residuals = {str(row["question_id"]): row for row in _read(residual_path)}
    remaining = {question_id for question_id, row in control_rows.items() if not row["TREATMENT"]}
    if len(remaining) != 6:
        raise DA058AnalysisError("DA-057 residual population differs")
    catalogs = _selected(chunks_path, remaining)
    rows = []
    for question_id in sorted(control_rows):
        control = bool(control_rows[question_id]["TREATMENT"])
        if control:
            rows.append({"question_id": question_id,
                         "question_type": control_rows[question_id]["question_type"],
                         "CONTROL": True, "TREATMENT": True, "chunked_members": 0,
                         "new_chunks": 0, "retained_slots": 0,
                         "retained_chars": int(control_rows[question_id]["retained_chars"]),
                         "peak_auxiliary_chars": int(control_rows[question_id]["peak_auxiliary_chars"])})
            continue
        residual = residuals[question_id]
        needed = {str(member["member_id"]) for member in residual["members"]}
        by_member = {str(decision["member_id"]): decision
                     for decision in catalogs[question_id]["decisions"]}
        decisions = [by_member[member] for member in needed]
        chunked = [decision for decision in decisions if decision["selected"] == "CHUNKED"]
        prior_slots = int(retained[question_id]["retained_members"]) + int(local[question_id]["new_frames"])
        new_chunks = sum(int(decision["chunk_count"]) for decision in chunked)
        treatment = prior_slots + new_chunks <= RETAINED_SLOTS
        retained_chars = int(local[question_id]["retained_chars"])
        peak = int(local[question_id]["peak_auxiliary_chars"])
        for decision in chunked:
            for block in decision["blocks"]:
                cost = int(block["cost"])
                peak = max(peak, retained_chars + cost)
                retained_chars += cost
        if peak > GENERAL_CAP:
            treatment = False
        rows.append({"question_id": question_id, "question_type": residual["question_type"],
                     "CONTROL": False, "TREATMENT": treatment,
                     "chunked_members": len(chunked), "new_chunks": new_chunks,
                     "retained_slots": prior_slots + new_chunks,
                     "retained_chars": retained_chars, "peak_auxiliary_chars": peak})
    if len(rows) != 465 or sum(row["CONTROL"] for row in rows) != 459:
        raise DA058AnalysisError("DA-057 anchor differs")
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    contrast = _paired(rows)
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell)
                                                       for arm in complete},
                         "contrast": _paired(cell)}
    nonnegative = all(cell["contrast"]["losses"] == 0 for cell in groups.values())
    status = ("EXACT_CHUNK_CAPACITY_SIGNAL" if contrast["gains"] >= 3
              and contrast["losses"] == 0 and nonnegative else "NO_EXACT_CHUNK_CAPACITY_SIGNAL")
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    result = {"schema": "da058-exact-chunk-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "by_question_type": groups,
              "oracle_gains": {"n": len(gains),
                               "new_chunks": dict(Counter(int(row["new_chunks"]) for row in gains)),
                               "retained_slots": dict(Counter(int(row["retained_slots"]) for row in gains)),
                               "retained_chars": {"p50": _quantile(
                                   [int(row["retained_chars"]) for row in gains], .5),
                                                  "max": max((int(row["retained_chars"]) for row in gains), default=None)},
                               "peak_auxiliary_chars": {"p50": _quantile(
                                   [int(row["peak_auxiliary_chars"]) for row in gains], .5),
                                                        "max": max((int(row["peak_auxiliary_chars"]) for row in gains), default=None)}},
              "remaining": sum(not row["TREATMENT"] for row in rows),
              "protected_payload_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "exact chunk-chain availability; reader reconstruction untested"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(chunks_path: Path, da057_outcomes_path: Path, da056_outcomes_path: Path,
                 da052_outcomes_path: Path, residual_path: Path, output_dir: Path) -> dict[str, Any]:
    args = (chunks_path, da057_outcomes_path, da056_outcomes_path,
            da052_outcomes_path, residual_path)
    result, rows = analyze(*args)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "outcomes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da058-result-") as directory:
        replay_result, replay_rows = analyze(*args)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(artifact)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    if not identical:
        raise DA058AnalysisError("Analysis replay differs")
    return result


__all__ = ["DA058AnalysisError", "analyze", "run_analysis"]
