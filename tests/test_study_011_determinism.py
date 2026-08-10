"""Tests for Study 011's determinism spot-check."""

from __future__ import annotations

import json

import pytest

from src.analysis import study_011_determinism as det


def _make_run(root, *, prompts, payloads, responses):
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "constructed_prompts").mkdir(parents=True, exist_ok=True)
    turns, ctx = [], []
    for index, turn in enumerate(sorted(prompts)):
        (root / "constructed_prompts" / f"turn_{turn:03d}.txt").write_text(
            prompts[turn], encoding="utf-8", newline="\n"
        )
        turns.append(
            {"turn_number": turn, "assistant_message": responses[turn]}
        )
        ctx.append(
            {"turn_number": turn, "retrieval_payload_sha256": payloads[turn]}
        )
    (root / "logs" / "turns.jsonl").write_text(
        "\n".join(json.dumps(row) for row in turns) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / "logs" / "context_match.jsonl").write_text(
        "\n".join(json.dumps(row) for row in ctx) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return root


def _identical(root, turns=(1, 2, 3)):
    return _make_run(
        root,
        prompts={t: f"prompt {t}" for t in turns},
        payloads={t: f"digest{t}" for t in turns},
        responses={t: f"answer {t}" for t in turns},
    )


def test_an_identical_rerun_passes(tmp_path) -> None:
    left = _identical(tmp_path / "a")
    right = _identical(tmp_path / "b")
    result = det.compare(left, right)
    assert result["status"] == "PASS"
    assert result["mechanism_deterministic"] is True
    assert result["response_deterministic"] is True
    assert result["first_divergence_turn"] == {
        "prompt": None,
        "payload": None,
        "response": None,
    }


def test_a_drifting_prompt_fails_the_mechanism_check(tmp_path) -> None:
    left = _identical(tmp_path / "a")
    right = _make_run(
        tmp_path / "b",
        prompts={1: "prompt 1", 2: "DIFFERENT", 3: "prompt 3"},
        payloads={t: f"digest{t}" for t in (1, 2, 3)},
        responses={t: f"answer {t}" for t in (1, 2, 3)},
    )
    result = det.compare(left, right)
    assert result["status"] == "FAIL"
    assert result["first_divergence_turn"]["prompt"] == 2


def test_a_drifting_payload_digest_fails(tmp_path) -> None:
    left = _identical(tmp_path / "a")
    right = _make_run(
        tmp_path / "b",
        prompts={t: f"prompt {t}" for t in (1, 2, 3)},
        payloads={1: "digest1", 2: "MOVED", 3: "digest3"},
        responses={t: f"answer {t}" for t in (1, 2, 3)},
    )
    result = det.compare(left, right)
    assert result["status"] == "FAIL"
    assert result["first_divergence_turn"]["payload"] == 2


def test_a_nondeterministic_model_does_not_fail_the_mechanism(tmp_path) -> None:
    """The distinction the gate exists to preserve.

    Identical prompts with different answers means the model is not
    bit-reproducible. That is reported, and it is not a mechanism defect.
    """

    left = _identical(tmp_path / "a")
    right = _make_run(
        tmp_path / "b",
        prompts={t: f"prompt {t}" for t in (1, 2, 3)},
        payloads={t: f"digest{t}" for t in (1, 2, 3)},
        responses={1: "answer 1", 2: "a different answer", 3: "answer 3"},
    )
    result = det.compare(left, right)
    assert result["status"] == "PASS"
    assert result["mechanism_deterministic"] is True
    assert result["response_deterministic"] is False
    assert result["first_divergence_turn"]["response"] == 2


def test_prompts_diverging_after_a_response_diverges_is_not_mechanism_drift(
    tmp_path,
) -> None:
    """Once a response differs the store differs, so later prompts must.

    Judging the mechanism on those turns would fail every live rerun on a
    runtime that is not bit-reproducible, and would say nothing about the
    mechanism.
    """

    left = _identical(tmp_path / "a")
    right = _make_run(
        tmp_path / "b",
        prompts={1: "prompt 1", 2: "downstream", 3: "downstream"},
        payloads={1: "digest1", 2: "downstream", 3: "downstream"},
        responses={1: "diverged here", 2: "answer 2", 3: "answer 3"},
    )
    result = det.compare(left, right)
    assert result["first_divergence_turn"]["response"] == 1
    assert result["testable_prefix_turns"] == 1
    assert result["mechanism_deterministic"] is True
    assert result["status"] == "PASS"


def test_a_short_testable_prefix_is_reported_as_a_limitation(tmp_path) -> None:
    left = _identical(tmp_path / "a")
    right = _make_run(
        tmp_path / "b",
        prompts={1: "prompt 1", 2: "x", 3: "y"},
        payloads={1: "digest1", 2: "x", 3: "y"},
        responses={1: "diverged", 2: "x", 3: "y"},
    )
    result = det.compare(left, right)
    assert result["testable_prefix_turns"] == 1
    assert "weak evidence" in result["limitation"]


def test_mechanism_drift_inside_the_prefix_still_fails(tmp_path) -> None:
    left = _identical(tmp_path / "a")
    right = _make_run(
        tmp_path / "b",
        prompts={1: "DIFFERENT", 2: "prompt 2", 3: "prompt 3"},
        payloads={t: f"digest{t}" for t in (1, 2, 3)},
        responses={1: "diverged", 2: "answer 2", 3: "answer 3"},
    )
    result = det.compare(left, right)
    assert result["status"] == "FAIL"


def test_runs_sharing_no_turns_stop_the_check(tmp_path) -> None:
    left = _identical(tmp_path / "a", turns=(1, 2))
    right = _identical(tmp_path / "b", turns=(8, 9))
    with pytest.raises(det.DeterminismError, match="share no turns"):
        det.compare(left, right)


def test_a_missing_log_stops_the_check(tmp_path) -> None:
    left = _identical(tmp_path / "a")
    with pytest.raises(det.DeterminismError, match="missing log"):
        det.compare(left, tmp_path / "absent")


def test_only_shared_turns_are_compared(tmp_path) -> None:
    left = _identical(tmp_path / "a", turns=(1, 2, 3))
    right = _identical(tmp_path / "b", turns=(1, 2))
    result = det.compare(left, right)
    assert result["turns_compared"] == 2
    assert result["status"] == "PASS"
