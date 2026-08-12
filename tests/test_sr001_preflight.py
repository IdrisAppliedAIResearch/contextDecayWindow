from __future__ import annotations

from src.analysis.sr001_gates import evaluate_gates, synthetic_reachability


def passing_values() -> dict:
    return {
        "integrity_pass": True,
        "retrieval_identity_match": True,
        "q11_control_facts": 7,
        "q11_treatment_facts": 8,
        "holdout_control_facts": 10,
        "holdout_treatment_facts": 11,
        "targeted_losses": [],
        "aggregate_regressions": [],
    }


def test_all_dispositions_are_reachable() -> None:
    observed = synthetic_reachability()
    assert set(observed) == {
        "INTEGRITY_STOP",
        "RETRIEVAL_IDENTITY_MISMATCH",
        "NO_BROAD_GAIN",
        "TARGETED_REGRESSION",
        "CLASS_OR_DOMAIN_REGRESSION",
        "SPAN_REPRESENTATION_OFFLINE_ELIGIBLE",
    }


def test_gate_order_stops_at_first_failure() -> None:
    values = passing_values()
    values.update(integrity_pass=False, targeted_losses=["later"])
    result = evaluate_gates(**values)
    assert result["first_failure"] == "G1"
    assert result["disposition"] == "INTEGRITY_STOP"


def test_passing_offline_gates_do_not_authorize_live() -> None:
    result = evaluate_gates(**passing_values())
    assert result["ablation_authorized"] is True
    assert result["live_run_authorized"] is False
