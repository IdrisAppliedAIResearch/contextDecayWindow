from __future__ import annotations

import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from src.analysis.sal001_shared import (
    EXPECTED_COUNTS,
    REPO_ROOT,
    STRATA,
    artifact_identity,
    canonical_digest,
    read_json,
    write_json,
)
from src.analysis.sal001_statistics import (
    cluster_bootstrap_interval,
    evaluate_gates,
    group_predictor_rows,
    macro_session_auc,
    permutation_p_value,
)


class SAL001AnalysisError(RuntimeError):
    pass


def _committed_and_clean(path: Path) -> bool:
    relative = path.relative_to(REPO_ROOT).as_posix()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    ).returncode == 0
    clean = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relative],
        cwd=REPO_ROOT,
        check=False,
    ).returncode == 0
    return tracked and clean


def _label_maps(labels: Mapping[str, Any]) -> tuple[dict[str, list[bool]], dict[str, str]]:
    label_map: dict[str, list[bool]] = {}
    stratum_map: dict[str, str] = {}
    for session in labels["sessions"]:
        session_hash = str(session["session_sha256"])
        if session_hash in label_map:
            raise SAL001AnalysisError("Duplicate sealed session key")
        label_map[session_hash] = [bool(value) for value in session["labels"]]
        stratum_map[session_hash] = str(session["stratum"])
    return label_map, stratum_map


def analyze_core(scores: Mapping[str, Any], labels: Mapping[str, Any]) -> dict[str, Any]:
    records = list(scores["records"])
    label_map, stratum_map = _label_maps(labels)
    scored_sessions = {str(row["session_sha256"]) for row in records}
    if scored_sessions != set(label_map):
        raise SAL001AnalysisError("Score and label session identities differ")
    if len(records) != EXPECTED_COUNTS["eligible_exchanges"]:
        raise SAL001AnalysisError("Score record count differs from registration")
    by_session: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        by_session[str(row["session_sha256"])].append(row)
    for session_hash, session_records in by_session.items():
        indices = sorted(int(row["exchange_index"]) for row in session_records)
        if indices != list(range(len(label_map[session_hash]))):
            raise SAL001AnalysisError("Exchange identity join is incomplete")

    adjusted = group_predictor_rows(
        records,
        label_map,
        stratum_map,
        field="adjusted_salience",
        direction="symmetric",
    )
    raw = group_predictor_rows(
        records,
        label_map,
        stratum_map,
        field="mean_nll",
        direction="symmetric",
    )
    prior = group_predictor_rows(
        records,
        label_map,
        stratum_map,
        field="adjusted_salience",
        direction="prior",
    )
    next_rows = group_predictor_rows(
        records,
        label_map,
        stratum_map,
        field="adjusted_salience",
        direction="next",
    )
    adjusted_auc = macro_session_auc(adjusted)
    raw_auc = macro_session_auc(raw)
    prior_auc = macro_session_auc(prior)
    next_auc = macro_session_auc(next_rows)
    permutation = permutation_p_value(adjusted, adjusted_auc["auc"])
    bootstrap = cluster_bootstrap_interval(
        [row["auc"] for row in adjusted_auc["sessions"]]
    )
    stratum_auc: dict[str, float] = {}
    stratum_details: dict[str, Any] = {}
    for stratum in STRATA:
        result = macro_session_auc(
            row for row in adjusted if row["stratum"] == stratum
        )
        stratum_auc[stratum] = result["auc"]
        stratum_details[stratum] = result

    metrics = {
        "adjusted_symmetric_auc": adjusted_auc["auc"],
        "raw_symmetric_auc": raw_auc["auc"],
        "adjusted_prior_auc": prior_auc["auc"],
        "adjusted_next_auc": next_auc["auc"],
        "permutation_p": permutation["p_value"],
        "stratum_auc": stratum_auc,
    }
    verdict = evaluate_gates(True, metrics)
    return {
        "schema": "sal001-analysis-v1",
        "metrics": metrics,
        "adjusted_symmetric": adjusted_auc,
        "raw_symmetric": raw_auc,
        "adjusted_prior": prior_auc,
        "adjusted_next": next_auc,
        "permutation": permutation,
        "cluster_bootstrap_95": bootstrap,
        "strata": stratum_details,
        "verdict": verdict,
    }


def run(
    score_path: Path,
    labels_path: Path,
    preflight_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite analysis: {output_path}")
    if not _committed_and_clean(preflight_path):
        raise SAL001AnalysisError("Preflight must be a committed clean ancestor")
    preflight = read_json(preflight_path)
    if (
        preflight.get("status") != "PASS"
        or not preflight.get("measurement_authorized", False)
    ):
        raise SAL001AnalysisError("Passing Preflight is required before labels open")
    scores = read_json(score_path)
    labels = read_json(labels_path)
    result = analyze_core(scores, labels)
    result["inputs"] = {
        "scores": artifact_identity(score_path),
        "sealed_labels": artifact_identity(labels_path),
        "preflight": artifact_identity(preflight_path),
    }
    result["deterministic_digest"] = canonical_digest(
        {key: value for key, value in result.items() if key != "inputs"}
    )
    write_json(output_path, result)
    return result

