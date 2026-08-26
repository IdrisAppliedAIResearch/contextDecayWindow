from __future__ import annotations

from copy import deepcopy

from analysis.lv005_live import (
    ARMS,
    _content_checks,
    _prompt_rows,
    _reachability,
    arm_order,
    disposition,
    validate_answer_schedule,
)
from analysis.lv005_prompts import build_prompt_rows


def test_prompts_rebuild_and_preserve_frozen_content() -> None:
    frozen = _prompt_rows()
    rebuilt, manifest = build_prompt_rows()
    assert rebuilt == frozen
    assert len(frozen) == 17
    assert manifest["control_reproductions"] == 17
    checks = _content_checks(frozen)
    assert checks["set_exact"] == checks["expected_set_exact"] == 68
    assert checks["episode_elements_exact"] == checks["expected_element_exact"] == 68
    assert checks["treatment_order_changes"] == checks["expected_treatment_rows"] == 51
    assert checks["child_earlier_pairs"] > 0
    assert checks["child_later_pairs"] > 0


def test_group_and_temporal_roles_are_exact() -> None:
    for row in _prompt_rows():
        for group in row["arms"]["GROUPED"]["groups"]:
            assert group["items"][0]["role"] == "query_anchor"
            if len(group["items"]) == 2:
                assert group["items"][1]["role"] == "related_spread"
        for group in row["arms"]["GROUPED_CHRONO"]["groups"]:
            assert [item["turn"] for item in group["items"]] == sorted(
                item["turn"] for item in group["items"]
            )
        chrono = row["arms"]["GROUPED_CHRONO"]["emitted_ids"]
        guided = row["arms"]["TEMPORAL_GUIDANCE"]["emitted_ids"]
        assert chrono == guided
        for group in row["arms"]["TEMPORAL_GUIDANCE"]["groups"]:
            roles = [item["temporal_role"] for item in group["items"]]
            assert roles == (["only_retrieved_item"] if len(roles) == 1 else ["earlier_in_conversation", "later_in_conversation"])


def test_schedule_and_arm_order_are_reachable() -> None:
    prompts = _prompt_rows()
    rows = []
    for prompt in prompts:
        for replicate in range(5):
            order = arm_order(prompt["comparison_key"], replicate)
            assert set(order) == set(ARMS)
            assert order == arm_order(prompt["comparison_key"], replicate)
            for arm in order:
                rows.append({
                    "comparison_key": prompt["comparison_key"],
                    "arm": arm,
                    "replicate": replicate,
                    "response": {"done_reason": "stop"},
                })
    assert validate_answer_schedule(rows, prompts)["pass"]
    truncated = deepcopy(rows)
    truncated[0]["response"]["done_reason"] = "length"
    assert not validate_answer_schedule(truncated, prompts)["pass"]


def test_registered_dispositions_reachable() -> None:
    assert all(_reachability().values())
    assert disposition(3, 1, 1, 3, 1, valid=True) == "PROMISING"
    assert disposition(1, 0, 0, 1, 0, valid=True) == "WEAK_SIGNAL"
    assert disposition(0, 0, 0, 0, 0, valid=True) == "NO_SIGNAL"
    assert disposition(3, 1, -1, 3, 1, valid=True) == "REGRESSES"
    assert disposition(3, 1, 1, 3, -1, valid=True) == "NOT_INTERPRETABLE"
