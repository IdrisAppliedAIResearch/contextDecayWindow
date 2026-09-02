from analysis.da005_guards import decisions


def test_noop_is_rejected_by_every_guard() -> None:
    assert not any(decisions(0, 0, 0).values())


def test_boundaries_are_inclusive_and_nested() -> None:
    result = decisions(1, 1, 512)
    assert not result["COUNT_0"]
    assert result["COUNT_1"] and result["COUNT_2"] and result["COUNT_4"]
    assert not result["CHARS_256"]
    assert result["CHARS_512"] and result["CHARS_1024"]
    assert result["DUAL_1_512"]


def test_dual_requires_both_limits() -> None:
    assert not decisions(1, 2, 400)["DUAL_1_512"]
    assert not decisions(1, 1, 513)["DUAL_1_512"]
