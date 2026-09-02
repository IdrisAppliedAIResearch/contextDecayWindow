from analysis.da009_role_pattern import append_role_pair, decode_role_pairs, incremental_role_cost, role_pattern_pairs


def test_modal_role_pattern_is_reversible_with_exceptions() -> None:
    pairs = [
        [{"speaker": "A", "text": "one"}, {"speaker": "B", "text": "two"}],
        [{"speaker": "A", "text": "café\nline"}, {"speaker": "B", "text": "four"}],
        [{"speaker": "B", "text": "five"}, {"speaker": "A", "text": "six"}],
    ]
    context = role_pattern_pairs(pairs)
    assert context.default_pattern == (0, 1)
    assert context.pair_chars[0] == len("one\ntwo")
    assert context.pair_chars[2] == len("1:five\n0:six")
    assert decode_role_pairs(context) == ["A: one\nB: two", "A: café\nline\nB: four", "B: five\nA: six"]


def test_modal_role_pattern_tie_is_lexicographic() -> None:
    pairs = [
        [{"speaker": "B", "text": "x"}, {"speaker": "A", "text": "y"}],
        [{"speaker": "A", "text": "z"}, {"speaker": "B", "text": "q"}],
    ]
    assert role_pattern_pairs(pairs).default_pattern == (0, 1)


def test_append_preserves_default_and_charges_new_speaker_explicitly() -> None:
    context = role_pattern_pairs([[{"speaker": "A", "text": "x"}, {"speaker": "B", "text": "y"}]])
    pair = [{"speaker": "C", "text": "new"}, {"speaker": "A", "text": "again"}]
    updated = append_role_pair(context, pair)
    assert updated.default_pattern == context.default_pattern
    assert updated.pair_chars[-1] == len("2:new\n0:again")
    assert incremental_role_cost(context, pair) == len("@2=C") + len("2:new\n0:again")
