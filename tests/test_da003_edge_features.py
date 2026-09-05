from __future__ import annotations

import numpy as np

from analysis.da003_edge_features import edge_features, one_edge_order, tokens, weighted_coverage
from analysis.nf004_mechanism import Candidate


def test_one_edge_interleaves_neighbor_once() -> None:
    assert one_edge_order((0, 1, 2, 3), 1, 3) == (0, 1, 3, 2)
    assert one_edge_order((0, 1, 2, 3), 1, 0) == (1, 0, 2, 3)


def test_weighted_coverage_is_neighbor_complementarity() -> None:
    query = tokens("When was Project Cedar launched?")
    seed = tokens("Project Cedar was discussed")
    neighbor = tokens("It launched in 2024")
    idf = {token: 1.0 for token in query}
    assert weighted_coverage(query, neighbor - seed, idf) == 1 / 5


def test_edge_features_account_for_displacement_and_residual() -> None:
    candidates = [
        Candidate("a", "s", 0, 0, "cedar project", 8_000),
        Candidate("b", "s", 0, 1, "launched 2024", 8_000),
        Candidate("c", "s", 0, 2, "other", 7_000),
    ]
    vectors = np.zeros((3, 1024), dtype=np.float32)
    vectors[:, 0] = 1
    scores = np.asarray([.8, .2, .5], dtype=np.float32)
    features, audit = edge_features(question_text="cedar 2024", candidates=candidates, vectors=vectors,
        scores=scores, direct_order=(0, 2, 1), seed=0, neighbor=1,
        idf={"cedar": 1.0, "2024": 1.0})
    assert audit["counterfactual_selected_ids"] == ["a", "b"]
    assert audit["displaced_ids"] == ["c"]
    assert features["displaced_count"] == 1
    assert features["neighbor_only_query_coverage"] == .5
    assert np.isclose(features["residual_semantic_score"], -.6)
