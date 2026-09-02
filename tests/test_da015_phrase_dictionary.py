from analysis.da015_phrase_dictionary import decode, encode


def test_phrase_codec_is_exact_and_saves_repetition() -> None:
    texts = ("project cedar launched in 2024; project cedar grew", "project cedar launched in 2024")
    context = encode(texts)
    assert decode(context) == texts
    assert context.phrases
    assert context.content_chars + context.declaration_chars < sum(map(len, texts))


def test_prefix_avoids_literal_code_collision() -> None:
    texts = ("~p0~ project cedar project cedar", "project cedar")
    context = encode(texts)
    assert context.prefix == "~~"
    assert decode(context) == texts


def test_nonrepeating_text_uses_no_dictionary() -> None:
    texts = ("alpha beta", "gamma delta")
    context = encode(texts)
    assert not context.phrases
    assert decode(context) == texts


def test_pruning_keeps_registered_greedy_tie_order() -> None:
    texts = ("alpha beta alpha beta gamma delta gamma delta", "alpha beta gamma delta")
    first = encode(texts)
    second = encode(texts)
    assert first == second
    assert decode(first) == texts
