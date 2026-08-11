from __future__ import annotations

from pathlib import Path

import pytest

from src.analysis.ta001_preflight import MeasurementBoundary, replay_records, run, source_existence


def test_preflight_passes_all_checks(tmp_path: Path) -> None:
    result = run(tmp_path / "preflight")
    assert result["status"] == "PASS"
    assert set(result["checks"]) == {f"PF{number}" for number in range(1, 11)}
    assert all(row["pass"] for row in result["checks"].values())
    assert result["checks"]["PF6"]["evidence"]["c0"]["packed_fact_count"] == 7


def test_required_sources_and_registered_ceilings_exist() -> None:
    evidence = source_existence()
    assert evidence["holdout_all_sources_present"]
    assert evidence["q11_item_ceiling"] == 17
    assert evidence["q11_art_ceiling"] == 4


def test_replay_is_stateless_and_measurement_fails_closed() -> None:
    assert replay_records() == replay_records()
    with pytest.raises(RuntimeError):
        MeasurementBoundary().require_open()


def test_preflight_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "preflight"
    run(output)
    with pytest.raises(FileExistsError):
        run(output)
