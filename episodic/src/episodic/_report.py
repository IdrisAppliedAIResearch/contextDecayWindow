"""The observability object returned by every ``context()`` call."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextReport:
    """What one context construction did, in exact numbers.

    ``truncated`` is honest reporting of a condition the caller should know
    about: selection wanted more than the budget allowed. Acting on it -
    hard-ceiling semantics - is deliberately out of scope here (CC-003).

    ``stm_count``, ``k_count``, and ``coverage_count`` attribute delivered
    episodes to the path that claimed them first: the recency window, the
    K-threshold similarity path, then the coverage selector.
    """

    chars_delivered: int
    chars_wanted: int
    episodes_delivered: int
    episodes_dropped: int
    truncated: bool
    stm_count: int
    k_count: int
    coverage_count: int
    latency_ms: float
    pool_size: int
