from analysis.da006_reserved_links import choose_turn, pack_ids


def test_pack_ids_uses_exact_skip_overflow_without_slack_return() -> None:
    selected, used = pack_ids(["a", "b", "c"], {"a": 7, "b": 5, "c": 3}, 10)
    assert selected == ["a", "c"]
    assert used == 10


def test_turn_choice_uses_idf_coverage_then_source_order() -> None:
    members = [
        {"speaker": "A", "text": "project cedar"},
        {"speaker": "B", "text": "launched 2024"},
    ]
    idf = {"when": 1, "launched": 2, "2024": 3}
    assert choose_turn("when launched 2024", members, idf) == 1
    assert choose_turn("unmatched", members, {"unmatched": 1}) == 0
