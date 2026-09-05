from __future__ import annotations

from analysis.da002_provenance import order_with_provenance
from analysis.nf004_mechanism import Candidate


def _nodes() -> list[Candidate]:
    return [
        Candidate("a0", "a", 0, 0, "a0", 2),
        Candidate("a1", "a", 0, 1, "a1", 2),
        Candidate("a2", "a", 0, 2, "a2", 2),
        Candidate("b0", "b", 1, 0, "b0", 2),
        Candidate("b1", "b", 1, 1, "b1", 2),
    ]


def test_first_emitter_gets_previous_next_provenance() -> None:
    order, provenance = order_with_provenance(_nodes(), (1, 4, 3, 0, 2), "TEMPORAL", 1)
    assert order == (1, 0, 2, 4, 3)
    assert provenance[0]["relation"] == "previous"
    assert provenance[2]["relation"] == "next"
    assert provenance[0]["seed_direct_rank"] == 1


def test_deduplication_preserves_first_emitter_credit() -> None:
    _, provenance = order_with_provenance(_nodes(), (1, 2, 4, 3, 0), "TEMPORAL", 2)
    assert provenance[0]["seed_index"] == 1
    assert provenance[2]["seed_index"] == 1
    assert 1 not in provenance


def test_event_distance_and_direction_are_exact() -> None:
    _, provenance = order_with_provenance(_nodes(), (0, 4, 3, 1, 2), "EVENT", 1)
    assert provenance[2]["graph_distance"] == 2
    assert provenance[2]["relation"] == "deep_next"


def test_zero_seed_order_is_direct_and_has_no_provenance() -> None:
    direct = (4, 1, 3, 0, 2)
    order, provenance = order_with_provenance(_nodes(), direct, "EVENT", 0)
    assert order == direct
    assert not provenance
