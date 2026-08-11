from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .e006 import assert_mechanism_path_allowed


def pattern_sha256(pattern: np.ndarray) -> str:
    state = np.asarray(pattern, dtype=np.int8)
    if state.ndim != 1 or not np.all(np.isin(state, (-1, 1))):
        raise ValueError("Pattern must be a one-dimensional bipolar vector")
    return hashlib.sha256(state.tobytes(order="C")).hexdigest()


def deterministic_flip_indices(
    content_sha256: str, dimension: int, count: int
) -> tuple[int, ...]:
    if len(content_sha256) != 64:
        raise ValueError("Content identity must be a SHA-256 hex digest")
    try:
        seed = bytes.fromhex(content_sha256)
    except ValueError as exc:
        raise ValueError("Content identity must be a SHA-256 hex digest") from exc
    if dimension <= 0 or not 0 <= count <= dimension:
        raise ValueError("Flip count must be between zero and the dimension")

    selected: list[int] = []
    seen: set[int] = set()
    counter = 0
    while len(selected) < count:
        block = hashlib.sha256(seed + counter.to_bytes(8, "big")).digest()
        counter += 1
        for offset in range(0, len(block), 4):
            candidate = int.from_bytes(block[offset : offset + 4], "big") % dimension
            if candidate in seen:
                continue
            seen.add(candidate)
            selected.append(candidate)
            if len(selected) == count:
                break
    return tuple(selected)


def degrade_pattern(
    pattern: np.ndarray, content_sha256: str, count: int
) -> tuple[np.ndarray, tuple[int, ...]]:
    state = np.asarray(pattern, dtype=np.int8)
    if state.ndim != 1 or not np.all(np.isin(state, (-1, 1))):
        raise ValueError("Pattern must be a one-dimensional bipolar vector")
    indices = deterministic_flip_indices(content_sha256, state.size, count)
    degraded = state.copy()
    if indices:
        degraded[np.asarray(indices, dtype=np.int64)] *= -1
    return degraded, indices


@dataclass(frozen=True)
class RecallTrace:
    converged: bool
    sweeps: int
    changed_per_sweep: tuple[int, ...]
    energy_trace: tuple[float, ...]
    state_sha256_trace: tuple[str, ...]
    repeated_nonfixed_state: bool
    terminal_state: np.ndarray
    terminal_sha256: str
    matched_pattern_index: int | None
    matched_content_sha256: str | None


@dataclass(frozen=True)
class EpisodeAutoassociativeMemory:
    content_hashes: tuple[str, ...]
    center: np.ndarray
    patterns: np.ndarray
    pattern_hashes: tuple[str, ...]
    weights: np.ndarray

    @classmethod
    def from_vectors(
        cls,
        vectors: np.ndarray,
        content_hashes: Sequence[str],
    ) -> EpisodeAutoassociativeMemory:
        matrix = np.asarray(vectors, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
            raise ValueError("Episode vectors must be a non-empty matrix")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("Episode vectors must be finite")
        center = np.median(matrix, axis=0)
        patterns = np.where(matrix >= center, 1, -1).astype(np.int8)
        return cls.from_patterns(patterns, content_hashes, center=center)

    @classmethod
    def from_patterns(
        cls,
        patterns: np.ndarray,
        content_hashes: Sequence[str],
        *,
        center: np.ndarray | None = None,
    ) -> EpisodeAutoassociativeMemory:
        matrix = np.asarray(patterns, dtype=np.int8)
        if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
            raise ValueError("Patterns must be a non-empty matrix")
        if not np.all(np.isin(matrix, (-1, 1))):
            raise ValueError("Patterns must contain only -1 and +1")
        identities = tuple(str(value) for value in content_hashes)
        if len(identities) != matrix.shape[0] or len(set(identities)) != len(identities):
            raise ValueError("Content hashes must be unique and match the patterns")
        if any(len(value) != 64 for value in identities):
            raise ValueError("Content identities must be SHA-256 hex digests")
        try:
            if any(len(bytes.fromhex(value)) != 32 for value in identities):
                raise ValueError
        except ValueError as exc:
            raise ValueError("Content identities must be SHA-256 hex digests") from exc

        hashes = tuple(pattern_sha256(row) for row in matrix)
        if len(set(hashes)) != len(hashes):
            raise ValueError("Bipolar episode patterns must be unique")

        dimension = matrix.shape[1]
        numeric = matrix.astype(np.float64)
        weights = (numeric.T @ numeric) / dimension
        np.fill_diagonal(weights, 0.0)
        if center is None:
            center_array = np.zeros(dimension, dtype=np.float64)
        else:
            center_array = np.asarray(center, dtype=np.float64)
            if center_array.shape != (dimension,) or not np.all(np.isfinite(center_array)):
                raise ValueError("Encoding center must be a finite dimension vector")
            center_array = center_array.copy()

        matrix = matrix.copy()
        weights = weights.copy()
        matrix.setflags(write=False)
        weights.setflags(write=False)
        center_array.setflags(write=False)
        return cls(
            content_hashes=identities,
            center=center_array,
            patterns=matrix,
            pattern_hashes=hashes,
            weights=weights,
        )

    @property
    def dimension(self) -> int:
        return int(self.patterns.shape[1])

    def encode_vector(self, vector: np.ndarray) -> np.ndarray:
        value = np.asarray(vector, dtype=np.float64)
        if value.shape != (self.dimension,) or not np.all(np.isfinite(value)):
            raise ValueError("Cue vector must be finite and match the pattern dimension")
        return np.where(value >= self.center, 1, -1).astype(np.int8)

    def energy(self, state: np.ndarray) -> float:
        value = self._validate_state(state).astype(np.float64)
        return float(-0.5 * value @ self.weights @ value)

    def recall(
        self, cue: np.ndarray, *, max_sweeps: int | None = None
    ) -> RecallTrace:
        state = self._validate_state(cue).copy()
        limit = self.dimension if max_sweeps is None else int(max_sweeps)
        if limit <= 0:
            raise ValueError("max_sweeps must be positive")

        fields = self.weights @ state.astype(np.float64)
        initial_hash = pattern_sha256(state)
        state_hashes = [initial_hash]
        energies = [self.energy(state)]
        seen = {initial_hash}
        changes_by_sweep: list[int] = []
        repeated_nonfixed = False
        converged = False

        for _sweep in range(limit):
            changes = 0
            for coordinate in range(self.dimension):
                old_value = int(state[coordinate])
                field = float(fields[coordinate])
                new_value = 1 if field > 0.0 else -1 if field < 0.0 else old_value
                if new_value == old_value:
                    continue
                delta = new_value - old_value
                state[coordinate] = new_value
                fields += self.weights[:, coordinate] * delta
                changes += 1

            changes_by_sweep.append(changes)
            state_hash = pattern_sha256(state)
            state_hashes.append(state_hash)
            energies.append(self.energy(state))
            if changes == 0:
                converged = True
                break
            if state_hash in seen:
                repeated_nonfixed = True
                break
            seen.add(state_hash)

        terminal_hash = state_hashes[-1]
        match = next(
            (
                index
                for index, stored_hash in enumerate(self.pattern_hashes)
                if stored_hash == terminal_hash
                and np.array_equal(self.patterns[index], state)
            ),
            None,
        )
        terminal = state.copy()
        terminal.setflags(write=False)
        return RecallTrace(
            converged=converged,
            sweeps=len(changes_by_sweep),
            changed_per_sweep=tuple(changes_by_sweep),
            energy_trace=tuple(energies),
            state_sha256_trace=tuple(state_hashes),
            repeated_nonfixed_state=repeated_nonfixed,
            terminal_state=terminal,
            terminal_sha256=terminal_hash,
            matched_pattern_index=match,
            matched_content_sha256=(
                None if match is None else self.content_hashes[match]
            ),
        )

    def overlaps(self, state: np.ndarray) -> np.ndarray:
        value = self._validate_state(state).astype(np.float64)
        return (self.patterns.astype(np.float64) @ value) / self.dimension

    def _validate_state(self, state: np.ndarray) -> np.ndarray:
        value = np.asarray(state, dtype=np.int8)
        if value.shape != (self.dimension,) or not np.all(np.isin(value, (-1, 1))):
            raise ValueError("State must be a bipolar pattern-dimension vector")
        return value
