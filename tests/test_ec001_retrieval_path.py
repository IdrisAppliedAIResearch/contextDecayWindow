from src.analysis.ec001_retrieval_path import _summarize_group


def _row(**overrides):
    row = {
        "answerable": True,
        "recall_any": False,
        "availability_any": False,
        "best_evidence_rank": 2,
        "best_evidence_cosine": 0.5,
        "k_threshold": 0.48,
        "candidate_recency_any": False,
        "hit_via_recency": False,
        "hit_via_nonrecency": False,
        "history_sessions": 40,
        "history_episodes": 200,
        "recency_candidate_sessions": 7,
        "delivered_recency_sessions": 4,
        "delivered_nonrecency_sessions": 1,
    }
    row.update(overrides)
    return row


def test_summary_separates_rank_threshold_recency_and_exact_turn():
    rows = [
        _row(
            recall_any=True,
            availability_any=False,
            candidate_recency_any=True,
            hit_via_recency=True,
        ),
        _row(
            best_evidence_rank=7,
            best_evidence_cosine=0.3,
            recall_any=True,
            availability_any=True,
            hit_via_nonrecency=True,
        ),
        _row(
            best_evidence_rank=1,
            best_evidence_cosine=0.4,
            candidate_recency_any=True,
        ),
        _row(
            answerable=False,
            best_evidence_rank=None,
            best_evidence_cosine=None,
        ),
    ]

    result = _summarize_group(rows)

    assert result["questions"] == 4
    assert result["answerable_questions"] == 3
    assert result["session_recall_any"] == 2
    assert result["exact_turn_availability_any"] == 1
    assert result["session_hit_without_exact_turn"] == 1
    assert result["best_evidence_rank_le_4"] == {
        "questions": 2,
        "session_recall_any": 1,
    }
    assert result["best_evidence_session_has_k_eligible_episode"] == {
        "questions": 1,
        "session_recall_any": 1,
    }
    assert result["best_evidence_session_below_k"] == {
        "questions": 2,
        "session_recall_any": 1,
    }
    assert result["recency_candidate"] == {
        "questions": 2,
        "session_recall_any": 1,
        "missed_after_packing": 1,
    }
    assert result["session_recall_path"] == {
        "delivered_recency_only": 1,
        "delivered_nonrecency_only": 1,
        "both": 0,
    }
