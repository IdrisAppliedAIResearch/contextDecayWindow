from __future__ import annotations

import numpy as np
import pytest

from analysis.nf005_measurement import paired_counts
from analysis.nf005_mechanism import (
    Candidate,
    NF005MechanismError,
    inherited_score_order,
    own_score_order,
    pack,
    retrieve,
)
from analysis.nf005_study import (
    NF005GateStop,
    disposition,
    enforce_gate_order,
    leakage_gate,
    mechanism_violations,
    registration_identity,
)


def candidate(
    name: str,
    parent: int,
    episode: int,
    turn: int,
    chars: int = 10,
) -> Candidate:
    return Candidate(name, parent, 0, episode, turn, name.ljust(chars, "x"), chars)


def vector(first: float, second: float = 0.0) -> np.ndarray:
    value = np.zeros(1024, dtype=np.float32)
    value[0] = first
    value[1] = second
    return value


def test_turns_inherit_parent_score_but_own_ranking_can_separate_them() -> None:
    turns = (
        candidate("p0-low", 0, 0, 0),
        candidate("p0-high", 0, 0, 1),
        candidate("p1-mid", 1, 1, 0),
    )
    parents = np.vstack((vector(0.6, 0.8), vector(0.8, 0.6)))
    turn_vectors = np.vstack((vector(0.1, 1.0), vector(1.0), vector(0.8, 0.6)))
    assert inherited_score_order(turns, parents, vector(1.0)) == (2, 0, 1)
    assert own_score_order(turns, turn_vectors, vector(1.0)) == (1, 2, 0)


def test_retrieve_changes_only_rank_for_the_primary_turn_contrast() -> None:
    episodes = (
        candidate("episode-0", 0, 0, -1, 12),
        candidate("episode-1", 1, 1, -1, 12),
    )
    turns = (
        candidate("turn-0", 0, 0, 0, 6),
        candidate("turn-1", 0, 0, 1, 6),
        candidate("turn-2", 1, 1, 0, 6),
        candidate("turn-3", 1, 1, 1, 6),
    )
    parent_vectors = np.vstack((vector(0.6, 0.8), vector(0.8, 0.6)))
    turn_vectors = np.vstack(
        (vector(0.1, 1), vector(1), vector(0.8, 0.6), vector(0.2, 1))
    )
    result = retrieve(
        episodes, turns, parent_vectors, turn_vectors, vector(1), budget=12
    )
    inherited = result["E_EPISODE_RANK_TURN_PACK"]
    own = result["T_TURN_RANK_TURN_PACK"]
    assert set(inherited.order) == set(own.order) == {turn.identity for turn in turns}
    assert inherited.selected != own.selected


def test_skip_on_overflow_continues_and_over_budget_candidate_remains() -> None:
    candidates = (
        candidate("first", 0, 0, 0, 8),
        candidate("impossible", 1, 1, 0, 15),
        candidate("ok", 2, 2, 0, 2),
    )
    delivery = pack(candidates, (0, 1, 2), 10)
    assert delivery.order == ("first", "impossible", "ok")
    assert delivery.selected == ("first", "ok")
    assert delivery.packed_chars == 10


def test_pack_rejects_cost_drift_and_incomplete_order() -> None:
    bad = Candidate("bad", 0, 0, 0, 0, "abc", 2)
    with pytest.raises(NF005MechanismError, match="character cost"):
        pack((bad,), (0,), 10)
    with pytest.raises(NF005MechanismError, match="permutation"):
        pack((candidate("a", 0, 0, 0),), (), 10)


def test_non_finite_and_zero_vectors_fail_closed() -> None:
    candidates = (candidate("a", 0, 0, 0),)
    with pytest.raises(NF005MechanismError, match="finite and non-zero"):
        own_score_order(candidates, np.zeros((1, 1024)), vector(1))
    bad_query = vector(1)
    bad_query[5] = np.nan
    with pytest.raises(NF005MechanismError, match="finite and non-zero"):
        own_score_order(candidates, np.vstack((vector(1),)), bad_query)


def comparison_rows(gains: int, losses: int, ties: int) -> list[dict]:
    rows = []
    for baseline, treatment, count in (
        (False, True, gains),
        (True, False, losses),
        (True, True, ties),
    ):
        for _ in range(count):
            rows.append(
                {
                    "arms": {
                        "E_EPISODE_RANK_TURN_PACK": {"any_target": baseline},
                        "T_TURN_RANK_TURN_PACK": {"any_target": treatment},
                    }
                }
            )
    return rows


@pytest.mark.parametrize(
    ("gains", "losses", "p_value"),
    ((6, 0, 0.015625), (4, 1, 0.1875), (1, 1, 0.75)),
)
def test_registered_discordant_configurations_are_reachable(
    gains: int, losses: int, p_value: float
) -> None:
    result = paired_counts(comparison_rows(gains, losses, 10))
    assert result["gains"] == gains
    assert result["losses"] == losses
    assert result["one_sided_exact_p"] == p_value


@pytest.mark.parametrize(
    ("gains", "losses", "expected"),
    (
        (6, 0, "INFORMATION_DILUTION_SUPPORTED"),
        (4, 1, "CARRIES_SIGNAL"),
        (1, 1, "NOT_SUPPORTED"),
    ),
)
def test_each_registered_disposition_is_applied_once(
    gains: int, losses: int, expected: str
) -> None:
    assert disposition(paired_counts(comparison_rows(gains, losses, 10))) == expected


def test_registration_identity_precedes_treatment_vector_access() -> None:
    result = registration_identity()
    assert result["pass"]
    assert result["treatment_vectors_accessed"] is False


def test_mechanism_purity_rejects_both_planted_leaks() -> None:
    assert leakage_gate()["pass"]
    assert mechanism_violations(
        "from analysis.nf005_measurement import paired_counts\n"
    )
    assert mechanism_violations("value = candidate.has_answer\n")


@pytest.mark.parametrize("failure_index", range(7))
def test_each_preflight_failure_keeps_outcome_unreachable(
    failure_index: int,
) -> None:
    trace: list[str] = []

    def gate(index: int):
        def run() -> dict[str, bool]:
            trace.append(f"G{index}")
            return {"pass": index != failure_index}

        return run

    def outcome() -> None:
        trace.append("G7")

    with pytest.raises(NF005GateStop) as stopped:
        enforce_gate_order(
            tuple((f"G{index}", gate(index)) for index in range(7)), outcome
        )
    assert stopped.value.gate == f"G{failure_index}"
    assert "G7" not in trace
