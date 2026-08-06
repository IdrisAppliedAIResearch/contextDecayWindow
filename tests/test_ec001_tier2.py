from __future__ import annotations

import inspect

import pytest

from src.analysis.ec001_tier2 import (
    EC001Tier2Error,
    aggregate_labels,
    build_label_prompt,
    calibration_cases,
    masked_id,
    parse_binary_label,
    prepare_reader_prompt,
    reduce_scoreable_response,
    select_h5,
    shuffled_ids,
)


def test_reader_prompt_cannot_accept_reference_material() -> None:
    assert tuple(inspect.signature(prepare_reader_prompt).parameters) == (
        "delivered_block",
        "question_date",
        "question",
    )
    prompt = prepare_reader_prompt(
        "<retrieved_stm><episode turn=\"1\"/></retrieved_stm>",
        "2023/05/02 (Tue) 12:00",
        "What did I choose?",
    )

    assert "History Chats:" in prompt
    assert "Current Date: 2023/05/02 (Tue) 12:00" in prompt
    assert prompt.endswith("Question: What did I choose?\nAnswer:")


def test_reasoning_only_response_is_no_answer() -> None:
    reduced = reduce_scoreable_response(
        "<think>The correct final fact is blue, with detailed reasoning.</think>"
    )

    assert reduced.reasoning_blocks_balanced is True
    assert reduced.scoreable_text == ""
    assert reduced.no_answer is True
    assert reduced.completeness_status == "COMPLETE"


def test_unbalanced_reasoning_is_a_completeness_failure() -> None:
    reduced = reduce_scoreable_response(
        "Visible lead.<think>unfinished reasoning"
    )

    assert reduced.scoreable_text == "Visible lead."
    assert reduced.reasoning_blocks_balanced is False
    assert reduced.completeness_status == "TRUNCATED_UNBALANCED_REASONING"


def test_reasoning_is_removed_without_changing_final_surface() -> None:
    reduced = reduce_scoreable_response(
        "<think>hidden</think>\nThe answer is blue."
    )

    assert reduced.scoreable_text == "The answer is blue."
    assert reduced.no_answer is False


@pytest.mark.parametrize(
    ("question_type", "needle"),
    [
        ("single-session-user", "Correct Answer: blue"),
        ("single-session-assistant", "Correct Answer: blue"),
        ("multi-session", "Correct Answer: blue"),
        ("temporal-reasoning", "do not penalize off-by-one errors"),
        ("knowledge-update", "some previous information"),
        ("single-session-preference", "Rubric: blue"),
    ],
)
def test_label_prompt_preserves_task_specific_protocol(
    question_type: str,
    needle: str,
) -> None:
    prompt = build_label_prompt(
        question_type,
        "What did I choose?",
        "blue",
        "I chose blue.",
        abstention=False,
    )

    assert needle in prompt
    assert prompt.endswith("Answer yes or no only.")


def test_abstention_prompt_uses_official_explanation_language() -> None:
    prompt = build_label_prompt(
        "single-session-user",
        "What is my passport number?",
        "It was not provided.",
        "I don't know.",
        abstention=True,
    )

    assert "unanswerable question, an explanation" in prompt
    assert "correctly identify the question as unanswerable" in prompt


@pytest.mark.parametrize(
    ("surface", "expected"),
    [("yes", True), ("YES.", True), (" no! ", False)],
)
def test_binary_label_parser_accepts_only_yes_no_surface(
    surface: str,
    expected: bool,
) -> None:
    assert parse_binary_label(surface) is expected


@pytest.mark.parametrize("surface", ["yes because", "yes or no", "", "maybe"])
def test_binary_label_parser_rejects_non_protocol_surface(
    surface: str,
) -> None:
    with pytest.raises(EC001Tier2Error, match="non-binary"):
        parse_binary_label(surface)


def test_masking_and_family_orders_are_stable_and_distinct() -> None:
    ids = ["q1", "q2", "q3", "q4", "q5", "q6"]

    assert masked_id("q1") == masked_id("q1")
    assert shuffled_ids(ids, "gemma") == shuffled_ids(ids, "gemma")
    assert shuffled_ids(ids, "gemma") != shuffled_ids(ids, "mistral")


def test_h5_sample_is_exact_ceiling_ten_percent() -> None:
    ids = [f"EC1-{index:03d}" for index in range(21)]

    first = select_h5(ids)
    second = select_h5(ids)

    assert first == second
    assert len(first) == 3
    assert set(first) <= set(ids)


def test_calibration_includes_reasoning_only_no_answer() -> None:
    cases = {case["calibration_id"]: case for case in calibration_cases()}

    no_answer = cases["reasoning-only-no-answer"]
    assert no_answer["response"] == "NO_ANSWER"
    assert no_answer["expected_label"] is False
    assert no_answer["mechanical_no_answer"] is True


def test_aggregation_reports_micro_and_population_weighted_scores() -> None:
    rows = [
        {"stratum": "large", "label": True},
        {"stratum": "small", "label": False},
    ]
    aggregate = aggregate_labels(rows, {"large": 9, "small": 1})

    assert aggregate["raw_subset_micro_average"]["accuracy"] == 0.5
    assert aggregate["benchmark_population_post_stratified_accuracy"] == 0.9
    assert aggregate["raw_subset_micro_average"]["comparability"] == (
        "NON_BENCHMARK_DISTRIBUTED_EQUAL_QUOTAS"
    )
