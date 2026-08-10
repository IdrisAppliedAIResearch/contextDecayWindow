from __future__ import annotations

from src.analysis.e006_p3_reproduction import (
    assert_tier4_source_identity,
    reproduce_a1,
)


def test_tier4_carried_sources_are_byte_unchanged() -> None:
    assert assert_tier4_source_identity()["status"] == "PASS"


def test_a1_reproduces_all_eight_registered_cells() -> None:
    result = reproduce_a1()

    assert result["status"] == "PASS"
    assert result["passing_cell_count"] == result["cell_count"] == 8
    assert result["primary_cell"]["serialized_chars"] == 28_562
    assert result["primary_cell"]["selected_episode_count"] == 12
