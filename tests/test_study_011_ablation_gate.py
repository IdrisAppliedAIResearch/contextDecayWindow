"""Tests for Study 011's G6 ablation gate."""

from __future__ import annotations

import json

import pytest

from src.analysis import study_011_ablation_gate as gate


def _write_turns(directory, rows) -> None:
    logs = directory / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "turns.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _clean_rows(count: int = 35) -> list[dict]:
    return [
        {
            "turn_number": index + 1,
            "assistant_message": f"answer {index} with distinct content",
            "output_tokens": 200,
        }
        for index in range(count)
    ]


def test_a_clean_arm_is_go(tmp_path) -> None:
    _write_turns(tmp_path, _clean_rows())
    result = gate.assess_arm("A", tmp_path)
    assert result["decision"] == "GO"
    assert result["reasons"] == []


def test_a_short_run_is_no_go(tmp_path) -> None:
    _write_turns(tmp_path, _clean_rows(30))
    result = gate.assess_arm("B", tmp_path)
    assert result["decision"] == "NO_GO"
    assert "completed 30 of 35 turns" in result["reasons"][0]


def test_an_empty_response_is_no_go(tmp_path) -> None:
    rows = _clean_rows()
    rows[7]["assistant_message"] = "   "
    _write_turns(tmp_path, rows)
    result = gate.assess_arm("B", tmp_path)
    assert result["decision"] == "NO_GO"
    assert result["scoreability"]["empty_response_turns"] == [8]


def test_a_verbatim_repeat_is_no_go(tmp_path) -> None:
    """Arm B's registered hazard: degenerate rather than merely worse."""

    rows = _clean_rows()
    rows[12]["assistant_message"] = rows[11]["assistant_message"]
    _write_turns(tmp_path, rows)
    result = gate.assess_arm("B", tmp_path)
    assert result["decision"] == "NO_GO"
    assert result["scoreability"]["verbatim_repeat_turns"] == [13]


def test_coherence_is_reported_and_never_decides(tmp_path) -> None:
    """A terse arm still passes; no coherence threshold is registered."""

    rows = _clean_rows()
    for row in rows:
        row["assistant_message"] = "ok"
    _write_turns(tmp_path, rows)
    result = gate.assess_arm("B", tmp_path)
    # Identical short answers repeat verbatim, so this arm is caught by
    # scoreability, not by a length rule.
    assert result["decision"] == "NO_GO"
    assert result["scoreability"]["verbatim_repeat_turns"]
    assert "not for deciding" in (
        result["coherence_reported_not_thresholded"]["note"]
    )


def test_budget_truncation_is_reported_without_deciding(tmp_path) -> None:
    rows = _clean_rows()
    rows[3]["output_tokens"] = 2048
    _write_turns(tmp_path, rows)
    result = gate.assess_arm("A", tmp_path)
    assert result["decision"] == "GO"
    assert result["scoreability"]["budget_truncated_turns"] == [4]


def test_a_missing_turn_log_stops_the_gate(tmp_path) -> None:
    with pytest.raises(gate.AblationGateError, match="no turn log"):
        gate.assess_arm("C", tmp_path)


def test_the_control_arm_reads_the_carried_output_directory(monkeypatch, tmp_path) -> None:
    """Arm D's directory is named by the carried runner, not renamed."""

    monkeypatch.setattr(gate, "ABLATION_RUNS", tmp_path)
    assert gate._arm_dir("D", {"D": "run"}).name == "context_matched_stm"
    assert gate._arm_dir("C", {"C": "run"}).name == "arm_c"


def test_one_no_go_arm_makes_the_gate_no_go(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(gate, "ABLATION_RUNS", tmp_path)
    for arm in gate.ARMS:
        directory = gate._arm_dir(arm, {arm: f"run_{arm}"})
        rows = _clean_rows(35 if arm != "B" else 20)
        _write_turns(directory, rows)
    result = gate.build({arm: f"run_{arm}" for arm in gate.ARMS})
    assert result["decision"] == "NO_GO"
    assert result["arms_not_go"] == ["B"]
    assert "recency floor" in result["consequence"]


def test_all_arms_clean_is_go(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(gate, "ABLATION_RUNS", tmp_path)
    for arm in gate.ARMS:
        _write_turns(gate._arm_dir(arm, {arm: f"run_{arm}"}), _clean_rows())
    result = gate.build({arm: f"run_{arm}" for arm in gate.ARMS})
    assert result["decision"] == "GO"
    assert result["arms_missing"] == []
