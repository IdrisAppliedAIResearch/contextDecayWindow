from analysis.da024_audit import classify


def test_blocker_priority() -> None:
    assert classify(False, True, True) == "MULTI_PAIR_CONJUNCTION"
    assert classify(True, True, False) == "WRONG_FROZEN_MEMBER"
    assert classify(True, False, False) == "INITIAL_BACKREF_SIZE"
    assert classify(True, False, True) == "PRIOR_ADDITIVE_CONSUMPTION"

