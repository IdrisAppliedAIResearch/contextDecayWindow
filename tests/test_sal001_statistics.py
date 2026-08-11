from __future__ import annotations

import pytest

from src.analysis.sal001_shared import STRATA
from src.analysis.sal001_statistics import (
    auc_for_labels,
    evaluate_gates,
    exact_session_null,
    macro_session_auc,
    permutation_p_value,
)


def passing_metrics() -> dict:
    return {
        "adjusted_symmetric_auc": 0.62,
        "raw_symmetric_auc": 0.61,
        "adjusted_prior_auc": 0.60,
        "adjusted_next_auc": 0.61,
        "permutation_p": 0.005,
        "stratum_auc": {name: 0.60 for name in STRATA},
    }


def test_auc_credit_and_macro_weight_sessions_equally() -> None:
    assert auc_for_labels([2.0, 1.0], [True, False]) == 1.0
    assert auc_for_labels([1.0, 1.0], [True, False]) == 0.5
    result = macro_session_auc(
        [
            {"session_sha256": "a", "values": [2.0, 1.0], "labels": [True, False]},
            {"session_sha256": "b", "values": [0.0, 1.0, 2.0], "labels": [True, False, False]},
        ]
    )
    assert result["auc"] == 0.5
    assert result["session_count"] == 2


def test_exact_null_and_seeded_permutation() -> None:
    distribution = exact_session_null([0.0, 1.0, 2.0], 1)
    assert sorted(distribution.tolist()) == [0.0, 0.5, 1.0]
    sessions = [
        {"session_sha256": str(index), "values": [0.0, 1.0, 2.0], "labels": [False, False, True]}
        for index in range(8)
    ]
    first = permutation_p_value(sessions, 1.0, permutations=5000, seed=5005)
    second = permutation_p_value(sessions, 1.0, permutations=5000, seed=5005)
    assert first == second
    assert first["p_value"] < 0.01


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({}, "SALIENCE_PROXY_SUPPORTED_OFFLINE"),
        ({"adjusted_symmetric_auc": 0.59}, "NO_INDEPENDENT_PROXIMITY"),
        ({"raw_symmetric_auc": 0.54}, "LENGTH_RARITY_OR_POSITION_CONFOUND"),
        ({"adjusted_prior_auc": 0.54}, "ASYMMETRIC_TEXT_SIGNAL"),
        ({"stratum_auc": {**{name: 0.60 for name in STRATA}, "multi-session": 0.44}}, "NON_GENERAL_SIGNAL"),
    ],
)
def test_first_failure_dispositions(mutation: dict, expected: str) -> None:
    metrics = {**passing_metrics(), **mutation}
    assert evaluate_gates(True, metrics)["status"] == expected


def test_integrity_stops_before_outcome_gates() -> None:
    verdict = evaluate_gates(False, passing_metrics())
    assert verdict["status"] == "INTEGRITY_STOP"
    assert verdict["first_failed_gate"] == "G1"

