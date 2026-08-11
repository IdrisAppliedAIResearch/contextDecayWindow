from __future__ import annotations

import struct

import numpy as np
import pytest

from src.retrieval_mechanism_ledger.ta001 import (
    assert_mechanism_path_allowed,
    content_sha256,
    fixed_query_candidates,
    rank_by_query,
    temporal_adjacency_bridge,
)


def episode(turn: int, vector: tuple[float, ...] = (1.0, 0.0)) -> dict:
    return {
        "id": f"id-{turn}",
        "turn_number": turn,
        "user_message": f"u{turn}",
        "assistant_message": f"a{turn}",
        "embedding": struct.pack(f"{len(vector)}f", *vector),
    }


def test_rank_by_query_uses_cosine_then_content_hash() -> None:
    rows = [episode(2), episode(1), episode(3, (0.0, 1.0))]
    ranked = rank_by_query(rows, np.array([1.0, 0.0]))
    tied = sorted(rows[:2], key=content_sha256)
    assert list(ranked[:2]) == tied
    assert ranked[2]["turn_number"] == 3


def test_bridge_interleaves_only_immediate_neighbors_and_stops_at_quota() -> None:
    rows = [episode(turn) for turn in (5, 1, 9, 2, 3, 4, 6, 7, 8, 10)]
    result = temporal_adjacency_bridge(rows, quota=7)
    first_neighbors = sorted((episode(4), episode(6)), key=content_sha256)
    expected = [5, *(row["turn_number"] for row in first_neighbors), 1, 2, 9]
    final_neighbor = min((episode(8), episode(10)), key=content_sha256)
    expected.append(final_neighbor["turn_number"])
    assert [row["turn_number"] for row in result.candidates] == expected
    assert [row.role for row in result.admissions[:3]] == [
        "seed",
        "previous" if first_neighbors[0]["turn_number"] == 4 else "next",
        "previous" if first_neighbors[1]["turn_number"] == 4 else "next",
    ]
    assert all(row.temporal_distance in (0, 1) for row in result.admissions)
    assert 3 not in [row["turn_number"] for row in result.candidates]


def test_seed_already_admitted_as_neighbor_is_not_recursively_expanded() -> None:
    rows = [episode(turn) for turn in (2, 3, 5, 1, 4, 6)]
    result = temporal_adjacency_bridge(rows, quota=5)
    first_neighbors = sorted((episode(1), episode(3)), key=content_sha256)
    last_neighbor = min((episode(4), episode(6)), key=content_sha256)
    assert [row["turn_number"] for row in result.candidates] == [
        2,
        *(row["turn_number"] for row in first_neighbors),
        5,
        last_neighbor["turn_number"],
    ]
    assert any(row["reason"] == "seed_already_admitted_as_neighbor" for row in result.skipped_duplicates)


def test_boundary_missing_turn_and_multiple_episodes_are_deterministic() -> None:
    extra = episode(2)
    extra["id"] = "other"
    extra["assistant_message"] = "other"
    rows = [episode(1), extra, episode(2), episode(4), episode(3)]
    result = temporal_adjacency_bridge(rows, quota=4)
    assert result.candidates[0]["turn_number"] == 1
    turn_two = [row for row in result.candidates if row["turn_number"] == 2]
    assert [content_sha256(row) for row in turn_two] == sorted(content_sha256(row) for row in turn_two)


def test_fixed_query_and_guards_fail_closed() -> None:
    rows = [episode(turn) for turn in range(1, 5)]
    assert len(fixed_query_candidates(rows, quota=3)) == 3
    with pytest.raises(ValueError):
        fixed_query_candidates(rows, quota=5)
    with pytest.raises(ValueError):
        temporal_adjacency_bridge(rows, quota=3, radius=2)
    with pytest.raises(ValueError):
        assert_mechanism_path_allowed("measurement/answer_key.json")
