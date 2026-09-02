import pytest

from analysis.da023_backrefs import Backref
from analysis.da034_sentinel_backrefs import (
    DA034CodecError,
    decode_members,
    encode_members,
    parse_reference,
    reference_code,
    sentinel_for,
)


def test_shortest_absent_sentinel() -> None:
    assert sentinel_for(("plain",)) == "~"
    assert sentinel_for(("has ~ and ~~",)) == "~~~"


def test_reference_roundtrip() -> None:
    ref = Backref(member=7, start=1024, length=32)
    code = reference_code("~", ref, 10)
    assert parse_reference(code, "~", 10) == ref


@pytest.mark.parametrize("code", ["~", "~AAA~", "~BAA~", "~aAAA~", "~AAAA~"])
def test_malformed_reference_rejected(code: str) -> None:
    with pytest.raises(DA034CodecError):
        parse_reference(code, "~", 10)


def test_codec_exact_replay() -> None:
    texts = ("alpha beta gamma", "beta gamma delta", "alpha beta gamma delta")
    sentinel = sentinel_for(texts)
    encoded = encode_members(texts, (), sentinel)
    assert decode_members(encoded, (), sentinel) == texts


def test_source_collision_rejected() -> None:
    with pytest.raises(DA034CodecError):
        encode_members(("contains ~",), (), "~")

