"""Composition for the deployed episodic-chat read path."""

from __future__ import annotations

import time
from typing import Sequence

from ._config import EpisodicConfig
from ._context import _recency_window
from ._errors import EpisodicError
from ._packing import DROP_POLICY
from ._render import render_stm_payload
from ._report import ContextReport


def build_chat_context(
    *,
    episodes: Sequence[dict],
    query_text: str,
    query_embedding,
    budget: int,
    config: EpisodicConfig,
) -> tuple[str, ContextReport]:
    """Build the CC-007 deployed context with additive recent continuity.

    ``budget`` governs only the long-term retrieval block. The latest
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
