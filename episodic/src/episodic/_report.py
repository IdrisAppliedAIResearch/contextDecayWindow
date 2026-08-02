"""The observability object returned by every ``context()`` call."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextReport:
    """What one context construction did, in exact numbers.

    ``chars_delivered`` never exceeds the requested budget. That is the
    library's hard ceiling (CC-003): there is no tolerance, no rounding,
    and no configuration that relaxes it, including at budgets too small
    to hold a single episode.

    ``truncated`` says selection wanted more than the budget allowed, and
    it is meant to be acted on rather than logged. A bare boolean tells a
    caller that something happened but not what, so it travels with
    ``chars_wanted``, ``episodes_dropped``, and ``dropped_ids`` - the
    identities of the episodes that were proposed and did not fit.

    ``chars_wanted`` is the exact serialized cost of everything the three
    retrieval paths jointly proposed, before packing dropped anything, so
    the caller sees the size of the shortfall and not merely its
    existence. It is not the cost of the whole store: the coverage
    selector is a budgeted greedy and has no unconstrained mode, so
    "wanted" means "proposed by the paths", which is the quantity a
    caller can actually respond to by raising the budget.

    ``stm_count``, ``k_count``, and ``coverage_count`` attribute delivered
    episodes to the path that claimed them first: the recency window, the
    K-threshold similarity path, then the coverage selector.

    ``drop_policy`` names the order in which candidates were considered
    and dropped; see ``_packing.DROP_POLICY`` for what the name means.
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

    @property
    def chars_available(self) -> int:
        """Unused budget. Zero or positive whenever the ceiling holds."""
        return self.budget_chars - self.chars_delivered

    @property
    def shortfall_chars(self) -> int:
        """How much more budget the proposed selection would have needed."""
        return max(0, self.chars_wanted - self.chars_delivered)
