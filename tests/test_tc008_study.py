from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from analysis import tc008_study as study


def _complete(net: int, budget: int, population: str):
    band = study.BANDS[budget][f"{population}_complete"]
    return {
        "net": net,
        "gains": max(net, 0),
        "losses": max(-net, 0),
        "band": band,
    }


def _share(net: int):
    return {
        "question_net": net,
        "question_gains": max(net, 0),
        "question_losses": max(-net, 0),
        "identity_net": net,
        "question_band": 0,
        "identity_band": 0,
    }


def _cell(budget: int, breadth: int, breadth_complete: int = 0, combined: int = 0, targeted: int = 0):
    return {
        "breadth_share": _share(breadth),
        "breadth_complete": _complete(breadth_complete, budget, "breadth"),
        "combined_complete": _complete(combined, budget, "combined"),
        "targeted_complete": _complete(targeted, budget, "targeted"),
    }


def test_registration_and_constants_are_locked() -> None:
    assert study.assert_registration()["status"] == "PASS"
    assert study.TOTAL_BUDGETS == (16_000, 32_000)
    assert study.POPULATION_N == {"combined": 868, "targeted": 704, "breadth": 44}
    assert study.WORKS_ALPHA == pytest.approx(.01 / 6)
    assert study.SIGNAL_ALPHA == pytest.approx(.10 / 6)


def test_session_works_requires_both_budgets_and_guardrails() -> None:
    cells = {"16000": _cell(16_000, 12), "32000": _cell(32_000, 12)}
    assert study.study_disposition(cells) == "SESSION_SPREAD_WORKS"
    cells["32000"] = _cell(32_000, 0)
    assert study.study_disposition(cells) != "SESSION_SPREAD_WORKS"
    cells["32000"] = _cell(32_000, 12, targeted=-12)
    assert study.study_disposition(cells) != "SESSION_SPREAD_WORKS"


def test_breadth_complete_loss_blocks_session_works() -> None:
    cells = {"16000": _cell(16_000, 12), "32000": _cell(32_000, 12, breadth_complete=-1)}
    assert study.study_disposition(cells) != "SESSION_SPREAD_WORKS"


def test_dense_work_is_symmetric_and_requires_both_budgets() -> None:
    cells = {"16000": _cell(16_000, -12), "32000": _cell(32_000, -12)}
    assert study.study_disposition(cells) == "DENSE_WORKS"


def test_leakage_audit_rejects_planted_key(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('X = "q_facts_key.md"\n', encoding="utf-8")
    with pytest.raises(study.TC008Error):
        study.audit_mechanism_leakage(bad)
    assert study.planted_leakage_control()["status"] == "PASS"


def test_blind_manifest_audit_rejects_evidence_key(tmp_path: Path) -> None:
    path = tmp_path / "bad.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write('{"evidence": ["D1:1"]}')
    with pytest.raises(study.TC008Error):
        study.audit_blind_manifest(path)


def test_run_precondition_refuses_missing_g0(tmp_path: Path) -> None:
    with pytest.raises(study.TC008Error):
        study.run_precondition(tmp_path)


def test_gzip_is_byte_deterministic(tmp_path: Path) -> None:
    rows = [{"b": 2, "a": 1}, {"value": "same payload"}]
    first = tmp_path / "first.jsonl.gz"
    second = tmp_path / "second.jsonl.gz"
    study._write_gzip_jsonl(first, rows)
    study._write_gzip_jsonl(second, rows)
    assert first.read_bytes() == second.read_bytes()
