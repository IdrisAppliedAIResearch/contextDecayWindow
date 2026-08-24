"""Frozen CC80 episode ranking used by the deployed read path.

CC80 independently min-max normalizes dense cosine and BM25, then combines
them with the registered 0.8/0.2 weights.  This module is deliberately small:
it has no experiment imports and ranks the complete store on every call.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ._errors import EpisodicError
from ._selection import vector

_TOKEN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)


@dataclass(frozen=True)
class CC80Ranking:
    order: tuple[int, ...]
    scores: tuple[float, ...]
    dense_scores: tuple[float, ...]
    bm25_scores: tuple[float, ...]
    dense_normalized: tuple[float, ...]
    bm25_normalized: tuple[float, ...]


def tokenize(text: str) -> list[str]:
    """Tokenize exactly as the frozen TC-005/TC-009 BM25 implementation."""

    return [match.group(0).casefold() for match in _TOKEN.finditer(text)]


def searchable_text(episode: dict) -> str:
    # Frozen adapters may carry the exact original candidate text explicitly.
    # Production rows reconstruct the text used at embedding time.
    return str(
        episode.get(
            "searchable_text",
            f"{episode['user_message']}\n{episode['assistant_message']}",
        )
    )


def _unit(value: object) -> np.ndarray:
    """Normalize one vector exactly as TC-005 did, one candidate at a time."""

    array = vector(value).astype(np.float32, copy=False)
    norm = float(np.linalg.norm(array))
    if not math.isfinite(norm) or norm == 0.0:
        raise EpisodicError("CC80 expected a finite non-zero embedding")
    return array / norm


def bm25_scores(
    episodes: Sequence[dict],
    query_text: str,
    *,
    k1: float,
    b: float,
) -> np.ndarray:
    """Robertson BM25 with the exact frozen constants and token stream."""

    frequencies = [Counter(tokenize(searchable_text(item))) for item in episodes]
    lengths = np.asarray(
        [sum(counter.values()) for counter in frequencies], dtype=np.float64
    )
    scores = np.zeros(len(episodes), dtype=np.float64)
    if not episodes:
        return scores
    average_length = float(np.mean(lengths))
    if average_length == 0.0:
        return scores

    document_frequency: Counter[str] = Counter()
    for counter in frequencies:
        document_frequency.update(counter.keys())
    total = len(episodes)
    idf = {
        term: math.log(1.0 + (total - count + 0.5) / (count + 0.5))
        for term, count in document_frequency.items()
    }
    query_terms = Counter(tokenize(query_text))
    for index, counter in enumerate(frequencies):
        length_ratio = lengths[index] / average_length
        normalization = k1 * (1.0 - b + b * length_ratio)
        score = 0.0
        for term, query_frequency in query_terms.items():
            term_frequency = counter.get(term, 0)
            if not term_frequency:
                continue
            numerator = term_frequency * (k1 + 1.0)
            score += (
                query_frequency
                * idf.get(term, 0.0)
                * numerator
                / (term_frequency + normalization)
            )
        scores[index] = score
    return scores


def normalize_scores(values: Sequence[float]) -> np.ndarray:
    """Min-max normalize one query's component scores.

    TC-009's parity population is nondegenerate.  A real store is not: one
    candidate, an empty query token stream, or identical vectors can make a
    component constant.  Such a component contributes zero rather than making
    the entire context call undefined.
    """

    array = np.asarray(values, dtype=np.float64)
    if not np.isfinite(array).all():
        raise EpisodicError("CC80 received a non-finite component score")
    if array.size == 0:
        return array
    score_range = float(array.max() - array.min())
    if score_range <= 0.0:
        return np.zeros_like(array)
    return (array - array.min()) / score_range


def rank_cc80(
    episodes: Sequence[dict],
    query_text: str,
    query_embedding: object,
    *,
    dense_weight: float,
    bm25_k1: float,
    bm25_b: float,
) -> CC80Ranking:
    """Rank the complete store by frozen CC80 with stable deployed tie-breaks."""

    if not 0.0 <= dense_weight <= 1.0:
        raise EpisodicError("semantic_dense_weight must be in [0, 1]")
    if not episodes:
        return CC80Ranking((), (), (), (), (), ())

    # Per-vector normalization is intentional.  Vectorizing the row norms
    # changes float32 cosine components by ~6e-8 and was enough to alter one
    # frozen CC80 tie plus downstream ASPECT identities in the parity gate.
    matrix = np.stack([_unit(episode["embedding"]) for episode in episodes])
    dense = (matrix @ _unit(query_embedding)).astype(np.float64)
    sparse = bm25_scores(episodes, query_text, k1=bm25_k1, b=bm25_b)
    dense_normalized = normalize_scores(dense)
    sparse_normalized = normalize_scores(sparse)
    scores = dense_weight * dense_normalized + (1.0 - dense_weight) * sparse_normalized
    order = tuple(
        sorted(
            range(len(episodes)),
            key=lambda index: (
                -float(scores[index]),
                int(episodes[index]["turn_number"]),
                str(episodes[index]["id"]),
            ),
        )
    )
    return CC80Ranking(
        order=order,
        scores=tuple(float(value) for value in scores),
        dense_scores=tuple(float(value) for value in dense),
        bm25_scores=tuple(float(value) for value in sparse),
        dense_normalized=tuple(float(value) for value in dense_normalized),
        bm25_normalized=tuple(float(value) for value in sparse_normalized),
    )


__all__ = [
    "CC80Ranking",
    "bm25_scores",
    "normalize_scores",
    "rank_cc80",
    "searchable_text",
    "tokenize",
]
