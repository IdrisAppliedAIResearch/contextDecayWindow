from analysis.da018_analysis import paired


def test_paired_exact_counts() -> None:
    rows = [{"a": False, "b": True}, {"a": True, "b": False}, {"a": True, "b": True}]
    result = paired(rows, "a", "b")
    assert result["gains"] == 1
    assert result["losses"] == 1
    assert result["ties"] == 1
    assert result["two_sided_exact_p"] == 1.0

