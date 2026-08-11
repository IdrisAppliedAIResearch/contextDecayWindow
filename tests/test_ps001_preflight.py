from __future__ import annotations

import inspect
import json
from pathlib import Path

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
from src.analysis.ps001_preflight import (
    build_preflight,
    verify_manifest,
)


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


def test_committed_part2_preflight_answers_pf1_through_pf10() -> None:
    result = build_preflight()

    assert result["status"] == "PASS"
    assert result["check_order"] == [
        "PF1",
        "PF2",
        "PF3",
        "PF4",
        "PF5",
        "PF6",
        "PF7",
        "PF8",
        "PF9",
        "PF10",
    ]
    assert all(check["status"] == "PASS" for check in result["checks"].values())
    assert result["checks"]["PF7"]["trace_inventory"]["total_trace_count"] == 602
    assert not result["additional_real_mechanism_run"]


def test_manifest_verification_detects_identity_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    payload = root / "payload.json"
    payload.write_text('{"value":1}\n', encoding="utf-8")
    manifest = root / "artifact_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "payload.json",
                        "bytes": payload.stat().st_size,
                        "sha256": "0" * 64,
                    }
                ],
                "file_sequence_sha256": "fixture",
            }
        ),
        encoding="utf-8",
    )

    result = verify_manifest(root, manifest)

    assert result["status"] == "FAIL"
    assert result["identity_mismatches"] == ["payload.json"]
