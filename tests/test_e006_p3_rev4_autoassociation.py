from __future__ import annotations

import numpy as np
import pytest

from src.retrieval_mechanism_ledger.e006_p3_rev4 import (
    EpisodeAutoassociativeMemory,
    assert_mechanism_path_allowed,
    degrade_pattern,
    deterministic_flip_indices,
    pattern_sha256,
)


def hashes(count: int) -> tuple[str, ...]:
    return tuple(f"{index + 1:064x}" for index in range(count))


def reference_recall(weights: np.ndarray, cue: np.ndarray) -> tuple[np.ndarray, list[float]]:
    state = cue.astype(np.int8).copy()
    energies = [float(-0.5 * state @ weights @ state)]
    for _sweep in range(len(state)):
        changed = False
        for coordinate in range(len(state)):
            field = float(np.dot(weights[coordinate], state))
            old = int(state[coordinate])
            state[coordinate] = 1 if field > 0 else -1 if field < 0 else old
            changed |= int(state[coordinate]) != old
        energies.append(float(-0.5 * state @ weights @ state))
        if not changed:
            return state, energies
    return state, energies


def orthogonal_fixture() -> EpisodeAutoassociativeMemory:
    patterns = np.array(
        [
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, -1, -1, -1, -1],
        ],
        dtype=np.int8,
    )
    return EpisodeAutoassociativeMemory.from_patterns(patterns, hashes(2))


def test_population_centered_encoding_and_hebbian_weight_identity() -> None:
    vectors = np.array(
        [
            [-2.0, 3.0, 1.0, 0.0],
            [0.0, 2.0, -1.0, 1.0],
            [2.0, 1.0, 0.0, -1.0],
        ]
    )

    memory = EpisodeAutoassociativeMemory.from_vectors(vectors, hashes(3))

    assert np.array_equal(memory.center, np.array([0.0, 2.0, 0.0, 0.0]))
    assert set(np.unique(memory.patterns)) == {-1, 1}
    assert np.array_equal(memory.weights, memory.weights.T)
    assert np.count_nonzero(np.diag(memory.weights)) == 0
    expected = memory.patterns.astype(float).T @ memory.patterns.astype(float) / 4
    np.fill_diagonal(expected, 0.0)
    assert np.array_equal(memory.weights, expected)


def test_duplicate_bipolar_patterns_fail_before_learning() -> None:
    vectors = np.array([[0.0, 1.0], [0.0, 1.0]])

    with pytest.raises(ValueError, match="must be unique"):
        EpisodeAutoassociativeMemory.from_vectors(vectors, hashes(2))


def test_synthetic_patterns_are_fixed_points_and_recover_one_bit() -> None:
    memory = orthogonal_fixture()

    for index, pattern in enumerate(memory.patterns):
        stable = memory.recall(pattern)
        assert stable.converged
        assert stable.changed_per_sweep == (0,)
        assert stable.matched_pattern_index == index
        for coordinate in range(memory.dimension):
            cue = pattern.copy()
            cue[coordinate] *= -1
            recalled = memory.recall(cue)
            assert recalled.converged
            assert recalled.matched_pattern_index == index
            assert np.array_equal(recalled.terminal_state, pattern)


def test_incremental_recall_matches_independent_slow_reference() -> None:
    memory = orthogonal_fixture()
    cue = np.array([-1, 1, 1, 1, -1, -1, -1, -1], dtype=np.int8)

    actual = memory.recall(cue)
    expected_state, expected_energies = reference_recall(memory.weights, cue)

    assert np.array_equal(actual.terminal_state, expected_state)
    assert actual.energy_trace == pytest.approx(expected_energies)
    assert all(
        later <= earlier + 1e-12
        for earlier, later in zip(actual.energy_trace, actual.energy_trace[1:])
    )


def test_hash_derived_corruption_is_deterministic_unique_and_exact() -> None:
    pattern = np.ones(64, dtype=np.int8)
    first, first_indices = degrade_pattern(pattern, hashes(1)[0], 19)
    second, second_indices = degrade_pattern(pattern, hashes(1)[0], 19)

    assert first_indices == second_indices
    assert first_indices == deterministic_flip_indices(hashes(1)[0], 64, 19)
    assert len(first_indices) == len(set(first_indices)) == 19
    assert np.array_equal(first, second)
    assert np.count_nonzero(first != pattern) == 19
    assert pattern_sha256(first) == pattern_sha256(second)


def test_runtime_guard_is_not_reported_as_convergence() -> None:
    memory = orthogonal_fixture()
    cue = np.array([-1, 1, 1, 1, -1, -1, -1, -1], dtype=np.int8)

    result = memory.recall(cue, max_sweeps=1)

    assert not result.converged
    assert result.sweeps == 1


def test_repair_mechanism_rejects_measurement_paths() -> None:
    with pytest.raises(ValueError, match="measurement boundary"):
        assert_mechanism_path_allowed("experiments/study_009/q_facts_key.md")
