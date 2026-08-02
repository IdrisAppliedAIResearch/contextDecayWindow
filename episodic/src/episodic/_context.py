"""Context construction: the three carried paths under one exact budget.

This module is composition, not mechanism. Each stage is moved, committed
code - the recency window, the K-threshold similarity path, the A3
coverage selector, N-first packing at exact cost, and the DR-001
renderer. What is new here is only the order they are wired in:

1. recency claims the ``recent_context`` block (N most recent episodes),
2. K-threshold hits claim the ``retrieved_stm`` block first,
3. the A3 coverage selection fills the remainder,
4. everything is packed N-first at exact serialized cost.

``build_context`` is a pure function of (episodes, query embedding,
budget, config): no store handle, no clock beyond the latency
measurement, no mutation.
"""

from __future__ import annotations

import time
from typing import Sequence

from ._config import EpisodicConfig
from ._packing import pack_stm_payload
from ._render import render_stm_payload
from ._report import ContextReport
from ._selection import (
    ClusterDiversitySelector,
    deterministic_clusters,
    relevance_vector,
    select,
    vector,
)


def build_context(
    *,
    episodes: Sequence[dict],
    query_embedding,
    budget: int,
    config: EpisodicConfig,
) -> tuple[str, ContextReport]:
    started = time.perf_counter()
    query = vector(query_embedding)

    recent = _recency_window(episodes, config.recency_window_n)
    recent_ids = {str(episode["id"]) for episode in recent}

    relevance_by_id = {}
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
    k_ids = {str(episode["id"]) for episode in k_hits}

    pool = _candidate_pool(episodes, relevance_by_id, config)
    coverage: list[dict] = []
    if pool:
        result = select(
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
        coverage = [by_id[identifier] for identifier in result.selected_ids]

    stm_candidates = [*k_hits, *coverage]
    packed = pack_stm_payload(recent, stm_candidates, budget)

    wanted_stm: list[dict] = []
    wanted_seen = set(recent_ids)
    for episode in stm_candidates:
        identifier = str(episode["id"])
        if identifier in wanted_seen:
            continue
        wanted_seen.add(identifier)
        wanted_stm.append(episode)
    chars_wanted = len(render_stm_payload(recent, wanted_stm))

    delivered_ids = set(packed.selected_ids)
    stm_count = len(delivered_ids & recent_ids)
    k_count = len((delivered_ids & k_ids) - recent_ids)
    coverage_count = len(delivered_ids - recent_ids - k_ids)
    wanted_count = len(recent) + len(wanted_stm)

    report = ContextReport(
        chars_delivered=len(packed.payload),
        chars_wanted=chars_wanted,
        episodes_delivered=len(delivered_ids),
        episodes_dropped=wanted_count - len(delivered_ids),
        truncated=wanted_count > len(delivered_ids),
        stm_count=stm_count,
        k_count=k_count,
        coverage_count=coverage_count,
        latency_ms=(time.perf_counter() - started) * 1_000.0,
        pool_size=len(pool),
    )
    return packed.payload, report


def _recency_window(episodes: Sequence[dict], n: int) -> list[dict]:
    """The last N episodes, delivered in conversation order."""
    if n <= 0:
        return []
    return list(episodes[-n:])


def _candidate_pool(
    episodes: Sequence[dict],
    relevance_by_id: dict[str, float],
    config: EpisodicConfig,
) -> list[dict]:
    """Candidates the coverage selector may consider.

    The default is the full store. ``unsafe_cosine_top_n`` exists because
    callers will ask for it, and it is named unsafe because DR-002 measured
    what it does: dropping the 19 lowest-cosine episodes from a 119-episode
    pool cost an entire domain and all oracle overlap, even though 4 of the
    5 oracle episodes survived the cut - the selector clusters over the
    pool, so tail removal reshuffles the objective rather than removing
    options. (Source repository, DR-002:
    `experiments/components/retrieval_mechanism_ledger/DR_002_*`,
    `artifacts/e005/dr_002/`.)
    """
    if config.candidate_policy == "full_store":
        return list(episodes)
    ordered = sorted(
        range(len(episodes)),
        key=lambda index: (
            -relevance_by_id[str(episodes[index]["id"])],
            int(episodes[index]["turn_number"]),
            str(episodes[index]["id"]),
        ),
    )
    kept = sorted(ordered[: config.unsafe_cosine_top_n])
    return [episodes[index] for index in kept]
