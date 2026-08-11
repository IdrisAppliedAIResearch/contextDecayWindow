from __future__ import annotations

import inspect

import numpy as np
import pytest

from src.analysis.ps001_exploration import (
    GRID,
    LIVE_ARRAY_CEILING,
    execute_ordered_gates,
    synthetic_reachability,
    StageResult,
)
from src.retrieval_mechanism_ledger.ps001 import SparseEngramAutoassociator


def test_pf3_planted_g1_through_g4_failures_make_later_imports_unreachable() -> None:
    names = ["G1", "G2", "G3", "G4", "G5"]
    for failing_index in range(4):
        calls: list[str] = []

        def make_stage(index: int):
            def stage() -> StageResult:
                calls.append(names[index])
                status = "FAIL" if index == failing_index else "PASS"
                return StageResult(status, {"status": status})

            return stage

        results = execute_ordered_gates(
            [(name, make_stage(index)) for index, name in enumerate(names)]
        )

        assert calls == names[: failing_index + 1]
        assert all(results[name] == "NOT_REACHED" for name in names[failing_index + 1 :])


def test_pf4_all_fixed_cells_and_bars_are_structurally_reachable() -> None:
    assert len(GRID) == len(set(GRID)) == 9
    assert all(dimension > 1024 for dimension, _active in GRID)
    assert all(0 < active < dimension for dimension, active in GRID)
    assert synthetic_reachability()["status"] == "PASS"


def test_pf5_fit_api_rejects_unstable_or_forbidden_comparison_keys() -> None:
    parameters = inspect.signature(SparseEngramAutoassociator.fit).parameters

    assert tuple(parameters) == (
        "vectors",
        "code_dimension",
        "active_count",
        "projection_seed",
    )
    vectors = np.eye(2, dtype=np.float64)
    with pytest.raises(TypeError):
        SparseEngramAutoassociator.fit(
            vectors,
            code_dimension=4,
            active_count=1,
            projection_seed=bytes(32),
            source_turns=(1, 2),
        )


def test_pf8_and_pf10_have_no_live_ablation_or_model_surface() -> None:
    parameters = inspect.signature(SparseEngramAutoassociator.fit).parameters

    assert "model" not in parameters
    assert "query" not in parameters
    assert "ablation_turns" not in parameters
    assert LIVE_ARRAY_CEILING == 536_870_912
