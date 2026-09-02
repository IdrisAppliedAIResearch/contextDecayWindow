from analysis.da025_analysis import paired


def test_atomic_paired_trade() -> None:
    result = paired([{"a": False, "b": True}, {"a": True, "b": False}], "a", "b")
    assert (result["gains"], result["losses"]) == (1, 1)

