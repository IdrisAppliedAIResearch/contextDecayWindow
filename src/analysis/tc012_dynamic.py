"""Label-blind registered TC-012 dynamic-ASPECT mechanisms."""

from __future__ import annotations

from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.tc011_spread import RHO, W_Q, unit
from episodic._packing import EMPTY_PAYLOAD_CHARS
from episodic._selection import additive_weight


class TC012DynamicError(RuntimeError):
    pass


def normalize_scores(values: np.ndarray) -> np.ndarray:
    span = float(values.max() - values.min())
    if not np.isfinite(values).all() or span <= 0:
        raise TC012DynamicError("degenerate dynamic dense scores")
    return (values - values.min()) / span


def dynamic_scores(
    matrix: np.ndarray, cue: np.ndarray, bm25_contribution: np.ndarray
) -> np.ndarray:
    return 0.8 * normalize_scores(matrix @ cue) + bm25_contribution


def _feasible(
    episodes: Sequence[Any], excluded: set[int], spent: int, allowance: int
) -> list[int]:
    return [
        index
        for index in range(len(episodes))
        if index not in excluded
        and spent + additive_weight(episodes[index].record) <= allowance
    ]


def _coverage(
    selected: Sequence[int],
    candidate_facets: Sequence[frozenset[str]],
    idf: Mapping[str, float],
    scores: np.ndarray,
) -> dict[str, float]:
    state: dict[str, float] = {}
    for index in selected:
        for facet in sorted(candidate_facets[index]):
            state[facet] = max(
                state.get(facet, 0.0), scores[index] * idf[facet]
            )
    return state


def dynamic_aspect(
    episodes: Sequence[Any],
    matrix: np.ndarray,
    candidate_facets: Sequence[frozenset[str]],
    idf: Mapping[str, float],
    query_vector: np.ndarray,
    query_facets: frozenset[str],
    bm25_contribution: np.ndarray,
    relevance_order: Sequence[int],
    initial: Sequence[int],
    allowance: int,
    *,
    residual: bool,
) -> tuple[tuple[int, ...], dict[str, Any]]:
    count = len(episodes)
    if sorted(relevance_order) != list(range(count)):
        raise TC012DynamicError("CC80 order must permute the store")
    if not initial or len(set(initial)) != len(initial):
        raise TC012DynamicError("dynamic ASPECT requires a unique nonempty seed")
    query = unit(np.asarray(query_vector, dtype=np.float64))
    context = unit(matrix[np.asarray(initial)].mean(axis=0))
    selected = list(initial)
    excluded = set(initial)
    chosen: list[int] = []
    spent = EMPTY_PAYLOAD_CHARS
    cue_query: list[float] = []
    uncovered_counts: list[int] = []
    residual_fallbacks = 0
    rank = {candidate: position for position, candidate in enumerate(relevance_order)}
    while True:
        fit = _feasible(episodes, excluded, spent, allowance)
        if not fit:
            reason = "no_complete_candidate_fits"
            break
        if residual:
            covered_query = set().union(
                *(candidate_facets[index] for index in selected)
            )
            uncovered = set(query_facets) - covered_query
            weights = np.asarray(
                [
                    sum(
                        idf.get(facet, 0.0)
                        for facet in sorted(candidate_facets[index] & uncovered)
                    )
                    for index in range(count)
                ],
                dtype=np.float64,
            )
            if uncovered and float(weights.sum()) > 0:
                aspect_cue = unit(weights @ matrix)
                cue = unit(W_Q * query + (1.0 - W_Q) * aspect_cue)
            else:
                cue = query
                residual_fallbacks += 1
            uncovered_counts.append(len(uncovered))
        else:
            cue = unit(W_Q * query + (1.0 - W_Q) * context)
            uncovered_counts.append(0)
        scores = dynamic_scores(matrix, cue, bm25_contribution)
        covered = _coverage(selected, candidate_facets, idf, scores)
        options = []
        for candidate in fit:
            raw = sum(
                max(
                    0.0,
                    scores[candidate] * idf[facet] - covered.get(facet, 0.0),
                )
                for facet in sorted(candidate_facets[candidate])
            )
            ratio = raw / additive_weight(episodes[candidate].record)
            options.append((ratio, -rank[candidate], candidate, raw))
        _, _, candidate, raw = max(options)
        if raw <= 1e-12:
            reason = "no_positive_marginal"
            break
        chosen.append(candidate)
        selected.append(candidate)
        excluded.add(candidate)
        spent += additive_weight(episodes[candidate].record)
        context = unit(RHO * context + (1.0 - RHO) * matrix[candidate])
        cue_query.append(float(cue @ query))
    return tuple(chosen), {
        "steps": len(chosen),
        "solo_chars": spent,
        "cue_query_median": float(median(cue_query)) if cue_query else 1.0,
        "cue_query_final": cue_query[-1] if cue_query else 1.0,
        "uncovered_median": float(median(uncovered_counts)) if uncovered_counts else 0.0,
        "residual_fallbacks": residual_fallbacks,
        "stopping_reason": reason,
    }


__all__ = [
    "TC012DynamicError",
    "dynamic_aspect",
    "dynamic_scores",
    "normalize_scores",
]
