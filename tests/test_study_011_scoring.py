"""Tests for Study 011's blind scoring preparation."""

from __future__ import annotations

import json

import pytest

from src.analysis import study_011_scoring as scoring


def _make_arm(root, arm: str, *, answer: str = "a distinct answer") -> None:
    directory = root / arm
    (directory / "logs").mkdir(parents=True, exist_ok=True)
    rows = [
        {"turn_number": turn, "assistant_message": f"{answer} for {arm} at {turn}"}
        for turn in range(112, 121)
    ]
    (directory / "logs" / "turns.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (directory / "responses.md").write_text(
        f"# {arm}\n{answer}\n", encoding="utf-8", newline="\n"
    )


@pytest.fixture()
def run_dirs(tmp_path):
    for arm in scoring.ARMS:
        _make_arm(tmp_path, arm, answer=f"answer text {arm}")
    return {arm: tmp_path / arm for arm in scoring.ARMS}


# --------------------------------------------------------------------------
# Only content outside reasoning blocks is scoreable
# --------------------------------------------------------------------------


def test_closed_reasoning_is_stripped() -> None:
    assert scoring.scoreable_answer(
        "<think>working it out</think>The answer is 847."
    ) == "The answer is 847."


def test_an_unclosed_reasoning_block_leaves_no_answer() -> None:
    """The calibration set's own NO_ANSWER case."""

    assert scoring.scoreable_answer("<think>the first fact is Alpha") == ""


def test_a_stripped_item_is_flagged_no_answer(tmp_path) -> None:
    for arm in scoring.ARMS:
        _make_arm(tmp_path, arm, answer=f"x {arm}")
    directory = tmp_path / "A"
    rows = [
        {"turn_number": turn, "assistant_message": "<think>never closed"}
        for turn in range(112, 121)
    ]
    (directory / "logs" / "turns.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    run_dirs = {arm: tmp_path / arm for arm in scoring.ARMS}
    packets = scoring.build_packets(run_dirs, scoring.seal_mapping(run_dirs))
    flagged = [row for row in packets["items"] if row["no_answer"]]
    assert flagged
    assert all(row["answer"] == "" for row in flagged if row["question"] != "Q13")


# --------------------------------------------------------------------------
# Blinding
# --------------------------------------------------------------------------


def test_packets_carry_no_arm_identity(run_dirs) -> None:
    packets = scoring.build_packets(run_dirs, scoring.seal_mapping(run_dirs))
    serialized = json.dumps(packets["items"])
    for arm in scoring.ARMS:
        assert f'"arm": "{arm}"' not in serialized
    assert {row["blind_label"] for row in packets["items"]} == {
        "arm_W",
        "arm_X",
        "arm_Y",
        "arm_Z",
    }


def test_mechanism_facts_are_named_as_withheld(run_dirs) -> None:
    packets = scoring.build_packets(run_dirs, scoring.seal_mapping(run_dirs))
    assert "arm identity" in packets["withheld_from_raters"]
    assert "packing order" in packets["withheld_from_raters"]
    assert "the plant key" in packets["withheld_from_raters"]


def test_the_mapping_is_derived_from_digests_not_chosen(run_dirs) -> None:
    first = scoring.seal_mapping(run_dirs)
    second = scoring.seal_mapping(run_dirs)
    assert first["mapping"] == second["mapping"]
    assert "not selected by the rater" in first["assignment_source"]


def test_changing_a_response_changes_the_blind_label(tmp_path) -> None:
    for arm in scoring.ARMS:
        _make_arm(tmp_path, arm, answer=f"answer {arm}")
    run_dirs = {arm: tmp_path / arm for arm in scoring.ARMS}
    before = scoring.seal_mapping(run_dirs)["response_sha256"]["A"]
    _make_arm(tmp_path, "A", answer="a different answer entirely")
    after = scoring.seal_mapping(run_dirs)["response_sha256"]["A"]
    assert before != after


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------


def test_every_arm_gets_all_thirteen_questions(run_dirs) -> None:
    packets = scoring.build_packets(run_dirs, scoring.seal_mapping(run_dirs))
    assert packets["item_count"] == 13 * len(scoring.ARMS)
    for label in ("arm_W", "arm_X", "arm_Y", "arm_Z"):
        questions = {
            row["question"] for row in packets["items"] if row["blind_label"] == label
        }
        assert len(questions) == 13
        assert "Q13" in questions


def test_q13_carries_the_late_turns_rather_than_one_answer(run_dirs) -> None:
    packets = scoring.build_packets(run_dirs, scoring.seal_mapping(run_dirs))
    q13 = next(row for row in packets["items"] if row["question"] == "Q13")
    assert q13["turn"] is None
    assert "[turn 112]" in q13["answer"]
    assert "[turn 120]" in q13["answer"]


def test_a_missing_answer_stops_the_build(tmp_path) -> None:
    for arm in scoring.ARMS:
        _make_arm(tmp_path, arm)
    directory = tmp_path / "B"
    (directory / "logs" / "turns.jsonl").write_text(
        json.dumps({"turn_number": 112, "assistant_message": "only one"}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    run_dirs = {arm: tmp_path / arm for arm in scoring.ARMS}
    with pytest.raises(scoring.ScoringError, match="no answer at turn"):
        scoring.build_packets(run_dirs, scoring.seal_mapping(run_dirs))


def test_the_three_rater_requirement_is_stated_in_the_packet(run_dirs) -> None:
    packets = scoring.build_packets(run_dirs, scoring.seal_mapping(run_dirs))
    assert packets["passes_required"] == 3
    assert "distinct model families" in packets["rater_requirement"]
    assert "disclosed in the report" in packets["rater_requirement"]
