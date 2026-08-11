from __future__ import annotations

import numpy as np

from src.analysis.e006_p3_rev4_exploration import (
    evaluate_gates,
    load_memory,
    synthetic_reachability,
)
from src.retrieval_mechanism_ledger.e006_p3_rev4 import (
    EpisodeAutoassociativeMemory,
    deterministic_flip_indices,
)


def hashes(count: int) -> tuple[str, ...]:
    return tuple(f"{index + 1:064x}" for index in range(count))


def test_corruption_fixture_has_committed_expected_coordinates() -> None:
    assert deterministic_flip_indices(hashes(1)[0], 64, 19) == (
        55,
        22,
        47,
        7,
        49,
        48,
        10,
        31,
        15,
        14,
        20,
        24,
        52,
        56,
        29,
        43,
        21,
        9,
        37,
    )


def test_synthetic_g3_and_g4_bars_are_reachable() -> None:
    assert synthetic_reachability()["status"] == "PASS"


def test_real_input_identity_is_119_by_1024_without_measurement() -> None:
    memory, turns, inventory = load_memory()

    assert memory.patterns.shape == (119, 1024)
    assert len(set(memory.content_hashes)) == 119
    assert len(set(memory.pattern_hashes)) == 119
    assert (min(turns), max(turns)) == (1, 119)
    assert inventory["vector_shape"] == [119, 1024]


def test_g3_failure_stops_before_all_later_cues() -> None:
    patterns = np.array(
        [
            [1, -1, 1, -1, -1, -1],
            [1, -1, -1, -1, -1, -1],
            [1, 1, -1, 1, -1, -1],
        ],
        dtype=np.int8,
    )
    memory = EpisodeAutoassociativeMemory.from_patterns(patterns, hashes(3))
    vectors = patterns.astype(np.float64)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    result = evaluate_gates(
        memory,
        (1, 2, 3),
        {"episode_count": 3},
        vectors,
    )

    assert result["disposition"] == "PATTERNS_NOT_STORED"
    assert result["gates"]["G3"]["status"] == "FAIL"
    assert result["gates"]["G4"] == "NOT_REACHED"
    assert result["gates"]["G5"] == "NOT_REACHED"
    assert "descriptive_recovery" not in result
