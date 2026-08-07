"""Tests for Study 011's B1 bar and registered contrasts."""

from __future__ import annotations

import json

import pytest

from src.analysis import study_011_verdict as verdict


def _scores(**overrides) -> dict[str, dict[str, float]]:
    base = {arm: {q: 1.0 for q in verdict.QUESTIONS} for arm in verdict.ARMS}
    for arm, changes in overrides.items():
        base[arm].update(changes)
    return base


def _write(tmp_path, scores) -> object:
    path = tmp_path / "rubric_scores.json"
    path.write_text(json.dumps({"scores": scores}), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# B1 is the only bar
# --------------------------------------------------------------------------


def test_b1_passes_when_c_equals_d() -> None:
    result = verdict.b1_verdict(_scores())
    assert result["status"] == "PASS"
    assert result["delta"] == 0.0


def test_b1_passes_when_c_beats_d() -> None:
    scores = _scores(D={"Q5": 0.0})
    assert verdict.b1_verdict(scores)["status"] == "PASS"


def test_b1_fails_when_c_falls_below_d(  ) -> None:
    """The LV-001 rule generalised: delivery up, answers down, not adopted."""

    scores = _scores(C={"Q5": 0.0})
    result = verdict.b1_verdict(scores)
    assert result["status"] == "FAIL"
    assert result["delta"] == -1.0
    assert "NOT adopted" in result["consequence"]
    assert "availability gain" in result["consequence"]


def test_b1_fails_on_half_a_point() -> None:
    assert verdict.b1_verdict(_scores(C={"Q5": 0.5}))["status"] == "FAIL"


# --------------------------------------------------------------------------
# Paired contrasts keep gains and losses apart
# --------------------------------------------------------------------------


def test_gains_and_losses_are_separated_not_netted() -> None:
    scores = _scores(C={"Q1": 1.0, "Q2": 0.0}, D={"Q1": 0.0, "Q2": 1.0})
    contrast = verdict.paired(scores, "C", "D")
    assert contrast["total_delta"] == 0.0
    assert [row["question"] for row in contrast["gains"]] == ["Q1"]
    assert [row["question"] for row in contrast["losses"]] == ["Q2"]


def test_a_zero_total_does_not_hide_offsetting_moves() -> None:
    """The aggregate reads unchanged while two questions moved."""

    scores = _scores(C={"Q1": 1.0, "Q2": 0.0}, D={"Q1": 0.0, "Q2": 1.0})
    contrast = verdict.paired(scores, "C", "D")
    assert contrast["total_delta"] == 0.0
    assert contrast["unchanged_count"] == 11
    assert len(contrast["gains"]) + len(contrast["losses"]) == 2


def test_every_registered_contrast_is_reported() -> None:
    result = verdict.build(_scores())
    assert set(result["registered_contrasts"]) == {"C-D", "C-A", "C-B", "A-B"}


def test_per_question_rows_accompany_every_contrast() -> None:
    result = verdict.build(_scores())
    for contrast in result["registered_contrasts"].values():
        assert len(contrast["per_question"]) == 13


# --------------------------------------------------------------------------
# What the module refuses to claim
# --------------------------------------------------------------------------


def test_no_significance_claim_is_stated_in_the_artifact() -> None:
    result = verdict.build(_scores())
    assert "no variance estimate" in result["no_significance_claim"]
    assert "single run per arm" in result["no_significance_claim"]


def test_study_009_is_a_reference_not_an_arm() -> None:
    result = verdict.build(_scores())
    assert result["study_009_reference"]["arm_S"] == 9.0
    assert result["study_009_reference"]["arm_L"] == 12.0
    assert "not a comparison arm" in result["study_009_reference"]["caveat"]


# --------------------------------------------------------------------------
# Scores must be committed and complete
# --------------------------------------------------------------------------


def test_missing_scores_file_stops_the_verdict(tmp_path) -> None:
    with pytest.raises(verdict.VerdictError, match="no committed scores"):
        verdict.load_scores(tmp_path / "absent.json")


def test_a_missing_arm_stops_the_verdict(tmp_path) -> None:
    scores = _scores()
    del scores["B"]
    with pytest.raises(verdict.VerdictError, match="no committed score for arm B"):
        verdict.load_scores(_write(tmp_path, scores))


def test_a_missing_question_stops_the_verdict(tmp_path) -> None:
    scores = _scores()
    del scores["C"]["Q7"]
    with pytest.raises(verdict.VerdictError, match="missing scores"):
        verdict.load_scores(_write(tmp_path, scores))


def test_totals_are_out_of_thirteen(tmp_path) -> None:
    scores = verdict.load_scores(_write(tmp_path, _scores()))
    assert verdict.totals(scores) == {arm: 13.0 for arm in verdict.ARMS}
