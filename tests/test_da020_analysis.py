from analysis.da020_analysis import paired


def test_paired_counts_boundary_trades() -> None:
    rows = [{"CONTROL": False, "TREATMENT": True},
            {"CONTROL": True, "TREATMENT": False},
            {"CONTROL": True, "TREATMENT": True}]
    result = paired(rows)
    assert (result["gains"], result["losses"], result["ties"]) == (1, 1, 1)
    assert result["two_sided_exact_p"] == 1.0

