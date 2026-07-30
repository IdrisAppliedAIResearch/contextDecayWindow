from pathlib import Path

import numpy as np
import pytest

from src.analysis.e002_segmented_query import (
    BUDGET_CHARS,
    leakage_audit,
    load_candidates,
    load_queries,
    same_budget_baseline,
)
from src.memory.context_matched_stm import render_stm_payload
from src.retrieval_bakeoff.config import EMBEDDING_DIMENSION
from src.retrieval_mechanism_ledger.e002 import (
    assert_mechanism_path_allowed,
    eligible_candidates,
    exhaustive_configurations,
    retrieve_segmented,
    segment_query,
)


def _vector(index: int, second: int | None = None) -> np.ndarray:
    value = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    value[index] = 1.0
    if second is not None:
        value[second] = 1.0
    return value


def _candidate(
    candidate_id: str,
    turn: int,
    embedding: np.ndarray,
    *,
    assistant: str = "short",
) -> dict:
    return {
        "id": candidate_id,
        "turn_number": turn,
        "user_message": f"user {candidate_id}",
        "assistant_message": assistant,
        "embedding": embedding,
        "ground_truth_domain": "fixture",
    }


def test_every_boundary_offset_preserves_each_query_unit_once() -> None:
    query = "one two three four five"

    for width in range(1, 6):
        for offset in range(width):
            segments = segment_query(
                query,
                segment_width=width,
                boundary_offset=offset,
            )
            assert " ".join(segment.text for segment in segments) == query


def test_exhaustive_sweep_covers_all_width_offset_budget_cells() -> None:
    configurations = exhaustive_configurations("one two three")

    assert len(configurations) == 12
    assert configurations[0] == (1, 0, 1)
    assert configurations[-1] == (3, 2, 2)


def test_rank_round_robin_deduplicates_repeated_segment_hits() -> None:
    candidates = [
        _candidate("a", 1, _vector(0)),
        _candidate("b", 2, _vector(1)),
        _candidate("c", 3, _vector(0, 1)),
    ]
    embeddings = {"alpha": _vector(0), "beta": _vector(1)}

    result = retrieve_segmented(
        query="alpha beta",
        candidates=candidates,
        segment_width=1,
        boundary_offset=0,
        per_segment_budget=2,
        budget_chars=10_000,
        embed=embeddings.__getitem__,
    )

    assert result.selected_ids == ("a", "b", "c")
    assert [hit.outcome for hit in result.hits] == [
        "selected",
        "selected",
        "selected",
        "duplicate",
    ]


def test_oversized_candidate_is_skipped_and_later_candidate_can_fit() -> None:
    large = _candidate("large", 1, _vector(0), assistant="x" * 2_000)
    small = _candidate("small", 2, _vector(0, 1))
    budget = len(render_stm_payload([], [small]))

    result = retrieve_segmented(
        query="alpha",
        candidates=[large, small],
        segment_width=1,
        boundary_offset=0,
        per_segment_budget=2,
        budget_chars=budget,
        embed=lambda _text: _vector(0),
    )

    assert result.selected_ids == ("small",)
    assert [hit.outcome for hit in result.hits] == [
        "budget_skip",
        "selected",
    ]
    assert result.serialized_chars == budget


def test_temporal_filter_excludes_probe_and_future_turns() -> None:
    candidates = [
        _candidate("old", 9, _vector(0)),
        _candidate("probe", 10, _vector(0)),
        _candidate("future", 11, _vector(0)),
    ]

    eligible = eligible_candidates(candidates, probe_turn=10)

    assert [candidate["id"] for candidate in eligible] == ["old"]


def test_planted_measurement_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="measurement boundary"):
        assert_mechanism_path_allowed(
            Path("experiments/study_009/q_facts_key.md")
        )


def test_mechanism_import_graph_and_planted_violation_pass_audit() -> None:
    result = leakage_audit()

    assert result["status"] == "PASS"
    assert result["forbidden_imports"] == []
    assert result["planted_forbidden_path_rejected"] is True


def test_same_budget_baseline_is_exact_and_distinct_from_historical_hurdle() -> None:
    result = same_budget_baseline(load_queries(), load_candidates())

    assert result["budget_chars"] == BUDGET_CHARS
    assert result["serialized_chars"] == 31_946
    assert result["selected_episode_count"] == 8
    assert result["fact_count"] == 6
    assert result["domain_count"] == 3
