from analysis.da028_analysis import paired


def test_paired_protected_gain() -> None:
    result = paired([{"CONTROL": False, "TREATMENT": True},
                     {"CONTROL": True, "TREATMENT": True}])
    assert (result["gains"], result["losses"]) == (1, 0)

