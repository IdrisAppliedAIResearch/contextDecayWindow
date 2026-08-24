from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from analysis.tc008_session_spread import (
    SESSION_LAMBDA,
    session_assignments,
    session_spread_order,
)
from analysis.tc008_exploration import leakage_violations


def episode(index: int, session: str, session_order: int, vector: np.ndarray):
    identifier = f"e{index}"
    return SimpleNamespace(
        identity=identifier,
        pair=SimpleNamespace(session_id=session, session_order=session_order),
        record={
            "id": identifier,
            "turn_number": index + 1,
            "user_message": f"u{index}",
            "assistant_message": f"a{index}",
            "embedding": vector.astype(np.float32),
            "ground_truth_domain": "test",
        },
    )


def vector(x: float, y: float = 0.0) -> np.ndarray:
    value = np.zeros(1024, dtype=np.float32)
    value[0], value[1] = x, y
    return value


def test_assignments_follow_source_session_order() -> None:
    episodes = (
        episode(0, "late", 3, vector(1)),
        episode(1, "early", 1, vector(1)),
        episode(2, "late", 3, vector(1)),
    )
    assignments, sessions = session_assignments(episodes)
    assert sessions == ("early", "late")
    assert assignments.tolist() == [1, 0, 1]


def test_session_bonus_promotes_a_relevant_new_session() -> None:
    episodes = (
        episode(0, "s1", 0, vector(1.0, 0.0)),
        episode(1, "s1", 0, vector(.99, .01)),
        episode(2, "s2", 1, vector(.95, .05)),
    )
    result = session_spread_order(episodes, vector(1.0, 0.0))
    assert result.order[:3] == (0, 2, 1)
    assert result.result.steps[1].objective_gain > result.result.steps[2].objective_gain


def test_one_session_receives_exactly_one_novelty_bonus() -> None:
    episodes = tuple(episode(i, "only", 0, vector(1.0, i / 100)) for i in range(4))
    result = session_spread_order(episodes, vector(1.0, 0.0))
    bonuses = [
        round(step.objective_gain - max(step.relevance, 0.0), 8)
        for step in result.result.steps
    ]
    assert bonuses.count(SESSION_LAMBDA) == 1
    assert bonuses.count(0.0) == 3


def test_zero_lambda_orders_positive_relevance_descending() -> None:
    episodes = (
        episode(0, "s1", 0, vector(.7, .3)),
        episode(1, "s2", 1, vector(.9, .1)),
        episode(2, "s3", 2, vector(.8, .2)),
    )
    result = session_spread_order(episodes, vector(1.0, 0.0), lambda_=0.0)
    assert result.order == (1, 2, 0)


def test_leakage_audit_catches_planted_measurement_import() -> None:
    assert not leakage_violations("from episodic import select\n")
    assert leakage_violations("from measurement.evidence_key import q_facts_key\n")
