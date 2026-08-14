from __future__ import annotations

import pytest

from analysis.nf007_t1_coverage import (
    CLUSTER_COUNT,
    EXPECTED_SELECTED,
    coverage_summary,
    select_sealed_record,
)


def test_coverage_stops_when_all_clusters_are_already_touched() -> None:
    statement_ids = [f"s{index}" for index in range(EXPECTED_SELECTED)]
    assignments = [index % CLUSTER_COUNT for index in range(EXPECTED_SELECTED)]

    result = coverage_summary(statement_ids, statement_ids, assignments)

    assert result["status"] == "FLOOR_INERT_STOP"
    assert result["forced_admissions_for_floor_one"] == 0


def test_coverage_reports_exact_missing_clusters_and_forced_admissions() -> None:
    statement_ids = [f"s{index}" for index in range(EXPECTED_SELECTED)]
    assignments = [index % (CLUSTER_COUNT - 2) for index in range(EXPECTED_SELECTED)]

    result = coverage_summary(statement_ids, statement_ids, assignments)

    assert result["status"] == "FLOOR_CAN_BIND"
    assert result["missing_clusters"] == [14, 15]
    assert result["forced_admissions_for_floor_one"] == 2


def test_coverage_rejects_unknown_or_duplicate_sealed_identities() -> None:
    statement_ids = [f"s{index}" for index in range(EXPECTED_SELECTED)]
    assignments = [index % CLUSTER_COUNT for index in range(EXPECTED_SELECTED)]

    with pytest.raises(AssertionError, match="80 unique"):
        coverage_summary(statement_ids[:-1] + [statement_ids[0]], statement_ids, assignments)
    with pytest.raises(AssertionError, match="missing from assignments"):
        coverage_summary(statement_ids[:-1] + ["unknown"], statement_ids, assignments)


def test_sealed_record_requires_one_exact_arm_and_turn() -> None:
    payload = {
        "records": [
            {"arm": "T1_OWN_STATEMENT", "probe_turn": 120},
            {"arm": "T1_OWN_STATEMENT", "probe_turn": 119},
        ]
    }
    assert select_sealed_record(payload)["probe_turn"] == 120

    with pytest.raises(AssertionError, match="exactly one"):
        select_sealed_record({"records": payload["records"][:1] * 2})
