"""Prospective EC-002 offline replay of K-first exact-cost packing.

The shipping ``episodic`` package remains unchanged.  This module reconstructs
its frozen candidate sets, then changes only the order in which unique episode
identities are offered to the exact serializer:

    K-threshold hits -> recency -> A3 coverage.

Selected episodes retain their original render tier.  In particular, a
K/recency overlap is considered at K priority but is rendered in
``recent_context``.  Reference labels enter only the separate scoring helpers
imported by the runner after both blocks have been built.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from episodic._config import EpisodicConfig
from episodic._context import _candidate_pool, _recency_window
from episodic._packing import EMPTY_PAYLOAD_CHARS
from episodic._render import render_stm_payload
from episodic._report import ContextReport
from episodic._selection import (
    ClusterDiversitySelector,
    deterministic_clusters,
    relevance_vector,
    select,
    vector,
)

K_FIRST_DROP_POLICY = "k_first_exact_cost_skip_on_overflow"


class EC002Error(ValueError):
    """Raised when the registered replay boundary is violated."""


@dataclass(frozen=True)
class CandidateState:
    recent: tuple[dict, ...]
    k_hits: tuple[dict, ...]
    coverage: tuple[dict, ...]
    pool_size: int


@dataclass(frozen=True)
class KFirstPack:
    payload: str
    selected_recent: tuple[dict, ...]
    selected_stm: tuple[dict, ...]
    selected_ids: tuple[str, ...]
    dropped_ids: tuple[str, ...]
    considered_ids: tuple[str, ...]


def build_candidate_state(
    *,
    episodes: Sequence[dict],
    query_embedding,
    budget: int,
    config: EpisodicConfig,
) -> CandidateState:
    """Reconstruct the unchanged EC-001 recency, K, and A3 candidate lists."""

    query = vector(query_embedding)
    recent = _recency_window(episodes, config.recency_window_n)

    relevance_by_id: dict[str, float] = {}
    if episodes:
        relevance = relevance_vector(query, episodes)
        relevance_by_id = {
            str(episode["id"]): float(relevance[index])
            for index, episode in enumerate(episodes)
        }
    k_hits = [
        episode
        for episode in episodes
        if relevance_by_id[str(episode["id"])] >= config.k_threshold
    ]

    pool = _candidate_pool(episodes, relevance_by_id, config)
    coverage: list[dict] = []
    if pool and budget >= EMPTY_PAYLOAD_CHARS:
        selection = select(
            candidates=pool,
            query_embedding=query,
            selector=ClusterDiversitySelector(
                lambda_=config.selector_lambda,
                cost_exponent=config.selector_cost_exponent,
                assignments=deterministic_clusters(
                    pool, config.selector_cluster_count
                ),
                cluster_count=config.selector_cluster_count,
            ),
            budget_chars=budget,
        )
        by_id = {str(episode["id"]): episode for episode in pool}
        coverage = [
            by_id[identifier] for identifier in selection.selected_ids
        ]

    return CandidateState(
        recent=tuple(recent),
        k_hits=tuple(k_hits),
        coverage=tuple(coverage),
        pool_size=len(pool),
    )


def pack_k_first(
    state: CandidateState,
    *,
    budget: int,
) -> KFirstPack:
    """Pack K, then recency, then coverage while preserving render tiers."""

    recent_ids = {str(episode["id"]) for episode in state.recent}
    stm_order = _unique(
        [
            episode
            for episode in (*state.k_hits, *state.coverage)
            if str(episode["id"]) not in recent_ids
        ]
    )

    def render(selected: set[str]) -> tuple[str, tuple[dict, ...], tuple[dict, ...]]:
        selected_recent = tuple(
            episode
            for episode in state.recent
            if str(episode["id"]) in selected
        )
        selected_stm = tuple(
            episode
            for episode in stm_order
            if str(episode["id"]) in selected
        )
        return (
            render_stm_payload(selected_recent, selected_stm),
            selected_recent,
            selected_stm,
        )

    consideration = _unique(
        [*state.k_hits, *state.recent, *state.coverage]
    )
    if budget < EMPTY_PAYLOAD_CHARS:
        return KFirstPack(
            payload="",
            selected_recent=(),
            selected_stm=(),
            selected_ids=(),
            dropped_ids=tuple(str(episode["id"]) for episode in consideration),
            considered_ids=tuple(
                str(episode["id"]) for episode in consideration
            ),
        )

    selected: set[str] = set()
    dropped: list[str] = []
    for candidate in consideration:
        identifier = str(candidate["id"])
        tentative = {*selected, identifier}
        payload, _, _ = render(tentative)
        if len(payload) <= budget:
            selected.add(identifier)
        else:
            dropped.append(identifier)

    payload, selected_recent, selected_stm = render(selected)
    if len(payload) > budget:
        raise AssertionError("K-first payload exceeded its character budget")
    selected_ids = tuple(
        str(episode["id"])
        for episode in (*selected_recent, *selected_stm)
    )
    if len(selected_ids) != len(set(selected_ids)):
        raise AssertionError("K-first payload contains a duplicate episode")
    return KFirstPack(
        payload=payload,
        selected_recent=selected_recent,
        selected_stm=selected_stm,
        selected_ids=selected_ids,
        dropped_ids=tuple(dropped),
        considered_ids=tuple(
            str(episode["id"]) for episode in consideration
        ),
    )


def build_k_first_context(
    *,
    episodes: Sequence[dict],
    query_embedding,
    budget: int,
    config: EpisodicConfig,
) -> tuple[str, ContextReport, dict]:
    """Build the registered A1 block and an identity-level mechanism record."""

    started = time.perf_counter()
    state = build_candidate_state(
        episodes=episodes,
        query_embedding=query_embedding,
        budget=budget,
        config=config,
    )
    packed = pack_k_first(state, budget=budget)

    recent_ids = {str(episode["id"]) for episode in state.recent}
    k_ids = {str(episode["id"]) for episode in state.k_hits}
    delivered_ids = set(packed.selected_ids)

    wanted_stm = _unique(
        [
            episode
            for episode in (*state.k_hits, *state.coverage)
            if str(episode["id"]) not in recent_ids
        ]
    )
    chars_wanted = len(render_stm_payload(state.recent, wanted_stm))

    report = ContextReport(
        chars_delivered=len(packed.payload),
        chars_wanted=chars_wanted,
        episodes_delivered=len(delivered_ids),
        episodes_dropped=len(packed.dropped_ids),
        truncated=bool(packed.dropped_ids),
        stm_count=len(delivered_ids & recent_ids),
        k_count=len((delivered_ids & k_ids) - recent_ids),
        coverage_count=len(delivered_ids - recent_ids - k_ids),
        latency_ms=(time.perf_counter() - started) * 1_000.0,
        pool_size=state.pool_size,
        dropped_ids=packed.dropped_ids,
        drop_policy=K_FIRST_DROP_POLICY,
        budget_chars=budget,
    )
    diagnostics = {
        "candidate_turns": {
            "recency": _turns(state.recent),
            "k": _turns(state.k_hits),
            "coverage": _turns(state.coverage),
        },
        "selected_turns": {
            "recency": _turns(packed.selected_recent),
            "nonrecency": _turns(packed.selected_stm),
        },
        "considered_turns_k_first": [
            _turn_by_id(episodes, identifier)
            for identifier in packed.considered_ids
        ],
        "dropped_turns": [
            _turn_by_id(episodes, identifier)
            for identifier in packed.dropped_ids
        ],
        "payload_sha256": hashlib.sha256(
            packed.payload.encode("utf-8")
        ).hexdigest(),
    }
    return packed.payload, report, diagnostics


def normalized_report(value: Mapping[str, object] | ContextReport) -> dict:
    """Remove only latency and normalize tuples for committed comparison."""

    report = asdict(value) if isinstance(value, ContextReport) else dict(value)
    report.pop("latency_ms", None)
    return json.loads(json.dumps(report, sort_keys=True))


def check_reproduction_row(
    *,
    original_score: Mapping[str, object],
    original_mechanism: Mapping[str, object],
    reproduced_score: Mapping[str, object],
    reproduced_block: str,
    reproduced_report: ContextReport,
) -> dict:
    """Return the binding A0 checks for one question."""

    block_sha256 = hashlib.sha256(
        reproduced_block.encode("utf-8")
    ).hexdigest()
    return {
        "question_id": str(original_score["question_id"]),
        "block_sha256_match": (
            block_sha256 == str(original_mechanism["block_sha256"])
        ),
        "report_match": (
            normalized_report(reproduced_report)
            == normalized_report(original_mechanism["report"])
        ),
        "score_match": (
            json.loads(json.dumps(reproduced_score, sort_keys=True))
            == json.loads(json.dumps(original_score, sort_keys=True))
        ),
    }


def evaluate_reproduction(
    *,
    checks: Sequence[Mapping[str, object]],
    reproduced_summary: Mapping[str, object],
    original_summary: Mapping[str, object],
) -> dict:
    """Evaluate the registered 500-row reproduction gate."""

    expected = 500
    if len(checks) != expected:
        raise EC002Error(
            f"Reproduction gate expected {expected} rows, got {len(checks)}"
        )
    block_matches = sum(bool(row["block_sha256_match"]) for row in checks)
    report_matches = sum(bool(row["report_match"]) for row in checks)
    score_matches = sum(bool(row["score_match"]) for row in checks)
    summary_match = (
        json.loads(json.dumps(reproduced_summary, sort_keys=True))
        == json.loads(json.dumps(original_summary, sort_keys=True))
    )
    passed = (
        block_matches == expected
        and report_matches == expected
        and score_matches == expected
        and summary_match
    )
    return {
        "record": "EC-002 A0 reproduction gate",
        "expected_questions": expected,
        "block_sha256_matches": block_matches,
        "report_matches_excluding_latency": report_matches,
        "score_matches": score_matches,
        "summary_match": summary_match,
        "status": "PASS" if passed else "FAIL",
        "failed_question_ids": [
            str(row["question_id"])
            for row in checks
            if not (
                bool(row["block_sha256_match"])
                and bool(row["report_match"])
                and bool(row["score_match"])
            )
        ],
    }


def compare_score_rows(
    *,
    baseline_rows: Sequence[Mapping[str, object]],
    treatment_rows: Sequence[Mapping[str, object]],
    treatment_mechanisms: Sequence[Mapping[str, object]],
) -> dict:
    """Aggregate the registered paired A1-minus-A0 Tier 1 measurements."""

    baseline = {str(row["question_id"]): row for row in baseline_rows}
    treatment = {str(row["question_id"]): row for row in treatment_rows}
    mechanisms = {
        str(row["question_id"]): row for row in treatment_mechanisms
    }
    if set(baseline) != set(treatment) or set(baseline) != set(mechanisms):
        raise EC002Error("A0, A1, and mechanism question ids differ")

    paired = []
    for question_id in baseline:
        before = baseline[question_id]
        after = treatment[question_id]
        mechanism = mechanisms[question_id]
        if before["stratum"] != after["stratum"]:
            raise EC002Error(f"{question_id}: stratum changed")
        paired.append(
            {
                "question_id": question_id,
                "stratum": str(before["stratum"]),
                "answerable": before["evidence_session_recall_any"] is not None,
                "session_any_a0": before["evidence_session_recall_any"],
                "session_any_a1": after["evidence_session_recall_any"],
                "session_all_a0": before["evidence_session_recall_all"],
                "session_all_a1": after["evidence_session_recall_all"],
                "turn_any_a0": before["availability_any"],
                "turn_any_a1": after["availability_any"],
                "turn_all_a0": before["availability_all"],
                "turn_all_a1": after["availability_all"],
                "best_evidence_rank": (
                    min(before["evidence_session_ranks"])
                    if before["evidence_session_ranks"]
                    else None
                ),
                "report": mechanism["report"],
            }
        )

    answerable = [row for row in paired if row["answerable"]]
    groups: dict[str, list[dict]] = defaultdict(list)
    groups["all"] = answerable
    for row in answerable:
        groups[row["stratum"]].append(row)

    return {
        "record": "EC-002 K-first paired Tier 1 comparison",
        "questions": len(paired),
        "answerable_questions": len(answerable),
        "by_stratum": {
            name: _paired_group(rows)
            for name, rows in sorted(groups.items())
        },
        "gained_question_ids": {
            metric: [
                row["question_id"]
                for row in answerable
                if row[f"{metric}_a0"] is False
                and row[f"{metric}_a1"] is True
            ]
            for metric in ("session_any", "session_all", "turn_any", "turn_all")
        },
        "lost_question_ids": {
            metric: [
                row["question_id"]
                for row in answerable
                if row[f"{metric}_a0"] is True
                and row[f"{metric}_a1"] is False
            ]
            for metric in ("session_any", "session_all", "turn_any", "turn_all")
        },
        "top_four_subset": _paired_group(
            [
                row
                for row in answerable
                if row["best_evidence_rank"] is not None
                and int(row["best_evidence_rank"]) <= 4
            ]
        ),
        "block_delivery": {
            key: _distribution(
                [int(row["report"][key]) for row in paired]
            )
            for key in (
                "chars_delivered",
                "episodes_delivered",
                "episodes_dropped",
                "stm_count",
                "k_count",
                "coverage_count",
            )
        },
        "truncated_questions": sum(
            bool(row["report"]["truncated"]) for row in paired
        ),
    }


def _paired_group(rows: Sequence[Mapping[str, object]]) -> dict:
    metrics = {}
    for metric in ("session_any", "session_all", "turn_any", "turn_all"):
        a0 = sum(bool(row[f"{metric}_a0"]) for row in rows)
        a1 = sum(bool(row[f"{metric}_a1"]) for row in rows)
        gains = sum(
            row[f"{metric}_a0"] is False and row[f"{metric}_a1"] is True
            for row in rows
        )
        losses = sum(
            row[f"{metric}_a0"] is True and row[f"{metric}_a1"] is False
            for row in rows
        )
        metrics[metric] = {
            "a0": a0,
            "a1": a1,
            "net_delta_questions": a1 - a0,
            "delta_percentage_points": (
                100.0 * (a1 - a0) / len(rows) if rows else None
            ),
            "gains": gains,
            "losses": losses,
            "unchanged": len(rows) - gains - losses,
        }
    return {"denominator": len(rows), **metrics}


def _distribution(values: Sequence[int]) -> dict:
    return {
        "sum": sum(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def _unique(episodes: Sequence[dict]) -> list[dict]:
    seen: set[str] = set()
    result = []
    for episode in episodes:
        identifier = str(episode["id"])
        if identifier in seen:
            continue
        seen.add(identifier)
        result.append(episode)
    return result


def _turns(episodes: Sequence[dict]) -> list[int]:
    return [int(episode["turn_number"]) for episode in episodes]


def _turn_by_id(episodes: Sequence[dict], identifier: str) -> int:
    for episode in episodes:
        if str(episode["id"]) == identifier:
            return int(episode["turn_number"])
    raise EC002Error(f"Unknown episode id in packing record: {identifier}")
