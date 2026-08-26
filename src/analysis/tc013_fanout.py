"""Label-blind CC80-parent ASPECT fan-out for TC-013."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from episodic._packing import EMPTY_PAYLOAD_CHARS
from episodic._selection import additive_weight


class TC013FanoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class FanoutTrace:
    parents: tuple[int, ...]
    proposed: tuple[int, ...]
    parent_for_child: tuple[int, ...]
    marginal: tuple[float, ...]
    ratio: tuple[float, ...]
    no_positive_child: int
    no_fitting_child: int


def weighted_facet_overlap(
    candidate_facets: Sequence[frozenset[str]], idf: Mapping[str, float]
) -> tuple[np.ndarray, np.ndarray]:
    """Return total facet weight and pairwise shared facet weight."""

    count = len(candidate_facets)
    totals = np.asarray(
        [sum(idf[facet] for facet in facets) for facets in candidate_facets],
        dtype=np.float64,
    )
    overlap = np.zeros((count, count), dtype=np.float64)
    postings: dict[str, list[int]] = {}
    for index, facets in enumerate(candidate_facets):
        for facet in sorted(facets):
            if facet not in idf or not math.isfinite(float(idf[facet])):
                raise TC013FanoutError("missing or non-finite facet IDF")
            postings.setdefault(facet, []).append(index)
    for facet in sorted(postings):
        indices = np.asarray(postings[facet], dtype=np.int64)
        overlap[np.ix_(indices, indices)] += float(idf[facet])
    if not np.allclose(np.diag(overlap), totals, rtol=0.0, atol=1e-12):
        raise TC013FanoutError("facet overlap diagonal drift")
    return totals, overlap


def fanout_aspect(
    episodes: Sequence[Any],
    facet_weight: np.ndarray,
    facet_overlap: np.ndarray,
    relevance_scores: Sequence[float],
    relevance_order: Sequence[int],
    parents: Sequence[int],
    allowance: int,
) -> FanoutTrace:
    """Give every CC80 parent one independent frozen-ASPECT child attempt."""

    count = len(episodes)
    if sorted(relevance_order) != list(range(count)):
        raise TC013FanoutError("CC80 order must permute the store")
    if not parents or len(set(parents)) != len(parents):
        raise TC013FanoutError("fan-out requires unique nonempty parents")
    if any(parent < 0 or parent >= count for parent in parents):
        raise TC013FanoutError("parent escaped the store")
    scores = np.asarray(relevance_scores, dtype=np.float64)
    weights = np.asarray(facet_weight, dtype=np.float64)
    overlap = np.asarray(facet_overlap, dtype=np.float64)
    if scores.shape != (count,) or weights.shape != (count,) or overlap.shape != (count, count):
        raise TC013FanoutError("fan-out input shape drift")
    if not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1):
        raise TC013FanoutError("CC80 scores escaped [0,1]")
    if allowance <= EMPTY_PAYLOAD_CHARS:
        raise TC013FanoutError("allowance cannot hold a payload")

    rank = {candidate: position for position, candidate in enumerate(relevance_order)}
    costs = np.asarray(
        [additive_weight(episode.record) for episode in episodes], dtype=np.int64
    )
    individually_feasible = EMPTY_PAYLOAD_CHARS + costs <= allowance
    excluded = set(parents)
    proposed: list[int] = []
    parent_for_child: list[int] = []
    marginal: list[float] = []
    ratios: list[float] = []
    no_positive = 0
    no_fit = 0

    for parent in parents:
        available = [
            candidate
            for candidate in range(count)
            if candidate not in excluded and bool(individually_feasible[candidate])
        ]
        if not available:
            no_fit += 1
            continue
        raw = (
            scores * weights
            - np.minimum(scores, scores[parent]) * overlap[:, parent]
        )
        options = [
            (
                float(raw[candidate] / costs[candidate]),
                -rank[candidate],
                candidate,
                float(raw[candidate]),
            )
            for candidate in available
        ]
        ratio, _, child, gain = max(options)
        if gain <= 1e-12:
            no_positive += 1
            continue
        proposed.append(child)
        parent_for_child.append(parent)
        marginal.append(gain)
        ratios.append(ratio)
        excluded.add(child)

    if len(proposed) != len(set(proposed)) or set(proposed) & set(parents):
        raise TC013FanoutError("fan-out repeated a child or parent")
    if len(proposed) + no_positive + no_fit != len(parents):
        raise TC013FanoutError("not every parent received exactly one attempt")
    return FanoutTrace(
        parents=tuple(parents),
        proposed=tuple(proposed),
        parent_for_child=tuple(parent_for_child),
        marginal=tuple(marginal),
        ratio=tuple(ratios),
        no_positive_child=no_positive,
        no_fitting_child=no_fit,
    )


__all__ = [
    "FanoutTrace",
    "TC013FanoutError",
    "fanout_aspect",
    "weighted_facet_overlap",
]
