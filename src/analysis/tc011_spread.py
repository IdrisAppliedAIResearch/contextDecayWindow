"""Registered TC-011 protected-spread mechanisms.

This module is label blind.  It receives candidate text, vectors, CC80 scores
and an already packed semantic seed; it never imports outcome annotations.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from episodic._packing import EMPTY_PAYLOAD_CHARS
from episodic._selection import additive_weight

W_Q = 0.3
RHO = 0.5
OBJECT_DEPENDENCIES = frozenset(
    {"dobj", "obj", "pobj", "attr", "oprd", "dative", "nsubjpass"}
)


class TC011SpreadError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpreadTrace:
    order: tuple[int, ...]
    marginal: tuple[float, ...]
    auxiliary: tuple[float, ...]
    solo_chars: int
    stopping_reason: str


def unit(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float64)
    norm = float(np.linalg.norm(value))
    if not np.isfinite(value).all() or not math.isfinite(norm) or norm == 0:
        raise TC011SpreadError("non-finite or zero vector")
    return value / norm


def unit_matrix(episodes: Sequence[Any]) -> np.ndarray:
    return np.stack(
        [unit(np.asarray(episode.record["embedding"], dtype=np.float64)) for episode in episodes]
    )


def _rank_map(relevance_order: Sequence[int], count: int) -> dict[int, int]:
    if sorted(relevance_order) != list(range(count)):
        raise TC011SpreadError("CC80 order must permute the store")
    return {candidate: position for position, candidate in enumerate(relevance_order)}


def _feasible(
    episodes: Sequence[Any], excluded: set[int], spent: int, allowance: int
) -> list[int]:
    return [
        index
        for index in range(len(episodes))
        if index not in excluded
        and spent + additive_weight(episodes[index].record) <= allowance
    ]


def _normalized_words(tokens: Any) -> str:
    words = [
        token.lemma_.casefold()
        for token in tokens
        if not token.is_space
        and not token.is_punct
        and (not token.is_stop or token.like_num)
    ]
    return "_".join(words)


def extract_facets(doc: Any) -> frozenset[str]:
    """Extract the exact six registered deterministic facet families."""

    found: set[str] = set()
    for entity in doc.ents:
        value = _normalized_words(entity)
        if value:
            found.add(f"entity:{entity.label_}:{value}")
            if entity.label_ == "DATE":
                found.add(f"date:{value}")
    for token in doc:
        if token.like_num:
            found.add(f"number:{token.lower_}")
        if token.pos_ == "VERB":
            found.add(f"event:{token.lemma_.casefold()}")
        if (
            token.dep_ in OBJECT_DEPENDENCIES
            and token.head.pos_ in {"VERB", "AUX"}
        ):
            value = _normalized_words(token.subtree)
            if value:
                found.add(
                    f"relation:{token.head.lemma_.casefold()}:{token.dep_}:{value}"
                )
    for chunk in doc.noun_chunks:
        value = _normalized_words(chunk)
        if value:
            found.add(f"noun:{value}")
    return frozenset(found)


def facet_idf(
    candidate_facets: Sequence[frozenset[str]],
) -> tuple[dict[str, float], dict[str, int]]:
    count = len(candidate_facets)
    document_frequency = Counter(
        facet for candidate in candidate_facets for facet in sorted(candidate)
    )
    idf = {
        facet: math.log((count + 1) / (frequency + 1)) + 1.0
        for facet, frequency in document_frequency.items()
    }
    families = Counter(
        facet.split(":", 1)[0]
        for candidate in candidate_facets
        for facet in sorted(candidate)
    )
    return idf, dict(families)


def logdet_spread(
    episodes: Sequence[Any],
    matrix: np.ndarray,
    relevance_scores: Sequence[float],
    relevance_order: Sequence[int],
    initial: Sequence[int],
    allowance: int,
) -> SpreadTrace:
    """Greedy exact-cost-normalized marginal log determinant."""

    count = len(episodes)
    rank = _rank_map(relevance_order, count)
    scores = np.asarray(relevance_scores, dtype=np.float64)
    if matrix.shape[0] != count or scores.shape != (count,):
        raise TC011SpreadError("LOGDET input shape drift")
    if not len(initial) or len(set(initial)) != len(initial):
        raise TC011SpreadError("LOGDET requires a unique nonempty seed")
    if not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1):
        raise TC011SpreadError("CC80 scores escaped [0,1]")

    roots = np.sqrt(scores)
    seed = np.asarray(initial, dtype=np.int64)
    gram_seed = matrix[seed] @ matrix.T
    kernel_seed_all = roots[seed, None] * roots[None, :] * gram_seed
    kernel_seed = kernel_seed_all[:, seed].copy()
    kernel_seed.flat[:: len(seed) + 1] += 1.0
    cholesky = np.linalg.cholesky(kernel_seed)
    projection = np.linalg.solve(cholesky, kernel_seed_all).T
    residual = 1.0 + scores - np.sum(projection * projection, axis=1)
    if np.any(residual < 1.0 - 1e-9):
        raise TC011SpreadError("LOGDET residual left its mathematical range")
    residual = np.maximum(residual, 1.0)

    excluded = set(initial)
    chosen: list[int] = []
    marginal: list[float] = []
    remaining_positive: list[float] = []
    spent = EMPTY_PAYLOAD_CHARS
    while True:
        fit = _feasible(episodes, excluded, spent, allowance)
        if not fit:
            reason = "no_complete_candidate_fits"
            break
        options = []
        for candidate in fit:
            raw = math.log(max(1.0, float(residual[candidate])))
            ratio = raw / additive_weight(episodes[candidate].record)
            options.append((ratio, -rank[candidate], candidate, raw))
        _, _, candidate, raw = max(options)
        if raw <= 1e-12:
            reason = "no_positive_marginal"
            break

        chosen.append(candidate)
        excluded.add(candidate)
        marginal.append(raw)
        spent += additive_weight(episodes[candidate].record)

        cross = roots[candidate] * roots * (matrix @ matrix[candidate])
        cross[candidate] += 1.0
        diagonal = math.sqrt(max(float(residual[candidate]), 1e-15))
        correction = (
            cross - projection @ projection[candidate]
        ) / diagonal
        projection = np.column_stack((projection, correction))
        next_residual = residual - correction * correction
        if np.any(next_residual > residual + 1e-9):
            raise TC011SpreadError("LOGDET residual increased")
        residual = np.maximum(next_residual, 1.0)
        remaining_positive.append(float(np.sum(np.log(residual) > 1e-12)))

    return SpreadTrace(
        order=tuple(chosen),
        marginal=tuple(marginal),
        auxiliary=tuple(remaining_positive),
        solo_chars=spent,
        stopping_reason=reason,
    )


def aspect_spread(
    episodes: Sequence[Any],
    candidate_facets: Sequence[frozenset[str]],
    idf: Mapping[str, float],
    relevance_scores: Sequence[float],
    relevance_order: Sequence[int],
    initial: Sequence[int],
    allowance: int,
) -> SpreadTrace:
    """Greedy CC80-weighted saturation of deterministic text facets."""

    count = len(episodes)
    rank = _rank_map(relevance_order, count)
    scores = np.asarray(relevance_scores, dtype=np.float64)
    if len(candidate_facets) != count or scores.shape != (count,):
        raise TC011SpreadError("ASPECT input shape drift")
    if not len(initial) or len(set(initial)) != len(initial):
        raise TC011SpreadError("ASPECT requires a unique nonempty seed")

    covered: dict[str, float] = {}
    for candidate in initial:
        for facet in sorted(candidate_facets[candidate]):
            covered[facet] = max(
                covered.get(facet, 0.0), scores[candidate] * idf[facet]
            )
    excluded = set(initial)
    chosen: list[int] = []
    marginal: list[float] = []
    covered_counts: list[float] = []
    spent = EMPTY_PAYLOAD_CHARS
    while True:
        fit = _feasible(episodes, excluded, spent, allowance)
        if not fit:
            reason = "no_complete_candidate_fits"
            break
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

        prior = dict(covered)
        chosen.append(candidate)
        excluded.add(candidate)
        marginal.append(raw)
        spent += additive_weight(episodes[candidate].record)
        for facet in sorted(candidate_facets[candidate]):
            covered[facet] = max(
                covered.get(facet, 0.0), scores[candidate] * idf[facet]
            )
        if any(covered[key] + 1e-12 < value for key, value in prior.items()):
            raise TC011SpreadError("ASPECT coverage decreased")
        covered_counts.append(float(len(covered)))

    return SpreadTrace(
        order=tuple(chosen),
        marginal=tuple(marginal),
        auxiliary=tuple(covered_counts),
        solo_chars=spent,
        stopping_reason=reason,
    )


def chain_spread(
    episodes: Sequence[Any],
    matrix: np.ndarray,
    query_vector: np.ndarray,
    relevance_order: Sequence[int],
    initial: Sequence[int],
    allowance: int,
    *,
    anchored: bool,
) -> SpreadTrace:
    """Run the registered anchored or pure growing-centroid chain."""

    count = len(episodes)
    rank = _rank_map(relevance_order, count)
    if matrix.shape[0] != count:
        raise TC011SpreadError("CHAIN matrix shape drift")
    if not len(initial) or len(set(initial)) != len(initial):
        raise TC011SpreadError("CHAIN requires a unique nonempty seed")
    query = unit(query_vector)
    context = unit(matrix[np.asarray(initial, dtype=np.int64)].mean(axis=0))
    excluded = set(initial)
    chosen: list[int] = []
    selected_cosine: list[float] = []
    query_cosine: list[float] = []
    spent = EMPTY_PAYLOAD_CHARS
    while True:
        fit = _feasible(episodes, excluded, spent, allowance)
        if not fit:
            reason = "no_complete_candidate_fits"
            break
        cue = unit(W_Q * query + (1.0 - W_Q) * context) if anchored else context
        scores = matrix[np.asarray(fit)] @ cue
        candidate, candidate_score = min(
            zip(fit, scores, strict=True),
            key=lambda item: (-float(item[1]), rank[item[0]]),
        )
        chosen.append(candidate)
        excluded.add(candidate)
        selected_cosine.append(float(candidate_score))
        spent += additive_weight(episodes[candidate].record)
        context = unit(RHO * context + (1.0 - RHO) * matrix[candidate])
        query_cosine.append(float(context @ query))

    return SpreadTrace(
        order=tuple(chosen),
        marginal=tuple(selected_cosine),
        auxiliary=tuple(query_cosine),
        solo_chars=spent,
        stopping_reason=reason,
    )


__all__ = [
    "OBJECT_DEPENDENCIES",
    "RHO",
    "SpreadTrace",
    "TC011SpreadError",
    "W_Q",
    "aspect_spread",
    "chain_spread",
    "extract_facets",
    "facet_idf",
    "logdet_spread",
    "unit",
    "unit_matrix",
]
