from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Sequence

import numpy as np

from src.retrieval_mechanism_ledger.ps001 import (
    SparseEngramAutoassociator,
    SparseRecallTrace,
    array_sha256,
    fixed_order_norm,
    state_sha256,
    top_k_binary,
)
from src.retrieval_mechanism_ledger.ps002 import (
    deterministic_softmax,
    fixed_order_dot,
    stable_descending_indices,
)


SUPPORT_WIDTH = 4
TEMPERATURE = 0.025
TARGET_OUTPUTS = 8
ATTEMPT_BUDGET = 16


def deterministic_probe_family(
    field: np.ndarray,
    *,
    active_count: int,
    probe_count: int,
    swap_count: int,
) -> tuple[tuple[np.ndarray, ...], float]:
    values = np.asarray(field, dtype=np.dtype("<f8"))
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("Probe field must be one finite vector")
    if probe_count < 2 or swap_count <= 0:
        raise ValueError("Probe and swap counts must be positive and nontrivial")
    if active_count <= 0 or active_count >= values.size:
        raise ValueError("Active count is outside the probe field")
    boundary_span = (probe_count - 1) * swap_count
    if boundary_span > active_count or active_count + boundary_span > values.size:
        raise ValueError("Probe family crosses the active boundary")

    order = stable_descending_indices(values)
    base, margin = top_k_binary(values, active_count)
    base.setflags(write=False)
    probes = [base]
    for probe_index in range(1, probe_count):
        probe = base.copy()
        offset = (probe_index - 1) * swap_count
        for local_index in range(swap_count):
            probe[int(order[active_count - 1 - offset - local_index])] = 0
            probe[int(order[active_count + offset + local_index])] = 1
        if int(probe.sum()) != active_count:
            raise AssertionError("Probe construction changed the active count")
        probe.setflags(write=False)
        probes.append(probe)
    return tuple(probes), float(margin)


@dataclass(frozen=True)
class AmbiguityProbe:
    probe_index: int
    cue_sha256: str
    cue_active_count: int
    recall: SparseRecallTrace
    stored_index: int | None


@dataclass(frozen=True)
class ResolutionAttempt:
    attempt_index: int
    candidate_indices: tuple[int, ...]
    candidate_supports: tuple[float, ...]
    candidate_weights: tuple[float, ...]
    field_sha256: str
    cue_margin: float
    base_cue_sha256: str
    probes: tuple[AmbiguityProbe, ...]
    outcome: str
    consensus_index: int | None
    emitted_index: int | None
    inhibited_index: int


@dataclass(frozen=True)
class AmbiguityResolutionTrace:
    query_sha256: str
    semantic_supports: tuple[float, ...]
    semantic_order: tuple[int, ...]
    attempts: tuple[ResolutionAttempt, ...]
    emitted_indices: tuple[int, ...]
    emitted_code_hashes: tuple[str, ...]
    exhausted: bool


def classify_consensus(
    probes: Sequence[AmbiguityProbe], emitted_indices: Collection[int]
) -> tuple[str, int | None]:
    if not probes:
        raise ValueError("Consensus requires at least one probe")
    recalls = tuple(row.recall for row in probes)
    stored_indices = tuple(row.stored_index for row in probes)
    if any(row.runtime_guard for row in recalls):
        return "runtime_guard", None
    if any(row.cycle for row in recalls):
        return "cycle", None
    if any(index is None for index in stored_indices):
        return "spurious", None
    if len(set(stored_indices)) != 1:
        return "disagreement", None
    consensus_index = int(stored_indices[0])
    if consensus_index in emitted_indices:
        return "duplicate", None
    return "accepted", consensus_index


@dataclass(frozen=True)
class EngramAmbiguityResolver:
    memory: SparseEngramAutoassociator
    episode_vectors: np.ndarray
    probe_count: int
    swap_count: int

    @classmethod
    def fit(
        cls,
        memory: SparseEngramAutoassociator,
        episode_vectors: np.ndarray,
        *,
        probe_count: int,
        swap_count: int,
    ) -> EngramAmbiguityResolver:
        vectors = np.asarray(episode_vectors, dtype=np.dtype("<f8"))
        if vectors.shape != (len(memory.codes), memory.input_dimension):
            raise ValueError("Episode vectors must align with the carried memory")
        if not np.all(np.isfinite(vectors)):
            raise ValueError("Episode vectors must be finite")
        norms = np.asarray([fixed_order_norm(row) for row in vectors])
        if not np.all(np.abs(norms - 1.0) <= 1e-12):
            raise ValueError("Episode vectors must be normalized")
        if probe_count not in (3, 5) or swap_count not in (1, 4):
            raise ValueError("Resolver parameters are outside the registered grid")
        deterministic_probe_family(
            np.arange(memory.code_dimension, dtype=np.float64),
            active_count=memory.active_count,
            probe_count=probe_count,
            swap_count=swap_count,
        )
        stored = vectors.copy()
        stored.setflags(write=False)
        return cls(memory, stored, int(probe_count), int(swap_count))

    def semantic_support(self, query_vector: np.ndarray) -> np.ndarray:
        query = np.asarray(query_vector, dtype=np.dtype("<f8"))
        if query.shape != (self.memory.input_dimension,) or not np.all(
            np.isfinite(query)
        ):
            raise ValueError("Query vector must be finite and match input dimension")
        if abs(fixed_order_norm(query) - 1.0) > 1e-12:
            raise ValueError("Query vector must be normalized")
        supports = np.asarray(
            [fixed_order_dot(row, query) for row in self.episode_vectors],
            dtype=np.dtype("<f8"),
        )
        supports.setflags(write=False)
        return supports

    def resolve(
        self,
        query_vector: np.ndarray,
        *,
        query_sha256: str,
        target_outputs: int = TARGET_OUTPUTS,
        attempt_budget: int = ATTEMPT_BUDGET,
    ) -> AmbiguityResolutionTrace:
        if len(query_sha256) != 64:
            raise ValueError("Query identity must be a SHA-256 hex digest")
        try:
            bytes.fromhex(query_sha256)
        except ValueError as exc:
            raise ValueError("Query identity must be a SHA-256 hex digest") from exc
        if target_outputs <= 0 or target_outputs > TARGET_OUTPUTS:
            raise ValueError("Target output count exceeds the registered bound")
        if attempt_budget <= 0 or attempt_budget > ATTEMPT_BUDGET:
            raise ValueError("Attempt budget exceeds the registered bound")
        if attempt_budget < target_outputs:
            raise ValueError("Attempt budget cannot be smaller than target outputs")

        supports = self.semantic_support(query_vector)
        semantic_order = stable_descending_indices(supports)
        hash_to_index = {
            identity: index for index, identity in enumerate(self.memory.code_hashes)
        }
        inhibited: set[int] = set()
        emitted: list[int] = []
        attempts: list[ResolutionAttempt] = []

        for attempt_index in range(attempt_budget):
            if len(emitted) == target_outputs:
                break
            available = [
                int(index) for index in semantic_order if int(index) not in inhibited
            ]
            candidates = tuple(available[:SUPPORT_WIDTH])
            if len(candidates) != SUPPORT_WIDTH:
                raise RuntimeError("Not enough uninhibited support candidates")
            selected_supports = np.asarray(
                [supports[index] for index in candidates], dtype=np.dtype("<f8")
            )
            weights = deterministic_softmax(selected_supports, TEMPERATURE)
            field = np.zeros(self.memory.code_dimension, dtype=np.dtype("<f8"))
            for local_index, episode_index in enumerate(candidates):
                np.add(
                    field,
                    np.float64(weights[local_index]) * self.memory.eta[episode_index],
                    out=field,
                )
            probes, cue_margin = deterministic_probe_family(
                field,
                active_count=self.memory.active_count,
                probe_count=self.probe_count,
                swap_count=self.swap_count,
            )
            probe_records: list[AmbiguityProbe] = []
            for probe_index, cue in enumerate(probes):
                recall = self.memory.recall(cue)
                stored_index = hash_to_index.get(recall.terminal_sha256)
                if recall.cycle or recall.runtime_guard:
                    stored_index = None
                probe_records.append(
                    AmbiguityProbe(
                        probe_index=probe_index,
                        cue_sha256=state_sha256(cue),
                        cue_active_count=int(cue.sum()),
                        recall=recall,
                        stored_index=stored_index,
                    )
                )

            outcome, consensus_index = classify_consensus(probe_records, emitted)

            if consensus_index is None:
                emitted_index = None
                inhibited_index = candidates[0]
            else:
                emitted_index = consensus_index
                emitted.append(emitted_index)
                inhibited_index = emitted_index
            inhibited.add(inhibited_index)
            attempts.append(
                ResolutionAttempt(
                    attempt_index=attempt_index,
                    candidate_indices=candidates,
                    candidate_supports=tuple(float(value) for value in selected_supports),
                    candidate_weights=tuple(float(value) for value in weights),
                    field_sha256=array_sha256(field),
                    cue_margin=cue_margin,
                    base_cue_sha256=probe_records[0].cue_sha256,
                    probes=tuple(probe_records),
                    outcome=outcome,
                    consensus_index=consensus_index,
                    emitted_index=emitted_index,
                    inhibited_index=inhibited_index,
                )
            )

        return AmbiguityResolutionTrace(
            query_sha256=query_sha256.lower(),
            semantic_supports=tuple(float(value) for value in supports),
            semantic_order=tuple(int(value) for value in semantic_order),
            attempts=tuple(attempts),
            emitted_indices=tuple(emitted),
            emitted_code_hashes=tuple(self.memory.code_hashes[index] for index in emitted),
            exhausted=len(emitted) != target_outputs,
        )
