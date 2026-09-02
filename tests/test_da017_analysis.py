from analysis.da017_analysis import _paired


def test_paired_exact_counts() -> None:
    rows = [{"a": False, "b": True}, {"a": True, "b": True}]
    result = _paired(rows, "a", "b")
    assert result["gains"] == 1
    assert result["losses"] == 0
    assert result["two_sided_exact_p"] == 1.0
