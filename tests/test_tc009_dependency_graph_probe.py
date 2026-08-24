from __future__ import annotations

import numpy as np
import pytest

from analysis.tc009_dependency_graph_probe import (
    DependencyGraphProbeError,
    disposition,
    graph_from_doc,
    pagerank,
)


def test_pagerank_path_matches_closed_linear_solution() -> None:
    nodes = ("a", "b", "c")
    edges = (("a", "b", 1), ("b", "c", 1))
    actual, iterations, residual = pagerank(nodes, edges)
    transition = np.asarray([[0, 1, 0], [0.5, 0, 0.5], [0, 1, 0]], dtype=np.float64)
    expected = np.linalg.solve(np.eye(3) - 0.85 * transition.T, np.full(3, 0.15 / 3))
    assert np.allclose([actual[node] for node in nodes], expected, atol=1e-10)
    assert iterations <= 200
    assert residual <= 1e-12


def test_personalized_pagerank_handles_isolated_seed() -> None:
    ranks, _, _ = pagerank(("isolated", "left", "right"), (("left", "right", 1),), personalization={"isolated": 1})
    assert ranks["isolated"] == pytest.approx(1.0)
    assert ranks["left"] == pytest.approx(0.0)
    assert ranks["right"] == pytest.approx(0.0)


def test_personalization_without_mass_rejected() -> None:
    with pytest.raises(DependencyGraphProbeError):
        pagerank(("a",), (), personalization={})


def test_planted_parser_extracts_subjects_and_edges() -> None:
    import en_core_web_sm

    nlp = en_core_web_sm.load(disable=["ner", "textcat"])
    graph = graph_from_doc(nlp("Alice bought apples. Bob slept."))
    assert {"alice", "bob"} <= set(graph["subjects"])
    assert ["alice", "buy", 1] in graph["edges"]
    assert ["apple", "buy", 1] in graph["edges"]


def test_disposition_requires_every_clause() -> None:
    good = {"combined": {"gains": 3, "losses": 1}, "targeted": {"gains": 1, "losses": 1}, "breadth": {"gains": 1, "losses": 0}, "breadth_identity": {"net_identities": 1}, "conversation_nets": {"a": 1, "b": 1, "c": 0, "d": 0}}
    assert disposition({"arm": good})["status"] == "DESCRIPTIVE_POSITIVE_SIGNAL"
    good["breadth_identity"]["net_identities"] = 0
    assert disposition({"arm": good})["status"] == "NO_POSITIVE_SIGNAL"
