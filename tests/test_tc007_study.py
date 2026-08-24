from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from analysis import tc007_study as study


def _cell(net: int, *, population="combined", budget=16_000, p_t=1.0, p_c=1.0):
    return {
        "net": net,
        "gains": max(net, 0),
        "losses": max(-net, 0),
        "band": study.BANDS[budget][population],
        "treatment_one_sided_p": p_t,
        "control_one_sided_p": p_c,
    }


def _budget(budget, combined, breadth, targeted):
    return {
        "combined": _cell(combined, budget=budget, p_t=.0001 if combined > 0 else 1, p_c=.0001 if combined < 0 else 1),
        "breadth": _cell(breadth, population="breadth", budget=budget, p_t=.0001 if breadth > 0 else 1, p_c=.0001 if breadth < 0 else 1),
        "targeted": _cell(targeted, population="targeted", budget=budget, p_t=.0001 if targeted > 0 else 1, p_c=.0001 if targeted < 0 else 1),
    }


def test_registration_and_constants_are_locked() -> None:
    assert study.assert_registration()["status"] == "PASS"
    assert study.TOTAL_BUDGETS == (16_000, 32_000)
    assert study.POPULATION_N == {"combined": 868, "targeted": 704, "breadth": 44}
    assert study.WORKS_ALPHA == pytest.approx(.01 / 12)
    assert study.SIGNAL_ALPHA == pytest.approx(.10 / 12)


def test_joint_work_requires_combined_breadth_and_targeted_guardrail() -> None:
    cells = {"16000": _budget(16_000, 20, 15, 0), "32000": _budget(32_000, 20, 15, 0)}
    assert study.treatment_disposition(cells) == "TREATMENT_WORKS"
    cells["32000"] = _budget(32_000, 20, 0, 0)
    assert study.treatment_disposition(cells) != "TREATMENT_WORKS"
    cells["32000"] = _budget(32_000, 20, 15, -20)
    assert study.treatment_disposition(cells) != "TREATMENT_WORKS"


def test_no_carries_signal_arm_can_select() -> None:
    contrasts = {
        "a3": {"disposition": "TREATMENT_CARRIES_SIGNAL", "cells": {}},
        "facility": {"disposition": "MIXED_OR_NO_DIFFERENCE", "cells": {}},
    }
    assert study.select_architecture(contrasts)["selected_arm"] == "control"


def test_lexicographic_selection_prefers_combined_then_breadth() -> None:
    def contrast(combined, breadth):
        cells = {
            "16000": _budget(16_000, combined, breadth, 0),
            "32000": _budget(32_000, combined, breadth, 0),
        }
        return {"disposition": "TREATMENT_WORKS", "cells": cells}
    result = study.select_architecture({"a3": contrast(20, 20), "facility": contrast(21, 15)})
    assert result["selected_arm"] == "facility"


def test_leakage_audit_rejects_planted_key(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('X = "q_facts_key.md"\n', encoding="utf-8")
    with pytest.raises(study.TC007Error):
        study.audit_mechanism_leakage(bad)
    assert study.planted_leakage_control()["status"] == "PASS"


def test_run_precondition_refuses_missing_g0(tmp_path: Path) -> None:
    with pytest.raises(study.TC007Error):
        study.run_precondition(tmp_path)


def test_diagnostic_gzip_is_byte_deterministic(tmp_path: Path) -> None:
    rows = [{"b": 2, "a": 1}, {"value": "same payload"}]
    first = tmp_path / "first.jsonl.gz"
    second = tmp_path / "second.jsonl.gz"
    study._write_gzip_jsonl(first, rows)
    study._write_gzip_jsonl(second, rows)
    assert first.read_bytes() == second.read_bytes()
    with gzip.open(first, "rt", encoding="utf-8") as handle:
        assert handle.read() == '{"a":1,"b":2}\n{"value":"same payload"}\n'
