import pytest

from analysis.da023_backrefs import Backref
from analysis.da027_compact_backrefs import (
    DA027CodecError,
    base36,
    decode_members,
    encode_members,
    parse36,
    parse_reference,
    prefix_for,
    reference_code,
)


def test_base36_boundaries() -> None:
    assert [base36(value) for value in (0, 35, 36, 1295, 1296)] == ["0", "Z", "10", "ZZ", "100"]
    assert [parse36(value) for value in ("0", "Z", "10", "ZZ", "100")] == [0, 35, 36, 1295, 1296]


def test_relative_reference_roundtrip() -> None:
    ref = Backref(member=7, start=1295, length=36)
    code = reference_code("~", ref, history_size=10)
    assert code == "~q3.ZZ.10~"
    assert parse_reference(code, "~", 10) == ref


@pytest.mark.parametrize("code", ["~q0.0.1~", "~qB.0.1~", "~q1.0.0~", "~q01.0.1~", "~q1..1~"])
def test_invalid_reference_rejected(code: str) -> None:
    with pytest.raises(DA027CodecError):
        parse_reference(code, "~", 10)


def test_compact_codec_exactly_replays() -> None:
    texts = ("alpha beta gamma", "beta gamma delta", "alpha beta gamma delta")
    prefix = prefix_for(texts)
    encoded = encode_members(texts, (), prefix)
    assert decode_members(encoded, ()) == texts


def test_prefix_avoids_both_reference_markers() -> None:
    assert prefix_for(("literal ~q and ~~r",)) == "~~~"

