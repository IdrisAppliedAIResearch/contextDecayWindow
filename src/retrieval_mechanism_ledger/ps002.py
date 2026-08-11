from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

import numpy as np

from src.retrieval_mechanism_ledger.ps001 import (
    SparseEngramAutoassociator,
    SparseRecallTrace,
    fixed_order_norm,
    state_sha256,
    top_k_binary,
)


FORBIDDEN_MECHANISM_PATH_PARTS = (
    "q_facts_key",
    "answer_key",
    "rubric",
    "criteria_evaluator",
    "atomic_items",
    "targeted_items",
)


def assert_binder_path_allowed(path: str | PurePath) -> None:
    normalized = str(path).replace("\\", "/").casefold()
    if any(part in normalized for part in FORBIDDEN_MECHANISM_PATH_PARTS):
        raise ValueError("PS-002 mechanism path crosses the measurement boundary")


def fixed_order_dot(left: np.ndarray, right: np.ndarray) -> float:
    lhs = np.asarray(left, dtype=np.dtype("<f8"))
    rhs = np.asarray(right, dtype=np.dtype("<f8"))
    if lhs.ndim != 1 or rhs.shape != lhs.shape:
        raise ValueError("Dot operands must be equal-length vectors")
    if not np.all(np.isfinite(lhs)) or not np.all(np.isfinite(rhs)):
        raise ValueError("Dot operands must be finite")
    total = np.float64(0.0)
    for index in range(lhs.size):
        total = np.float64(total + np.float64(lhs[index] * rhs[index]))
    return float(total)


def stable_descending_indices(values: np.ndarray) -> np.ndarray:
    scores = np.asarray(values, dtype=np.dtype("<f8"))
    if scores.ndim != 1 or not np.all(np.isfinite(scores)):
        raise ValueError("Scores must be one finite vector")
    indices = np.arange(scores.size, dtype=np.int64)
    return np.lexsort((indices, -scores))


def deterministic_softmax(values: np.ndarray, temperature: float) -> np.ndarray:
    scores = np.asarray(values, dtype=np.dtype("<f8"))
    if scores.ndim != 1 or scores.size == 0 or not np.all(np.isfinite(scores)):
        raise ValueError("Softmax values must be one non-empty finite vector")
    if not np.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("Temperature must be positive and finite")
    maximum = np.float64(scores.max())
    shifted = (scores - maximum) / np.float64(temperature)
    exponentials = np.exp(shifted, dtype=np.float64)
    denominator = np.float64(0.0)
    for value in exponentials:
        denominator = np.float64(denominator + value)
    if not np.isfinite(denominator) or denominator <= 0.0:
        raise FloatingPointError("Softmax denominator is not positive and finite")
    weights = np.asarray(exponentials / denominator, dtype=np.dtype("<f8"))
    weights.setflags(write=False)
    return weights


@dataclass(frozen=True)
class CueBindingRound:
    round_index: int
    candidate_indices: tuple[int, ...]
    candidate_supports: tuple[float, ...]
    candidate_weights: tuple[float, ...]
    cue_margin: float
    cue_sha256: str
    cue_active_count: int
    initial_terminal_hamming: int
    recall: SparseRecallTrace
    emitted_index: int | None
    inhibited_index: int
    outcome: str


@dataclass(frozen=True)
class CueBindingTrace:
    query_sha256: str
    semantic_supports: tuple[float, ...]
    semantic_order: tuple[int, ...]
    rounds: tuple[CueBindingRound, ...]
    emitted_indices: tuple[int, ...]
    emitted_code_hashes: tuple[str, ...]


@dataclass(frozen=True)
class SemanticEngramCueBinder:
    memory: SparseEngramAutoassociator
    episode_vectors: np.ndarray
    support_width: int
    temperature: float

    @classmethod
    def fit(
        cls,
        memory: SparseEngramAutoassociator,
        episode_vectors: np.ndarray,
        *,
        support_width: int,
        temperature: float,
    ) -> SemanticEngramCueBinder:
        vectors = np.asarray(episode_vectors, dtype=np.dtype("<f8"))
        if vectors.shape != (len(memory.codes), memory.input_dimension):
            raise ValueError("Episode vectors must align with the carried memory")
        if not np.all(np.isfinite(vectors)):
            raise ValueError("Episode vectors must be finite")
        norms = np.asarray([fixed_order_norm(row) for row in vectors])
        if not np.all(np.abs(norms - 1.0) <= 1e-12):
            raise ValueError("Episode vectors must be normalized")
        if not 1 <= support_width <= len(memory.codes):
            raise ValueError("Support width is outside the episode population")
        if not np.isfinite(temperature) or temperature <= 0.0:
            raise ValueError("Temperature must be positive and finite")
        stored = vectors.copy()
        stored.setflags(write=False)
        return cls(memory, stored, int(support_width), float(temperature))

    def semantic_support(self, query_vector: np.ndarray) -> np.ndarray:
        query = np.asarray(query_vector, dtype=np.dtype("<f8"))
        if query.shape != (self.memory.input_dimension,) or not np.all(
            np.isfinite(query)
        ):
            raise ValueError("Query vector must be finite and match input dimension")
        norm = fixed_order_norm(query)
        if abs(norm - 1.0) > 1e-12:
            raise ValueError("Query vector must be normalized")
        supports = np.asarray(
            [fixed_order_dot(row, query) for row in self.episode_vectors],
            dtype=np.dtype("<f8"),
        )
        supports.setflags(write=False)
        return supports

    def bind(
        self,
        query_vector: np.ndarray,
        *,
        query_sha256: str,
        rounds: int = 8,
    ) -> CueBindingTrace:
        if rounds <= 0 or rounds > len(self.memory.codes):
            raise ValueError("Round count is outside the episode population")
        if len(query_sha256) != 64:
            raise ValueError("Query identity must be a SHA-256 hex digest")
        try:
            bytes.fromhex(query_sha256)
        except ValueError as exc:
            raise ValueError("Query identity must be a SHA-256 hex digest") from exc

        supports = self.semantic_support(query_vector)
        semantic_order = stable_descending_indices(supports)
        inhibited: set[int] = set()
        emitted: list[int] = []
        records: list[CueBindingRound] = []
        hash_to_index = {value: index for index, value in enumerate(self.memory.code_hashes)}

        for round_index in range(rounds):
            available = [index for index in semantic_order if int(index) not in inhibited]
            candidates = tuple(int(index) for index in available[: self.support_width])
            if len(candidates) != self.support_width:
                raise RuntimeError("Not enough uninhibited support candidates")
            selected_supports = np.asarray(
                [supports[index] for index in candidates], dtype=np.dtype("<f8")
            )
            weights = deterministic_softmax(selected_supports, self.temperature)
            field = np.zeros(self.memory.code_dimension, dtype=np.dtype("<f8"))
            for local_index, episode_index in enumerate(candidates):
                np.add(
                    field,
                    np.float64(weights[local_index]) * self.memory.eta[episode_index],
                    out=field,
                )
            cue, cue_margin = top_k_binary(field, self.memory.active_count)
            recall = self.memory.recall(cue)
            emitted_index = hash_to_index.get(recall.terminal_sha256)
            if recall.cycle:
                outcome = "cycle"
                emitted_index = None
            elif recall.runtime_guard:
                outcome = "runtime_guard"
                emitted_index = None
            elif emitted_index is None:
                outcome = "spurious"
            elif emitted_index in emitted:
                outcome = "duplicate"
                emitted_index = None
            else:
                outcome = "stored"

            if emitted_index is None:
                inhibited_index = candidates[0]
            else:
                inhibited_index = emitted_index
                emitted.append(emitted_index)
            inhibited.add(inhibited_index)
            records.append(
                CueBindingRound(
                    round_index=round_index,
                    candidate_indices=candidates,
                    candidate_supports=tuple(float(value) for value in selected_supports),
                    candidate_weights=tuple(float(value) for value in weights),
                    cue_margin=float(cue_margin),
                    cue_sha256=state_sha256(cue),
                    cue_active_count=int(cue.sum()),
                    initial_terminal_hamming=int(
                        np.count_nonzero(cue != recall.terminal_state)
                    ),
                    recall=recall,
                    emitted_index=emitted_index,
                    inhibited_index=inhibited_index,
                    outcome=outcome,
                )
            )

        return CueBindingTrace(
            query_sha256=query_sha256.lower(),
            semantic_supports=tuple(float(value) for value in supports),
            semantic_order=tuple(int(value) for value in semantic_order),
            rounds=tuple(records),
            emitted_indices=tuple(emitted),
            emitted_code_hashes=tuple(self.memory.code_hashes[index] for index in emitted),
        )
