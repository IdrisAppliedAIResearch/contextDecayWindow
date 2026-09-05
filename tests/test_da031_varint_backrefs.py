import pytest

from analysis.da023_backrefs import Backref
from analysis.da031_varint_backrefs import (
    CONTINUATION,
    DA031CodecError,
    TERMINAL,
    decode_members,
    decode_uint,
    encode_members,
    encode_uint,
    parse_reference,
    prefix_for,
    reference_code,
)


def test_alphabets_are_disjoint_and_complete() -> None:
    assert len(TERMINAL) == len(CONTINUATION) == 32
    assert not set(TERMINAL) & set(CONTINUATION)


@pytest.mark.parametrize("value", [0, 1, 31, 32, 1023, 1024, 32767, 32768, 1_000_000])
def test_uint_boundaries(value: int) -> None:
    encoded = encode_uint(value)
    assert decode_uint(encoded) == (value, len(encoded))


def test_reference_roundtrip() -> None:
    ref = Backref(member=7, start=1024, length=32)
    code = reference_code("~", ref, 10)
    assert parse_reference(code, "~", 10) == ref


@pytest.mark.parametrize("code", ["~v", "~vAAA~", "~vBAA~", "~vaAAA~", "~vAAAA~"])
def test_malformed_reference_rejected(code: str) -> None:
    with pytest.raises(DA031CodecError):
        parse_reference(code, "~", 10)


def test_codec_exact_replay() -> None:
    texts = ("alpha beta gamma", "beta gamma delta", "alpha beta gamma delta")
    encoded = encode_members(texts, (), prefix_for(texts))
    assert decode_members(encoded, ()) == texts


def test_prefix_avoids_all_markers() -> None:
    assert prefix_for(("~v ~~q ~~~r",)) == "~~~~"

