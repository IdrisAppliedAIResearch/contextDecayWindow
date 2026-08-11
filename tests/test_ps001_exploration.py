from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pytest

from src.analysis.e006_p3_rev4_exploration import load_episode_vectors
from src.analysis.ps001_exploration import (
    EXPECTED_NORMALIZED_VECTOR_SHA256,
    GRID,
    REV4_COMMIT,
    REV4_RESULT_SHA256,
    apply_selection_rule,
    assert_imports_label_blind,
    audit_operator,
    compare_explorations,
    degenerate_cues,
    execute_ordered_gates,
    load_episode_population,
    load_historical_gate,
    synthetic_reachability,
    trace_record,
    StageResult,
    MECHANISM_SOURCE,
)
from src.retrieval_mechanism_ledger.ps001 import (
    SparseEngramAutoassociator,
    state_sha256,
)


def readonly(value: np.ndarray) -> np.ndarray:
    value.setflags(write=False)
    return value


def code(dimension: int, active: tuple[int, ...]) -> np.ndarray:
    value = np.zeros(dimension, dtype=np.uint8)
    value[np.asarray(active, dtype=np.int64)] = 1
    return value


def memory_from_codes(codes: np.ndarray) -> SparseEngramAutoassociator:
    matrix = np.asarray(codes, dtype=np.uint8)
    active_count = int(matrix[0].sum())
    dimension = matrix.shape[1]
    activity = active_count / dimension
    eta = matrix.astype(np.float64) - activity
    denominator = dimension * activity * (1.0 - activity)
    diagonal = (eta * eta).sum(axis=0) / denominator
    return SparseEngramAutoassociator(
        input_dimension=2,
        code_dimension=dimension,
        active_count=active_count,
        projection_seed=bytes(32),
        center=readonly(np.zeros(2, dtype=np.float64)),
        projection=readonly(np.zeros((dimension, 2), dtype=np.int8)),
        codes=readonly(matrix.copy()),
        activation_margins=readonly(np.ones(matrix.shape[0], dtype=np.float64)),
        eta=readonly(eta),
        denominator=denominator,
        diagonal=readonly(diagonal),
        code_hashes=tuple(state_sha256(row) for row in matrix),
    )


def gate(status: str, **payload: object) -> dict[str, object]:
    return {"status": status, **payload}


def cell(
    *,
    dimension: int = 2048,
    active: int = 20,
    g2: str = "PASS",
    g3: str = "FAIL",
    g4: str | None = None,
    g5: str | None = None,
    ten_percent: int = 0,
) -> dict[str, object]:
    gates: dict[str, object] = {
        "G1": gate("PASS"),
        "G2": gate(g2),
        "G3": gate(g3, fixed_point_count=119 if g3 == "PASS" else 0),
        "G4": "NOT_REACHED" if g4 is None else gate(g4, exact_recovery_count=119 if g4 == "PASS" else 0),
        "G5": "NOT_REACHED",
    }
    if g5 is not None:
        gates["G5"] = gate(
            g5,
            basin_levels={"10_percent": {"exact_recovery_count": ten_percent}},
        )
    return {
        "cell": f"d{dimension}_k{active}",
        "code_dimension": dimension,
        "active_count": active,
        "gates": gates,
    }


def test_grid_is_the_nine_locked_cells() -> None:
    assert GRID == (
        (2048, 20),
        (2048, 41),
        (2048, 102),
        (4096, 41),
        (4096, 82),
        (4096, 205),
        (8192, 82),
        (8192, 164),
        (8192, 410),
    )


def test_real_population_reproduces_rev4_identity_without_measurement() -> None:
    population = load_episode_population()
    rev4_vectors, rev4_hashes, rev4_turns = load_episode_vectors()

    assert population.vectors.shape == (119, 1024)
    assert population.inventory["normalized_float64_sha256"] == (
        EXPECTED_NORMALIZED_VECTOR_SHA256
    )
    assert np.array_equal(population.vectors, rev4_vectors)
    assert population.content_hashes == rev4_hashes
    assert population.source_turns == rev4_turns


def test_synthetic_storage_and_one_swap_bars_are_reachable() -> None:
    result = synthetic_reachability()

    assert result == {
        "status": "PASS",
        "stored_fixed_points": 1,
        "one_swap_recoveries": 12,
        "one_swap_required": 12,
    }


def test_gate_failure_short_circuits_all_later_stage_calls() -> None:
    calls: list[str] = []

    def stage(name: str, status: str) -> StageResult:
        calls.append(name)
        return StageResult(status, {"status": status})

    results = execute_ordered_gates(
        [
            ("G1", lambda: stage("G1", "PASS")),
            ("G2", lambda: stage("G2", "FAIL")),
            ("G3", lambda: stage("G3", "PASS")),
            ("G4", lambda: stage("G4", "PASS")),
            ("G5", lambda: stage("G5", "PASS")),
        ]
    )

    assert calls == ["G1", "G2"]
    assert results["G3"] == results["G4"] == results["G5"] == "NOT_REACHED"


def test_selection_rule_reaches_all_registered_valid_dispositions() -> None:
    assert apply_selection_rule([cell(g2="FAIL")]) == (
        None,
        "NO_VALID_IMPLEMENTATION",
    )
    assert apply_selection_rule([cell(g3="FAIL")]) == (
        None,
        "NO_STORED_SPARSE_CODE",
    )
    assert apply_selection_rule([cell(g3="PASS", g4="FAIL")]) == (
        None,
        "NO_VIABLE_SPARSE_CODE",
    )
    selected, disposition = apply_selection_rule(
        [
            cell(dimension=4096, active=82, g3="PASS", g4="PASS", g5="PASS", ten_percent=100),
            cell(dimension=2048, active=41, g3="PASS", g4="PASS", g5="PASS", ten_percent=100),
            cell(dimension=2048, active=20, g3="PASS", g4="PASS", g5="PASS", ten_percent=99),
        ]
    )
    assert disposition == "SPARSE_ENGRAM_CANDIDATE_CHARACTERIZED"
    assert selected == {
        "code_dimension": 2048,
        "active_count": 41,
        "ten_percent_exact_recovery_count": 100,
    }


def test_operator_audit_reconstructs_real_fields_and_weights() -> None:
    memory = memory_from_codes(
        np.stack([code(8, (0, 1)), code(8, (3, 4)), code(8, (6, 7))])
    )

    result = audit_operator(memory, time.perf_counter())

    assert result["status"] == "PASS"
    assert result["eta_reproduced_by_bytes"]
    assert result["diagonal_reproduced_by_bytes"]
    assert result["symmetric"] and result["zero_diagonal"]
    assert result["all_real_fields_match"]
    assert result["all_real_transitions_match"]


def test_trace_schema_distinguishes_spurious_cycle_and_runtime_fields() -> None:
    memory = memory_from_codes(
        np.stack([code(6, (2, 5)), code(6, (1, 5)), code(6, (0, 1))])
    )
    hashes = tuple(f"{index + 1:064x}" for index in range(3))
    row = trace_record(
        memory,
        memory.recall(code(6, (0, 3))),
        cue_level="fixture",
        swap_count=1,
        source_index=0,
        content_hashes=hashes,
    )

    assert row["cycle"] and not row["converged"]
    assert row["repeated_state_witness"] == [0, 2]
    assert row["terminal_status"] == "spurious"
    assert len(row["active_count_per_state"]) == len(row["state_sha256_trace"])
    assert set(row) >= {
        "quadratic_score_trace",
        "field_margin_trace",
        "terminal_hamming_distance",
        "exact_source_recovery",
    }


def test_degenerate_cues_are_exact_sparsity_and_deterministic() -> None:
    memory = memory_from_codes(
        np.stack([code(8, (0, 1)), code(8, (3, 4)), code(8, (6, 7))])
    )
    hashes = tuple(f"{index + 1:064x}" for index in range(6))

    first = degenerate_cues(memory, hashes)
    second = degenerate_cues(memory, hashes)

    assert [name for name, _cue in first] == [
        "lowest_indices",
        "highest_indices",
        "union_biased",
        "hash_seeded_random_0",
        "hash_seeded_random_1",
        "hash_seeded_random_2",
        "hash_seeded_random_3",
    ]
    assert all(int(cue.sum()) == memory.active_count for _name, cue in first)
    assert all(np.array_equal(left[1], right[1]) for left, right in zip(first, second))


def test_mechanism_source_and_import_graph_are_label_blind() -> None:
    result = assert_imports_label_blind([MECHANISM_SOURCE])

    assert result["status"] == "PASS"
    assert "planted forbidden import rejected" in result["planted_forbidden_import"]


def test_historical_gate_requires_exact_commit_digest_and_basins(tmp_path: Path) -> None:
    gate = {
        "status": "PASS",
        "control_commit": REV4_COMMIT,
        "generated_result_sha256": REV4_RESULT_SHA256,
        "exact_reproduction": {
            "converged_count": 119,
            "stored_fixed_point_count": 0,
            "basin_sizes": [5, 13, 15, 20, 29, 37],
        },
    }
    path = tmp_path / "historical.json"
    path.write_text(json.dumps(gate), encoding="utf-8")

    assert load_historical_gate(path) == gate
    gate["generated_result_sha256"] = "0" * 64
    path.write_text(json.dumps(gate), encoding="utf-8")
    with pytest.raises(RuntimeError, match="digest"):
        load_historical_gate(path)


def test_comparison_accepts_only_identical_canonical_outputs(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for directory in (first, second):
        (directory / "exploration.json").write_text(
            json.dumps({"determinism": {"mechanism_digest": "abc"}}),
            encoding="utf-8",
        )
        (directory / "trace.jsonl").write_text('{"x":1}\n', encoding="utf-8")
    output = tmp_path / "comparison.json"

    result = compare_explorations(first, second, output)

    assert result["status"] == "PASS"
    with pytest.raises(FileExistsError, match="overwrite"):
        compare_explorations(first, second, output)
