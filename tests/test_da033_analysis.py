from analysis.da033_analysis import paired


def test_paired_protected_gain() -> None:
    result = paired([{"CONTROL": False, "TREATMENT": True}])
    assert result["gains"] == 1 and result["losses"] == 0

