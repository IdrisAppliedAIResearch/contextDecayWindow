from analysis.da048_continuation import encode_uint, render_block


def test_varint_matches_frozen_small_ordinals() -> None:
    assert encode_uint(0) == "A"
    assert encode_uint(31) == "7"
    assert encode_uint(32) == "aB"


def test_render_block_is_exact() -> None:
    assert render_block("~~", 1, {"speaker": "User", "text": "hello"}) == "~~NB~~User: hello"
