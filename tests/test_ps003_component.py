from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from src.retrieval_mechanism_ledger.ps001 import SparseEngramAutoassociator, state_sha256
from src.retrieval_mechanism_ledger.ps003 import (
    AmbiguityProbe,
    EngramAmbiguityResolver,
    classify_consensus,
    deterministic_probe_family,
)


def readonly(value: np.ndarray) -> np.ndarray:
    value.setflags(write=False)
    return value


def code(dimension: int, active: tuple[int, ...]) -> np.ndarray:
    value = np.zeros(dimension, dtype=np.uint8)
    value[np.asarray(active, dtype=np.int64)] = 1
    return value


def memory_from_codes(codes: np.ndarray, input_dimension: int) -> SparseEngramAutoassociator:
    matrix = np.asarray(codes, dtype=np.uint8)
    active_count = int(matrix[0].sum())
    dimension = matrix.shape[1]
    activity = active_count / dimension
    eta = matrix.astype(np.float64) - activity
    denominator = dimension * activity * (1.0 - activity)
    diagonal = (eta * eta).sum(axis=0) / denominator
    return SparseEngramAutoassociator(
        input_dimension=input_dimension,
        code_dimension=dimension,
        active_count=active_count,
        projection_seed=bytes(32),
        center=readonly(np.zeros(input_dimension, dtype=np.float64)),
        projection=readonly(np.zeros((dimension, input_dimension), dtype=np.int8)),
        codes=readonly(matrix.copy()),
        activation_margins=readonly(np.ones(matrix.shape[0], dtype=np.float64)),
        eta=readonly(eta),
        denominator=denominator,
        diagonal=readonly(diagonal),
        code_hashes=tuple(state_sha256(row) for row in matrix),
    )


def fixture() -> tuple[SparseEngramAutoassociator, np.ndarray]:
    memory = memory_from_codes(
        np.stack(
            [
                code(64, tuple(range(offset, offset + 4)))
                for offset in range(0, 64, 8)
            ]
        ),
        input_dimension=8,
    )
    return memory, np.eye(8, dtype=np.float64)


def probe(stored_index: int | None, *, cycle: bool = False, guard: bool = False) -> AmbiguityProbe:
    recall = SimpleNamespace(cycle=cycle, runtime_guard=guard)
    return AmbiguityProbe(0, "ab" * 32, 41, recall, stored_index)


def test_probe_family_uses_registered_disjoint_boundary_bands() -> None:
    field = np.arange(12, 0, -1, dtype=np.float64)

    probes, margin = deterministic_probe_family(
        field, active_count=4, probe_count=3, swap_count=1
    )

    assert margin == 1.0
    assert [row.nonzero()[0].tolist() for row in probes] == [
        [0, 1, 2, 3],
        [0, 1, 2, 4],
        [0, 1, 3, 5],
    ]
    assert all(int(row.sum()) == 4 for row in probes)
    assert all(not row.flags.writeable for row in probes)


@pytest.mark.parametrize(
    ("probes", "emitted", "expected"),
    [
        ([probe(1), probe(1), probe(1)], set(), ("accepted", 1)),
        ([probe(1, guard=True), probe(1)], set(), ("runtime_guard", None)),
        ([probe(1, cycle=True), probe(1)], set(), ("cycle", None)),
        ([probe(None), probe(1)], set(), ("spurious", None)),
        ([probe(1), probe(2)], set(), ("disagreement", None)),
        ([probe(1), probe(1)], {1}, ("duplicate", None)),
    ],
)
def test_consensus_accepts_only_one_safe_new_identity(
    probes: list[AmbiguityProbe], emitted: set[int], expected: tuple[str, int | None]
) -> None:
    assert classify_consensus(probes, emitted) == expected


def test_fit_enforces_registered_grid_and_normalized_alignment() -> None:
    memory, vectors = fixture()

    resolver = EngramAmbiguityResolver.fit(
        memory, vectors, probe_count=3, swap_count=1
    )

    assert resolver.probe_count == 3
    assert not resolver.episode_vectors.flags.writeable
    with pytest.raises(ValueError, match="registered grid"):
        EngramAmbiguityResolver.fit(memory, vectors, probe_count=4, swap_count=1)
    with pytest.raises(ValueError, match="normalized"):
        EngramAmbiguityResolver.fit(
            memory, vectors * 2.0, probe_count=3, swap_count=1
        )


def test_resolver_keeps_probe_and_attempt_bounds_without_fallback() -> None:
    memory, vectors = fixture()
    resolver = EngramAmbiguityResolver.fit(
        memory, vectors, probe_count=3, swap_count=1
    )
    query = np.array([0.8, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)

    trace = resolver.resolve(
        query,
        query_sha256="cd" * 32,
        target_outputs=2,
        attempt_budget=4,
    )

    assert len(trace.attempts) <= 4
    assert len(trace.emitted_indices) <= 2
    assert all(len(row.probes) == 3 for row in trace.attempts)
    assert all(
        row.emitted_index is None or row.outcome == "accepted" for row in trace.attempts
    )
    assert all(
        row.inhibited_index
        == (row.emitted_index if row.emitted_index is not None else row.candidate_indices[0])
        for row in trace.attempts
    )


def test_query_and_budget_guards_fail_loudly() -> None:
    memory, vectors = fixture()
    resolver = EngramAmbiguityResolver.fit(
        memory, vectors, probe_count=3, swap_count=1
    )
    with pytest.raises(ValueError, match="SHA-256"):
        resolver.resolve(vectors[0], query_sha256="bad")
    with pytest.raises(ValueError, match="registered bound"):
        resolver.resolve(vectors[0], query_sha256="00" * 32, target_outputs=9)
    with pytest.raises(ValueError, match="smaller"):
        resolver.resolve(
            vectors[0], query_sha256="00" * 32, target_outputs=4, attempt_budget=3
        )
