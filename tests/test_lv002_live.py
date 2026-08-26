from __future__ import annotations

from analysis.lv002_live import arm_order, blind_id, disposition, majority


def test_majority_requires_odd_votes() -> None:
    assert majority((True, False, True))
    assert not majority((False, False, True, True, False))


def test_arm_schedule_is_stable_and_balanced_per_call() -> None:
    first = arm_order("question-a", 0)
    assert first == arm_order("question-a", 0)
    assert set(first) == {"FULL_CC80", "OPPORTUNITY"}


def test_blind_identity_binds_arm_and_replicate() -> None:
    values = {
        blind_id("q", arm, replicate)
        for arm in ("FULL_CC80", "OPPORTUNITY")
        for replicate in range(5)
    }
    assert len(values) == 10


def test_registered_dispositions_are_reachable() -> None:
    assert disposition(3, 1, 1, 3, 1, valid=True) == "CONVERTS"
    assert disposition(1, 0, 0, 1, 0, valid=True) == "WEAK_CONVERSION"
    assert disposition(0, 0, 0, 0, 0, valid=True) == "NO_CONVERSION"
    assert disposition(-1, 0, 0, -1, -1, valid=True) == "REGRESSES"
    assert disposition(3, -1, 1, 3, 1, valid=True) == "REGRESSES"
    assert disposition(3, 1, 1, 3, -1, valid=True) == "NOT_INTERPRETABLE"
    assert disposition(3, 1, 1, 3, 1, valid=False) == "NOT_INTERPRETABLE"
