"""Label-blind one-hop traversal ablations for TC-014 exploration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from episodic._packing import EMPTY_PAYLOAD_CHARS
from episodic._selection import additive_weight


class TC014TraversalError(RuntimeError):
    pass


@dataclass(frozen=True)
class EdgeTrace:
    parents: tuple[int, ...]
    children: tuple[int, ...]
    parent_for_child: tuple[int, ...]
    utility: tuple[float, ...]
    raw_marginal: tuple[float, ...]
    parent_cosine: tuple[float, ...]
    no_child: int


def unit_similarity(episodes: Sequence[Any]) -> np.ndarray:
    matrix = np.stack(
        [np.asarray(episode.record["embedding"], dtype=np.float64) for episode in episodes]
    )
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.isfinite(matrix).all() or np.any(norms == 0):
        raise TC014TraversalError("non-finite or zero candidate vector")
    matrix /= norms
    return matrix @ matrix.T


def edge_matrices(
    episodes: Sequence[Any],
    facet_weight: np.ndarray,
    facet_overlap: np.ndarray,
    relevance_scores: Sequence[float],
    parents: Sequence[int],
    allowance: int,
    similarity: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return raw, frozen-ASPECT, and parent-bound edge utilities."""

    count = len(episodes)
    parent_array = np.asarray(parents, dtype=np.int64)
    scores = np.asarray(relevance_scores, dtype=np.float64)
    weights = np.asarray(facet_weight, dtype=np.float64)
    overlap = np.asarray(facet_overlap, dtype=np.float64)
    if not len(parents) or len(set(parents)) != len(parents):
        raise TC014TraversalError("unique nonempty parents required")
    if (
        scores.shape != (count,)
        or weights.shape != (count,)
        or overlap.shape != (count, count)
        or similarity.shape != (count, count)
    ):
        raise TC014TraversalError("edge input shape drift")
    if not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1):
        raise TC014TraversalError("CC80 scores escaped [0,1]")
    costs = np.asarray(
        [additive_weight(episode.record) for episode in episodes], dtype=np.float64
    )
    raw = (
        scores[None, :] * weights[None, :]
        - np.minimum(scores[None, :], scores[parent_array, None])
        * overlap[:, parent_array].T
    )
    base = raw / costs[None, :]
    affinity = np.maximum(0.0, similarity[parent_array])
    bound = base * affinity
    feasible = EMPTY_PAYLOAD_CHARS + costs <= allowance
    excluded = np.zeros(count, dtype=bool)
    excluded[parent_array] = True
    invalid = excluded | ~feasible
    raw[:, invalid] = -math.inf
    base[:, invalid] = -math.inf
    bound[:, invalid] = -math.inf
    return raw, base, bound


def _trace(
    parents: Sequence[int],
    pairs: Sequence[tuple[int, int]],
    utility: np.ndarray,
    raw: np.ndarray,
    similarity: np.ndarray,
) -> EdgeTrace:
    children = tuple(child for _, child in pairs)
    parent_for_child = tuple(parents[row] for row, _ in pairs)
    if len(children) != len(set(children)) or set(children) & set(parents):
        raise TC014TraversalError("assignment repeated a parent or child")
    return EdgeTrace(
        parents=tuple(parents),
        children=children,
        parent_for_child=parent_for_child,
        utility=tuple(float(utility[row, child]) for row, child in pairs),
        raw_marginal=tuple(float(raw[row, child]) for row, child in pairs),
        parent_cosine=tuple(float(similarity[parents[row], child]) for row, child in pairs),
        no_child=len(parents) - len(pairs),
    )


def sequential_assignment(
    parents: Sequence[int],
    utility: np.ndarray,
    raw: np.ndarray,
    relevance_order: Sequence[int],
    similarity: np.ndarray,
) -> EdgeTrace:
    """Assign the best remaining child to each parent in parent order."""

    count = utility.shape[1]
    if utility.shape != raw.shape or utility.shape[0] != len(parents):
        raise TC014TraversalError("sequential matrix shape drift")
    if sorted(relevance_order) != list(range(count)):
        raise TC014TraversalError("CC80 order must permute the store")
    rank = {candidate: position for position, candidate in enumerate(relevance_order)}
    excluded = set(parents)
    pairs: list[tuple[int, int]] = []
    for row, _ in enumerate(parents):
        options = [
            (float(utility[row, child]), -rank[child], child)
            for child in range(count)
            if child not in excluded and math.isfinite(float(utility[row, child]))
        ]
        if not options:
            continue
        value, _, child = max(options)
        if value <= 1e-12 or float(raw[row, child]) <= 1e-12:
            continue
        pairs.append((row, child))
        excluded.add(child)
    return _trace(parents, pairs, utility, raw, similarity)


def _hungarian_min(cost: np.ndarray) -> tuple[int, ...]:
    """Deterministic rectangular Hungarian assignment for rows <= columns."""

    rows, columns = cost.shape
    if not rows or rows > columns or not np.isfinite(cost).all():
        raise TC014TraversalError("invalid Hungarian cost matrix")
    u = np.zeros(rows + 1, dtype=np.float64)
    v = np.zeros(columns + 1, dtype=np.float64)
    p = np.zeros(columns + 1, dtype=np.int64)
    way = np.zeros(columns + 1, dtype=np.int64)
    for row in range(1, rows + 1):
        p[0] = row
        minv = np.full(columns + 1, math.inf, dtype=np.float64)
        used = np.zeros(columns + 1, dtype=bool)
        column0 = 0
        while True:
            used[column0] = True
            row0 = int(p[column0])
            available = np.flatnonzero(~used[1:]) + 1
            current = cost[row0 - 1, available - 1] - u[row0] - v[available]
            better = current < minv[available] - 1e-15
            improved = available[better]
            minv[improved] = current[better]
            way[improved] = column0
            position = int(np.argmin(minv[available]))
            column1 = int(available[position])
            delta = float(minv[column1])
            if not math.isfinite(delta):
                raise TC014TraversalError("Hungarian assignment became unreachable")
            used_columns = np.flatnonzero(used)
            u[p[used_columns]] += delta
            v[used_columns] -= delta
            minv[~used] -= delta
            column0 = column1
            if p[column0] == 0:
                break
        while True:
            column1 = int(way[column0])
            p[column0] = p[column1]
            column0 = column1
            if column0 == 0:
                break
    assignment = np.full(rows, -1, dtype=np.int64)
    for column in range(1, columns + 1):
        if p[column]:
            assignment[int(p[column]) - 1] = column - 1
    if np.any(assignment < 0):
        raise TC014TraversalError("Hungarian assignment omitted a row")
    return tuple(map(int, assignment))


def global_assignment(
    parents: Sequence[int],
    utility: np.ndarray,
    raw: np.ndarray,
    relevance_order: Sequence[int],
    similarity: np.ndarray,
) -> EdgeTrace:
    """Globally maximize unique parent-child utility with optional no-child dummies."""

    count = utility.shape[1]
    if utility.shape != raw.shape or utility.shape[0] != len(parents):
        raise TC014TraversalError("global matrix shape drift")
    if sorted(relevance_order) != list(range(count)):
        raise TC014TraversalError("CC80 order must permute the store")
    candidates = [
        child
        for child in relevance_order
        if child not in set(parents)
        and any(math.isfinite(float(utility[row, child])) for row in range(len(parents)))
    ]
    values = np.full((len(parents), len(candidates) + len(parents)), -1e12, dtype=np.float64)
    if candidates:
        candidate_values = utility[:, np.asarray(candidates, dtype=np.int64)]
        values[:, : len(candidates)] = np.where(
            np.isfinite(candidate_values), candidate_values, -1e12
        )
    values[:, len(candidates) :] = 0.0
    finite = values > -1e11
    maximum = float(values[finite].max()) if np.any(finite) else 0.0
    cost = maximum - values
    assignment = _hungarian_min(cost)
    pairs = []
    for row, column in enumerate(assignment):
        if column >= len(candidates):
            continue
        child = candidates[column]
        if float(utility[row, child]) <= 1e-12 or float(raw[row, child]) <= 1e-12:
            continue
        pairs.append((row, child))
    return _trace(parents, pairs, utility, raw, similarity)


def utility_order(trace: EdgeTrace) -> tuple[int, ...]:
    """Order assigned children by edge utility, then parent and child identity order."""

    positions = sorted(
        range(len(trace.children)),
        key=lambda index: (
            -trace.utility[index],
            trace.parents.index(trace.parent_for_child[index]),
            trace.children[index],
        ),
    )
    return tuple(trace.children[index] for index in positions)


__all__ = [
    "EdgeTrace",
    "TC014TraversalError",
    "edge_matrices",
    "global_assignment",
    "sequential_assignment",
    "unit_similarity",
    "utility_order",
]
