import json
from dataclasses import asdict

import numpy as np

from episodic._config import EpisodicConfig
from episodic._packing import pack_stm_payload
from episodic._render import render_stm_payload
from episodic._report import ContextReport
from src.analysis.ec002_k_first_packing import (
    CandidateState,
    build_k_first_context,
    check_reproduction_row,
    compare_score_rows,
    normalized_report,
    pack_k_first,
)


def episode(identifier: str, turn: int, size: int = 80, axis: int = 0) -> dict:
    embedding = np.zeros(1024, dtype=np.float32)
    embedding[axis] = 1.0
    return {
        "id": identifier,
        "turn_number": turn,
        "user_message": "u" * size,
        "assistant_message": "a" * size,
        "embedding": embedding,
    }


def report(**overrides) -> ContextReport:
    values = {
        "chars_delivered": 100,
        "chars_wanted": 200,
        "episodes_delivered": 1,
        "episodes_dropped": 1,
        "truncated": True,
        "stm_count": 1,
        "k_count": 0,
        "coverage_count": 0,
        "latency_ms": 1.0,
        "pool_size": 2,
        "dropped_ids": ("x",),
        "drop_policy": "test",
        "budget_chars": 100,
    }
    values.update(overrides)
    return ContextReport(**values)


def test_k_first_changes_only_which_single_tier_claims_the_budget() -> None:
    recent = episode("recent", 2, size=120)
    k_hit = episode("k", 1, size=120)
    state = CandidateState(
        recent=(recent,),
        k_hits=(k_hit,),
        coverage=(),
        pool_size=2,
    )
    budget = max(
        len(render_stm_payload([recent], [])),
        len(render_stm_payload([], [k_hit])),
    )
    assert len(render_stm_payload([recent], [k_hit])) > budget

    baseline = pack_stm_payload([recent], [k_hit], budget)
    treatment = pack_k_first(state, budget=budget)

    assert baseline.selected_ids == ("recent",)
    assert treatment.selected_ids == ("k",)
    assert len(treatment.payload) <= budget


def test_k_recency_overlap_gets_k_priority_but_keeps_recency_tag() -> None:
    overlap = episode("overlap", 1, size=120)
    later = episode("later", 2, size=120)
    state = CandidateState(
        recent=(overlap, later),
        k_hits=(overlap,),
        coverage=(),
        pool_size=2,
    )
    budget = len(render_stm_payload([overlap], []))

    packed = pack_k_first(state, budget=budget)

    assert packed.selected_ids == ("overlap",)
    assert [row["id"] for row in packed.selected_recent] == ["overlap"]
    assert packed.selected_stm == ()
    assert "<recent_context>" in packed.payload
    assert "<retrieved_stm/>" in packed.payload


def test_k_first_skips_oversized_candidate_and_continues() -> None:
    too_large = episode("large", 1, size=1_000)
    small = episode("small", 2, size=20)
    state = CandidateState(
        recent=(),
        k_hits=(too_large, small),
        coverage=(),
        pool_size=2,
    )
    budget = len(render_stm_payload([], [small]))

    packed = pack_k_first(state, budget=budget)

    assert packed.selected_ids == ("small",)
    assert packed.dropped_ids == ("large",)


def test_build_context_reports_k_first_path_without_exceeding_budget() -> None:
    rows = [
        episode("old-k", 1, size=80, axis=0),
        episode("recent", 2, size=80, axis=1),
    ]
    config = EpisodicConfig(
        recency_window_n=1,
        k_threshold=0.48,
        selector_cluster_count=2,
    )
    budget = len(render_stm_payload([], [rows[0]]))

    block, result, diagnostics = build_k_first_context(
        episodes=rows,
        query_embedding=rows[0]["embedding"],
        budget=budget,
        config=config,
    )

    assert len(block) <= budget
    assert result.k_count == 1
    assert result.stm_count == 0
    assert diagnostics["candidate_turns"]["k"] == [1]
    assert diagnostics["selected_turns"]["nonrecency"] == [1]


def test_normalized_report_removes_only_latency_and_normalizes_tuples() -> None:
    original = report(latency_ms=9.5)
    mapping = asdict(original)
    mapping["latency_ms"] = 12.5
    mapping["dropped_ids"] = ["x"]

    assert normalized_report(original) == normalized_report(mapping)


def test_reproduction_check_requires_block_report_and_score_identity() -> None:
    block = "<recent_context/><retrieved_stm/>"
    result = report(
        chars_delivered=len(block),
        dropped_ids=(),
        episodes_dropped=0,
        truncated=False,
    )
    score = {"question_id": "q1", "availability_any": True}
    mechanism = {
        "block_sha256": __import__("hashlib").sha256(
            block.encode("utf-8")
        ).hexdigest(),
        "report": {**asdict(result), "latency_ms": 99.0},
    }

    check = check_reproduction_row(
        original_score=score,
        original_mechanism=mechanism,
        reproduced_score=json.loads(json.dumps(score)),
        reproduced_block=block,
        reproduced_report=result,
    )

    assert check == {
        "question_id": "q1",
        "block_sha256_match": True,
        "report_match": True,
        "score_match": True,
    }


def test_paired_comparison_reports_gains_and_losses_separately() -> None:
    baseline = [
        {
            "question_id": "gain",
            "stratum": "single-session-user",
            "evidence_session_recall_any": False,
            "evidence_session_recall_all": False,
            "availability_any": False,
            "availability_all": False,
            "evidence_session_ranks": [1],
        },
        {
            "question_id": "loss",
            "stratum": "single-session-user",
            "evidence_session_recall_any": True,
            "evidence_session_recall_all": True,
            "availability_any": True,
            "availability_all": True,
            "evidence_session_ranks": [2],
        },
    ]
    treatment = [
        {
            **baseline[0],
            "evidence_session_recall_any": True,
            "availability_any": True,
        },
        {
            **baseline[1],
            "evidence_session_recall_any": False,
            "availability_any": False,
        },
    ]
    mechanism_report = {
        "chars_delivered": 100,
        "episodes_delivered": 1,
        "episodes_dropped": 1,
        "stm_count": 0,
        "k_count": 1,
        "coverage_count": 0,
        "truncated": True,
    }
    mechanisms = [
        {"question_id": row["question_id"], "report": mechanism_report}
        for row in baseline
    ]

    result = compare_score_rows(
        baseline_rows=baseline,
        treatment_rows=treatment,
        treatment_mechanisms=mechanisms,
    )

    session_any = result["by_stratum"]["all"]["session_any"]
    assert session_any["net_delta_questions"] == 0
    assert session_any["gains"] == 1
    assert session_any["losses"] == 1
    assert result["gained_question_ids"]["session_any"] == ["gain"]
    assert result["lost_question_ids"]["session_any"] == ["loss"]
