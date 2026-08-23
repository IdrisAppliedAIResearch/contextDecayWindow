"""Behavioral identity tests for TC-004's pre-registration exploration."""

from __future__ import annotations

import numpy as np
import pytest

from analysis.nf005_measurement import EpisodeSource, QuestionRecord, TurnSource
from analysis.nf005_mechanism import Candidate
from analysis.tc004_exploration import (
    TC004ExplorationError,
    average_precision,
    mixed_delivery,
    policy_order,
    score_candidates,
    split_count,
)


def _candidate(identity: str, parent: int, offset: int, text: str) -> Candidate:
    return Candidate(
        identity=identity,
        parent_index=parent,
        session_order=0,
        episode_order=parent,
        turn_offset=offset,
        text=text,
        chars=len(text),
    )


def _record() -> QuestionRecord:
    p0 = _candidate("p0", 0, -1, "User: target\nAssistant: filler")
    p1 = _candidate("p1", 1, -1, "User: other\nAssistant: other")
    turns = (
        TurnSource(_candidate("t0u", 0, 0, "User: target"), True),
        TurnSource(_candidate("t0a", 0, 1, "Assistant: filler"), False),
        TurnSource(_candidate("t1u", 1, 0, "User: other"), False),
        TurnSource(_candidate("t1a", 1, 1, "Assistant: other"), False),
    )
    return QuestionRecord(
        question_id="q",
        question_type="test",
        question="target?",
        episodes=(
            EpisodeSource(p0, ("t0u", "t0a")),
            EpisodeSource(p1, ("t1u", "t1a")),
        ),
        turns=turns,
    )


def test_localization_gain_names_the_score_change_caused_by_splitting() -> None:
    record = _record()
    parent = np.asarray([0.2, 0.4])
    children = np.asarray([0.9, 0.1, 0.5, 0.3])
    scores = score_candidates(record, parent, children)
    assert scores["lexical_localization_gain"].tolist() == pytest.approx(
        [
            1 / np.sqrt(2) - 1 / 2,
            0.0,
        ]
    )
    assert scores["localization_gain"].tolist() == pytest.approx([0.7, 0.1])
    assert scores["child_spread"].tolist() == pytest.approx([0.8, 0.2])
    assert scores["max_child"].tolist() == pytest.approx([0.9, 0.5])
    assert scores["length"].tolist() == [len(source.candidate.text) for source in record.episodes]


def test_a_split_replaces_the_parent_instead_of_duplicating_it() -> None:
    record = _record()
    delivery = mixed_delivery(
        record,
        episode_scores=[0.2, 0.4],
        turn_scores=[0.9, 0.1, 0.5, 0.3],
        split_parents=[0],
        budget=10_000,
    )
    assert "p0" not in delivery.selected
    assert "t0u" in delivery.selected
    assert "t0a" in delivery.selected
    assert {"t0u", "t0a", "t1u", "t1a"} <= delivery.delivered_turns


def test_an_unsplit_parent_delivers_both_of_its_source_turns() -> None:
    record = _record()
    delivery = mixed_delivery(
        record,
        episode_scores=[0.9, 0.1],
        turn_scores=[0.9, 0.1, 0.5, 0.3],
        split_parents=[],
        budget=len(record.episodes[0].candidate.text),
    )
    assert delivery.selected == ("p0",)
    assert delivery.delivered_turns == frozenset({"t0u", "t0a"})


def test_split_children_compete_by_their_own_scores() -> None:
    record = _record()
    delivery = mixed_delivery(
        record,
        episode_scores=[0.2, 0.4],
        turn_scores=[0.9, 0.1, 0.5, 0.3],
        split_parents=[0],
        budget=len(record.turns[0].candidate.text),
    )
    assert delivery.selected == ("t0u",)
    assert delivery.delivered_turns == frozenset({"t0u"})


def test_policy_order_has_a_stable_source_tie_break() -> None:
    assert policy_order(_record(), [1.0, 1.0]) == (0, 1)


@pytest.mark.parametrize(
    ("rate", "expected"),
    [(0.0, 0), (0.01, 1), (0.5, 2), (1.0, 3)],
)
def test_split_count_keeps_endpoints_exact(rate: float, expected: int) -> None:
    assert split_count(rate, 3) == expected


def test_invalid_split_policy_fails_closed() -> None:
    with pytest.raises(TC004ExplorationError):
        mixed_delivery(_record(), [0.1, 0.2], [0.1] * 4, [2])
    with pytest.raises(TC004ExplorationError):
        split_count(1.1, 3)


def test_average_precision_scores_a_within_store_policy_order() -> None:
    assert average_precision((2, 0, 1, 3), frozenset({0, 3})) == pytest.approx(
        (1 / 2 + 2 / 4) / 2
    )
    assert average_precision((0, 1), frozenset()) is None
