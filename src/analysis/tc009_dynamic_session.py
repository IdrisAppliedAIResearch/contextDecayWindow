"""TC-009 mechanism: global semantic competition with cumulative session penalty."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from analysis.tc008_session_spread import session_assignments

DYNAMIC_SESSION_LAMBDA = 0.03


class TC009DynamicSessionError(RuntimeError):
    pass


@dataclass(frozen=True)
class DynamicSessionStep:
    step: int
    candidate_id: str
    candidate_index: int
    session_id: str
    session_count_before: int
    raw_similarity: float
    accumulated_penalty: float
    adjusted_score: float


@dataclass(frozen=True)
class DynamicSessionOrder:
    order: tuple[int, ...]
    session_ids: tuple[str, ...]
    steps: tuple[DynamicSessionStep, ...]


def dynamic_session_order(
    episodes: Sequence[Any],
    dense_scores: Sequence[float],
    *,
    lambda_: float = DYNAMIC_SESSION_LAMBDA,
) -> DynamicSessionOrder:
    """Return a full order from repeated best-remaining-session competition."""

    frozen = tuple(episodes)
    scores = tuple(float(value) for value in dense_scores)
    if not frozen or len(frozen) != len(scores):
        raise TC009DynamicSessionError("Episodes and dense scores must be nonempty and aligned")
    if lambda_ < 0:
        raise TC009DynamicSessionError("Session penalty must be nonnegative")
    assignments, session_ids = session_assignments(frozen)
    queues: list[list[int]] = [[] for _ in session_ids]
    for index, assignment in enumerate(assignments.tolist()):
        queues[int(assignment)].append(index)
    for queue in queues:
        queue.sort(
            key=lambda index: (
                -scores[index],
                int(frozen[index].pair.session_order),
                int(frozen[index].pair.pair_order),
                frozen[index].identity,
            )
        )
    positions = [0] * len(session_ids)
    counts = [0] * len(session_ids)
    order: list[int] = []
    steps: list[DynamicSessionStep] = []
    while len(order) < len(frozen):
        active = [session for session, queue in enumerate(queues) if positions[session] < len(queue)]
        if not active:
            raise TC009DynamicSessionError("Dynamic session competition ended before a full permutation")

        def key(session: int):
            index = queues[session][positions[session]]
            adjusted = scores[index] - float(lambda_) * counts[session]
            return (
                -adjusted,
                int(frozen[index].pair.session_order),
                int(frozen[index].pair.pair_order),
                frozen[index].identity,
            )

        chosen_session = min(active, key=key)
        chosen = queues[chosen_session][positions[chosen_session]]
        count_before = counts[chosen_session]
        penalty = float(lambda_) * count_before
        order.append(chosen)
        steps.append(
            DynamicSessionStep(
                step=len(steps) + 1,
                candidate_id=frozen[chosen].identity,
                candidate_index=chosen,
                session_id=session_ids[chosen_session],
                session_count_before=count_before,
                raw_similarity=scores[chosen],
                accumulated_penalty=penalty,
                adjusted_score=scores[chosen] - penalty,
            )
        )
        positions[chosen_session] += 1
        counts[chosen_session] += 1
    if sorted(order) != list(range(len(frozen))):
        raise TC009DynamicSessionError("Dynamic session order is not a permutation")
    return DynamicSessionOrder(tuple(order), session_ids, tuple(steps))


__all__ = [
    "DYNAMIC_SESSION_LAMBDA",
    "DynamicSessionOrder",
    "DynamicSessionStep",
    "TC009DynamicSessionError",
    "dynamic_session_order",
]
