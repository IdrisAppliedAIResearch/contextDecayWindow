from __future__ import annotations

import pytest

from analysis.lv009_exploration import (
    ARMS,
    LV009ExplorationError,
    assert_no_label_fields,
    load_blind_population,
    load_blind_cases,
    ordered_schedule,
    population_inventory,
    reader_seed,
    render_question_each,
)


def test_full_population_matches_draft_counts() -> None:
    rows = load_blind_population()
    inventory = population_inventory(rows)
    assert inventory["rows"] == 1_986
    assert inventory["primary"] == 1_540
    assert inventory["category5"] == 446
    assert inventory["development_primary"] == 692
    assert inventory["transfer_primary"] == 848
    assert inventory["categories"] == {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}
    assert len(inventory["conversations"]) == 10
    cases = load_blind_cases()
    assert len(cases) == 10
    assert all(case.pairs for case in cases)
    assert all("date_time" not in pair.session_id for case in cases for pair in case.pairs)


def test_seed_and_schedule_are_deterministic_and_arm_paired() -> None:
    rows = load_blind_population()
    schedule_a = ordered_schedule(rows)
    schedule_b = ordered_schedule(rows)
    assert schedule_a == schedule_b
    assert len(schedule_a) == 7_944
    assert len(set(schedule_a)) == 7_944
    for row in rows:
        seeds = {seed for key, arm, seed in schedule_a if key == row.comparison_key and arm in ARMS}
        assert seeds == {reader_seed(row.comparison_key)}


def test_question_each_inserts_only_between_groups() -> None:
    question = "Where was it?"
    block = '<retrieved_stm>\n<g rank="1">a</g>\n<g rank="2">b</g>\n<g rank="3">c</g>\n</retrieved_stm>'
    prompt = (
        "You are answering a question about a conversation between two people.\n\n"
        f"Question to answer: {question}\n\n{block}\n\nQuestion: {question}"
    )
    result = render_question_each(prompt, block, question, ({}, {}, {}))
    reminder = f"<question_reminder>Question to answer: {question}</question_reminder>"
    assert result.count(reminder) == 2
    assert f'</g>\n{reminder}\n<g rank="2">' in result
    assert f'</g>\n{reminder}\n<g rank="3">' in result
    assert result.endswith(f"Question: {question}")


def test_one_group_question_each_is_identical() -> None:
    question = "What happened?"
    block = '<retrieved_stm>\n<g rank="1">a</g>\n</retrieved_stm>'
    prompt = (
        "You are answering a question about a conversation between two people.\n\n"
        f"Question to answer: {question}\n\n{block}\n\nQuestion: {question}"
    )
    assert render_question_each(prompt, block, question, ({},)) == prompt


def test_label_fields_are_rejected() -> None:
    assert_no_label_fields({"question": "q", "category": 1})
    with pytest.raises(LV009ExplorationError):
        assert_no_label_fields({"question": "q", "answer": "a"})
