from __future__ import annotations

import inspect
import os
import subprocess
import sys

import numpy as np
import pytest

from src.retrieval_mechanism_ledger.ps001 import (
    FIELD_REFERENCE_ATOL,
    SparseEngramAutoassociator,
    array_sha256,
    assert_mechanism_path_allowed,
    degrade_sparse_code,
    deterministic_coordinate_permutation,
    fixed_order_activations,
    materialize_centered_weights,
    rademacher_projection,
    slow_reference_transition,
    stable_population_center,
    state_sha256,
    top_k_binary,
)


SEED = bytes.fromhex("00" * 32)


def readonly(value: np.ndarray) -> np.ndarray:
    value.setflags(write=False)
    return value


def memory_from_codes(codes: np.ndarray) -> SparseEngramAutoassociator:
    matrix = np.asarray(codes, dtype=np.uint8)
    active_count = int(matrix[0].sum())
    assert np.all(matrix.sum(axis=1) == active_count)
    dimension = matrix.shape[1]
    activity = active_count / dimension
    eta = matrix.astype(np.float64) - activity
    denominator = dimension * activity * (1.0 - activity)
    diagonal = (eta * eta).sum(axis=0) / denominator
    return SparseEngramAutoassociator(
        input_dimension=2,
        code_dimension=dimension,
        active_count=active_count,
        projection_seed=SEED,
        center=readonly(np.zeros(2, dtype=np.float64)),
        projection=readonly(np.zeros((dimension, 2), dtype=np.int8)),
        codes=readonly(matrix.copy()),
        activation_margins=readonly(np.ones(matrix.shape[0], dtype=np.float64)),
        eta=readonly(eta),
        denominator=denominator,
        diagonal=readonly(diagonal),
        code_hashes=tuple(state_sha256(row) for row in matrix),
    )


def code(dimension: int, active: tuple[int, ...]) -> np.ndarray:
    value = np.zeros(dimension, dtype=np.uint8)
    value[np.asarray(active, dtype=np.int64)] = 1
    return value


def normalized_fixture() -> np.ndarray:
    rows = np.array(
        [
            [1.0, 2.0, 3.0, 4.0],
            [-4.0, 1.0, 2.0, 3.0],
            [3.0, -2.0, 4.0, 1.0],
            [2.0, 4.0, -1.0, -3.0],
        ],
        dtype=np.float64,
    )
    return rows / np.linalg.norm(rows, axis=1, keepdims=True)


def test_literal_projection_bytes_shape_and_bit_mapping() -> None:
    projection = rademacher_projection(SEED, 5, 3)

    assert projection.tolist() == [
        [-1, -1, 1],
        [-1, 1, 1],
        [-1, -1, -1],
        [-1, 1, 1],
        [-1, 1, -1],
    ]
    assert array_sha256(projection) == (
        "25d616c9508c6fd4783d096758d4d8300654a8e8f27594fa39268708cbbae0fb"
    )


def test_projection_is_independent_of_numpy_rng_and_process() -> None:
    np.random.seed(123)
    first = array_sha256(rademacher_projection(SEED, 17, 11))
    np.random.seed(987654)
    second = array_sha256(rademacher_projection(SEED, 17, 11))
    script = (
        "from src.retrieval_mechanism_ledger.ps001 import "
        "array_sha256,rademacher_projection;"
        "print(array_sha256(rademacher_projection(bytes.fromhex('00'*32),17,11)))"
    )
    child = subprocess.check_output(
        [sys.executable, "-c", script],
        cwd=os.getcwd(),
        text=True,
        encoding="utf-8",
    ).strip()

    assert first == second == child


def test_top_k_uses_descending_value_then_ascending_index() -> None:
    state, margin = top_k_binary(np.array([1.0, 2.0, 2.0, 2.0, -1.0]), 2)

    assert np.array_equal(state, np.array([0, 1, 1, 0, 0], dtype=np.uint8))
    assert margin == 0.0


def test_center_and_activation_match_fixed_order_reference() -> None:
    vectors = normalized_fixture()
    center = stable_population_center(vectors)
    projection = rademacher_projection(SEED, 12, vectors.shape[1])
    actual = fixed_order_activations(vectors - center, projection)
    expected_center = np.zeros(vectors.shape[1], dtype=np.float64)
    for row in sorted(vectors, key=lambda value: value.tobytes(order="C")):
        expected_center += row
    expected_center /= len(vectors)
    expected = np.empty_like(actual)
    for row_index, row in enumerate(vectors - expected_center):
        for projection_index, projection_row in enumerate(projection):
            total = np.float64(0.0)
            for coordinate in range(vectors.shape[1]):
                total = np.float64(
                    total + projection_row[coordinate] * row[coordinate]
                )
            expected[row_index, projection_index] = total / np.sqrt(
                vectors.shape[1]
            )

    assert np.array_equal(center, expected_center)
    assert np.array_equal(actual, expected)


def test_fit_is_row_order_invariant_after_remapping() -> None:
    vectors = normalized_fixture()
    first = SparseEngramAutoassociator.fit(
        vectors, code_dimension=64, active_count=8, projection_seed=SEED
    )
    order = np.array([2, 0, 3, 1])
    second = SparseEngramAutoassociator.fit(
        vectors[order], code_dimension=64, active_count=8, projection_seed=SEED
    )
    inverse = np.argsort(order)

    assert np.array_equal(first.center, second.center)
    assert np.array_equal(first.codes, second.codes[inverse])
    assert first.code_hashes == tuple(second.code_hashes[index] for index in inverse)


def test_implicit_operator_matches_materialized_slow_oracle() -> None:
    memory = memory_from_codes(
        np.stack([code(8, (0, 1)), code(8, (3, 4)), code(8, (6, 7))])
    )
    weights = materialize_centered_weights(memory.eta, memory.denominator)

    assert np.array_equal(weights, weights.T)
    assert np.count_nonzero(np.diag(weights)) == 0
    for state in memory.codes:
        centered = state.astype(np.float64) - memory.activity
        actual_field = memory.field(centered)
        next_state, expected_field, expected_margin = slow_reference_transition(
            weights, state, memory.active_count, memory.activity
        )
        actual_state, actual_margin = top_k_binary(actual_field, memory.active_count)
        assert np.allclose(
            actual_field, expected_field, rtol=0.0, atol=FIELD_REFERENCE_ATOL
        )
        assert np.array_equal(actual_state, next_state)
        assert actual_margin == pytest.approx(expected_margin, abs=FIELD_REFERENCE_ATOL)


def test_reachable_fixture_stores_code_and_recovers_every_one_swap() -> None:
    source = code(8, (0, 1))
    memory = memory_from_codes(np.stack([source]))

    stable = memory.recall(source)
    assert stable.fixed_point
    assert stable.changed_per_sweep == (0,)
    assert stable.active_counts == (2, 2)
    for deactivate in (0, 1):
        for activate in range(2, 8):
            cue = source.copy()
            cue[deactivate] = 0
            cue[activate] = 1
            trace = memory.recall(cue)
            assert trace.fixed_point
            assert np.array_equal(trace.terminal_state, source)


def test_cycle_and_runtime_guard_are_not_convergence() -> None:
    memory = memory_from_codes(
        np.stack([code(6, (2, 5)), code(6, (1, 5)), code(6, (0, 1))])
    )
    cue = code(6, (0, 3))

    cycle = memory.recall(cue)
    guarded = memory.recall(cue, max_sweeps=1)

    assert cycle.cycle and not cycle.converged and not cycle.runtime_guard
    assert cycle.repeated_state_witness == (0, 2)
    assert guarded.runtime_guard and not guarded.converged and not guarded.cycle


def test_spurious_fixed_point_is_distinguishable_from_stored_codes() -> None:
    memory = memory_from_codes(
        np.stack([code(6, (2, 5)), code(6, (1, 5)), code(6, (0, 1))])
    )

    trace = memory.recall(code(6, (0, 2)))

    assert trace.fixed_point
    assert trace.terminal_sha256 not in memory.code_hashes


def test_corruption_fixture_uses_independent_active_inactive_domains() -> None:
    identity = f"{1:064x}"
    source = code(8, (0, 1, 4))
    degraded, deactivated, activated = degrade_sparse_code(source, identity, 2)

    assert deterministic_coordinate_permutation(range(8), identity, "active") == (
        3,
        0,
        2,
        1,
        6,
        5,
        7,
        4,
    )
    assert deactivated == (4, 1)
    assert activated == (2, 7)
    assert int(degraded.sum()) == int(source.sum())
    assert np.count_nonzero(degraded != source) == 4


def test_invalid_inputs_duplicates_and_measurement_paths_fail() -> None:
    vectors = normalized_fixture()
    with pytest.raises(ValueError, match="expand"):
        SparseEngramAutoassociator.fit(
            vectors, code_dimension=4, active_count=2, projection_seed=SEED
        )
    with pytest.raises(ValueError, match="normalized"):
        SparseEngramAutoassociator.fit(
            vectors * 2.0, code_dimension=16, active_count=2, projection_seed=SEED
        )
    with pytest.raises(ValueError, match="unique"):
        SparseEngramAutoassociator.fit(
            np.stack([vectors[0], vectors[0]]),
            code_dimension=16,
            active_count=2,
            projection_seed=SEED,
        )
    memory = memory_from_codes(np.stack([code(8, (0, 1))]))
    with pytest.raises(ValueError, match="active count"):
        memory.recall(code(8, (0, 1, 2)))
    with pytest.raises(ValueError, match="measurement boundary"):
        assert_mechanism_path_allowed("experiments/study_011/q_facts_key.md")


def test_fit_signature_cannot_accept_identity_text_turn_or_label_features() -> None:
    parameters = set(inspect.signature(SparseEngramAutoassociator.fit).parameters)
    assert parameters == {
        "vectors",
        "code_dimension",
        "active_count",
        "projection_seed",
    }
    with pytest.raises(TypeError):
        SparseEngramAutoassociator.fit(
            normalized_fixture(),
            code_dimension=16,
            active_count=2,
            projection_seed=SEED,
            content_sha256=(f"{1:064x}",),
        )
