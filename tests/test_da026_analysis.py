from analysis.da026_analysis import paired


def test_protected_paired_gain() -> None:
    result = paired([{"a": False, "b": True}, {"a": True, "b": True}], "a", "b")
    assert (result["gains"], result["losses"]) == (1, 0)

