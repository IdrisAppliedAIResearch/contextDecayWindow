from analysis.da013_analysis import _paired


def test_paired_counts_and_exact_test() -> None:
    rows = [
        {"a": False, "b": True},
        {"a": False, "b": True},
        {"a": True, "b": False},
        {"a": True, "b": True},
    ]
    result = _paired(rows, "a", "b")
    assert result["gains"] == 2
    assert result["losses"] == 1
    assert result["ties"] == 1
    assert result["two_sided_exact_p"] == 1.0
