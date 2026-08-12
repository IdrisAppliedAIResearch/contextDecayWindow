from __future__ import annotations

from src.analysis.sup001_measurement import evaluate_gates


def passing_metrics() -> dict:
    return {
        "integrity": True,
        "t1_current_only": 64,
        "current_only_gain": 16,
        "unchanged_losses": 0,
        "exact_lineages": 64,
        "natural_stale_selected": 0,
        "provenance": True,
    }


def test_gate_evaluator_passes_only_complete_fixture() -> None:
    gates, disposition = evaluate_gates(passing_metrics())
    assert disposition == "SUPERSESSION_OFFLINE_ELIGIBLE"
    assert all(row["status"] == "PASS" for row in gates)


def test_gate_evaluator_stops_after_first_failure() -> None:
    metrics = {**passing_metrics(), "unchanged_losses": 1}
    gates, disposition = evaluate_gates(metrics)
    assert disposition == "UNCHANGED_FACT_REGRESSION"
    assert [row["status"] for row in gates] == ["PASS", "PASS", "FAIL", "NOT_EVALUATED", "NOT_EVALUATED"]
