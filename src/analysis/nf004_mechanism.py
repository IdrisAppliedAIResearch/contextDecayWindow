"""Evidence-blind ranking and packing mechanism for NF-004."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


class NF004MechanismError(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    identity: str
    session_identity: str
    session_order: int
    pair_order: int
    text: str
    chars: int


@dataclass(frozen=True)
class Delivery:
    order: tuple[str, ...]
    selected: tuple[str, ...]
    packed_chars: int


def unit_vector(vector: np.ndarray) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32)
    if array.shape != (1024,):
        raise NF004MechanismError(
            f"Expected a 1024-dimensional vector, got {array.shape}"
        )
    norm = float(np.linalg.norm(array))
    if norm == 0.0:
        raise NF004MechanismError("Zero-norm embedding")
    return array / norm


def ranking_orders(
    candidates: Sequence[Candidate],
    candidate_vectors: np.ndarray,
    query_vector: np.ndarray,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    matrix = np.asarray(candidate_vectors, dtype=np.float32)
    if matrix.shape != (len(candidates), 1024):
        raise NF004MechanismError(
            "Candidate vector matrix does not match candidate count and dimension"
        )
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(norms == 0.0):
        raise NF004MechanismError("Zero-norm candidate embedding")
    scores = (matrix / norms[:, None]) @ unit_vector(query_vector)
    session_scores: dict[str, float] = {}
    for candidate, score in zip(candidates, scores, strict=True):
        session_scores[candidate.session_identity] = max(
            float(score),
            session_scores.get(candidate.session_identity, float("-inf")),
        )
    session_order = tuple(
        sorted(
            range(len(candidates)),
            key=lambda index: (
                -session_scores[candidates[index].session_identity],
                candidates[index].session_order,
                candidates[index].pair_order,
            ),
        )
    )
    pair_order = tuple(
        sorted(
            range(len(candidates)),
            key=lambda index: (
                -float(scores[index]),
                candidates[index].session_order,
                candidates[index].pair_order,
            ),
        )
    )
    return session_order, pair_order


def pack(
    candidates: Sequence[Candidate], order: Sequence[int], budget: int
) -> Delivery:
    if budget < 0:
        raise NF004MechanismError("Budget must be non-negative")
    selected: list[str] = []
    used = 0
    for index in order:
        candidate = candidates[index]
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
    candidates: Sequence[Candidate],
    candidate_vectors: np.ndarray,
    query_vector: np.ndarray,
    budget: int,
) -> dict[str, Delivery]:
    session_order, pair_order = ranking_orders(
        candidates, candidate_vectors, query_vector
    )
    return {
        "S_SESSION_RANK": pack(candidates, session_order, budget),
        "P_PAIR_RANK": pack(candidates, pair_order, budget),
    }


def source_order(candidates: Sequence[Candidate], budget: int) -> Delivery:
    return pack(candidates, tuple(range(len(candidates))), budget)
