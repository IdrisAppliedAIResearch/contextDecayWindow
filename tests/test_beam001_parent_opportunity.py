from __future__ import annotations

import hashlib

import numpy as np

from analysis.beam001_parent_opportunity import select_parent_opportunity
from episodic._ranking import CC80Ranking


def _episode(index: int, size: int = 4_000) -> dict:
    vector = np.zeros(1024, dtype=np.float32)
    vector[index] = 1.0
    return {
        "id": hashlib.sha256(f"beam-{index}".encode()).hexdigest(),
        "turn_number": index + 1,
        "user_message": f"user {index} " + "u" * size,
        "assistant_message": f"assistant {index} " + "a" * size,
        "embedding": vector,
    }


def _ranking(count: int) -> CC80Ranking:
    scores = tuple(1.0 - index / (count + 1) for index in range(count))
    return CC80Ranking(
        order=tuple(range(count)),
        scores=scores,
        dense_scores=scores,
        bm25_scores=tuple(0.0 for _ in range(count)),
        dense_normalized=scores,
        bm25_normalized=tuple(0.0 for _ in range(count)),
    )


def test_t1_excludes_recent_and_terminates_once_per_parent() -> None:
    episodes = [_episode(index) for index in range(10)]
    facets = tuple(frozenset({f"noun:item-{index}"}) for index in range(10))
    idf = {next(iter(values)): 1.0 for values in facets}
    recent = tuple(episode["id"] for episode in episodes[-2:])
    result = select_parent_opportunity(
        episodes=episodes,
        ranking=_ranking(len(episodes)),
        excluded_ids=recent,
        facets=facets,
        idf=idf,
        facet_families={"noun": len(episodes)},
    )

    assert set(result.recent_ids) == set(recent)
    assert not set(result.selected_ids) & set(recent)
    assert len(result.retrieval_payload) <= 32_000
    assert len((*result.recent_indices, *result.selected_indices)) == len(
        set((*result.recent_indices, *result.selected_indices))
    )
    trace = result.trace
    assert trace.finite_attempts == len(trace.parents)
    assert (
        len(trace.proposed_children)
        + trace.no_positive_child
        + trace.no_fitting_child
        == len(trace.parents)
    )
    assert len(trace.proposed_children) == len(set(trace.proposed_children))
    assert not set(trace.proposed_children) & set(trace.parents)
    assert all(
        decision.reason in {"accepted", "rejected_capacity", "rejected_value"}
        for decision in trace.decisions
    )


def test_t1_degenerate_all_recent_store_has_no_long_term_path() -> None:
    episodes = [_episode(index, size=10) for index in range(4)]
    facets = tuple(frozenset({f"noun:item-{index}"}) for index in range(4))
    result = select_parent_opportunity(
        episodes=episodes,
        ranking=_ranking(len(episodes)),
        excluded_ids=tuple(episode["id"] for episode in episodes),
        facets=facets,
        idf={next(iter(values)): 1.0 for values in facets},
        facet_families={"noun": 4},
    )

    assert result.selected_ids == ()
    assert result.retrieval_payload == ""
    assert result.trace.finite_attempts == 0
    assert result.payload.count("<episode turn=") == 4


def test_t1_is_deterministic_for_identical_inputs() -> None:
    episodes = [_episode(index) for index in range(8)]
    facets = tuple(frozenset({f"noun:item-{index}"}) for index in range(8))
    arguments = {
        "episodes": episodes,
        "ranking": _ranking(len(episodes)),
        "excluded_ids": tuple(episode["id"] for episode in episodes[-2:]),
        "facets": facets,
        "idf": {next(iter(values)): 1.0 for values in facets},
        "facet_families": {"noun": 8},
    }
    first = select_parent_opportunity(**arguments)
    second = select_parent_opportunity(**arguments)

    assert first.payload_sha256 == second.payload_sha256
    assert first.selected_ids == second.selected_ids
    assert first.trace == second.trace
