import numpy as np

from analysis.da012_carrier import edge_tie, grouped_scores


def test_grouped_scores_exclude_target_group_and_are_deterministic() -> None:
    matrix = np.asarray([[i, i % 3] for i in range(12)], dtype=float)
    labels = np.asarray([i % 2 for i in range(12)], dtype=int)
    groups = np.asarray(["a"] * 4 + ["b"] * 4 + ["c"] * 4)
    first, audit = grouped_scores(matrix, labels, groups)
    second, _ = grouped_scores(matrix, labels, groups)
    assert np.array_equal(first, second)
    assert all(row["overlap"] == 0 and row["train"] == 8 and row["test"] == 4 for row in audit.values())


def test_edge_tie_prefers_prior_then_neighbor_identity() -> None:
    prior = {"neighbor_id": "z", "features": {"seed_rank": 1, "signed_direction": -1}}
    following = {"neighbor_id": "a", "features": {"seed_rank": 1, "signed_direction": 1}}
    assert edge_tie(prior) < edge_tie(following)
