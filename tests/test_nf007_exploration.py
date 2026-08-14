from __future__ import annotations

import numpy as np

from analysis.nf007_exploration import (
    ART_LABEL,
    CLUSTER_COUNT,
    MONETARY_LABEL,
    cluster_parents,
    occupancy_rows,
    reachability_disposition,
)


def _row(cluster: int, art: int, monetary: int) -> dict:
    return {
        "cluster": cluster,
        "domain_counts": {ART_LABEL: art, MONETARY_LABEL: monetary},
    }


def test_reachability_requires_an_art_cluster_without_monetary() -> None:
    failed = [_row(index, int(index == 0), int(index == 0)) for index in range(16)]
    passed = [_row(index, int(index == 0), 0) for index in range(16)]

    assert reachability_disposition(failed)["status"] == "NO_CLUSTER_REACHABILITY"
    assert reachability_disposition(passed)["status"] == "CLUSTER_FLOOR_REACHABLE"


def test_historical_short_labels_do_not_match_the_frozen_vocabulary() -> None:
    rows = [
        {"cluster": index, "domain_counts": {"art": 1, "monetary": 0}}
        for index in range(CLUSTER_COUNT)
    ]

    result = reachability_disposition(rows)

    assert result["art_occupied_clusters"] == []
    assert result["evaluation_vocabulary"] == {
        "art": "renaissance_art",
        "monetary": "monetary_policy",
    }


def test_cluster_assignments_ignore_domain_labels() -> None:
    vectors = np.eye(CLUSTER_COUNT + 1, 1024, dtype=np.float32)
    first = [
        {"embedding": vector.tobytes(), "ground_truth_domain": "art"}
        for vector in vectors
    ]
    second = [
        {"embedding": vector.tobytes(), "ground_truth_domain": "monetary"}
        for vector in vectors
    ]

    assert np.array_equal(cluster_parents(first), cluster_parents(second))


def test_occupancy_reports_empty_clusters_and_blank_labels() -> None:
    parents = [
        {"turn_number": 1},
        {"turn_number": 2},
    ]
    statements = [
        {"role": "user", "ground_truth_domain": "art"},
        {"role": "assistant", "ground_truth_domain": ""},
    ]
    assignments = np.array([0, 1], dtype=np.int64)

    rows = occupancy_rows(parents, statements, assignments, assignments)

    assert len(rows) == CLUSTER_COUNT
    assert rows[0]["domain_counts"] == {"": 0, "art": 1}
    assert rows[1]["domain_counts"] == {"": 1, "art": 0}
    assert rows[2]["parent_members"] == 0
    assert rows[2]["statement_members"] == 0
