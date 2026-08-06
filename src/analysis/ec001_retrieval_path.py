"""Post-run path audit for EC-001's sealed Tier 1 mechanism log.

This diagnostic does not rerun retrieval or change any registered metric. It
joins the already-committed measurement rows to the already-opened mechanism
log and attributes delivered evidence-session hits to the carried recency
window versus all non-recency paths.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence


class RetrievalPathDiagnosticError(ValueError):
    """Raised when committed EC-001 artifacts do not join consistently."""


def _median(values: Sequence[int | float]) -> int | float | None:
    return statistics.median(values) if values else None


def _count(rows: Sequence[Mapping[str, object]], key: str) -> int:
    return sum(bool(row[key]) for row in rows)


def _summarize_group(rows: Sequence[Mapping[str, object]]) -> dict:
    answerable = [row for row in rows if bool(row["answerable"])]
    recalled = [row for row in answerable if bool(row["recall_any"])]
    top_four = [
        row
        for row in answerable
        if row["best_evidence_rank"] is not None
        and int(row["best_evidence_rank"]) <= 4
    ]
    k_eligible = [
        row
        for row in answerable
        if row["best_evidence_cosine"] is not None
        and float(row["best_evidence_cosine"]) >= float(row["k_threshold"])
    ]
    below_k = [
        row
        for row in answerable
        if row["best_evidence_cosine"] is not None
        and float(row["best_evidence_cosine"]) < float(row["k_threshold"])
    ]
    candidate_recency = [
        row for row in answerable if bool(row["candidate_recency_any"])
    ]

    return {
        "questions": len(rows),
        "answerable_questions": len(answerable),
        "session_recall_any": _count(answerable, "recall_any"),
        "exact_turn_availability_any": _count(answerable, "availability_any"),
        "session_hit_without_exact_turn": sum(
            bool(row["recall_any"]) and not bool(row["availability_any"])
            for row in answerable
        ),
        "best_evidence_rank_le_4": {
            "questions": len(top_four),
            "session_recall_any": _count(top_four, "recall_any"),
        },
        "best_evidence_session_has_k_eligible_episode": {
            "questions": len(k_eligible),
            "session_recall_any": _count(k_eligible, "recall_any"),
        },
        "best_evidence_session_below_k": {
            "questions": len(below_k),
            "session_recall_any": _count(below_k, "recall_any"),
        },
        "recency_candidate": {
            "questions": len(candidate_recency),
            "session_recall_any": _count(candidate_recency, "recall_any"),
            "missed_after_packing": sum(
                not bool(row["recall_any"]) for row in candidate_recency
            ),
        },
        "session_recall_path": {
            "delivered_recency_only": sum(
                bool(row["hit_via_recency"])
                and not bool(row["hit_via_nonrecency"])
                for row in answerable
            ),
            "delivered_nonrecency_only": sum(
                bool(row["hit_via_nonrecency"])
                and not bool(row["hit_via_recency"])
                for row in answerable
            ),
            "both": sum(
                bool(row["hit_via_recency"])
                and bool(row["hit_via_nonrecency"])
                for row in answerable
            ),
        },
        "median_best_question_evidence_rank": _median(
            [
                int(row["best_evidence_rank"])
                for row in answerable
                if row["best_evidence_rank"] is not None
            ]
        ),
        "median_best_evidence_cosine": _median(
            [
                float(row["best_evidence_cosine"])
                for row in answerable
                if row["best_evidence_cosine"] is not None
            ]
        ),
        "median_history_sessions": _median(
            [int(row["history_sessions"]) for row in rows]
        ),
        "median_history_episodes": _median(
            [int(row["history_episodes"]) for row in rows]
        ),
        "median_unique_sessions_in_recency_candidates": _median(
            [int(row["recency_candidate_sessions"]) for row in rows]
        ),
        "median_unique_sessions_in_delivered_recency": _median(
            [int(row["delivered_recency_sessions"]) for row in rows]
        ),
        "median_unique_sessions_in_delivered_nonrecency": _median(
            [int(row["delivered_nonrecency_sessions"]) for row in rows]
        ),
    }


def build_retrieval_path_diagnostic(
    *,
    dataset,
    score_rows: Sequence[Mapping[str, object]],
    mechanism_rows: Sequence[Mapping[str, object]],
    k_threshold: float,
    recency_window_n: int,
) -> dict:
    """Join committed outputs and compute a measurement-only path audit."""

    scores = {str(row["question_id"]): row for row in score_rows}
    mechanisms = {
        str(row["question_id"]): row for row in mechanism_rows
    }
    dataset_ids = {
        bundle.measurement.question_id for bundle in dataset.instances
    }
    if dataset_ids != set(scores) or dataset_ids != set(mechanisms):
        raise RetrievalPathDiagnosticError(
            "Dataset, score, and mechanism question ids differ"
        )

    rows: list[dict] = []
    pooled_evidence_ranks: list[int] = []
    for bundle in dataset.instances:
        measurement = bundle.measurement
        question_id = measurement.question_id
        score = scores[question_id]
        mechanism = mechanisms[question_id]
        report = mechanism["report"]
        ranking = mechanism["session_cosine_ranking"]
        evidence_ranks = [int(value) for value in score["evidence_session_ranks"]]
        pooled_evidence_ranks.extend(evidence_ranks)
        best_rank = min(evidence_ranks) if evidence_ranks else None
        best_cosine = (
            None
            if best_rank is None
            else float(ranking[best_rank - 1]["cosine"])
        )

        episode_count = len(measurement.episode_session_ids)
        recent_start = max(1, episode_count - recency_window_n + 1)
        recent_turns = set(range(recent_start, episode_count + 1))
        delivered_turns = {
            int(value) for value in mechanism["delivered_turn_numbers"]
        }
        if any(
            turn_number < 1 or turn_number > episode_count
            for turn_number in delivered_turns
        ):
            raise RetrievalPathDiagnosticError(
                f"{question_id}: delivered turn outside episode sequence"
            )
        delivered_recent_turns = delivered_turns & recent_turns
        delivered_nonrecent_turns = delivered_turns - recent_turns
        if len(delivered_recent_turns) != int(report["stm_count"]):
            raise RetrievalPathDiagnosticError(
                f"{question_id}: recency attribution disagrees with stm_count"
            )

        session_by_turn = measurement.episode_session_ids
        recent_sessions = {
            session_by_turn[turn_number - 1] for turn_number in recent_turns
        }
        delivered_recent_sessions = {
            session_by_turn[turn_number - 1]
            for turn_number in delivered_recent_turns
        }
        delivered_nonrecent_sessions = {
            session_by_turn[turn_number - 1]
            for turn_number in delivered_nonrecent_turns
        }
        answer_sessions = set(measurement.answer_session_keys)
        answerable = not measurement.is_abstention
        candidate_recency_any = (
            bool(answer_sessions & recent_sessions) if answerable else False
        )
        hit_via_recency = (
            bool(answer_sessions & delivered_recent_sessions)
            if answerable
            else False
        )
        hit_via_nonrecency = (
            bool(answer_sessions & delivered_nonrecent_sessions)
            if answerable
            else False
        )
        recall_any = (
            bool(score["evidence_session_recall_any"])
            if answerable
            else False
        )
        if answerable and recall_any != (
            hit_via_recency or hit_via_nonrecency
        ):
            raise RetrievalPathDiagnosticError(
                f"{question_id}: path attribution disagrees with recall"
            )

        rows.append(
            {
                "question_id": question_id,
                "stratum": measurement.stratum,
                "answerable": answerable,
                "recall_any": recall_any,
                "availability_any": (
                    bool(score["availability_any"]) if answerable else False
                ),
                "best_evidence_rank": best_rank,
                "best_evidence_cosine": best_cosine,
                "top_session_cosine": float(ranking[0]["cosine"]),
                "k_threshold": k_threshold,
                "candidate_recency_any": candidate_recency_any,
                "hit_via_recency": hit_via_recency,
                "hit_via_nonrecency": hit_via_nonrecency,
                "history_sessions": len(measurement.session_ids),
                "history_episodes": episode_count,
                "recency_candidate_sessions": len(recent_sessions),
                "delivered_recency_sessions": len(delivered_recent_sessions),
                "delivered_nonrecency_sessions": len(
                    delivered_nonrecent_sessions
                ),
                "chars_delivered": int(report["chars_delivered"]),
                "chars_wanted": int(report["chars_wanted"]),
                "episodes_delivered": int(report["episodes_delivered"]),
                "episodes_dropped": int(report["episodes_dropped"]),
                "truncated": bool(report["truncated"]),
                "stm_count": int(report["stm_count"]),
                "k_count": int(report["k_count"]),
                "coverage_count": int(report["coverage_count"]),
            }
        )

    all_summary = _summarize_group(rows)
    strata = sorted({str(row["stratum"]) for row in rows})
    by_stratum = {
        stratum: _summarize_group(
            [row for row in rows if row["stratum"] == stratum]
        )
        for stratum in strata
    }

    def values(key: str) -> list[int]:
        return [int(row[key]) for row in rows]

    all_summary.update(
        {
            "evidence_session_rank_count": len(pooled_evidence_ranks),
            "pooled_evidence_session_rank_median": _median(
                pooled_evidence_ranks
            ),
            "candidate_k_questions": sum(
                float(row["top_session_cosine"]) >= k_threshold
                for row in rows
            ),
            "delivered_nonrecency_k_questions": sum(
                int(row["k_count"]) > 0 for row in rows
            ),
            "delivered_nonrecency_k_episodes": sum(values("k_count")),
            "delivered_coverage_questions": sum(
                int(row["coverage_count"]) > 0 for row in rows
            ),
            "delivered_coverage_episodes": sum(values("coverage_count")),
            "all_blocks_truncated": all(
                bool(row["truncated"]) for row in rows
            ),
            "all_blocks_at_least_31000_chars": all(
                int(row["chars_delivered"]) >= 31_000 for row in rows
            ),
            "block_composition": {
                "stm": _distribution(values("stm_count")),
                "k": _distribution(values("k_count")),
                "coverage": _distribution(values("coverage_count")),
                "episodes_delivered": _distribution(
                    values("episodes_delivered")
                ),
                "episodes_dropped": _distribution(values("episodes_dropped")),
                "chars_delivered": _distribution(values("chars_delivered")),
                "chars_wanted": _distribution(values("chars_wanted")),
            },
        }
    )
    return {
        "status": "POST_HOC_DIAGNOSTIC",
        "registered_metrics_changed": False,
        "definitions": {
            "candidate_k_question": (
                "At least one exchange episode reaches the carried cosine "
                "threshold; equivalently, the maximum session score reaches K."
            ),
            "delivered_nonrecency_k": (
                "The committed ContextReport.k_count: delivered K-eligible "
                "episodes excluding episodes already claimed by recency."
            ),
            "recency_candidate": (
                "At least one annotated evidence session intersects the final "
                "N exchange episodes before exact packing."
            ),
            "session_recall_path": (
                "Evidence-session identity attributed from delivered turn "
                "numbers. Non-recency does not uniquely separate K from A3 "
                "when both paths delivered episodes."
            ),
        },
        "config": {
            "k_threshold": k_threshold,
            "recency_window_n": recency_window_n,
            "packing_order": "recency, K, A3 coverage",
            "budget_policy": "N-first, exact serialized cost",
        },
        "all": all_summary,
        "by_stratum": by_stratum,
    }


def _distribution(values: Sequence[int]) -> dict:
    return {
        "sum": sum(values),
        "min": min(values),
        "median": _median(values),
        "max": max(values),
    }
