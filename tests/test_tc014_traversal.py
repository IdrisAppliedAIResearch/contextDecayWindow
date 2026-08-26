from __future__ import annotations

import numpy as np

from analysis.tc014_traversal import (
    EdgeTrace,
    global_assignment,
    sequential_assignment,
    utility_order,
)
from analysis.tc014_study import arm_disposition, cell_direction


def _matrices() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    utility = np.full((2, 4), -np.inf, dtype=np.float64)
    utility[0, 2:] = (10.0, 9.0)
    utility[1, 2:] = (8.0, 1.0)
    raw = utility.copy()
    similarity = np.eye(4, dtype=np.float64)
    return utility, raw, similarity


def test_global_assignment_improves_on_parent_order_greedy() -> None:
    utility, raw, similarity = _matrices()
    sequential = sequential_assignment((0, 1), utility, raw, (0, 1, 2, 3), similarity)
    global_trace = global_assignment((0, 1), utility, raw, (0, 1, 2, 3), similarity)
    assert sequential.children == (2, 3)
    assert global_trace.children == (3, 2)
    assert sum(global_trace.utility) > sum(sequential.utility)


def test_global_assignment_uses_unique_children_and_optional_dummy() -> None:
    utility, raw, similarity = _matrices()
    utility[1, 2:] = -np.inf
    raw[1, 2:] = -np.inf
    trace = global_assignment((0, 1), utility, raw, (0, 1, 2, 3), similarity)
    assert trace.children == (2,)
    assert trace.no_child == 1


def test_utility_order_changes_packing_without_changing_edges() -> None:
    trace = EdgeTrace(
        parents=(0, 1, 2),
        children=(3, 4, 5),
        parent_for_child=(0, 1, 2),
        utility=(0.2, 0.9, 0.4),
        raw_marginal=(2.0, 9.0, 4.0),
        parent_cosine=(0.5, 0.5, 0.5),
        no_child=0,
    )
    assert utility_order(trace) == (4, 5, 3)
    assert set(utility_order(trace)) == set(trace.children)


def test_sequential_assignment_respects_changed_edge_score() -> None:
    base, raw, similarity = _matrices()
    bound = base.copy()
    bound[0, 2:] = (0.1, 8.0)
    trace = sequential_assignment((0, 1), bound, raw, (0, 1, 2, 3), similarity)
    assert trace.children == (3, 2)


def _cell(combined: int, targeted: int, breadth: int, other: int, identities: int) -> dict:
    return {
        "combined": {"net": combined},
        "targeted": {"net": targeted},
        "breadth": {"net": breadth},
        "other": {"net": other},
        "breadth_identity": {"net": identities},
    }


def test_registered_component_directions_and_dispositions_are_reachable() -> None:
    assert cell_direction(_cell(2, 0, 1, 1, 1)) == "HELPS"
    assert cell_direction(_cell(0, 0, 0, 0, 1)) == "NEUTRAL"
    assert cell_direction(_cell(1, -1, 1, 1, 1)) == "HURTS"
    assert arm_disposition({"16000": "HELPS", "32000": "HELPS"}) == "TRANSFERABLE_HELP"
    assert arm_disposition({"16000": "HELPS", "32000": "HURTS"}) == "BUDGET_SPECIFIC_HELP"
    assert arm_disposition({"16000": "NEUTRAL", "32000": "HURTS"}) == "NO_HELP"
