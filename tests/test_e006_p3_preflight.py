from __future__ import annotations

from src.analysis.e006_p3_preflight import (
    evidence_order_audit,
    surrogate_audit,
    targeted_trace_hits,
    threshold_reachability,
)


def test_all_primary_dispositions_are_reachable_before_labels() -> None:
    result = threshold_reachability()

    assert result["status"] == "PASS"
    assert set(result["synthetic_witnesses"]) == {
        "NO_DIFFERENTIATED_CUE",
        "REACH_ONLY_NOT_DELIVERED",
        "VOLUME_CONSISTENT_PACKED_GAIN",
        "DIFFERENTIATED_OFFLINE_DELIVERY",
    }


def test_evidence_reproduces_identity_before_local_measurement_import() -> None:
    result = evidence_order_audit()

    assert result["status"] == "PASS"
    assert result["selection_before_measurement"] is True
    assert result["measurement_import_is_function_local"] is True


def test_surrogate_audit_has_every_gate_and_registered_metric() -> None:
    rows = surrogate_audit()

    assert len(rows) == 15
    observations = {row["observation"] for row in rows}
    for index in range(1, 11):
        assert any(value.startswith(f"PF{index} ") for value in observations)


def test_targeted_trace_absence_comes_from_committed_cache_audit() -> None:
    assert targeted_trace_hits() == 0
