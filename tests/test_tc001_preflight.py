"""Unit checks for TC-001's Preflight machinery.

These run without the LoCoMo corpus or the embedding cache: the pieces
under test are the ones that decide what a Preflight artifact is allowed
to contain, and they have to hold whether or not the corpus is present.
"""

from __future__ import annotations

import numpy as np
import pytest

from analysis.locomo_nf_development import PairCandidate
from analysis.tc001_exploration import (
    TC001ExplorationError,
    _delivered_ids,
    _score,
    _sham_row,
    build_episodes,
    flat_context,
    flat_order,
)
from analysis.tc001_reachability import _forbid_direction, _one_sided_extreme_p
from episodic._packing import pack_stm_payload
from episodic._render import render_stm_payload


class _Case:
    """The two attributes ``build_episodes`` reads off a conversation."""

    def __init__(self, pairs):
        self.sample_id = "dev"
        self.pairs = tuple(pairs)


def _pair(order: int, text: str) -> PairCandidate:
    return PairCandidate(
        identity=f"id-{order}",
        sample_id="dev",
        session_id="session_1",
        session_order=0,
        pair_order=order,
        text=text,
        chars=len(text),
        dialog_ids=(f"D1:{order}",),
    )


def _episodes(texts, vectors):
    pairs = [_pair(index, text) for index, text in enumerate(texts)]
    lookup = {
        text: np.asarray(vector, dtype=np.float32)
        for text, vector in zip(texts, vectors)
    }
    return build_episodes(_Case(pairs), lookup)


def test_pair_text_survives_an_embedded_newline() -> None:
    # 20 of the 1,365 development pairs carry a newline inside a speaker's
    # own text. Splitting on every newline would silently drop it, so the
    # rendered element would no longer be the candidate that was embedded.
    text = "Alice: one\n\nBob: two\nstill Bob"
    episodes = _episodes([text], [np.ones(1024)])
    record = episodes[0].record
    assert record["user_message"] + "\n" + record["assistant_message"] == text


def test_flat_order_is_cosine_descending_then_conversation_order() -> None:
    vectors = [
        np.array([1.0, 0.0] + [0.0] * 1022),
        np.array([0.0, 1.0] + [0.0] * 1022),
        np.array([1.0, 0.0] + [0.0] * 1022),
    ]
    episodes = _episodes(["a", "b", "c"], vectors)
    order = flat_order(episodes, np.array([1.0, 0.0] + [0.0] * 1022))
    assert order == (0, 2, 1)


def test_flat_arm_uses_the_shipped_packer_with_an_empty_recency_tier() -> None:
    vectors = [np.array([1.0] + [0.0] * 1023), np.array([0.0, 1.0] + [0.0] * 1022)]
    episodes = _episodes(["a", "b"], vectors)
    query = np.array([1.0] + [0.0] * 1023)
    payload, delivered = flat_context(episodes, query, 10_000)
    order = flat_order(episodes, query)
    expected = pack_stm_payload(
        [], [episodes[index].record for index in order], 10_000
    )
    assert payload == expected.payload
    assert delivered == expected.selected_ids
    assert payload.startswith("<recent_context/>")


def test_delivered_ids_read_the_payload_not_the_report() -> None:
    episodes = _episodes(["a", "b"], [np.ones(1024), np.ones(1024)])
    records = [episode.record for episode in episodes]
    payload = render_stm_payload([records[1]], [records[0]])
    assert _delivered_ids(payload, records) == ("id-1", "id-0")


def test_delivered_ids_refuse_a_store_with_repeated_turn_numbers() -> None:
    records = [
        {"id": "a", "turn_number": 1, "user_message": "", "assistant_message": ""},
        {"id": "b", "turn_number": 1, "user_message": "", "assistant_message": ""},
    ]
    with pytest.raises(TC001ExplorationError):
        _delivered_ids("", records)


def test_sham_scoring_counts_gains_and_losses_and_ignores_ties() -> None:
    counter = [0, 0]
    _score(counter, baseline=False, perturbed=True)
    _score(counter, baseline=True, perturbed=False)
    _score(counter, baseline=True, perturbed=True)
    _score(counter, baseline=False, perturbed=False)
    assert counter == [1, 1]
    row = _sham_row(0.01, 16_000, 16_160, 1, 1)
    assert row["net"] == 0
    assert row["discordant"] == 2


def test_reachability_reports_the_best_p_a_sign_test_could_reach() -> None:
    # PF4 as arithmetic: with 10 discordant pairs all falling one way, the
    # one-sided exact binomial cannot go below 2**-10.
    assert _one_sided_extreme_p(10) == pytest.approx(0.0009765625)
    assert _one_sided_extreme_p(1) == 0.5


def test_reachability_artifacts_may_not_carry_a_direction() -> None:
    _forbid_direction({"budgets": {"16000": {"discordant_pairs": 12}}})
    with pytest.raises(TC001ExplorationError):
        _forbid_direction({"budgets": {"16000": {"gains": 7}}})
    with pytest.raises(TC001ExplorationError):
        _forbid_direction({"rows": [{"net": -3}]})
