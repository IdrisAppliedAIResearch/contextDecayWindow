from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from analysis.tc007_allocation import TC007AllocationError, allocate


@dataclass(frozen=True)
class _Episode:
    identity: str
    record: dict


def _episode(index: int, size: int = 180) -> _Episode:
    identifier = f"candidate-{index}"
    text = chr(65 + index) * size
    return _Episode(
        identifier,
        {
            "id": identifier,
            "turn_number": index + 1,
            "user_message": text,
            "assistant_message": text,
            "embedding": np.eye(8, dtype=np.float32)[index % 8],
            "ground_truth_domain": f"d{index % 3}",
        },
    )


def test_admission_phase_owns_shared_candidates_and_deduplicates() -> None:
    episodes = tuple(_episode(index) for index in range(30))
    relevance = tuple(range(30))
    spread = tuple(reversed(range(30)))
    result = allocate(episodes, relevance, spread, 16_000)
    assert len(result.selected_ids) == len(set(result.selected_ids))
    assert set(result.initial_relevance_ids).isdisjoint(result.spread_ids)
    assert all(result.owner[item] == "relevance" for item in result.initial_relevance_ids)
    assert all(result.owner[item] == "spread" for item in result.spread_ids)
    assert len(result.payload) <= 16_000


def test_spread_may_admit_a_candidate_relevance_only_proposed() -> None:
    episodes = tuple(_episode(index, 500) for index in range(40))
    result = allocate(episodes, tuple(range(40)), tuple(reversed(range(40))), 16_000)
    assert result.spread_ids
    assert result.spread_ids[0] in {episode.identity for episode in episodes}
    assert result.spread_ids[0] not in result.initial_relevance_ids


def test_empty_spread_returns_capacity_to_relevance() -> None:
    episodes = tuple(_episode(index, 250) for index in range(50))
    relevance = tuple(range(50))
    result = allocate(episodes, relevance, (), 16_000)
    assert result.spread_ids == ()
    assert result.returned_relevance_ids
    assert result.selected_ids == (
        *result.initial_relevance_ids,
        *result.returned_relevance_ids,
    )


def test_unregistered_budget_and_partial_order_fail() -> None:
    episodes = tuple(_episode(index) for index in range(3))
    with pytest.raises(TC007AllocationError):
        allocate(episodes, (0, 1, 2), (2, 1, 0), 12_000)
    with pytest.raises(TC007AllocationError):
        allocate(episodes, (0, 1), (2, 1, 0), 16_000)
