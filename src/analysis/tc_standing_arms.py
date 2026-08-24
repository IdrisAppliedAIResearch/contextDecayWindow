"""The TC arc's standing arms, named once so every study carries the same ones.

TC-001 compared two arms; TC-001B added two more and found that TC-001's
435-question deficit decomposed into 158 questions of recency-tier cost and 276
questions of K-tier ordering cost. Neither number was visible from TC-001's two
arms alone, and both were only measurable because the later study kept the
earlier one's reference arm alongside its own.

The author's standing instruction after TC-001B is that the dual arm travels
with the arc from here on. This module is where that instruction lives, so a
later study inherits the arms by importing them rather than by remembering to.

    A_FLAT         rank every candidate by cosine, pack greedily to budget.
    A_DUAL         ``build_context`` with ``recency_window_n=0``: relevance and
                   coverage, no recency tier. One config field, no new code.
    A_DUAL_RANKED  A_DUAL with the K tier offered best-first rather than in
                   store order.

``STANDING_ARMS`` is the set every TC study carries. A study adds its own arms
on top; it does not drop these. ``tests/test_dual_arm_standing.py`` holds the
registry and each arm's behavioural identity to that promise, independently of
whichever study is currently open.

Nothing here is new mechanism. Every constructor forwards to code that already
produced a committed number, and the forwarding is what makes the arms
comparable across studies.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

import numpy as np

from analysis.tc001_exploration import Episode, flat_context, tiered_context
from analysis.tc001b_exploration import (
    DUAL_CONFIG,
    SHIPPED_CONFIG,
    dual_context,
    dual_ranked_context,
)

#: Carried by every TC study from TC-002 onward. Order is reporting order.
STANDING_ARMS: tuple[str, ...] = ("flat", "dual", "dual_ranked")

#: The study that first measured each standing arm, for provenance in a
#: report that inherits it rather than re-deriving it.
STANDING_ARM_ORIGIN: dict[str, str] = {
    "flat": "TC-001",
    "dual": "TC-001B",
    "dual_ranked": "TC-001B",
}


class TCArmError(RuntimeError):
    """Raised when an arm is requested that this arc does not define."""


def deliver(
    arm: str,
    episodes: Sequence[Episode],
    query: np.ndarray,
    budget: int,
) -> tuple[str, tuple[str, ...]]:
    """One arm's delivered block and delivered episode identities.

    The third element each underlying constructor returns differs by arm - a
    ``ContextReport`` for two of them, a counts dictionary for the third - so
    it is deliberately not part of this signature. A caller that needs tier
    counts calls the constructor directly and knows which shape it is getting.
    """
    if arm not in _CONSTRUCTORS:
        raise TCArmError(
            f"Unregistered arm {arm!r}; this arc defines {sorted(_CONSTRUCTORS)}"
        )
    return _CONSTRUCTORS[arm](episodes, query, budget)


def _flat(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[str, tuple[str, ...]]:
    return flat_context(episodes, query, budget)


def _tiered(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[str, tuple[str, ...]]:
    payload, delivered, _report = tiered_context(
        episodes, query, budget, SHIPPED_CONFIG
    )
    return payload, delivered


def _dual(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[str, tuple[str, ...]]:
    payload, delivered, _report = dual_context(episodes, query, budget)
    return payload, delivered


def _dual_ranked(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[str, tuple[str, ...]]:
    payload, delivered, _counts = dual_ranked_context(episodes, query, budget)
    return payload, delivered


#: ``tiered`` is defined here but is not standing: it is the shipped
#: configuration, which a study carries when it is under test and omits when it
#: is not. The three in ``STANDING_ARMS`` are the ones that travel regardless.
_CONSTRUCTORS: dict[str, Callable[..., tuple[str, tuple[str, ...]]]] = {
    "flat": _flat,
    "tiered": _tiered,
    "dual": _dual,
    "dual_ranked": _dual_ranked,
}


def arm_configs() -> dict[str, Any]:
    """The configuration each arm runs under, for a run header."""
    return {
        "flat": None,
        "tiered": SHIPPED_CONFIG,
        "dual": DUAL_CONFIG,
        "dual_ranked": DUAL_CONFIG,
    }


__all__ = [
    "STANDING_ARMS",
    "STANDING_ARM_ORIGIN",
    "TCArmError",
    "arm_configs",
    "deliver",
]
