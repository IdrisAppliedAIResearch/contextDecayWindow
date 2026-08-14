"""Evidence-blind ranking and packing mechanism for NF-005."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


class NF005MechanismError(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    identity: str
    parent_index: int
    session_order: int
    episode_order: int
    turn_offset: int
    text: str
    chars: int


@dataclass(frozen=True)
class Delivery:
    order: tuple[str, ...]
    selected: tuple[str, ...]
    packed_chars: int


def unit_rows(vectors: np.ndarray, expected_rows: int) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float64)
    if matrix.shape != (expected_rows, 1024):
        raise NF005MechanismError(
            f"Expected {(expected_rows, 1024)} vectors, got {matrix.shape}"
        )
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(~np.isfinite(norms)) or np.any(norms == 0.0):
        raise NF005MechanismError("Candidate vectors must be finite and non-zero")
    return matrix / norms[:, None]


def unit_vector(vector: np.ndarray) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float64)
    if array.shape != (1024,):
        raise NF005MechanismError(f"Expected a 1024-vector, got {array.shape}")
    norm = float(np.linalg.norm(array))
    if not np.isfinite(norm) or norm == 0.0:
        raise NF005MechanismError("Query vector must be finite and non-zero")
    return array / norm


def cosine_scores(vectors: np.ndarray, query_vector: np.ndarray) -> np.ndarray:
    return unit_rows(vectors, len(vectors)) @ unit_vector(query_vector)


def _source_key(candidate: Candidate) -> tuple[int, int, int]:
    return candidate.session_order, candidate.episode_order, candidate.turn_offset


def own_score_order(
    candidates: Sequence[Candidate],
    vectors: np.ndarray,
    query_vector: np.ndarray,
) -> tuple[int, ...]:
    scores = cosine_scores(vectors, query_vector)
    return tuple(
        sorted(
            range(len(candidates)),
            key=lambda index: (-float(scores[index]), *_source_key(candidates[index])),
        )
    )


def inherited_score_order(
    candidates: Sequence[Candidate],
    parent_vectors: np.ndarray,
    query_vector: np.ndarray,
) -> tuple[int, ...]:
    parent_scores = cosine_scores(parent_vectors, query_vector)
    if any(
        candidate.parent_index < 0 or candidate.parent_index >= len(parent_scores)
        for candidate in candidates
    ):
        raise NF005MechanismError("Candidate parent index is out of range")
    return tuple(
        sorted(
            range(len(candidates)),
            key=lambda index: (
                -float(parent_scores[candidates[index].parent_index]),
                *_source_key(candidates[index]),
            ),
        )
    )


def pack(
    candidates: Sequence[Candidate], order: Sequence[int], budget: int
) -> Delivery:
    if budget < 0:
        raise NF005MechanismError("Budget must be non-negative")
    if len(order) != len(candidates) or set(order) != set(range(len(candidates))):
        raise NF005MechanismError("Order must be a permutation of every candidate")
    used = 0
    selected: list[str] = []
    for index in order:
        candidate = candidates[index]
        if candidate.chars != len(candidate.text):
            raise NF005MechanismError("Candidate character cost differs from its text")
        if used + candidate.chars > budget:
            continue
        used += candidate.chars
        selected.append(candidate.identity)
    return Delivery(
        order=tuple(candidates[index].identity for index in order),
        selected=tuple(selected),
        packed_chars=used,
    )


def retrieve(
    episodes: Sequence[Candidate],
    turns: Sequence[Candidate],
    episode_vectors: np.ndarray,
    turn_vectors: np.ndarray,
    query_vector: np.ndarray,
    budget: int,
) -> dict[str, Delivery]:
    episode_order = own_score_order(episodes, episode_vectors, query_vector)
    inherited_order = inherited_score_order(turns, episode_vectors, query_vector)
    turn_order = own_score_order(turns, turn_vectors, query_vector)
    return {
        "E_EPISODE_RANK_EPISODE_PACK": pack(episodes, episode_order, budget),
        "E_EPISODE_RANK_TURN_PACK": pack(turns, inherited_order, budget),
        "T_TURN_RANK_TURN_PACK": pack(turns, turn_order, budget),
    }


def source_order(candidates: Sequence[Candidate], budget: int) -> Delivery:
    return pack(candidates, tuple(range(len(candidates))), budget)
