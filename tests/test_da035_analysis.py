from analysis.da035_analysis import paired


def test_paired_atomic_gain() -> None:
    result = paired([{"CONTROL": False, "TREATMENT": True}])
    assert result["gains"] == 1 and result["losses"] == 0

