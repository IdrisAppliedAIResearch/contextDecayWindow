import random
import gc

import pytest

from analysis.da034_sentinel_backrefs import (
    decode_members,
    encode_members,
    encoded_chars,
    sentinel_for,
)
from analysis.da099_indexed_sentinel import (
    IndexedSentinelCodec,
    MemberSuffixIndex,
    encoded_length,
)
from analysis.da098_budget_replay import suspended_gc


def test_member_boundaries_are_not_matchable() -> None:
    index = MemberSuffixIndex(("abcd", "efgh"))
    assert index.longest_prefix("cdef") is None
    assert index.longest_prefix("efgh") == (4, 1, 0)


def test_earliest_source_wins_equal_longest_match() -> None:
    index = MemberSuffixIndex(("xx repeated value yy", "repeated value"))
    assert index.longest_prefix("repeated value") == (14, 0, 3)


def test_sequential_payload_can_reference_earlier_payload_member() -> None:
    history = ("unrelated source",)
    texts = ("a sufficiently long new phrase", "sufficiently long new phrase")
    sentinel = sentinel_for((*history, *texts))
    indexed = IndexedSentinelCodec(history, sentinel).encode(texts)
    assert indexed == encode_members(texts, history, sentinel)
    assert decode_members(indexed, history, sentinel) == texts


def test_indexed_codec_matches_legacy_on_fixed_random_corpus() -> None:
    randomizer = random.Random(99)
    alphabet = "abcde     ~"
    for _ in range(100):
        history = tuple(
            "".join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(0, 80)))
            for _ in range(randomizer.randrange(0, 12))
        )
        texts = tuple(
            "".join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(0, 80)))
            for _ in range(randomizer.randrange(1, 4))
        )
        sentinel = sentinel_for((*history, *texts))
        assert IndexedSentinelCodec(history, sentinel).encode(texts) == encode_members(
            texts, history, sentinel
        )


def test_appended_history_matches_fresh_index() -> None:
    sentinel = "~"
    codec = IndexedSentinelCodec(("alpha beta gamma",), sentinel)
    codec.append(("delta alpha beta gamma",))
    texts = ("alpha beta gamma and delta",)
    assert codec.encode(texts) == encode_members(
        texts, ("alpha beta gamma", "delta alpha beta gamma"), sentinel
    )


def test_encode_and_append_matches_sequential_legacy() -> None:
    texts = ("alpha beta gamma", "beta gamma delta", "alpha beta gamma delta")
    sentinel = sentinel_for(texts)
    codec = IndexedSentinelCodec((), sentinel)
    assert codec.encode_and_append(texts) == encode_members(texts, (), sentinel)
    assert codec.history_size == len(texts)


def test_fast_encoded_length_matches_wire_codec() -> None:
    history = ("alpha beta gamma", "beta gamma delta")
    texts = ("alpha beta gamma delta", "beta gamma delta again")
    sentinel = sentinel_for((*history, *texts))
    encoded = encode_members(texts, history, sentinel)
    assert encoded_length(encoded, sentinel, len(history)) == encoded_chars(
        encoded, sentinel, len(history)
    )
    codec = IndexedSentinelCodec(history, sentinel)
    for text in texts:
        singleton = encode_members((text,), history, sentinel)
        assert codec.encoded_text_length(text) == encoded_chars(
            singleton, sentinel, len(history)
        )


def test_fused_length_matches_legacy_on_fixed_random_corpus() -> None:
    randomizer = random.Random(100)
    alphabet = "abcde     ~"
    for _ in range(200):
        history = tuple(
            "".join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(0, 100)))
            for _ in range(randomizer.randrange(0, 15))
        )
        text = "".join(
            randomizer.choice(alphabet) for _ in range(randomizer.randrange(0, 120))
        )
        sentinel = sentinel_for((*history, text))
        encoded = encode_members((text,), history, sentinel)
        assert IndexedSentinelCodec(history, sentinel).encoded_text_length(text) == encoded_chars(
            encoded, sentinel, len(history)
        )


def test_suspended_gc_restores_state_after_success_and_exception() -> None:
    gc.enable()
    with suspended_gc():
        assert not gc.isenabled()
    assert gc.isenabled()
    with pytest.raises(RuntimeError):
        with suspended_gc():
            assert not gc.isenabled()
            raise RuntimeError("forced")
    assert gc.isenabled()
