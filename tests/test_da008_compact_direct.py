from analysis.da008_compact_direct import compact_pairs, decode_pairs, incremental_pair_cost


def test_dictionary_renderer_is_deterministic_and_reversible() -> None:
    pairs = [
        [{"speaker": "Alice", "text": "Hello: world"}, {"speaker": "Bob", "text": "café"}],
        [{"speaker": "Alice", "text": "Again"}, {"speaker": "Bob", "text": "Done"}],
    ]
    compact = compact_pairs(pairs)
    assert compact.speakers == ("Alice", "Bob")
    assert compact.pairs[0] == ((0, "Hello: world"), (1, "café"))
    assert decode_pairs(compact) == ["Alice: Hello: world\nBob: café", "Alice: Again\nBob: Done"]
    assert compact_pairs(pairs) == compact


def test_dictionary_charged_once_and_pairs_independently() -> None:
    pairs = [
        [{"speaker": "A", "text": "x"}, {"speaker": "B", "text": "yy"}],
        [{"speaker": "A", "text": "z"}, {"speaker": "B", "text": "q"}],
    ]
    compact = compact_pairs(pairs)
    assert compact.dictionary_chars == len("@0=A") + len("@1=B")
    assert compact.pair_chars == (len("0:x\n1:yy"), len("0:z\n1:q"))
    assert compact.chars == compact.dictionary_chars + sum(compact.pair_chars)


def test_incremental_cost_adds_only_new_speaker_dictionary_entry() -> None:
    direct = compact_pairs([[{"speaker": "A", "text": "x"}]])
    known = [{"speaker": "A", "text": "more"}]
    new = [{"speaker": "C", "text": "new"}, {"speaker": "A", "text": "again"}]
    assert incremental_pair_cost(direct, known) == len("0:more")
    assert incremental_pair_cost(direct, new) == len("@1=C") + len("1:new\n0:again")
