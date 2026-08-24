"""The observability object returned by every ``context()`` call."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextReport:
    """What one context construction did, in exact numbers.

    On the CC-007 public path, ``chars_delivered`` is total output and may
    exceed the long-term allowance because recency is additive.
    ``retrieval_chars_delivered`` is the value governed by
    ``retrieval_budget_chars``. ``truncated`` and dropped identities describe
    nonrecent long-term shortfall only; recent episodes are never dropped.

    Compatibility counts map ``stm_count`` to recency, ``k_count`` to CC80,
    and ``coverage_count`` to ASPECT. The explicit fields next to them should
    be preferred by new callers. Private historical builders leave the new
    fields unset and retain their original total-budget semantics.
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
    dropped_ids: tuple[str, ...] = ()
    drop_policy: str = ""
    budget_chars: int = 0
    retrieval_chars_delivered: int | None = None
    retrieval_budget_chars: int | None = None
    recency_count: int = 0
    semantic_count: int = 0
    aspect_count: int = 0
    returned_semantic_count: int = 0
    aspect_enabled: bool = False
    recent_ids: tuple[str, ...] = ()
    recency_additive: bool = False

    @property
    def chars_available(self) -> int:
        """Unused retrieval budget, excluding additive recent continuity."""

        delivered = (
            self.chars_delivered
            if self.retrieval_chars_delivered is None
            else self.retrieval_chars_delivered
        )
        budget = (
            self.budget_chars
            if self.retrieval_budget_chars is None
            else self.retrieval_budget_chars
        )
        return budget - delivered

    @property
    def shortfall_chars(self) -> int:
        """How much more budget the proposed selection would have needed."""

        delivered = (
            self.chars_delivered
            if self.retrieval_chars_delivered is None
            else self.retrieval_chars_delivered
        )
        return max(0, self.chars_wanted - delivered)
