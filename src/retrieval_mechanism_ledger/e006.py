from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np


FORBIDDEN_MECHANISM_PATH_PARTS = (
    "q_facts_key",
    "rubric",
    "atomic_items",
    "targeted_items",
)


@dataclass(frozen=True)
class ChainStep:
    step: int
    hit_indices: tuple[int, ...]
    hit_content_sha256: tuple[str, ...]
    cue_query_cosine: float
    context_update_cosine: float
    hit_mean_norm_squared: float
    novelty_count: int
    context_fixed_point: bool


@dataclass(frozen=True)
class ChainedSelection:
    depth: int
    per_step: int
    query_weight: float
    retention: float
    steps: tuple[ChainStep, ...]
    ranked_seen_indices: tuple[int, ...]
    ranked_seen_content_sha256: tuple[str, ...]
    final_cue_query_cosine: float


def assert_mechanism_path_allowed(path: str | Path) -> None:
    normalized = str(path).replace("\\", "/").lower()
    if any(part in normalized for part in FORBIDDEN_MECHANISM_PATH_PARTS):
        raise ValueError(f"Mechanism path crosses the measurement boundary: {path}")


def _rank(
    scores: np.ndarray,
    content_hashes: Sequence[str],
    excluded: set[int],
) -> list[int]:
    return sorted(
        (index for index in range(len(scores)) if index not in excluded),
        key=lambda index: (-float(scores[index]), content_hashes[index]),
    )


def retrieve_chained(
    *,
    query_cosines: np.ndarray,
    gram: np.ndarray,
    content_hashes: Sequence[str],
    depth: int,
    per_step: int,
    query_weight: float,
    retention: float,
    fixed_point_tolerance: float = 1e-12,
) -> ChainedSelection:
    query_cosines = np.asarray(query_cosines, dtype=np.float64)
    gram = np.asarray(gram, dtype=np.float64)
    candidate_count = len(query_cosines)
    if gram.shape != (candidate_count, candidate_count):
        raise ValueError("Gram matrix shape does not match query cosines")
    if len(content_hashes) != candidate_count:
        raise ValueError("Content hash count does not match candidates")
    if depth < 0 or per_step <= 0:
        raise ValueError("Depth must be nonnegative and per_step must be positive")
    if per_step * (depth + 1) > candidate_count:
        raise ValueError("Registered chain requests more unique hits than candidates")
    if not 0.0 < query_weight < 1.0 or not 0.0 < retention < 1.0:
        raise ValueError("Registered weights must be strictly between zero and one")

    context_scores = query_cosines.copy()
    query_context = 1.0
    context_weight = 1.0 - query_weight
    reinstatement_weight = 1.0 - retention
    seen: set[int] = set()
    steps: list[ChainStep] = []
    final_cue_scores = query_cosines.copy()
    final_cue_query_cosine = 1.0

    for step_number in range(depth + 1):
        cue_norm = np.sqrt(
            query_weight**2
            + context_weight**2
            + 2.0 * query_weight * context_weight * query_context
        )
        cue_scores = (
            query_weight * query_cosines + context_weight * context_scores
        ) / cue_norm
        cue_query_cosine = float(
            (query_weight + context_weight * query_context) / cue_norm
        )
        order = _rank(cue_scores, content_hashes, seen)
        hits = tuple(order[:per_step])
        novelty_count = sum(index not in seen for index in hits)
        seen.update(hits)

        hit_array = np.array(hits, dtype=np.int64)
        hit_mean_scores = gram[hit_array].mean(axis=0)
        query_hit_mean = float(query_cosines[hit_array].mean())
        context_hit_mean = float(context_scores[hit_array].mean())
        hit_mean_norm_squared = float(
            gram[np.ix_(hit_array, hit_array)].mean()
        )
        context_norm = np.sqrt(
            retention**2
            + reinstatement_weight**2 * hit_mean_norm_squared
            + 2.0 * retention * reinstatement_weight * context_hit_mean
        )
        context_update_cosine = float(
            (retention + reinstatement_weight * context_hit_mean) / context_norm
        )
        context_update_cosine = min(1.0, max(-1.0, context_update_cosine))

        steps.append(
            ChainStep(
                step=step_number,
                hit_indices=hits,
                hit_content_sha256=tuple(content_hashes[index] for index in hits),
                cue_query_cosine=cue_query_cosine,
                context_update_cosine=context_update_cosine,
                hit_mean_norm_squared=hit_mean_norm_squared,
                novelty_count=novelty_count,
                context_fixed_point=(
                    abs(1.0 - context_update_cosine) <= fixed_point_tolerance
                ),
            )
        )
        final_cue_scores = cue_scores
        final_cue_query_cosine = cue_query_cosine
        context_scores = (
            retention * context_scores + reinstatement_weight * hit_mean_scores
        ) / context_norm
        query_context = (
            retention * query_context + reinstatement_weight * query_hit_mean
        ) / context_norm

    ranked_seen = tuple(
        sorted(
            seen,
            key=lambda index: (
                -float(final_cue_scores[index]),
                content_hashes[index],
            ),
        )
    )
    return ChainedSelection(
        depth=depth,
        per_step=per_step,
        query_weight=query_weight,
        retention=retention,
        steps=tuple(steps),
        ranked_seen_indices=ranked_seen,
        ranked_seen_content_sha256=tuple(
            content_hashes[index] for index in ranked_seen
        ),
        final_cue_query_cosine=final_cue_query_cosine,
    )
