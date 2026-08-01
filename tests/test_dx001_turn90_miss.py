import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from src.analysis.dx001_turn90_miss import (
    CONFIGURATION_COUNT,
    PRIMARY_CONFIGURATION,
    TARGET_ID,
    TARGET_TURN,
    _attribute,
    _cosine_ranks,
    _target_index,
    _walk,
)
from src.analysis.e005_diversity_selection import (
    BUDGET_CHARS,
    COMPONENT_ROOT,
    ORACLE_EPISODES,
    PRIMARY_POOL,
    REPO_ROOT,
)
from src.retrieval_bakeoff.config import EMBEDDING_DIMENSION
from src.retrieval_mechanism_ledger.e005 import (
    ClusterDiversitySelector,
    additive_weight,
    deterministic_clusters,
    relevance_vector,
    select,
)


E005_ARTIFACTS = COMPONENT_ROOT / "artifacts" / "e005"
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e005.py"


def _vector(*indices: int) -> np.ndarray:
    value = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    for index in indices:
        value[index] = 1.0
    return value


def _candidate(candidate_id: str, turn: int, embedding: np.ndarray) -> dict:
    return {
        "id": candidate_id,
        "turn_number": turn,
        "user_message": f"user {candidate_id}",
        "assistant_message": "body " * turn,
        "embedding": embedding,
        "ground_truth_domain": "fixture",
    }


def _fixture_pool() -> list[dict]:
    return [
        _candidate("a", 1, _vector(0)),
        _candidate("b", 2, _vector(0, 1)),
        _candidate("c", 3, _vector(5)),
        _candidate("d", 4, _vector(2, 3)),
        _candidate("e", 5, _vector(7)),
    ]


def _attribution_inputs(**overrides) -> dict:
    base = {
        "census": {"selecting_turn90": 0},
        "clusters": {
            "collision_at_primary_k": False,
            "rows": [{"k": 16, "cluster_size": 20}],
        },
        "cost": {"target_cheaper_than_median": False},
        "trace": {
            "steps": 3,
            "cluster_novel_steps": [1, 2, 3],
            "counterfactual_wins_any_step": True,
            "target_relevance_term": 0.5,
            "target_lambda_term": 0.1,
            "target_ever_affordable": True,
        },
        "sensitivity": {"best_rank_by_r": {"0.0": 5, "0.5": 5, "1.0": 5}},
        "termination": {
            "terminated_on": "candidates",
            "remaining_chars": 400,
            "affordable_unselected_at_end": 2,
            "target_affordable_at_end": True,
        },
    }
    base.update(overrides)
    return base


def test_walk_reproduces_the_select_loop_step_for_step() -> None:
    """The trace is only evidence if it mirrors the mechanism exactly."""
    pool = _fixture_pool()
    query = _vector(0)
    selector = ClusterDiversitySelector(
        lambda_=0.1,
        cost_exponent=0.0,
        assignments=deterministic_clusters(pool, 2),
        cluster_count=2,
    )
    relevance = relevance_vector(query, pool)
    costs = np.array(
        [float(_cost_of(pool, index)) for index in range(len(pool))],
        dtype=np.float64,
    )

    result = select(
        candidates=pool,
        query_embedding=query,
        selector=selector,
        budget_chars=BUDGET_CHARS,
    )
    walk = _walk(
        pool=pool,
        selector=selector,
        target_index=0,
        relevance=relevance,
        costs=costs,
    )

    assert [row["winner_turn"] for row in walk] == list(
        result.selected_source_turns
    )
    assert [round(row["winner_scaled_gain"], 9) for row in walk] == [
        round(step.scaled_gain, 9) for step in result.steps
    ]


def _cost_of(pool, index: int) -> int:
    return additive_weight(pool[index])


def test_walk_records_the_target_gap_at_every_step() -> None:
    pool = _fixture_pool()
    query = _vector(0)
    selector = ClusterDiversitySelector(
        lambda_=0.1,
        cost_exponent=0.0,
        assignments=deterministic_clusters(pool, 2),
        cluster_count=2,
    )
    relevance = relevance_vector(query, pool)
    costs = np.array(
        [float(_cost_of(pool, index)) for index in range(len(pool))],
        dtype=np.float64,
    )

    walk = _walk(
        pool=pool,
        selector=selector,
        target_index=4,
        relevance=relevance,
        costs=costs,
    )

    assert all(row["gap_to_winner"] >= 0.0 for row in walk)
    winner_steps = [row["step"] for row in walk if row["winner_index"] == 4]
    for row in walk:
        if row["step"] in winner_steps:
            assert row["gap_to_winner"] == pytest.approx(0.0)


def test_target_index_rejects_a_pool_without_the_target() -> None:
    with pytest.raises(AssertionError):
        _target_index(_fixture_pool())


def test_cosine_ranks_are_a_permutation_with_the_best_first() -> None:
    pool = _fixture_pool()
    relevance = relevance_vector(_vector(0), pool)

    ranks = _cosine_ranks(pool, relevance)

    assert sorted(ranks) == list(range(1, len(pool) + 1))
    assert ranks[0] == 1


def test_unresolved_is_a_permitted_attribution() -> None:
    """D.3 makes 'unresolved' preferable to a fix built on a guess."""
    attribution = _attribute(
        **_attribution_inputs(
            trace={
                "steps": 3,
                "cluster_novel_steps": [1, 2, 3],
                "counterfactual_wins_any_step": True,
                "target_relevance_term": 0.5,
                "target_lambda_term": 0.1,
                "target_ever_affordable": True,
            }
        )
    )

    assert attribution["verdict"] == "UNRESOLVED"
    assert attribution["distinguishable"] is False


def test_m3_requires_the_joint_counterfactual_to_fail() -> None:
    """A relevance floor is only established if paying diversity in full loses."""
    still_wins = _attribute(
        **_attribution_inputs(
            trace={
                "steps": 3,
                "cluster_novel_steps": [],
                "counterfactual_wins_any_step": True,
                "target_relevance_term": 0.0,
                "target_lambda_term": 0.1,
                "target_ever_affordable": True,
            }
        )
    )
    never_wins = _attribute(
        **_attribution_inputs(
            trace={
                "steps": 3,
                "cluster_novel_steps": [],
                "counterfactual_wins_any_step": False,
                "target_relevance_term": 0.0,
                "target_lambda_term": 0.1,
                "target_ever_affordable": True,
            }
        )
    )

    assert still_wins["M3_relevance_floor"]["fires"] is False
    assert never_wins["M3_relevance_floor"]["fires"] is True


def test_m4_requires_termination_on_budget() -> None:
    on_candidates = _attribute(**_attribution_inputs())
    on_budget = _attribute(
        **_attribution_inputs(
            termination={
                "terminated_on": "budget",
                "remaining_chars": 431,
                "affordable_unselected_at_end": 0,
                "target_affordable_at_end": False,
            }
        )
    )

    assert on_candidates["M4_budget_exhaustion"]["fires"] is False
    assert on_budget["M4_budget_exhaustion"]["fires"] is True


def test_m2_fires_only_when_r_moves_the_target() -> None:
    inert = _attribute(**_attribution_inputs())
    active = _attribute(
        **_attribution_inputs(
            sensitivity={"best_rank_by_r": {"0.0": 5, "0.5": 2, "1.0": 2}}
        )
    )

    assert inert["M2_cost_discount"]["fires"] is False
    assert active["M2_cost_discount"]["fires"] is True


def test_target_is_the_deepest_oracle_episode() -> None:
    assert (TARGET_ID, TARGET_TURN) in ORACLE_EPISODES


def test_census_denominator_matches_the_registered_configuration_count() -> None:
    rows = [
        json.loads(line)
        for line in (E005_ARTIFACTS / "raw" / "q11_selection.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    primary = [row for row in rows if row["pool"] == PRIMARY_POOL]

    assert len(primary) == CONFIGURATION_COUNT
    assert PRIMARY_CONFIGURATION in {row["configuration_id"] for row in primary}


def test_dx001_does_not_modify_the_e005_mechanism() -> None:
    """B7: E005's committed results are not re-scored under a changed mechanism."""
    committed = json.loads(
        (E005_ARTIFACTS / "source_integrity.json").read_text(encoding="utf-8")
    )["after"]
    key = next(name for name in committed if name.endswith("e005.py"))

    digest = hashlib.sha256(MECHANISM_SOURCE.read_bytes()).hexdigest()

    assert digest == committed[key]


def test_diagnostic_source_reads_no_rubric_artifact_path() -> None:
    source = Path(
        REPO_ROOT / "src" / "analysis" / "dx001_turn90_miss.py"
    ).read_text(encoding="utf-8")

    assert "q_facts_key" not in source
