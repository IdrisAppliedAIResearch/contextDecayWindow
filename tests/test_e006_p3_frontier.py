from __future__ import annotations

import numpy as np
import pytest

from src.retrieval_mechanism_ledger.e006_p3 import (
    assert_mechanism_path_allowed,
    build_union_knn_graph,
    retrieve_associative_frontier,
    retrieve_fixed_query,
)


def hashes(count: int) -> tuple[str, ...]:
    return tuple(f"{index:064x}" for index in range(count))


def test_union_knn_graph_is_symmetric_and_clamps_negative_edges() -> None:
    gram = np.array(
        [
            [1.0, 0.9, -0.2, 0.1],
            [0.9, 1.0, 0.8, -0.3],
            [-0.2, 0.8, 1.0, 0.7],
            [0.1, -0.3, 0.7, 1.0],
        ]
    )

    graph = build_union_knn_graph(gram, hashes(4), k=1)

    assert np.array_equal(graph.weights, graph.weights.T)
    assert np.all(graph.weights >= 0.0)
    assert graph.weights[0, 1] == pytest.approx(0.9)
    assert graph.weights[2, 3] == pytest.approx(0.7)


def test_frontier_selects_exact_quota_without_repeats() -> None:
    query = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4])
    gram = np.eye(6)
    gram[0, 5] = gram[5, 0] = 0.95
    graph = build_union_knn_graph(gram, hashes(6), k=1)

    result = retrieve_associative_frontier(
        query_cosines=query, graph=graph, depth=1, per_step=2
    )

    assert [len(step.hit_indices) for step in result.steps] == [2, 2]
    assert set(result.steps[0].hit_indices).isdisjoint(result.steps[1].hit_indices)
    assert 5 in result.steps[1].hit_indices
    assert len(result.ranked_seen_indices) == 4


def test_no_edge_fallback_preserves_query_order_and_hash_ties() -> None:
    query = np.array([0.5, 0.5, 0.4, 0.3])
    graph = build_union_knn_graph(np.eye(4), hashes(4), k=1)

    result = retrieve_associative_frontier(
        query_cosines=query, graph=graph, depth=1, per_step=2
    )
    control = retrieve_fixed_query(
        query_cosines=query, content_hashes=hashes(4), depth=1, per_step=2
    )

    assert result.ranked_seen_content_sha256 == control.ranked_seen_content_sha256
    assert result.steps[0].hit_indices == (0, 1)
    assert all(value == 0.0 for value in result.steps[1].all_associations)


def test_exhausted_unseen_candidates_fail_before_selection() -> None:
    with pytest.raises(ValueError, match="more unique hits"):
        retrieve_fixed_query(
            query_cosines=np.ones(3),
            content_hashes=hashes(3),
            depth=1,
            per_step=2,
        )


def test_frontier_mechanism_rejects_measurement_paths() -> None:
    with pytest.raises(ValueError, match="measurement boundary"):
        assert_mechanism_path_allowed("experiments/study_008/q_facts_key.md")
