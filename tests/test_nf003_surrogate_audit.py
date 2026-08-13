from __future__ import annotations

from pathlib import Path

import pytest

from analysis.nf003_surrogate_audit import evaluate


@pytest.fixture(scope="module")
def audit() -> dict:
    return evaluate(Path(__file__).resolve().parents[1])


def test_session_touch_reproduces_part1(audit: dict) -> None:
    assert audit["population"] == {
        "evaluated_items": 465,
        "excluded_without_turn_level_flags": 5,
    }
    assert audit["session_touch_measure"] == {
        "baseline_hits": 396,
        "treatment_hits": 445,
        "paired": {"gains": 49, "losses": 0, "ties": 416},
    }


def test_strict_answer_episode_measure_exposes_regression(audit: dict) -> None:
    assert audit["strict_answer_episode_measure"] == {
        "baseline_hits": 388,
        "treatment_hits": 351,
        "paired": {"gains": 26, "losses": 63, "ties": 376},
    }


def test_nf002_unit_change_retains_a_smaller_strict_gain(audit: dict) -> None:
    assert audit["nf002_strict_context"] == {
        "baseline_hits": 375,
        "treatment_hits": 388,
        "paired": {"gains": 17, "losses": 4, "ties": 444},
    }


def test_session_touch_can_pass_without_answer_evidence(audit: dict) -> None:
    assert audit["surrogate_gap"] == {
        "baseline_session_hit_without_answer_episode": 8,
        "treatment_session_hit_without_answer_episode": 94,
    }
    assert audit["model_calls"] == 0
    assert audit["embedding_calls"] == 0
