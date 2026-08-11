from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis.ps003_exploration import (
    EXPLORATION_SOURCE,
    GRID,
    PS003_SOURCE,
    assert_anchors,
    assert_carried_artifacts,
    assert_imports_label_blind,
    compare_explorations,
    construct_carried_memory,
    load_queries,
    reproduce_ps002_strongest,
    select_cell,
)


def eligible_cell(
    probe_count: int, swap_count: int, *, attempts: int
) -> dict[str, object]:
    return {
        "cell": f"p{probe_count}_s{swap_count}",
        "probe_count": probe_count,
        "swap_count": swap_count,
        "attempt_count": attempts,
        "eligible": True,
    }


def test_grid_is_exact_registered_row_major_order() -> None:
    assert GRID == ((3, 1), (3, 4), (5, 1), (5, 4))


def test_selection_prioritizes_radius_then_probe_count_then_attempts() -> None:
    cells = [
        eligible_cell(3, 1, attempts=190),
        eligible_cell(3, 4, attempts=220),
        eligible_cell(5, 1, attempts=200),
        eligible_cell(5, 4, attempts=230),
    ]

    assert select_cell(cells)["cell"] == "p5_s4"
    assert select_cell([dict(cell, eligible=False) for cell in cells]) is None


def test_locked_inputs_and_carried_artifacts_match() -> None:
    anchors = assert_anchors()
    carried = assert_carried_artifacts()

    assert anchors["design"].startswith("32cfe67e")
    assert carried["status"] == "PASS"


def test_ps002_strongest_cell_reproduces_exactly() -> None:
    population, memory, identity = construct_carried_memory()
    queries, _ = load_queries()

    result = reproduce_ps002_strongest(memory, population, queries)

    assert identity["fixed_points"] == 119
    assert result["status"] == "PASS"
    assert result["deterministic_digest"].startswith("b815c066")


def test_exploration_import_graph_is_label_blind() -> None:
    result = assert_imports_label_blind([PS003_SOURCE, EXPLORATION_SOURCE])

    assert result["status"] == "PASS"
    assert result["planted_sentinel"] == "planted forbidden path rejected"


def test_two_process_comparison_requires_exact_trace_files(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for directory in (first, second):
        (directory / "exploration.json").write_text(
            json.dumps({"determinism": {"mechanism_digest": "abc"}}),
            encoding="utf-8",
        )
        cell = directory / "cells" / "p3_s1"
        cell.mkdir(parents=True)
        (cell / "traces.jsonl").write_text('{"x":1}\n', encoding="utf-8")

    result = compare_explorations(first, second, tmp_path / "comparison.json")

    assert result["status"] == "PASS"
    (second / "cells" / "p3_s1" / "traces.jsonl").write_text(
        '{"x":2}\n', encoding="utf-8"
    )
    with pytest.raises(AssertionError, match="determinism"):
        compare_explorations(first, second, tmp_path / "failed.json")
