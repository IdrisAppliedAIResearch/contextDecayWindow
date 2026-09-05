"""Oracle session-local materialization capacity analysis for DA-056."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _paired, _quantile
from analysis.da048_continuation import sha256_file

CATALOG_SHA256 = "87fef862b5642cd8f6661498a776ad59d682b8052c9820a964af1bcbe506f794"
DA052_OUTCOMES_SHA256 = "c2f0359eedfe4460979634e1bd0d9038329895c4a6f208f9c80e354df65010dd"
DA053_RESIDUAL_SHA256 = "559f610177d6e4e9f499a3fe9ee4a7bd844b96d3e84558a2b5ccd634dd827560"
RETAINED_SLOTS = 5
GENERAL_CAP = 12_288


class DA056AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(catalog_path: Path, da052_outcomes_path: Path,
            residual_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((catalog_path, CATALOG_SHA256), (da052_outcomes_path, DA052_OUTCOMES_SHA256),
             (residual_path, DA053_RESIDUAL_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA056AnalysisError("Sealed input differs")
    catalogs = {str(row["question_id"]): row for row in _read(catalog_path)}
    prior = {str(row["question_id"]): row for row in _read(da052_outcomes_path)}
    residuals = {str(row["question_id"]): row for row in _read(residual_path)}
    rows = []
    for question_id in sorted(prior):
        control = bool(prior[question_id]["TREATMENT"])
        if control:
            rows.append({"question_id": question_id, "question_type": prior[question_id]["question_type"],
                         "CONTROL": True, "TREATMENT": True, "new_frames": 0,
                         "new_overflows": 0, "sessions_opened": 0,
                         "pointer_hops": 0, "retained_chars": int(prior[question_id]["retained_chars"]),
                         "peak_auxiliary_chars": int(prior[question_id]["peak_auxiliary_chars"])})
            continue
        residual = residuals[question_id]
        by_member = {str(action["member_id"]): action for action in catalogs[question_id]["ledger"]}
        actions = []
        for member in residual["members"]:
            action = by_member.get(str(member["member_id"]))
            if action is None:
                raise DA056AnalysisError("Directory member lacks materialization coordinate")
            actions.append(action)
        fitting = [action for action in actions if action["kind"] == "FRAME"]
        overflows = [action for action in actions if action["kind"] == "OVERFLOW"]
        prior_slots = int(prior[question_id]["retained_members"])
        treatment = not overflows and prior_slots + len(fitting) <= RETAINED_SLOTS
        retained_chars = int(prior[question_id]["retained_chars"])
        peak = int(prior[question_id]["peak_auxiliary_chars"])
        for action in fitting:
            peak = max(peak, retained_chars + int(action["cost"]))
            retained_chars += int(action["cost"])
        if peak > GENERAL_CAP:
            raise DA056AnalysisError("Oracle path exceeds registered auxiliary cap")
        rows.append({"question_id": question_id, "question_type": residual["question_type"],
                     "CONTROL": False, "TREATMENT": treatment,
                     "new_frames": len(fitting), "new_overflows": len(overflows),
                     "sessions_opened": len({str(action["session_id"]) for action in actions}),
                     "pointer_hops": sum(int(action["episode_order"]) + 3 for action in actions),
                     "retained_chars": retained_chars, "peak_auxiliary_chars": peak})
    if len(rows) != 465 or sum(row["CONTROL"] for row in rows) != 363:
        raise DA056AnalysisError("DA-052 anchor differs")
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    contrast = _paired(rows)
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell)
                                                       for arm in complete},
                         "contrast": _paired(cell)}
    nonnegative = all(cell["contrast"]["losses"] == 0 for cell in groups.values())
    status = ("SESSION_LOCAL_CAPACITY_SIGNAL" if contrast["gains"] >= 20
              and contrast["losses"] == 0 and nonnegative else "NO_SESSION_LOCAL_CAPACITY_SIGNAL")
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    def distribution(field: str) -> dict[str, float | int | None]:
        values = [int(row[field]) for row in gains]
        return {"p10": _quantile(values, .1), "p50": _quantile(values, .5),
                "p90": _quantile(values, .9), "max": max(values, default=None)}
    result = {"schema": "da056-session-local-materialization-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "by_question_type": groups,
              "oracle_gains": {"n": len(gains),
                               "new_frames": dict(sorted(Counter(int(row["new_frames"])
                                                                 for row in gains).items())),
                               "sessions_opened": distribution("sessions_opened"),
                               "pointer_hops": distribution("pointer_hops"),
                               "retained_chars": distribution("retained_chars"),
                               "peak_auxiliary_chars": distribution("peak_auxiliary_chars")},
              "residual_overflow_questions": sum(not row["CONTROL"] and not row["TREATMENT"]
                                                   and row["new_overflows"] > 0 for row in rows),
              "protected_payload_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware session-head and member-coordinate oracle only"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(catalog_path: Path, da052_outcomes_path: Path,
                 residual_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(catalog_path, da052_outcomes_path, residual_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "outcomes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da056-result-") as directory:
        replay_result, replay_rows = analyze(catalog_path, da052_outcomes_path, residual_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(artifact)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    if not identical:
        raise DA056AnalysisError("Analysis replay differs")
    return result


__all__ = ["DA056AnalysisError", "analyze", "run_analysis"]
