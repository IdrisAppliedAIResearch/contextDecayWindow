from __future__ import annotations

from analysis.locomo_nf_development import sha256_file
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX
from analysis.lv007_prompts import ARMS
from analysis.lv008_live import (
    LV007_PROMPTS,
    LV007_PROMPTS_SHA256,
    REGISTRATION,
    REGISTRATION_SHA256,
    _prompt_rows,
    _poststop_generation_complete,
    _reachability,
    arm_order,
    blind_id,
    repaired_judge_prompt,
    validate_answer_schedule,
    validate_judgments,
)


def test_registered_anchors_and_prompt_population() -> None:
    assert sha256_file(REGISTRATION) == REGISTRATION_SHA256
    assert sha256_file(LV007_PROMPTS) == LV007_PROMPTS_SHA256
    rows = _prompt_rows()
    assert len(rows) == 17
    assert all(set(row["arms"]) == set(ARMS) for row in rows)
    assert sum(len(row["arms"]) for row in rows) == 51


def test_order_and_blind_keys_are_deterministic() -> None:
    key = "a" * 64
    assert arm_order(key, 0) == arm_order(key, 0)
    assert set(arm_order(key, 0)) == set(ARMS)
    assert len(blind_id(key, "PAIRWISE", 0)) == 64
    assert blind_id(key, "PAIRWISE", 0) != blind_id(key, "COMMUNITY", 0)


def test_answer_schedule_requires_all_naturally_stopped_cells() -> None:
    prompts = _prompt_rows()
    rows = [
        {
            "comparison_key": prompt["comparison_key"],
            "arm": arm,
            "replicate": replicate,
            "response": {"done_reason": "stop"},
        }
        for prompt in prompts
        for arm in ARMS
        for replicate in range(5)
    ]
    assert validate_answer_schedule(rows, prompts)["pass"]
    rows[0]["response"]["done_reason"] = "length"
    result = validate_answer_schedule(rows, prompts)
    assert not result["pass"]
    assert result["truncated"] == 1


def test_all_dispositions_are_reachable() -> None:
    assert all(_reachability().values())


def test_judge_prompt_uses_registered_parse_repair() -> None:
    prompt = repaired_judge_prompt({"question": "Q?", "gold": "A", "answer": "A"})
    assert prompt.endswith(CLOSED_THINK_SUFFIX + "VERDICT:")


def test_poststop_override_accepts_only_the_exact_sealed_shape() -> None:
    summary = {
        "validation": {
            "rows": 255,
            "expected": 255,
            "duplicates": 0,
            "missing": 0,
            "extra": 0,
            "truncated": 1,
            "gpu_only_after": True,
        }
    }
    assert _poststop_generation_complete(summary)
    summary["validation"]["truncated"] = 2
    assert not _poststop_generation_complete(summary)


def test_poststop_judge_validation_can_accept_a_parseable_capped_row() -> None:
    surface = [{"blind_id": "x"}]
    rows = [
        {"blind_id": "x", "judge_pass": index, "seed": seed, "done_reason": "length" if index == 0 else "stop"}
        for index, seed in enumerate((9005, 9006, 9007))
    ]
    assert not validate_judgments(rows, surface)["pass"]
    assert validate_judgments(rows, surface, allow_truncated=True)["pass"]
