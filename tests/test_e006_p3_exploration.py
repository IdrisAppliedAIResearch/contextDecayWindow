from __future__ import annotations

from src.analysis.e006_p3_exploration import (
    degenerate_traces,
    mechanism_seal,
    run_arm_cells,
)


def test_exploration_grid_has_equal_registered_candidate_quotas() -> None:
    records, _inputs, _graph = run_arm_cells()

    assert len(records) == 24
    assert all(
        len(record["ranked_seen_content_sha256"])
        == record["m"] * (record["D"] + 1)
        for record in records
    )


def test_d0_is_identical_across_all_three_arms() -> None:
    records, _inputs, _graph = run_arm_cells()

    for per_step in (3, 5):
        cells = [
            record
            for record in records
            if record["D"] == 0 and record["m"] == per_step
        ]
        assert len({tuple(cell["ranked_seen_content_sha256"]) for cell in cells}) == 1


def test_all_registered_degenerate_states_are_executed() -> None:
    traces = degenerate_traces()

    assert set(traces) == {
        "empty_frontier_adjacency",
        "all_zero_association",
        "all_negative_association",
        "repeated_frontier",
        "graph_cycle",
        "query_only_fallback",
        "constant_ranking",
        "exhausted_unseen_candidates",
    }
    assert traces["repeated_frontier"]["all_disjoint"] is True
    assert traces["exhausted_unseen_candidates"]["rejected_before_run"]


def test_exploration_mechanism_seal_passes() -> None:
    assert mechanism_seal()["status"] == "PASS"
