from __future__ import annotations

from analysis.da001_linked_context import linked_order
from analysis.nf004_mechanism import Candidate


def _candidates() -> list[Candidate]:
    return [
        Candidate("a0", "a", 0, 0, "a0", 2),
        Candidate("a1", "a", 0, 1, "a1", 2),
        Candidate("a2", "a", 0, 2, "a2", 2),
        Candidate("b0", "b", 1, 0, "b0", 2),
        Candidate("b1", "b", 1, 1, "b1", 2),
    ]


def test_temporal_traversal_stays_in_session_and_preserves_suffix() -> None:
    order, linked = linked_order(_candidates(), (1, 4, 3, 0, 2), "TEMPORAL", 1)
    assert order == (1, 0, 2, 4, 3)
    assert linked == frozenset({0, 2})


def test_event_traversal_uses_distance_then_source_order() -> None:
    order, linked = linked_order(_candidates(), (1, 4, 3, 0, 2), "EVENT", 1)
    assert order == (1, 0, 2, 4, 3)
    assert linked == frozenset({0, 2})


def test_multiple_seeds_deduplicate_linked_nodes() -> None:
    order, linked = linked_order(_candidates(), (1, 4, 3, 0, 2), "TEMPORAL", 2)
    assert order == (1, 0, 2, 4, 3)
    assert linked == frozenset({0, 2, 3})
    assert len(order) == len(set(order)) == 5


def test_singleton_session_has_no_cross_session_neighbor() -> None:
    candidates = _candidates() + [Candidate("c0", "c", 2, 0, "c0", 2)]
    order, linked = linked_order(candidates, (5, 1, 4, 3, 0, 2), "TEMPORAL", 1)
    assert order == (5, 1, 4, 3, 0, 2)
    assert not linked


def test_zero_seed_traversal_is_direct_control() -> None:
    direct = (4, 1, 3, 0, 2)
    order, linked = linked_order(_candidates(), direct, "EVENT", 0)
    assert order == direct
    assert not linked
