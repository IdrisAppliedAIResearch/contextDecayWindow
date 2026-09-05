from analysis.da022_analysis import paired


def test_additive_contrast_counts_without_losses() -> None:
    rows = [{"CONTROL": False, "TREATMENT": True},
            {"CONTROL": True, "TREATMENT": True}]
    result = paired(rows)
    assert result["gains"] == 1
    assert result["losses"] == 0
    assert result["two_sided_exact_p"] == 1.0

