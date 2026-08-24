from __future__ import annotations

import pytest

from analysis.tc009_convex_protected_miss_audit import (
    MissAuditError,
    admission_phase,
    association_label,
    question_flags,
    structural_group,
)


def test_association_labels_are_symmetric_for_gains_and_losses() -> None:
    expected = ["BOTH_CONTROLS", "CC80_ONLY", "A3_ONLY", "COMBINATION_ONLY"]
    assert [association_label(True, a, b) for a, b in ((True, True), (True, False), (False, True), (False, False))] == expected
    assert [association_label(False, a, b) for a, b in ((False, False), (False, True), (True, False), (True, True))] == expected


def test_admission_phase_is_exclusive() -> None:
    allocation = {"initial_relevance_ids": ["a"], "spread_ids": ["b"], "returned_relevance_ids": ["c"]}
    assert [admission_phase(allocation, value) for value in "abcd"] == ["INITIAL_RELEVANCE", "PROTECTED_SPREAD", "RETURNED_RELEVANCE", "ABSENT"]
    allocation["spread_ids"].append("a")
    with pytest.raises(MissAuditError):
        admission_phase(allocation, "a")


def test_question_flags_are_transparent_and_overlap() -> None:
    assert question_flags("How many places did Pat visit before June?") == ("QUANTITY", "TEMPORAL", "LOCATION", "ENUMERATION")
    assert question_flags("Did Pat enjoy music?") == ("UNMARKED",)


def test_structural_groups() -> None:
    assert structural_group(1, 1) == "SINGLE_CARRIER_SINGLE_SESSION"
    assert structural_group(3, 1) == "MULTI_CARRIER_ONE_SESSION"
    assert structural_group(3, 2) == "MULTI_SESSION"
