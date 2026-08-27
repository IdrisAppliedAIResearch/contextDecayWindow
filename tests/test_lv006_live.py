from __future__ import annotations

from copy import deepcopy

import pytest

import analysis.lv006_live as live
from analysis.lv006_live import (
    LV006LiveError,
    _load_mapping,
    _surface_rows,
    expected_keys,
    repaired_prompt,
    validate_judgments,
)


def test_repair_is_exact_suffix_only() -> None:
    item = _surface_rows()[0]
    prompt = repaired_prompt(item)
    assert prompt.endswith("<think>\n</think>\nVERDICT:")
    assert len(expected_keys(_surface_rows())) == 960


def test_complete_repaired_schedule_reachable() -> None:
    surface = _surface_rows()
    rows = []
    for blind_id, judge_pass, seed in expected_keys(surface):
        rows.append({"blind_id": blind_id, "judge_pass": judge_pass, "seed": seed, "done_reason": "stop"})
    assert validate_judgments(rows, surface)["pass"]
    broken = deepcopy(rows)
    broken[0]["done_reason"] = "length"
    assert not validate_judgments(broken, surface)["pass"]


def test_mapping_is_blocked_before_completion(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(live, "JUDGMENT_SUMMARY", tmp_path / "absent.json")
    with pytest.raises(LV006LiveError):
        _load_mapping()
