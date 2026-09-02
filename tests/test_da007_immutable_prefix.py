from analysis.da007_immutable_prefix import immutable_prefix


def test_immutable_prefix_drops_only_suffix() -> None:
    core, removed, used = immutable_prefix(["a", "b", "c"], {"a": 4, "b": 5, "c": 3}, 9)
    assert core == ["a", "b"]
    assert removed == ["c"]
    assert used == 9


def test_immutable_prefix_does_not_backfill() -> None:
    core, removed, used = immutable_prefix(["a", "b", "c"], {"a": 7, "b": 5, "c": 3}, 10)
    assert core == ["a"]
    assert removed == ["b", "c"]
    assert used == 7
