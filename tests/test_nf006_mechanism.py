from __future__ import annotations

import numpy as np

from analysis.nf006_mechanism import (
    build_statement_candidates,
    parent_content_identity,
    render_statement_element,
    render_statement_payload,
    select_statements,
    split_assistant_statements,
    statement_additive_weight,
    statement_wrapper_chars,
)
from retrieval_bakeoff.config import EMBEDDING_DIMENSION


def _vector(axis: int) -> np.ndarray:
    value = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    value[axis] = 1.0
    return value


def _parent(identifier: str = "generated-id") -> dict:
    return {
        "id": identifier,
        "turn_number": 7,
        "user_message": "What changed?",
        "assistant_message": "1. First fact.\n\n2. Second fact.",
        "embedding": _vector(0),
        "ground_truth_domain": "domain",
    }


def test_statement_identity_ignores_generated_parent_id() -> None:
    first = build_statement_candidates((_parent("one"),))
    second = build_statement_candidates((_parent("two"),))
    assert parent_content_identity(_parent("one")) == parent_content_identity(
        _parent("two")
    )
    assert [row["id"] for row in first] == [row["id"] for row in second]


def test_locked_splitter_matches_numbered_and_risk_behavior() -> None:
    text = "Intro\n\n1. First.\n\n2. Second.\n\n(Risk: Low)"
    assert split_assistant_statements(text) == [
        "Intro",
        "1. First.",
        "2. Second.\n\n(Risk: Low)",
    ]


def test_statement_rendering_has_metadata_and_exactly_one_nonempty_role() -> None:
    rows = build_statement_candidates((_parent(),))
    user = render_statement_element(rows[0])
    assistant = render_statement_element(rows[1])
    assert 'turn="7" parent="' in user
    assert 'role="user" ordinal="0"' in user
    assert "<user>What changed?</user>" in user
    assert "<assistant></assistant>" in user
    assert 'role="assistant" ordinal="1"' in assistant
    assert "<user></user>" in assistant
    assert "<assistant>1. First fact.</assistant>" in assistant


def test_statement_costs_reproduce_payload() -> None:
    rows = build_statement_candidates((_parent(),))
    payload = render_statement_payload(rows)
    charged = statement_wrapper_chars() + sum(
        statement_additive_weight(row) for row in rows
    )
    assert len(payload) == charged


def test_own_and_inherited_relevance_are_separate() -> None:
    parents = (_parent(),)
    base = build_statement_candidates(parents)
    own = {
        row["id"]: _vector(1 if row["role"] == "assistant" else 2)
        for row in base
    }
    rows = build_statement_candidates(parents, own)
    query = _vector(1)
    inherited = select_statements(
        statements=rows,
        query_embedding=query,
        relevance_source="parent_embedding",
        budget_chars=1_000,
    )
    treatment = select_statements(
        statements=rows,
        query_embedding=query,
        relevance_source="own_embedding",
        budget_chars=1_000,
    )
    assert inherited.steps[0].relevance == 0.0
    assert treatment.steps[0].relevance == 1.0
    assert treatment.steps[0].candidate_id == rows[1]["id"]
