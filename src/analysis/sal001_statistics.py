from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from src.analysis.sal001_shared import SEED, STRATA


def auc_for_labels(values: Sequence[float], labels: Sequence[bool]) -> float:
    if len(values) != len(labels):
        raise ValueError("Values and labels differ in length")
    positives = [value for value, label in zip(values, labels, strict=True) if label]
    negatives = [value for value, label in zip(values, labels, strict=True) if not label]
    if not positives or not negatives:
        raise ValueError("AUC requires at least one positive and one negative")
    credits = 0.0
    for positive in positives:
        for negative in negatives:
            credits += float(positive > negative) + 0.5 * float(positive == negative)
    return credits / (len(positives) * len(negatives))


def macro_session_auc(sessions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for session in sessions:
        values = [float(value) for value in session["values"]]
        labels = [bool(value) for value in session["labels"]]
        if not any(labels) or all(labels):
            continue
        rows.append(
            {
                "session_sha256": str(session["session_sha256"]),
                "auc": auc_for_labels(values, labels),
                "exchange_count": len(values),
                "positive_count": sum(labels),
            }
        )
    if not rows:
        raise ValueError("No analyzable sessions")
    return {
        "auc": float(np.mean([row["auc"] for row in rows])),
        "session_count": len(rows),
        "sessions": rows,
    }


def exact_session_null(values: Sequence[float], positive_count: int) -> np.ndarray:
    if not 0 < positive_count < len(values):
        raise ValueError("Null distribution requires mixed labels")
    outcomes = []
    indices = range(len(values))
    for positive_indices in itertools.combinations(indices, positive_count):
        selected = set(positive_indices)
        labels = [index in selected for index in indices]
        outcomes.append(auc_for_labels(values, labels))
    return np.asarray(outcomes, dtype=np.float64)


def permutation_p_value(
    sessions: Iterable[Mapping[str, Any]],
    observed_auc: float,
    *,
    permutations: int = 100_000,
    seed: int = SEED,
) -> dict[str, Any]:
    distributions = []
    for session in sessions:
        values = [float(value) for value in session["values"]]
        labels = [bool(value) for value in session["labels"]]
        if not any(labels) or all(labels):
            continue
        distributions.append(exact_session_null(values, sum(labels)))
    if not distributions:
        raise ValueError("No session null distributions")
    rng = np.random.default_rng(seed)
    simulated = np.zeros(permutations, dtype=np.float64)
    for distribution in distributions:
        simulated += distribution[
            rng.integers(0, len(distribution), size=permutations)
        ]
    simulated /= len(distributions)
    exceedances = int(np.count_nonzero(simulated >= observed_auc))
    return {
        "p_value": (1 + exceedances) / (permutations + 1),
        "exceedances": exceedances,
        "permutations": permutations,
        "seed": seed,
        "null_mean": float(np.mean(simulated)),
        "null_std": float(np.std(simulated)),
    }


def cluster_bootstrap_interval(
    session_aucs: Sequence[float],
    *,
    resamples: int = 10_000,
    seed: int = SEED,
) -> dict[str, Any]:
    values = np.asarray(session_aucs, dtype=np.float64)
    if not len(values):
        raise ValueError("Bootstrap requires session values")
    rng = np.random.default_rng(seed)
    means = np.empty(resamples, dtype=np.float64)
    for start in range(0, resamples, 1000):
        stop = min(start + 1000, resamples)
        indices = rng.integers(0, len(values), size=(stop - start, len(values)))
        means[start:stop] = values[indices].mean(axis=1)
    return {
        "low": float(np.quantile(means, 0.025)),
        "high": float(np.quantile(means, 0.975)),
        "resamples": resamples,
        "seed": seed,
    }


def evaluate_gates(integrity_pass: bool, metrics: Mapping[str, Any]) -> dict[str, Any]:
    strata = metrics["stratum_auc"]
    conditions = {
        "G1": bool(integrity_pass),
        "G2": bool(
            metrics["adjusted_symmetric_auc"] >= 0.60
            and metrics["permutation_p"] <= 0.01
        ),
        "G3": bool(
            metrics["raw_symmetric_auc"] >= 0.55
            and metrics["adjusted_symmetric_auc"]
            >= metrics["raw_symmetric_auc"] - 0.02
        ),
        "G4": bool(
            metrics["adjusted_prior_auc"] >= 0.55
            and metrics["adjusted_next_auc"] >= 0.55
            and abs(
                metrics["adjusted_prior_auc"] - metrics["adjusted_next_auc"]
            )
            <= 0.10
        ),
        "G5": bool(
            set(strata) == set(STRATA)
            and sum(float(strata[name]) > 0.50 for name in STRATA) >= 5
            and min(float(strata[name]) for name in STRATA) >= 0.45
        ),
    }
    dispositions = {
        "G1": "INTEGRITY_STOP",
        "G2": "NO_INDEPENDENT_PROXIMITY",
        "G3": "LENGTH_RARITY_OR_POSITION_CONFOUND",
        "G4": "ASYMMETRIC_TEXT_SIGNAL",
        "G5": "NON_GENERAL_SIGNAL",
    }
    first_failure = next((name for name in conditions if not conditions[name]), None)
    return {
        "gates": {name: {"pass": value} for name, value in conditions.items()},
        "status": (
            "SALIENCE_PROXY_SUPPORTED_OFFLINE"
            if first_failure is None
            else dispositions[first_failure]
        ),
        "first_failed_gate": first_failure,
        "accessibility_study_authorized": first_failure is None,
        "ablation_authorized": False,
        "live_run_authorized": False,
    }


def group_predictor_rows(
    records: Sequence[Mapping[str, Any]],
    labels_by_session: Mapping[str, Sequence[bool]],
    strata_by_session: Mapping[str, str],
    *,
    field: str,
    direction: str,
) -> list[dict[str, Any]]:
    if direction not in {"symmetric", "prior", "next"}:
        raise ValueError(f"Unknown direction: {direction}")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["session_sha256"])].append(record)
    output = []
    for session_hash in sorted(grouped):
        session_records = sorted(grouped[session_hash], key=lambda row: row["exchange_index"])
        labels = list(labels_by_session[session_hash])
        values = []
        kept_labels = []
        for index, _record in enumerate(session_records):
            neighbors = []
            if direction in {"symmetric", "prior"} and index > 0:
                neighbors.append(float(session_records[index - 1][field]))
            if direction in {"symmetric", "next"} and index + 1 < len(session_records):
                neighbors.append(float(session_records[index + 1][field]))
            if not neighbors:
                continue
            values.append(float(np.mean(neighbors)))
            kept_labels.append(bool(labels[index]))
        if values:
            output.append(
                {
                    "session_sha256": session_hash,
                    "stratum": strata_by_session[session_hash],
                    "values": values,
                    "labels": kept_labels,
                }
            )
    return output

