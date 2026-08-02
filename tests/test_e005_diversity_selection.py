from pathlib import Path

import numpy as np
import pytest

from src.analysis.e005_diversity_selection import (
    A0_FACT_COUNT,
    BUDGET_CHARS,
    KILL_BAR,
    ORACLE_CHARS,
    ORACLE_EPISODES,
    committed_targeted_items,
    leakage_audit,
    targeted_key,
)
from src.memory.context_matched_stm import render_stm_payload
from src.retrieval_bakeoff.config import EMBEDDING_DIMENSION
from src.retrieval_mechanism_ledger.e005 import (
    CLUSTER_COUNTS,
    COST_EXPONENTS,
    LAMBDA_VALUES,
    ClusterDiversitySelector,
    FacilityLocationSelector,
    MmrSelector,
    additive_weight,
    assert_mechanism_path_allowed,
    build_selectors,
    configuration_id,
    deterministic_clusters,
    eligible_candidates,
    select,
    similarity_matrix,
    wrapper_chars,
)


def _vector(*indices: int) -> np.ndarray:
    value = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    for index in indices:
        value[index] = 1.0
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


def _fixture_pool() -> list[dict]:
    return [
        _candidate("a", 1, _vector(0)),
        _candidate("b", 2, _vector(0, 1)),
        _candidate("c", 3, _vector(5)),
    ]


def test_additive_weight_reproduces_the_exact_rendered_payload() -> None:
    candidates = _fixture_pool()

    payload = render_stm_payload([], candidates)

    assert len(payload) == wrapper_chars() + sum(
        additive_weight(candidate) for candidate in candidates
    )


def test_mmr_first_pick_is_the_most_relevant_candidate() -> None:
    candidates = _fixture_pool()
    selector = MmrSelector(
        lambda_=0.5,
        similarity=similarity_matrix(candidates),
    )

    result = select(
        candidates=candidates,
        query_embedding=_vector(5),
        selector=selector,
        budget_chars=BUDGET_CHARS,
    )

    assert result.steps[0].candidate_id == "c"


def test_mmr_penalty_defers_a_near_duplicate_of_an_already_selected_pick() -> None:
    candidates = [
        _candidate("query_twin", 1, _vector(0)),
        _candidate("near_duplicate", 2, _vector(0)),
        _candidate("orthogonal", 3, _vector(0, 7)),
    ]
    similarity = similarity_matrix(candidates)

    relevance_only = select(
        candidates=candidates,
        query_embedding=_vector(0),
        selector=MmrSelector(lambda_=1.0, similarity=similarity),
        budget_chars=BUDGET_CHARS,
    )
    diverse = select(
        candidates=candidates,
        query_embedding=_vector(0),
        selector=MmrSelector(lambda_=0.0, similarity=similarity),
        budget_chars=BUDGET_CHARS,
    )

    assert relevance_only.selected_ids[1] == "near_duplicate"
    assert diverse.selected_ids[1] == "orthogonal"


def test_facility_location_objective_is_monotone_and_submodular() -> None:
    candidates = _fixture_pool()
    selector = FacilityLocationSelector(
        cost_exponent=0.0,
        similarity=similarity_matrix(candidates),
    )
    relevance = np.zeros(len(candidates))
    costs = np.ones(len(candidates))

    empty = selector.objective_gains(relevance, [], costs)
    after_first = selector.objective_gains(relevance, [0], costs)

    assert selector.objective([], relevance) == 0.0
    assert selector.objective([0], relevance) > 0.0
    assert selector.objective([0, 1], relevance) >= selector.objective(
        [0],
        relevance,
    )
    assert np.all(after_first <= empty + 1e-9)


def test_cluster_diversity_gain_drops_once_a_cluster_is_covered() -> None:
    candidates = _fixture_pool()
    assignments = np.array([0, 0, 1])
    selector = ClusterDiversitySelector(
        lambda_=1.0,
        cost_exponent=0.0,
        assignments=assignments,
        cluster_count=2,
    )
    relevance = np.array([0.5, 0.5, 0.5])
    costs = np.ones(len(candidates))

    gains = selector.objective_gains(relevance, [0], costs)

    assert gains[1] == pytest.approx(0.5)
    assert gains[2] == pytest.approx(1.5)


def test_clustering_is_deterministic_and_free_of_random_state() -> None:
    candidates = [
        _candidate(name, index, _vector(index))
        for index, name in enumerate(["a", "b", "c", "d", "e"])
    ]

    first = deterministic_clusters(candidates, 3)
    second = deterministic_clusters(candidates, 3)

    assert np.array_equal(first, second)
    assert len(set(first.tolist())) <= 3


def test_clustering_degenerates_to_singletons_when_k_exceeds_the_pool() -> None:
    candidates = _fixture_pool()

    assignments = deterministic_clusters(candidates, 16)

    assert assignments.tolist() == [0, 1, 2]


def test_selection_never_exceeds_the_enforced_budget() -> None:
    large = _candidate("large", 1, _vector(0), assistant="x" * 4_000)
    small = _candidate("small", 2, _vector(0, 1))
    budget = len(render_stm_payload([], [small]))
    candidates = [large, small]

    result = select(
        candidates=candidates,
        query_embedding=_vector(0),
        selector=MmrSelector(
            lambda_=1.0,
            similarity=similarity_matrix(candidates),
        ),
        budget_chars=budget,
    )

    assert result.selected_ids == ("small",)
    assert result.serialized_chars == budget
    assert "large" in result.skipped_ids


def test_oversized_candidate_is_skipped_without_stopping_the_greedy_loop() -> None:
    candidates = [
        _candidate("huge", 1, _vector(0), assistant="x" * 4_000),
        _candidate("fits_a", 2, _vector(0)),
        _candidate("fits_b", 3, _vector(0)),
    ]
    budget = len(
        render_stm_payload([], [candidates[1], candidates[2]])
    )

    result = select(
        candidates=candidates,
        query_embedding=_vector(0),
        selector=MmrSelector(
            lambda_=1.0,
            similarity=similarity_matrix(candidates),
        ),
        budget_chars=budget,
    )

    assert set(result.selected_ids) == {"fits_a", "fits_b"}


def test_selection_is_deterministic_across_repeated_runs() -> None:
    candidates = _fixture_pool()
    similarity = similarity_matrix(candidates)

    runs = [
        select(
            candidates=candidates,
            query_embedding=_vector(0),
            selector=MmrSelector(lambda_=0.5, similarity=similarity),
            budget_chars=BUDGET_CHARS,
        )
        for _ in range(3)
    ]

    assert len({run.payload_sha256 for run in runs}) == 1
    assert len({run.selected_ids for run in runs}) == 1


def test_optimality_bound_is_absent_for_mmr_and_present_for_submodular_arms() -> None:
    candidates = _fixture_pool()
    similarity = similarity_matrix(candidates)

    mmr = select(
        candidates=candidates,
        query_embedding=_vector(0),
        selector=MmrSelector(lambda_=0.5, similarity=similarity),
        budget_chars=BUDGET_CHARS,
    )
    facility = select(
        candidates=candidates,
        query_embedding=_vector(0),
        selector=FacilityLocationSelector(
            cost_exponent=0.0,
            similarity=similarity,
        ),
        budget_chars=BUDGET_CHARS,
    )

    assert mmr.objective_value is None
    assert mmr.optimality_bound is None
    assert facility.optimality_bound >= facility.objective_value


def test_registered_sweep_covers_every_committed_configuration() -> None:
    selectors = build_selectors(_fixture_pool())
    identifiers = [config_id for config_id, _selector in selectors]

    assert len(LAMBDA_VALUES) == 11
    assert COST_EXPONENTS == (0.0, 0.5, 1.0)
    assert CLUSTER_COUNTS == (2, 4, 8, 16)
    assert len(identifiers) == 11 + 3 + 11 * 3 * 4
    assert len(set(identifiers)) == len(identifiers)
    assert identifiers[0] == configuration_id("A1", lambda_=0.0)
    assert "A2_r0.5" in identifiers
    assert "A3_l0.5_r0.0_k04" in identifiers


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


def test_mechanism_import_graph_and_literals_pass_the_leakage_audit() -> None:
    result = leakage_audit()

    assert result["status"] == "PASS"
    assert result["forbidden_imports"] == []
    assert result["forbidden_literals"] == []
    assert result["planted_forbidden_path_rejected"] is True


def test_kill_bar_sits_one_item_above_the_committed_a0_baseline() -> None:
    assert A0_FACT_COUNT == 6
    assert KILL_BAR == 7


def test_no_regression_numerator_and_denominator_share_one_unit() -> None:
    """Q7 and Q10 both probe turn 118 and share two items.

    Keying availability on (turn, item) collapses those rows while the
    required count still counts them, capping preservation at 14 of 16 and
    making the gate unpassable. The question-scoped key must restore parity.
    """
    committed = committed_targeted_items()
    available = [row for row in committed if row["committed_available"]]

    required = len(available)
    naive_keys = {(int(row["turn"]), str(row["item"])) for row in available}
    scoped_keys = {targeted_key(row) for row in available}

    assert required == 16
    assert len(naive_keys) == 14
    assert len(scoped_keys) == required


def test_carried_oracle_matches_the_ar_001_committed_result() -> None:
    assert ORACLE_CHARS == 5_455
    assert [turn for _episode, turn in ORACLE_EPISODES] == [
        90,
        112,
        113,
        116,
        118,
    ]
