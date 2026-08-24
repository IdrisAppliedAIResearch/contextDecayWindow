"""Registered-unit checks for TC-003's arms, bars, anchors, and phase gates."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from analysis import tc003_study as study
from analysis.tc003_exploration import equal_shares
from analysis.tc003_reachability import _forbid_direction
from analysis.tc003_study import (
    ALPHA,
    ANCHOR,
    ARMS,
    CONTRASTS,
    CONTROL_ANCHOR,
    ISOLATING_CONTRAST,
    NO_BAR,
    NULL_BAND_BY_BUDGET,
    PRIMARY_BUDGET,
    PRIMARY_CONTRAST,
    PRIMARY_ENDPOINT,
    SECONDARY_BUDGET,
    SIGNAL_ALPHA,
    TC003Error,
    all_contrasts,
    assert_registration_agrees,
    band_for,
    paired,
    run_precondition,
    verdict,
    wrapper_matched_c3,
)

C1 = CONTRASTS[0]
C5 = CONTRASTS[4]


def _row(question: str, **hits: bool) -> dict:
    base = {
        "question_id": question,
        "sample_id": "conv-41",
        "category": "4",
        "complete_evaluable": True,
        "evidence_episodes": 1,
        "flat_best_evidence_rank": 3,
        "flat_worst_evidence_rank": 9,
    }
    for arm in ARMS:
        hit = hits.get(arm, False)
        base[f"{arm}_complete"] = hit
        base[f"{arm}_any"] = hit
        base[f"{arm}_delivered"] = 50
        base[f"{arm}_evidence_delivered"] = int(hit)
        base[f"{arm}_chars"] = 15_950
        base[f"{arm}_evidence_tiers"] = "k" if hit else ""
        for tier in ("recency", "k", "coverage", "outside"):
            base[f"{arm}_{tier}"] = 0
    base["flat_matched_complete"] = base["flat_complete"]
    base["flat_matched_any"] = base["flat_any"]
    base["flat_matched_delivered"] = base["flat_delivered"]
    base["flat_matched_evidence_delivered"] = base["flat_evidence_delivered"]
    base["flat_matched_chars"] = 15_932
    base["flat_matched_evidence_tiers"] = base["flat_evidence_tiers"]
    for tier in ("recency", "k", "coverage", "outside"):
        base[f"flat_matched_{tier}"] = base[f"flat_{tier}"]
    return base


def _pair_rows(
    left: str, right: str, gains: int, losses: int, ties: int = 0
) -> list[dict]:
    result = [
        _row(f"g{index}", **{left: True, right: False})
        for index in range(gains)
    ]
    result += [
        _row(f"l{index}", **{left: False, right: True})
        for index in range(losses)
    ]
    result += [
        _row(f"t{index}", **{left: True, right: True})
        for index in range(ties)
    ]
    return result


def test_registered_bands_are_budget_specific_and_cannot_default() -> None:
    assert NULL_BAND_BY_BUDGET == {16_000: 4, 32_000: 10}
    assert band_for(PRIMARY_BUDGET) == 4
    assert band_for(SECONDARY_BUDGET) == 10
    with pytest.raises(TC003Error):
        band_for(24_000)


def test_alphas_keep_the_six_contrast_divisor() -> None:
    assert len(CONTRASTS) == 6
    assert ALPHA == pytest.approx(0.01 / 6)
    assert SIGNAL_ALPHA == pytest.approx(0.10 / 6)


@pytest.mark.parametrize(
    "gains,losses,expected_disposition,expected_verdict",
    [
        (30, 0, "D1", "FLOORS_WINS"),
        (0, 30, "D3", "N_FIRST_WINS"),
        (9, 1, "D2", "FLOORS_WINS_CARRIES_SIGNAL"),
        (1, 9, "D4", "N_FIRST_WINS_CARRIES_SIGNAL"),
        (3, 0, "D0a", "NO_DIFFERENCE_ESTABLISHED_INSIDE_BAND"),
        (12, 4, "D0b", "NO_DIFFERENCE_ESTABLISHED_NOT_SEPARABLE"),
    ],
)
def test_every_registered_disposition_branch(
    gains: int,
    losses: int,
    expected_disposition: str,
    expected_verdict: str,
) -> None:
    rows = _pair_rows("floors", "n_first", gains, losses, ties=50)
    outcome = verdict(paired(rows, "floors", "n_first", "complete"), C1, budget=16_000)
    assert outcome["disposition"] == expected_disposition
    assert outcome["verdict"] == expected_verdict


def test_disposition_table_is_exhaustive_over_a_grid() -> None:
    seen = set()
    for gains in range(15):
        for losses in range(15):
            rows = _pair_rows("floors", "n_first", gains, losses, ties=2)
            outcome = verdict(
                paired(rows, "floors", "n_first", "complete"),
                C1,
                budget=16_000,
            )
            assert outcome["disposition"] in {
                "D0a",
                "D0b",
                "D1",
                "D2",
                "D3",
                "D4",
            }
            seen.add(outcome["disposition"])
    assert {"D0a", "D1", "D3"} <= seen


def test_band_is_applied_before_p_value() -> None:
    rows = _pair_rows("floors", "n_first", 3, 0, ties=800)
    statistic = paired(rows, "floors", "n_first", "complete")
    assert verdict(statistic, C1, budget=16_000)["disposition"] == "D0a"


def test_c5_is_descriptive_only_at_32000() -> None:
    assert NO_BAR == frozenset({(32_000, "C5")})
    rows = _pair_rows("floors_dual", "dual_ranked", 30, 0, ties=800)
    statistic = paired(rows, "floors_dual", "dual_ranked", "complete")
    assert verdict(statistic, C5, budget=16_000)["disposition"] == "D1"
    descriptive = verdict(statistic, C5, budget=32_000)
    assert descriptive["disposition"] == "DESCRIPTIVE"
    assert descriptive["band"] is None
    assert descriptive["registered_budget_band"] == 10


def test_all_other_contrasts_keep_bars_at_both_budgets() -> None:
    rows = [_row(f"q{index}") for index in range(20)]
    for budget in (16_000, 32_000):
        outcomes = all_contrasts(rows, "complete", budget=budget)
        for identifier, outcome in outcomes.items():
            if (budget, identifier) == (32_000, "C5"):
                assert outcome["disposition"] == "DESCRIPTIVE"
            else:
                assert outcome["disposition"] != "DESCRIPTIVE"


def test_headline_is_c1_and_c5_is_the_isolating_contrast() -> None:
    assert PRIMARY_CONTRAST == "C1"
    assert PRIMARY_ENDPOINT == "complete"
    assert ISOLATING_CONTRAST == "C5"
    assert CONTRASTS[0][:3] == ("C1", "floors", "n_first")
    assert CONTRASTS[4][:3] == ("C5", "floors_dual", "dual_ranked")


def test_exactly_the_seven_registered_arms_exist() -> None:
    assert ARMS == (
        "flat",
        "n_first",
        "k_first",
        "dual",
        "dual_ranked",
        "floors",
        "floors_dual",
    )


def test_equal_share_rule_has_no_free_parameter() -> None:
    assert tuple(inspect.signature(equal_shares).parameters) == ("state",)


def test_anchor_table_contains_all_twenty_registered_cells() -> None:
    assert set(ANCHOR) == {
        (16_000, "complete"),
        (16_000, "any"),
        (32_000, "complete"),
        (32_000, "any"),
    }
    assert all(set(row) == set(ARMS[:5]) for row in ANCHOR.values())
    assert sum(len(row) for row in ANCHOR.values()) == 20


def test_anchor_table_matches_both_committed_artifacts() -> None:
    assert study._committed_anchor() == ANCHOR


def test_control_anchor_is_the_direction_free_pf4_table() -> None:
    assert CONTROL_ANCHOR[(16_000, "floors")]["zero_service_separates"] == 871
    assert CONTROL_ANCHOR[(16_000, "floors_dual")]["zero_service_separates"] == 633
    assert CONTROL_ANCHOR[(32_000, "floors_dual")]["zero_service_separates"] == 351
    assert all(value["overlap"] == 871 for value in CONTROL_ANCHOR.values())


def test_registration_carries_every_constant_used_by_the_module() -> None:
    result = assert_registration_agrees()
    assert result["status"] == "PASS"
    assert len(result["pre_registration_sha256"]) == 64
    assert result["design_commit"].startswith("863d0a67")


def test_run_refuses_an_absent_or_uncommitted_g0(tmp_path: Path) -> None:
    with pytest.raises(TC003Error):
        run_precondition(tmp_path)
    gate = tmp_path / "g0"
    gate.mkdir()
    (gate / "g0_reproduction.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )
    with pytest.raises(TC003Error):
        run_precondition(tmp_path)


def test_unregistered_phase_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TC003Error):
        study.run_phase(tmp_path, "exploratory")


def test_pf4_artifact_contains_no_directional_key() -> None:
    payload = json.loads(study.PF4_ARTIFACT.read_text(encoding="utf-8"))
    _forbid_direction(payload)
    with pytest.raises(Exception):
        _forbid_direction({"gains": 1})


def test_wrapper_pass_is_c3_only_and_carries_no_bar() -> None:
    rows = [
        _row("q1", floors=True, flat=False),
        _row("q2", floors=False, flat=True),
    ]
    rows[0]["flat_matched_complete"] = False
    rows[1]["flat_matched_complete"] = False
    result = wrapper_matched_c3(rows, 16_000)
    assert study.WRAPPER_MATCHED_CONTRASTS == ("C3",)
    assert result["bar"] is None
    assert result["can_change_disposition"] is False
    assert set(result["endpoints"]) == {"complete", "any"}
