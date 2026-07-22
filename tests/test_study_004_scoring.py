import pytest

from src.analysis.study_004_bars import (
    evaluate_breadth_bar,
    evaluate_consolidation_bar,
    evaluate_non_regression_bar,
    validate_q14_score,
)


def test_q14_accepts_only_registered_half_point_scale():
    assert [validate_q14_score(value) for value in (0, 0.5, 1)] == [
        0.0, 0.5, 1.0
    ]
    with pytest.raises(ValueError, match="Q14 score"):
        validate_q14_score(0.75)


def test_breadth_bar_requires_each_probe_and_combined_1_5():
    assert evaluate_breadth_bar(1.0, 0.5, True, True)["passed"]
    assert not evaluate_breadth_bar(0.5, 0.5, True, True)["passed"]
    assert not evaluate_breadth_bar(1.0, 0.0, True, True)["passed"]


def test_breadth_score_pass_without_ltm_attribution_is_flagged_not_passed():
    result = evaluate_breadth_bar(1.0, 1.0, True, False)
    assert result["score_pass"]
    assert not result["attribution_pass"]
    assert not result["passed"]


def test_non_regression_uses_q1_through_q13_total_only():
    assert evaluate_non_regression_bar(12.0, 3.0, 3.0, 2.0, 2.0)["passed"]
    assert not evaluate_non_regression_bar(11.5, 3.0, 3.0, 2.0, 2.0)["passed"]


def test_consolidation_bar_requires_band_and_zero_cross_domain_merges():
    assert evaluate_consolidation_bar(3, 0)["passed"]
    assert evaluate_consolidation_bar(10, 0)["passed"]
    assert not evaluate_consolidation_bar(2, 0)["passed"]
    assert not evaluate_consolidation_bar(5, 1)["passed"]
