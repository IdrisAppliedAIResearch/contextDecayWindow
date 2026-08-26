from __future__ import annotations

import gzip
import json

from analysis.lv007_live import (
    ARMS,
    _reachability,
    arm_order,
    expected_answer_keys,
    repaired_judge_prompt,
)
from analysis.lv007_prompts import CAP, PROMPTS


def _rows() -> list[dict]:
    with gzip.open(PROMPTS, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_frozen_prompt_population_and_content_identity() -> None:
    rows = _rows()
    assert len(rows) == 17
    assert len(expected_answer_keys(rows)) == 255
    for row in rows:
        selected = set(row["selected_ids"])
        baseline = row["arms"]["PAIRWISE"]
        for arm in ARMS:
            value = row["arms"][arm]
            assert len(value["emitted_ids"]) == len(selected)
            assert set(value["emitted_ids"]) == selected
            assert value["episode_element_sha256"] == baseline["episode_element_sha256"]


def test_compact_community_and_question_repeat_are_isolated() -> None:
    for row in _rows():
        pairwise = row["arms"]["PAIRWISE"]
        community = row["arms"]["COMMUNITY"]
        repeated = row["arms"]["COMMUNITY_QB"]
        assert community["block_chars"] < pairwise["block_chars"]
        assert community["block"] == repeated["block"]
        assert community["emitted_ids"] == repeated["emitted_ids"]
        assert community["prompt"].count("Question to answer:") == 0
        assert repeated["prompt"].count(f"Question to answer: {row['question']}") == 1
        assert repeated["prompt"].count(f"\nQuestion: {row['question']}") == 1


def test_communities_are_chronological_and_absorbing_controls_fire() -> None:
    cap_bound = mixed = joins = new = 0
    for row in _rows():
        community = row["arms"]["COMMUNITY"]
        for group in community["groups"]:
            turns = [item["turn"] for item in group["items"]]
            assert turns == sorted(turns)
            assert 1 <= len(turns) <= CAP
            cap_bound += len(turns) == CAP
            mixed += len({item["route"] for item in group["items"]}) == 2
        joins += sum(item["decision"] == "join" for item in community["assignment_trace"])
        new += sum(item["decision"] == "new" for item in community["assignment_trace"])
        controls = community["absorbing_controls"]
        assert all(size == 1 for size in controls["all_singleton_group_sizes"])
        sizes = controls["capacity_partition_group_sizes"]
        assert all(size == CAP for size in sizes[:-1])
        assert 1 <= sizes[-1] <= CAP
    assert cap_bound > 0
    assert mixed > 0
    assert joins > 0
    assert new > 0


def test_schedule_is_deterministic_and_balanced() -> None:
    rows = _rows()
    observed = [arm_order(row["comparison_key"], replicate) for row in rows for replicate in range(5)]
    assert all(set(order) == set(ARMS) and len(order) == len(ARMS) for order in observed)
    assert observed == [arm_order(row["comparison_key"], replicate) for row in rows for replicate in range(5)]


def test_dispositions_and_repaired_judge_suffix() -> None:
    assert all(_reachability().values())
    prompt = repaired_judge_prompt({"question": "Q", "gold": "G", "answer": "A"})
    assert prompt.endswith("\n<think>\n</think>\nVERDICT:")
