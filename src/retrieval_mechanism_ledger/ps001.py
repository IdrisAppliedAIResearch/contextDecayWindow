from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .e006 import assert_mechanism_path_allowed


PROJECTION_FORMULA_VERSION = "ps001-rademacher-sha256-counter-v1"
OPERATOR_FORMULA_VERSION = "ps001-centered-covariance-low-rank-v1"
FIELD_REFERENCE_ATOL = 1e-10
TIE_SENSITIVE_MARGIN = 2e-10
MAX_REFERENCE_DIMENSION = 512
ALLOWED_PERMUTATION_DOMAINS = frozenset({"active", "inactive", "random"})


def _explicit_little_endian(value: np.ndarray, dtype: str) -> np.ndarray:
    return np.ascontiguousarray(np.asarray(value, dtype=np.dtype(dtype)))


def array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    header = json.dumps(
        {"dtype": str(array.dtype), "shape": list(array.shape)},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(header + b"\n" + array.tobytes(order="C")).hexdigest()


def state_sha256(state: np.ndarray) -> str:
    value = np.asarray(state)
    if value.ndim != 1 or not np.all(np.isin(value, (0, 1))):
        raise ValueError("State must be a one-dimensional binary vector")
    return array_sha256(_explicit_little_endian(value, "|u1"))


def _validate_sha256_hex(identity: str) -> bytes:
    if len(identity) != 64:
        raise ValueError("Content identity must be a SHA-256 hex digest")
    try:
        decoded = bytes.fromhex(identity)
    except ValueError as exc:
        raise ValueError("Content identity must be a SHA-256 hex digest") from exc
    if len(decoded) != 32:
        raise ValueError("Content identity must be a SHA-256 hex digest")
    return decoded


def sha256_counter_stream(seed: bytes, byte_count: int) -> bytes:
    if not isinstance(seed, bytes) or len(seed) == 0:
        raise ValueError("Counter-mode seed must be non-empty bytes")
    if byte_count < 0:
        raise ValueError("Requested byte count must be nonnegative")
    output = bytearray()
    counter = 0
    while len(output) < byte_count:
        output.extend(hashlib.sha256(seed + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(output[:byte_count])


def rademacher_projection(
    seed: bytes, output_dimension: int, input_dimension: int
) -> np.ndarray:
    if output_dimension <= 0 or input_dimension <= 0:
        raise ValueError("Projection dimensions must be positive")
    bit_count = output_dimension * input_dimension
    packed = sha256_counter_stream(seed, (bit_count + 7) // 8)
    bits = np.unpackbits(
        np.frombuffer(packed, dtype=np.uint8), bitorder="big", count=bit_count
    )
    projection = (bits.astype(np.int8) * 2 - 1).reshape(
        output_dimension, input_dimension
    )
    projection = _explicit_little_endian(projection, "|i1")
    projection.setflags(write=False)
    return projection


def fixed_order_norm(vector: np.ndarray) -> float:
    value = _explicit_little_endian(vector, "<f8")
    if value.ndim != 1 or not np.all(np.isfinite(value)):
        raise ValueError("Vector must be one-dimensional and finite")
    squared_sum = np.float64(0.0)
    for coordinate in range(value.size):
        squared_sum = np.float64(
            squared_sum + np.float64(value[coordinate] * value[coordinate])
        )
    return float(np.sqrt(squared_sum, dtype=np.float64))


def normalize_rows_fixed_order(vectors: np.ndarray) -> np.ndarray:
    matrix = _explicit_little_endian(vectors, "<f8")
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("Vectors must be a non-empty matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("Vectors must be finite")
    squared = np.multiply(matrix, matrix, dtype=np.float64)
    squared_sums = np.add.reduce(
        squared, axis=1, keepdims=True, dtype=np.float64
    )
    norms = np.sqrt(squared_sums, dtype=np.float64)
    if np.any(norms == 0.0):
        raise ValueError("Vectors must be nonzero")
    normalized = np.divide(matrix, norms, dtype=np.float64)
    return _explicit_little_endian(normalized, "<f8")


def stable_population_center(vectors: np.ndarray) -> np.ndarray:
    matrix = _explicit_little_endian(vectors, "<f8")
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("Vectors must be a non-empty matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("Vectors must be finite")
    row_order = sorted(
        range(matrix.shape[0]), key=lambda index: matrix[index].tobytes(order="C")
    )
    center = np.zeros(matrix.shape[1], dtype=np.dtype("<f8"))
    for row_index in row_order:
        np.add(center, matrix[row_index], out=center)
    np.divide(center, np.float64(matrix.shape[0]), out=center)
    center = _explicit_little_endian(center, "<f8")
    center.setflags(write=False)
    return center


def fixed_order_activations(
    centered_vectors: np.ndarray, projection: np.ndarray
) -> np.ndarray:
    centered = _explicit_little_endian(centered_vectors, "<f8")
    matrix = np.asarray(projection, dtype=np.int8)
    if centered.ndim != 2 or matrix.ndim != 2:
        raise ValueError("Centered vectors and projection must be matrices")
    if centered.shape[1] != matrix.shape[1]:
        raise ValueError("Projection input dimension does not match vectors")
    activations = np.zeros(
        (centered.shape[0], matrix.shape[0]), dtype=np.dtype("<f8")
    )
    scratch = np.empty_like(activations)
    for coordinate in range(centered.shape[1]):
        np.multiply(
            centered[:, coordinate, None],
            matrix[None, :, coordinate],
            out=scratch,
        )
        np.add(activations, scratch, out=activations)
    np.divide(
        activations,
        np.float64(math.sqrt(centered.shape[1])),
        out=activations,
    )
    return _explicit_little_endian(activations, "<f8")


def top_k_binary(values: np.ndarray, active_count: int) -> tuple[np.ndarray, float]:
    scores = _explicit_little_endian(values, "<f8")
    if scores.ndim != 1 or not np.all(np.isfinite(scores)):
        raise ValueError("Competition values must be one-dimensional and finite")
    if not 0 < active_count < scores.size:
        raise ValueError("Active count must be between zero and the dimension")
    indices = np.arange(scores.size, dtype=np.int64)
    order = np.lexsort((indices, -scores))
    selected = order[:active_count]
    state = np.zeros(scores.size, dtype=np.uint8)
    state[selected] = 1
    margin = float(scores[order[active_count - 1]] - scores[order[active_count]])
    return state, margin


def encode_activations(
    activations: np.ndarray, active_count: int
) -> tuple[np.ndarray, np.ndarray]:
    values = _explicit_little_endian(activations, "<f8")
    if values.ndim != 2:
        raise ValueError("Activations must be a matrix")
    codes = np.empty(values.shape, dtype=np.uint8)
    margins = np.empty(values.shape[0], dtype=np.dtype("<f8"))
    for row_index, row in enumerate(values):
        codes[row_index], margins[row_index] = top_k_binary(row, active_count)
    return _explicit_little_endian(codes, "|u1"), _explicit_little_endian(
        margins, "<f8"
    )


def deterministic_coordinate_permutation(
    coordinates: Iterable[int], content_sha256: str, domain: str
) -> tuple[int, ...]:
    if domain not in ALLOWED_PERMUTATION_DOMAINS:
        raise ValueError(f"Unsupported permutation domain: {domain}")
    pool = tuple(sorted(int(value) for value in coordinates))
    if len(pool) == 0 or len(set(pool)) != len(pool) or pool[0] < 0:
        raise ValueError("Coordinate pool must contain unique nonnegative values")
    identity = _validate_sha256_hex(content_sha256)
    domain_seed = hashlib.sha256(domain.encode("ascii") + identity).digest()
    selected: list[int] = []
    seen_positions: set[int] = set()
    counter = 0
    while len(selected) < len(pool):
        block = hashlib.sha256(
            domain_seed + counter.to_bytes(8, "big")
        ).digest()
        counter += 1
        for offset in range(0, len(block), 4):
            position = int.from_bytes(block[offset : offset + 4], "big") % len(pool)
            if position in seen_positions:
                continue
            seen_positions.add(position)
            selected.append(pool[position])
            if len(selected) == len(pool):
                break
    return tuple(selected)


def degrade_sparse_code(
    code: np.ndarray, content_sha256: str, swaps: int
) -> tuple[np.ndarray, tuple[int, ...], tuple[int, ...]]:
    state = np.asarray(code, dtype=np.uint8)
    if state.ndim != 1 or not np.all(np.isin(state, (0, 1))):
        raise ValueError("Code must be a one-dimensional binary vector")
    active = np.flatnonzero(state == 1)
    inactive = np.flatnonzero(state == 0)
    if swaps < 0 or swaps > min(active.size, inactive.size):
        raise ValueError("Swap count exceeds active or inactive coordinates")
    active_order = deterministic_coordinate_permutation(
        active, content_sha256, "active"
    )
    inactive_order = deterministic_coordinate_permutation(
        inactive, content_sha256, "inactive"
    )
    deactivated = active_order[:swaps]
    activated = inactive_order[:swaps]
    degraded = state.copy()
    if swaps:
        degraded[np.asarray(deactivated, dtype=np.int64)] = 0
        degraded[np.asarray(activated, dtype=np.int64)] = 1
    return degraded, deactivated, activated


def materialize_centered_weights(
    eta: np.ndarray, denominator: float
) -> np.ndarray:
    matrix = _explicit_little_endian(eta, "<f8")
    if matrix.ndim != 2 or matrix.shape[1] > MAX_REFERENCE_DIMENSION:
        raise ValueError(
            f"Dense reference is limited to dimension {MAX_REFERENCE_DIMENSION}"
        )
    weights = (matrix.T @ matrix) / np.float64(denominator)
    np.fill_diagonal(weights, 0.0)
    return _explicit_little_endian(weights, "<f8")


def slow_reference_transition(
    weights: np.ndarray, state: np.ndarray, active_count: int, activity: float
) -> tuple[np.ndarray, np.ndarray, float]:
    matrix = _explicit_little_endian(weights, "<f8")
    value = np.asarray(state, dtype=np.uint8)
    if matrix.shape != (value.size, value.size):
        raise ValueError("Reference weights and state dimensions do not match")
    centered = value.astype(np.float64) - np.float64(activity)
    field = np.empty(value.size, dtype=np.dtype("<f8"))
    for row_index in range(value.size):
        total = np.float64(0.0)
        for column_index in range(value.size):
            total = np.float64(
                total
                + np.float64(matrix[row_index, column_index] * centered[column_index])
            )
        field[row_index] = total
    next_state, margin = top_k_binary(field, active_count)
    return next_state, field, margin


@dataclass(frozen=True)
class SparseRecallTrace:
    converged: bool
    fixed_point: bool
    cycle: bool
    runtime_guard: bool
    sweeps: int
    changed_per_sweep: tuple[int, ...]
    active_counts: tuple[int, ...]
    state_sha256_trace: tuple[str, ...]
    quadratic_score_trace: tuple[float, ...]
    field_margin_trace: tuple[float, ...]
    repeated_state_witness: tuple[int, int] | None
    terminal_state: np.ndarray
    terminal_sha256: str


@dataclass(frozen=True)
class SparseEngramAutoassociator:
    input_dimension: int
    code_dimension: int
    active_count: int
    projection_seed: bytes
    center: np.ndarray
    projection: np.ndarray
    codes: np.ndarray
    activation_margins: np.ndarray
    eta: np.ndarray
    denominator: float
    diagonal: np.ndarray
    code_hashes: tuple[str, ...]

    @classmethod
    def fit(
        cls,
        vectors: np.ndarray,
        *,
        code_dimension: int,
        active_count: int,
        projection_seed: bytes,
    ) -> SparseEngramAutoassociator:
        matrix = _explicit_little_endian(vectors, "<f8")
        if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
            raise ValueError("Episode vectors must be a non-empty matrix")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("Episode vectors must be finite")
        if code_dimension <= matrix.shape[1]:
            raise ValueError("Code dimension must expand the input dimension")
        if not 0 < active_count < code_dimension:
            raise ValueError("Active count must be between zero and code dimension")
        if not isinstance(projection_seed, bytes) or len(projection_seed) != 32:
            raise ValueError("Projection seed must contain exactly 32 bytes")
        norms = np.asarray([fixed_order_norm(row) for row in matrix])
        if not np.all(np.abs(norms - 1.0) <= 1e-12):
            raise ValueError("Episode vectors must be normalized before fit")

        center = stable_population_center(matrix)
        centered = _explicit_little_endian(matrix - center, "<f8")
        projection = rademacher_projection(
            projection_seed, code_dimension, matrix.shape[1]
        )
        activations = fixed_order_activations(centered, projection)
        codes, margins = encode_activations(activations, active_count)
        code_hashes = tuple(state_sha256(row) for row in codes)
        if len(set(code_hashes)) != len(code_hashes):
            raise ValueError("Sparse episode codes must be unique")

        activity = np.float64(active_count / code_dimension)
        eta = _explicit_little_endian(codes.astype(np.float64) - activity, "<f8")
        denominator = float(
            np.float64(code_dimension)
            * activity
            * np.float64(1.0 - activity)
        )
        diagonal = np.zeros(code_dimension, dtype=np.dtype("<f8"))
        for row in eta:
            np.add(diagonal, row * row, out=diagonal)
        np.divide(diagonal, np.float64(denominator), out=diagonal)

        codes.setflags(write=False)
        margins.setflags(write=False)
        eta.setflags(write=False)
        diagonal.setflags(write=False)
        return cls(
            input_dimension=int(matrix.shape[1]),
            code_dimension=int(code_dimension),
            active_count=int(active_count),
            projection_seed=bytes(projection_seed),
            center=center,
            projection=projection,
            codes=codes,
            activation_margins=margins,
            eta=eta,
            denominator=denominator,
            diagonal=diagonal,
            code_hashes=code_hashes,
        )

    @property
    def activity(self) -> float:
        return self.active_count / self.code_dimension

    def encode(self, vector: np.ndarray) -> np.ndarray:
        value = _explicit_little_endian(vector, "<f8")
        if value.shape != (self.input_dimension,) or not np.all(np.isfinite(value)):
            raise ValueError("Vector must be finite and match input dimension")
        centered = _explicit_little_endian((value - self.center)[None, :], "<f8")
        activation = fixed_order_activations(centered, self.projection)[0]
        code, _margin = top_k_binary(activation, self.active_count)
        return code

    def field(self, centered_state: np.ndarray) -> np.ndarray:
        value = _explicit_little_endian(centered_state, "<f8")
        if value.shape != (self.code_dimension,) or not np.all(np.isfinite(value)):
            raise ValueError("Centered state must be finite and match code dimension")
        episode_support = self.eta @ value
        field = (
            self.eta.T @ episode_support
        ) / np.float64(self.denominator) - self.diagonal * value
        return _explicit_little_endian(field, "<f8")

    def quadratic_score(self, state: np.ndarray, field: np.ndarray | None = None) -> float:
        value = self._validate_state(state).astype(np.float64)
        centered = value - np.float64(self.activity)
        actual_field = self.field(centered) if field is None else np.asarray(field)
        return float(np.float64(0.5) * np.dot(centered, actual_field))

    def recall(
        self, cue: np.ndarray, *, max_sweeps: int | None = None
    ) -> SparseRecallTrace:
        state = self._validate_state(cue).copy()
        limit = self.code_dimension if max_sweeps is None else int(max_sweeps)
        if limit <= 0 or limit > self.code_dimension:
            raise ValueError("max_sweeps must be in [1, code_dimension]")

        state_hash = state_sha256(state)
        state_hashes = [state_hash]
        active_counts = [int(state.sum())]
        seen = {state_hash: 0}
        centered = state.astype(np.float64) - np.float64(self.activity)
        field = self.field(centered)
        scores = [self.quadratic_score(state, field)]
        changes_by_sweep: list[int] = []
        margins: list[float] = []
        repeated_witness: tuple[int, int] | None = None
        fixed_point = False
        cycle = False

        for _sweep in range(limit):
            next_state, margin = top_k_binary(field, self.active_count)
            changes = int(np.count_nonzero(next_state != state))
            changes_by_sweep.append(changes)
            margins.append(margin)
            state = next_state
            state_hash = state_sha256(state)
            state_hashes.append(state_hash)
            active_counts.append(int(state.sum()))
            centered = state.astype(np.float64) - np.float64(self.activity)
            field = self.field(centered)
            scores.append(self.quadratic_score(state, field))
            if changes == 0:
                fixed_point = True
                break
            if state_hash in seen:
                cycle = True
                repeated_witness = (seen[state_hash], len(state_hashes) - 1)
                break
            seen[state_hash] = len(state_hashes) - 1

        runtime_guard = not fixed_point and not cycle
        terminal = _explicit_little_endian(state, "|u1")
        terminal.setflags(write=False)
        return SparseRecallTrace(
            converged=fixed_point,
            fixed_point=fixed_point,
            cycle=cycle,
            runtime_guard=runtime_guard,
            sweeps=len(changes_by_sweep),
            changed_per_sweep=tuple(changes_by_sweep),
            active_counts=tuple(active_counts),
            state_sha256_trace=tuple(state_hashes),
            quadratic_score_trace=tuple(scores),
            field_margin_trace=tuple(margins),
            repeated_state_witness=repeated_witness,
            terminal_state=terminal,
            terminal_sha256=state_hashes[-1],
        )

    def degrade(
        self, code: np.ndarray, identity: str, swaps: int
    ) -> tuple[np.ndarray, tuple[int, ...], tuple[int, ...]]:
        value = self._validate_state(code)
        return degrade_sparse_code(value, identity, swaps)

    def learned_state_sha256(self) -> str:
        payload = json.dumps(
            {
                "active_count": self.active_count,
                "code_dimension": self.code_dimension,
                "denominator_hex": float(self.denominator).hex(),
                "diagonal_sha256": array_sha256(self.diagonal),
                "eta_sha256": array_sha256(self.eta),
                "formula_version": OPERATOR_FORMULA_VERSION,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        return hashlib.sha256(payload).hexdigest()

    def _validate_state(self, state: np.ndarray) -> np.ndarray:
        value = np.asarray(state, dtype=np.uint8)
        if value.shape != (self.code_dimension,) or not np.all(
            np.isin(value, (0, 1))
        ):
            raise ValueError("State must be a binary code-dimension vector")
        if int(value.sum()) != self.active_count:
            raise ValueError("State must preserve the registered active count")
        return value


__all__ = [
    "FIELD_REFERENCE_ATOL",
    "OPERATOR_FORMULA_VERSION",
    "PROJECTION_FORMULA_VERSION",
    "SparseEngramAutoassociator",
    "SparseRecallTrace",
    "TIE_SENSITIVE_MARGIN",
    "array_sha256",
    "assert_mechanism_path_allowed",
    "degrade_sparse_code",
    "deterministic_coordinate_permutation",
    "encode_activations",
    "fixed_order_activations",
    "fixed_order_norm",
    "materialize_centered_weights",
    "normalize_rows_fixed_order",
    "rademacher_projection",
    "sha256_counter_stream",
    "slow_reference_transition",
    "stable_population_center",
    "state_sha256",
    "top_k_binary",
]
