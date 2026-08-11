from __future__ import annotations

import numpy as np
import pytest

from src.retrieval_mechanism_ledger.ps001 import SparseEngramAutoassociator, state_sha256
from src.retrieval_mechanism_ledger.ps002 import (
    SemanticEngramCueBinder,
    assert_binder_path_allowed,
    deterministic_softmax,
    fixed_order_dot,
    stable_descending_indices,
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
        np.stack([code(12, (0, 1)), code(12, (4, 5)), code(12, (8, 9))]),
        input_dimension=3,
    )
    vectors = np.eye(3, dtype=np.float64)
    return memory, vectors


def test_fixed_order_dot_matches_literal_accumulation() -> None:
    left = np.array([0.1, -0.2, 0.3], dtype=np.float64)
    right = np.array([0.4, 0.5, -0.6], dtype=np.float64)
    expected = np.float64(0.0)
    for index in range(3):
        expected = np.float64(expected + left[index] * right[index])

    assert fixed_order_dot(left, right) == float(expected)


def test_stable_order_uses_index_for_exact_ties() -> None:
    assert stable_descending_indices(np.array([0.5, 0.7, 0.7, -1.0])).tolist() == [
        1,
        2,
        0,
        3,
    ]


def test_softmax_is_stable_normalized_and_temperature_guarded() -> None:
    values = deterministic_softmax(np.array([1000.0, 999.0]), 0.5)

    assert values.sum() == pytest.approx(1.0)
    assert values[0] > values[1]
    assert not values.flags.writeable
    with pytest.raises(ValueError, match="Temperature"):
        deterministic_softmax(np.array([1.0]), 0.0)


def test_single_support_binds_in_semantic_order_with_inhibition() -> None:
    memory, vectors = fixture()
    binder = SemanticEngramCueBinder.fit(
        memory, vectors, support_width=1, temperature=0.05
    )
    query = np.array([0.8, 0.6, 0.0], dtype=np.float64)

    trace = binder.bind(query, query_sha256="ab" * 32, rounds=3)

    assert trace.semantic_order == (0, 1, 2)
    assert trace.emitted_indices == (0, 1, 2)
    assert all(row.outcome == "stored" for row in trace.rounds)
    assert [row.inhibited_index for row in trace.rounds] == [0, 1, 2]
    assert all(row.cue_active_count == memory.active_count for row in trace.rounds)


def test_fit_rejects_misaligned_or_unnormalized_vectors() -> None:
    memory, vectors = fixture()
    with pytest.raises(ValueError, match="align"):
        SemanticEngramCueBinder.fit(
            memory, vectors[:2], support_width=1, temperature=0.05
        )
    with pytest.raises(ValueError, match="normalized"):
        SemanticEngramCueBinder.fit(
            memory, vectors * 2.0, support_width=1, temperature=0.05
        )


def test_query_and_round_guards_fail_loudly() -> None:
    memory, vectors = fixture()
    binder = SemanticEngramCueBinder.fit(
        memory, vectors, support_width=1, temperature=0.05
    )
    with pytest.raises(ValueError, match="SHA-256"):
        binder.bind(vectors[0], query_sha256="not-a-digest", rounds=1)
    with pytest.raises(ValueError, match="Round count"):
        binder.bind(vectors[0], query_sha256="00" * 32, rounds=0)


def test_measurement_paths_are_rejected() -> None:
    assert_binder_path_allowed("experiments/surveys/retrieval_bakeoff/holdout/queries_121.json")
    with pytest.raises(ValueError, match="measurement boundary"):
        assert_binder_path_allowed(
            "experiments/surveys/retrieval_bakeoff/holdout/answer_key_121.json"
        )
