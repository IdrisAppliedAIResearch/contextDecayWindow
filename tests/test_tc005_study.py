from __future__ import annotations

from pathlib import Path

import pytest

from analysis import tc005_study as study


def _cell(net: int, p_treatment: float = 1.0, p_dense: float = 1.0, budget: int = 8_000):
    gains = max(net, 0)
    losses = max(-net, 0)
    return {
        "net": net,
        "gains": gains,
        "losses": losses,
        "band": study.NULL_BAND[budget],
        "treatment_one_sided_p": p_treatment,
        "dense_one_sided_p": p_dense,
    }


def _primary(a: dict, b: dict):
    return {"8000": a, "16000": b}


def _guards(a: dict | None = None, b: dict | None = None):
    return {
        "16000": a or _cell(0, budget=16_000),
        "32000": b or _cell(0, budget=32_000),
    }


def test_registered_constants_match_the_pre_registration() -> None:
    assert study.BUDGETS == (8_000, 16_000, 32_000)
    assert study.NULL_BAND == {8_000: 1, 16_000: 2, 32_000: 0}
    assert study.WORKS_ALPHA == pytest.approx(0.00125)
    assert study.SIGNAL_ALPHA == pytest.approx(0.0125)
    assert study.TARGETED_N == 704
    assert study.ELIGIBLE_N == 868
    assert study.assert_registration()["status"] == "PASS"


def test_treatment_works_only_at_both_half_budgets() -> None:
    strong8 = _cell(10, p_treatment=0.0001, budget=8_000)
    strong16 = _cell(10, p_treatment=0.0001, budget=16_000)
    assert study.treatment_disposition(_primary(strong8, strong16), _guards()) == "TREATMENT_WORKS"
    weak16 = _cell(2, p_treatment=0.0001, budget=16_000)
    assert study.treatment_disposition(_primary(strong8, weak16), _guards()) != "TREATMENT_WORKS"


def test_full_budget_guardrail_blocks_a_half_budget_winner() -> None:
    strong8 = _cell(10, p_treatment=0.0001, budget=8_000)
    strong16 = _cell(10, p_treatment=0.0001, budget=16_000)
    harmful = _cell(-10, p_dense=0.0001, budget=32_000)
    assert study.treatment_disposition(
        _primary(strong8, strong16), _guards(b=harmful)
    ) != "TREATMENT_WORKS"


def test_signal_is_registered_but_cannot_select() -> None:
    signal8 = _cell(3, p_treatment=0.01, budget=8_000)
    neutral16 = _cell(0, budget=16_000)
    disposition = study.treatment_disposition(_primary(signal8, neutral16), _guards())
    assert disposition == "TREATMENT_CARRIES_SIGNAL"
    contrasts = {
        "bm25": {"disposition": disposition, "primary": _primary(signal8, neutral16)},
        "hybrid": {"disposition": "MIXED_OR_NO_DIFFERENCE", "primary": _primary(neutral16, neutral16)},
    }
    assert study.select_for_tc007(contrasts)["selected_arm"] == "dense"


def test_dense_dispositions_are_symmetric() -> None:
    dense8 = _cell(-10, p_dense=0.0001, budget=8_000)
    dense16 = _cell(-10, p_dense=0.0001, budget=16_000)
    assert study.treatment_disposition(_primary(dense8, dense16), _guards()) == "DENSE_WORKS"


def test_two_working_treatments_use_registered_lexicographic_rule() -> None:
    bm25 = _primary(
        {**_cell(12, p_treatment=0.0001, budget=8_000), "losses": 4},
        {**_cell(8, p_treatment=0.0001, budget=16_000), "losses": 3},
    )
    hybrid = _primary(
        {**_cell(10, p_treatment=0.0001, budget=8_000), "losses": 1},
        {**_cell(10, p_treatment=0.0001, budget=16_000), "losses": 1},
    )
    contrasts = {
        "bm25": {"disposition": "TREATMENT_WORKS", "primary": bm25},
        "hybrid": {"disposition": "TREATMENT_WORKS", "primary": hybrid},
    }
    assert study.select_for_tc007(contrasts)["selected_arm"] == "hybrid"


def test_leakage_audit_rejects_a_planted_key(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('PATH = "q_facts_key.md"\n', encoding="utf-8")
    with pytest.raises(study.TC005Error):
        study.audit_mechanism_leakage(bad)
    assert study.planted_leakage_control()["status"] == "PASS"


def test_run_precondition_refuses_missing_g0(tmp_path: Path) -> None:
    with pytest.raises(study.TC005Error):
        study.run_precondition(tmp_path)
