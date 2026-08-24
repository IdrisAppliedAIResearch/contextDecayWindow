"""TC-008 Preflight mechanism: carried relevance plus source-session novelty."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from episodic._selection import (
    ClusterDiversitySelector,
    SelectionResult,
    additive_weight,
    select,
    wrapper_chars,
)

SESSION_LAMBDA = 0.1
SESSION_COST_EXPONENT = 0.0


class TC008SessionSpreadError(RuntimeError):
    pass


@dataclass(frozen=True)
class SessionSpreadOrder:
    order: tuple[int, ...]
    assignments: np.ndarray
    session_ids: tuple[str, ...]
    result: SelectionResult


def session_assignments(episodes: Sequence[Any]) -> tuple[np.ndarray, tuple[str, ...]]:
    """Map source session ids to stable integers in source-session order."""

    if not episodes:
        raise TC008SessionSpreadError("Session spread requires candidates")
    first_order: dict[str, tuple[int, str]] = {}
    for episode in episodes:
        session_id = str(episode.pair.session_id)
        marker = (int(episode.pair.session_order), session_id)
        first_order[session_id] = min(marker, first_order.get(session_id, marker))
    session_ids = tuple(sorted(first_order, key=first_order.__getitem__))
    by_session = {session_id: index for index, session_id in enumerate(session_ids)}
    assignments = np.asarray(
        [by_session[str(episode.pair.session_id)] for episode in episodes],
        dtype=np.int64,
    )
    if set(assignments.tolist()) != set(range(len(session_ids))):
        raise TC008SessionSpreadError("Session assignment is not contiguous")
    return assignments, session_ids


def _complete_budget(episodes: Sequence[Any]) -> int:
    return wrapper_chars() + sum(additive_weight(episode.record) for episode in episodes)


def session_spread_order(
    episodes: Sequence[Any],
    query_vector: np.ndarray,
    *,
    lambda_: float = SESSION_LAMBDA,
) -> SessionSpreadOrder:
    """Return a full deterministic order under session rather than cluster novelty."""

    frozen = tuple(episodes)
    assignments, session_ids = session_assignments(frozen)
    selector = ClusterDiversitySelector(
        lambda_=lambda_,
        cost_exponent=SESSION_COST_EXPONENT,
        assignments=assignments,
        cluster_count=len(session_ids),
    )
    result = select(
        candidates=[episode.record for episode in frozen],
        query_embedding=query_vector,
        selector=selector,
        budget_chars=_complete_budget(frozen),
    )
    by_id = {episode.identity: index for index, episode in enumerate(frozen)}
    order = tuple(by_id[identifier] for identifier in result.selected_ids)
    if sorted(order) != list(range(len(frozen))):
        raise TC008SessionSpreadError("Session selector did not permute the store")
    return SessionSpreadOrder(order, assignments, session_ids, result)


__all__ = [
    "SESSION_COST_EXPONENT",
    "SESSION_LAMBDA",
    "SessionSpreadOrder",
    "TC008SessionSpreadError",
    "session_assignments",
    "session_spread_order",
]
