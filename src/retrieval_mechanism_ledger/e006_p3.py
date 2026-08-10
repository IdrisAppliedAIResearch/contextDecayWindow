from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class UnionKnnGraph:
    k: int
    weights: np.ndarray
    directed_neighbors: tuple[tuple[int, ...], ...]
    content_hashes: tuple[str, ...]


@dataclass(frozen=True)
class FrontierStep:
    hop: int
    hit_indices: tuple[int, ...]
    hit_content_sha256: tuple[str, ...]
    hit_scores: tuple[float, ...]
    all_scores: tuple[float, ...]
    all_associations: tuple[float, ...]
    predecessor_indices: tuple[tuple[int, ...], ...]
    query_only_fallback_count: int


@dataclass(frozen=True)
class FrontierSelection:
    arm: str
    depth: int
    per_step: int
    steps: tuple[FrontierStep, ...]
    ranked_seen_indices: tuple[int, ...]
    ranked_seen_content_sha256: tuple[str, ...]


def _validate_inputs(
    query_cosines: np.ndarray,
    content_hashes: Sequence[str],
    depth: int,
    per_step: int,
) -> np.ndarray:
    query = np.asarray(query_cosines, dtype=np.float64)
    if query.ndim != 1 or len(query) != len(content_hashes):
        raise ValueError("Query cosine and content hash counts must match")
    if len(set(content_hashes)) != len(content_hashes):
        raise ValueError("Content hashes must be unique")
    if depth < 0 or per_step <= 0:
        raise ValueError("Depth must be nonnegative and per_step must be positive")
    if per_step * (depth + 1) > len(query):
        raise ValueError("Registered frontier requests more unique hits than candidates")
    return query


def build_union_knn_graph(
    gram: np.ndarray,
    content_hashes: Sequence[str],
    *,
    k: int = 8,
) -> UnionKnnGraph:
    matrix = np.asarray(gram, dtype=np.float64)
    size = len(content_hashes)
    if matrix.shape != (size, size):
        raise ValueError("Gram matrix shape does not match content hashes")
    if len(set(content_hashes)) != size:
        raise ValueError("Content hashes must be unique")
    if k <= 0 or k >= size:
        raise ValueError("k must be positive and smaller than the graph")

    directed: list[tuple[int, ...]] = []
    weights = np.zeros((size, size), dtype=np.float64)
    for source in range(size):
        order = sorted(
            (index for index in range(size) if index != source),
            key=lambda index: (-float(matrix[source, index]), content_hashes[index]),
        )
        neighbors = tuple(order[:k])
        directed.append(neighbors)
        for destination in neighbors:
            weight = max(float(matrix[source, destination]), 0.0)
            if weight <= 0.0:
                continue
            retained = max(weights[source, destination], weight)
            weights[source, destination] = retained
            weights[destination, source] = retained
    np.fill_diagonal(weights, 0.0)
    return UnionKnnGraph(
        k=k,
        weights=weights,
        directed_neighbors=tuple(directed),
        content_hashes=tuple(content_hashes),
    )


def _rank(
    scores: np.ndarray,
    query_cosines: np.ndarray,
    content_hashes: Sequence[str],
    excluded: set[int],
) -> list[int]:
    return sorted(
        (index for index in range(len(scores)) if index not in excluded),
        key=lambda index: (
            -float(scores[index]),
            -float(query_cosines[index]),
            content_hashes[index],
        ),
    )


def retrieve_fixed_query(
    *,
    query_cosines: np.ndarray,
    content_hashes: Sequence[str],
    depth: int,
    per_step: int,
) -> FrontierSelection:
    query = _validate_inputs(query_cosines, content_hashes, depth, per_step)
    seen: set[int] = set()
    steps = []
    for hop in range(depth + 1):
        hits = tuple(_rank(query, query, content_hashes, seen)[:per_step])
        seen.update(hits)
        steps.append(
            FrontierStep(
                hop=hop,
                hit_indices=hits,
                hit_content_sha256=tuple(content_hashes[index] for index in hits),
                hit_scores=tuple(float(query[index]) for index in hits),
                all_scores=tuple(float(value) for value in query),
                all_associations=tuple(0.0 for _ in query),
                predecessor_indices=tuple(() for _ in query),
                query_only_fallback_count=len(query) - len(seen),
            )
        )
    ranked_seen = tuple(_rank(query, query, content_hashes, set(range(len(query))) - seen))
    return FrontierSelection(
        arm="A0",
        depth=depth,
        per_step=per_step,
        steps=tuple(steps),
        ranked_seen_indices=ranked_seen,
        ranked_seen_content_sha256=tuple(content_hashes[index] for index in ranked_seen),
    )


def retrieve_associative_frontier(
    *,
    query_cosines: np.ndarray,
    graph: UnionKnnGraph,
    depth: int,
    per_step: int,
    query_anchor: float = 0.3,
    association_weight: float = 0.7,
) -> FrontierSelection:
    query = _validate_inputs(
        query_cosines, graph.content_hashes, depth, per_step
    )
    if graph.weights.shape != (len(query), len(query)):
        raise ValueError("Graph shape does not match query cosines")
    if query_anchor != 0.3 or association_weight != 0.7:
        raise ValueError("E006-P3 weights are fixed at 0.3 and 0.7")

    seen: set[int] = set()
    frontier: tuple[int, ...] = ()
    final_scores = query.copy()
    steps = []
    for hop in range(depth + 1):
        if hop == 0:
            associations = np.zeros(len(query), dtype=np.float64)
            predecessors: tuple[tuple[int, ...], ...] = tuple(() for _ in query)
            scores = query.copy()
        else:
            frontier_weights = graph.weights[np.asarray(frontier, dtype=np.int64)]
            associations = frontier_weights.max(axis=0)
            predecessor_rows = []
            for index, association in enumerate(associations):
                if association <= 0.0:
                    predecessor_rows.append(())
                    continue
                predecessor_rows.append(
                    tuple(
                        source
                        for source in frontier
                        if float(graph.weights[source, index]) == float(association)
                    )
                )
            predecessors = tuple(predecessor_rows)
            scores = query_anchor * query + association_weight * associations
        hits = tuple(_rank(scores, query, graph.content_hashes, seen)[:per_step])
        seen.update(hits)
        steps.append(
            FrontierStep(
                hop=hop,
                hit_indices=hits,
                hit_content_sha256=tuple(graph.content_hashes[index] for index in hits),
                hit_scores=tuple(float(scores[index]) for index in hits),
                all_scores=tuple(float(value) for value in scores),
                all_associations=tuple(float(value) for value in associations),
                predecessor_indices=predecessors,
                query_only_fallback_count=sum(
                    index not in seen and associations[index] == 0.0
                    for index in range(len(query))
                ),
            )
        )
        frontier = hits
        final_scores = scores
    ranked_seen = tuple(
        sorted(
            seen,
            key=lambda index: (
                -float(final_scores[index]),
                -float(query[index]),
                graph.content_hashes[index],
            ),
        )
    )
    return FrontierSelection(
        arm="A2",
        depth=depth,
        per_step=per_step,
        steps=tuple(steps),
        ranked_seen_indices=ranked_seen,
        ranked_seen_content_sha256=tuple(
            graph.content_hashes[index] for index in ranked_seen
        ),
    )
