from analysis.da023_backrefs import Backref, decode_members, encode_members, prefix_for, reference_code


def test_backreference_round_trip_and_prior_only_source() -> None:
    texts = ["alpha beta gamma", "say alpha beta gamma again"]
    prefix = prefix_for(texts)
    encoded = encode_members(texts, (), prefix)
    assert decode_members(encoded, ()) == tuple(texts)
    refs = [segment for segment in encoded[1].segments if isinstance(segment, Backref)]
    assert refs and all(ref.member == 0 for ref in refs)


def test_tie_uses_earliest_member_and_start() -> None:
    encoded = encode_members(["abcdefghij"], ["xxabcdefghij", "abcdefghij"], "~")
    ref = next(segment for segment in encoded[0].segments if isinstance(segment, Backref))
    assert (ref.member, ref.start) == (0, 2)


def test_nonbeneficial_match_stays_literal_and_prefix_avoids_collision() -> None:
    prefix = prefix_for(["literal ~r collision"])
    assert prefix == "~~"
    encoded = encode_members(["abcd"], ["abcd"], prefix)
    assert not any(isinstance(segment, Backref) for segment in encoded[0].segments)
    assert reference_code("~", Backref(0, 0, 20)) == "~r0,0,20~"

