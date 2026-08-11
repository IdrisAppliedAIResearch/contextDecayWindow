from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.ps002_exploration import (
    GRID,
    MECHANISM_SOURCE,
    EXPLORATION_SOURCE,
    assert_imports_label_blind,
    compare_explorations,
    construct_carried_memory,
    load_queries,
    select_cell,
)


def eligible_cell(
    width: int,
    temperature: float,
    *,
    changed: int,
    margin: float,
    hamming: float,
) -> dict[str, object]:
    return {
        "cell": f"m{width}_t{temperature:.3f}",
        "support_width": width,
        "temperature": temperature,
        "changed_and_completed_count": changed,
        "minimum_positive_terminal_margin": margin,
        "median_initial_terminal_hamming": hamming,
        "eligible": True,
    }


def test_grid_is_exact_registered_row_major_order() -> None:
    assert GRID == (
        (4, 0.025),
        (4, 0.05),
        (4, 0.1),
        (8, 0.025),
        (8, 0.05),
        (8, 0.1),
        (16, 0.025),
        (16, 0.05),
        (16, 0.1),
    )


def test_selection_is_label_blind_and_uses_registered_tie_order() -> None:
    cells = [
        eligible_cell(8, 0.05, changed=100, margin=0.2, hamming=12),
        eligible_cell(4, 0.1, changed=100, margin=0.2, hamming=12),
        eligible_cell(4, 0.025, changed=100, margin=0.2, hamming=12),
        eligible_cell(16, 0.025, changed=101, margin=0.1, hamming=2),
    ]

    assert select_cell(cells)["support_width"] == 16
    assert select_cell([dict(cell, changed_and_completed_count=100) for cell in cells])[
        "temperature"
    ] == 0.025
    assert select_cell([dict(cells[0], eligible=False)]) is None


def test_sealed_query_cache_loads_all_24_without_model_calls() -> None:
    queries, inventory = load_queries()

    assert len(queries) == 24
    assert queries[0]["query_id"] == "h121_l01"
    assert queries[-1]["query_id"] == "h121_e04"
    assert all(row["vector"].shape == (1024,) for row in queries)
    assert inventory["cache_metadata"]["call_shape"] == "solo"


def test_carried_memory_reproduces_ps001_codes_and_fixed_points() -> None:
    population, memory, identity = construct_carried_memory()

    assert population.vectors.shape == (119, 1024)
    assert memory.codes.shape == (119, 4096)
    assert identity["status"] == "PASS"
    assert identity["fixed_points"] == 119


def test_exploration_import_graph_is_label_blind() -> None:
    result = assert_imports_label_blind([MECHANISM_SOURCE, EXPLORATION_SOURCE])

    assert result["status"] == "PASS"
    assert result["planted_sentinel"] == "planted forbidden path rejected"


def test_two_process_comparison_requires_exact_digests_and_traces(tmp_path: Path) -> None:
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

    result = compare_explorations(first, second, tmp_path / "comparison.json")

    assert result["status"] == "PASS"
    (second / "trace.jsonl").write_text('{"x":2}\n', encoding="utf-8")
    with pytest.raises(AssertionError, match="determinism"):
        compare_explorations(first, second, tmp_path / "failed.json")
