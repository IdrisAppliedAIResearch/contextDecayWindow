from analysis.da023_analysis import paired


def test_additive_paired_counts() -> None:
    result = paired([{"CONTROL": False, "TREATMENT": True},
                     {"CONTROL": True, "TREATMENT": True}])
    assert (result["gains"], result["losses"]) == (1, 0)

