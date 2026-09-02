from __future__ import annotations

from analysis.da002_mechanism_analysis import classify_trajectory


def test_persistent_gain_and_loss_states() -> None:
    assert classify_trajectory(False, [False, True, True, True, True])["class"] == "PERSISTENT_GAIN"
    assert classify_trajectory(True, [True, True, False, False, False])["class"] == "PERSISTENT_LOSS"


def test_revert_and_recover_states() -> None:
    assert classify_trajectory(False, [False, True, True, False, False])["class"] == "GAIN_THEN_REVERT"
    assert classify_trajectory(True, [True, False, False, True, True])["class"] == "LOSS_THEN_RECOVER"


def test_multiple_reversal_and_tie_states() -> None:
    row = classify_trajectory(False, [False, True, False, True, False])
    assert row["class"] == "MULTIPLE_GAIN_TIE_REVERSALS"
    assert row["sequence"] == "TGTGT"
    assert classify_trajectory(True, [True] * 5)["class"] == "ALWAYS_TIED"
