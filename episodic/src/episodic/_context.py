"""Context construction for the deployed and historical read paths.

``build_context`` below is the private pre-CC-007 compatibility builder. Each
stage is moved, committed
code - the recency window, the K-threshold similarity path, the A3
coverage selector, N-first packing at exact cost, and the DR-001
renderer. What is new here is only the order they are wired in:

1. recency claims the ``recent_context`` block (N most recent episodes),
2. K-threshold hits claim the ``retrieved_stm`` block first,
3. the A3 coverage selection fills the remainder,
4. everything is packed N-first at exact serialized cost.

The deployed ``build_chat_context`` instead composes additive recency with
CC80 and optional static ASPECT under an independent long-term budget. Both
functions are pure apart from latency measurement.
"""

from __future__ import annotations

import time
from typing import Sequence

from ._config import EpisodicConfig
from ._errors import EpisodicError
from ._packing import DROP_POLICY, EMPTY_PAYLOAD_CHARS, pack_stm_payload
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
    if pool and budget >= EMPTY_PAYLOAD_CHARS:
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

    # What the paths proposed, in the order they proposed it, minus what
    # actually landed. Order is preserved so the identities are reportable
    # rather than merely countable.
    wanted_order = [*recent, *wanted_stm]
    dropped_ids = tuple(
        str(episode["id"])
        for episode in wanted_order
        if str(episode["id"]) not in delivered_ids
    )

    # The ceiling, asserted on the way out. A negative budget cannot be
    # honoured literally - the empty string is already zero characters -
    # so it is read as zero rather than treated as unsatisfiable.
    if len(packed.payload) > max(budget, 0):
        raise AssertionError(
            "Context block exceeded its character budget: "
            f"{len(packed.payload)} > {budget}"
        )

    report = ContextReport(
        chars_delivered=len(packed.payload),
        chars_wanted=chars_wanted,
        episodes_delivered=len(delivered_ids),
        episodes_dropped=len(dropped_ids),
        truncated=bool(dropped_ids),
        stm_count=stm_count,
        k_count=k_count,
        coverage_count=coverage_count,
        latency_ms=(time.perf_counter() - started) * 1_000.0,
        pool_size=len(pool),
        dropped_ids=dropped_ids,
        drop_policy=DROP_POLICY,
        budget_chars=budget,
    )
    return packed.payload, report


def build_chat_context(
    *,
    episodes: Sequence[dict],
    query_text: str,
    query_embedding,
    budget: int,
    config: EpisodicConfig,
) -> tuple[str, ContextReport]:
    """Build the CC-007 deployed context with additive recent continuity.

    ``budget`` governs only the long-term retrieval block.  The latest
    ``recency_window_n`` complete episodes are always rendered and are excluded
    from CC80/ASPECT admission by stable identity.
    """

    from ._retrieval import retrieve_long_term

    started = time.perf_counter()
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
        raise EpisodicError("retrieval budget must be a non-negative integer")
    recent = _recency_window(episodes, config.recency_window_n)
    recent_ids = tuple(str(episode["id"]) for episode in recent)
    retrieval = retrieve_long_term(
        episodes=episodes,
        query_text=query_text,
        query_embedding=query_embedding,
        budget=budget,
        config=config,
        excluded_ids=recent_ids,
    )
    long_term = [episodes[index] for index in retrieval.selected_indices]
    long_term_ids = {str(episode["id"]) for episode in long_term}
    if long_term_ids & set(recent_ids):
        raise AssertionError("Recent and long-term context were not deduplicated")

    payload = render_stm_payload(recent, long_term)
    retrieval_chars = len(retrieval.payload)
    if retrieval_chars > max(budget, 0):
        raise AssertionError(
            "Long-term retrieval exceeded its character budget: "
            f"{retrieval_chars} > {budget}"
        )
    delivered_ids = (*recent_ids, *retrieval.selected_ids)
    if len(delivered_ids) != len(set(delivered_ids)):
        raise AssertionError("An episode serialized more than once")

    semantic_count = len(retrieval.initial_semantic_ids) + len(
        retrieval.returned_semantic_ids
    )
    report = ContextReport(
        chars_delivered=len(payload),
        chars_wanted=retrieval.chars_wanted,
        episodes_delivered=len(delivered_ids),
        episodes_dropped=len(retrieval.dropped_ids),
        truncated=bool(retrieval.dropped_ids),
        stm_count=len(recent_ids),
        k_count=semantic_count,
        coverage_count=len(retrieval.aspect_ids),
        latency_ms=(time.perf_counter() - started) * 1_000.0,
        pool_size=len(episodes),
        dropped_ids=retrieval.dropped_ids,
        drop_policy=DROP_POLICY,
        budget_chars=budget,
        retrieval_chars_delivered=retrieval_chars,
        retrieval_budget_chars=budget,
        recency_count=len(recent_ids),
        semantic_count=semantic_count,
        aspect_count=len(retrieval.aspect_ids),
        returned_semantic_count=len(retrieval.returned_semantic_ids),
        aspect_enabled=config.aspect_enabled,
        recent_ids=recent_ids,
        recency_additive=True,
    )
    return payload, report


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
