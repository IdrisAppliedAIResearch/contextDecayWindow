"""Tests for Amendment 001 Phase 1.

The probe's job is to distinguish four states that a careless
implementation collapses into one: reproduces everywhere, diverges only
inside a process, diverges only across processes, diverges in both. Most
of what follows is negative controls against that collapse, because a
probe that reports "temp 0 reproduces" without being able to report the
other three certifies nothing — which is the row Amendment 001 §5 already
flagged in its own surrogate audit.
"""

from __future__ import annotations

import json

import pytest

from src.analysis.study_011_sampling_determinism import (
    CONDITIONS,
    PROMPT_COUNT,
    PROMPT_SOURCE,
    REPEATS,
    Prompt,
    PromptOutcome,
    ProbeError,
    build_report,
    first_divergence,
    locate_divergence,
    run_condition,
    select_prompts,
    summarize_condition,
    write_report,
)


def outcome(turn: int, *outputs: str) -> PromptOutcome:
    return PromptOutcome(turn=turn, outputs=list(outputs))


def summary(condition: str, *outcomes: PromptOutcome) -> dict:
    return summarize_condition(condition, list(outcomes))


class TestFirstDivergence:
    def test_identical_strings_do_not_diverge(self):
        assert first_divergence("abcdef", "abcdef") is None

    def test_divergence_is_the_first_differing_character(self):
        assert first_divergence("abcdef", "abcXef") == 3

    def test_a_prefix_diverges_at_the_length_of_the_shorter(self):
        # A response that stops early is a different response. Returning
        # None here would report a truncated generation as reproducing.
        assert first_divergence("abcdef", "abc") == 3
        assert first_divergence("abc", "abcdef") == 3

    def test_divergence_at_the_first_character_is_zero_not_falsy(self):
        # 0 is a real position. Any caller writing `if position:` would
        # silently drop the most severe case there is.
        assert first_divergence("Xbc", "abc") == 0


class TestPromptOutcome:
    def test_a_reproducing_prompt_reports_no_divergence(self):
        row = outcome(7, "same", "same", "same")
        assert row.identical
        assert row.distinct_outputs == 1
        assert row.first_divergence() is None

    def test_divergence_is_measured_against_the_first_generation(self):
        row = outcome(7, "abcdef", "abcdef", "abXdef")
        assert not row.identical
        assert row.first_divergence() == 2

    def test_the_earliest_divergence_across_repeats_is_reported(self):
        row = outcome(7, "abcdef", "aXcdef", "abcdeZ")
        assert row.first_divergence() == 1

    def test_an_outcome_with_no_outputs_is_an_error_not_a_pass(self):
        with pytest.raises(ProbeError):
            outcome(7).first_divergence()


class TestSummarize:
    def test_identity_rate_counts_prompts_not_generations(self):
        result = summary(
            "greedy_temp0_same_process",
            outcome(1, "a", "a"),
            outcome(2, "a", "b"),
            outcome(3, "a", "a"),
            outcome(4, "a", "a"),
        )
        assert result["prompts_reproducing"] == 3
        assert result["identity_rate"] == 0.75

    def test_divergence_positions_are_bucketed_by_order_of_magnitude(self):
        result = summary(
            "standing_temp1_same_process",
            outcome(1, "X" + "y" * 50, "Z" + "y" * 50),
            outcome(2, "y" * 50 + "X", "y" * 50 + "Z"),
            outcome(3, "y" * 500 + "X", "y" * 500 + "Z"),
        )
        histogram = result["first_divergence_char"]["histogram_by_decade"]
        assert histogram == {"0-9": 1, "10-99": 1, "100-999": 1}
        assert result["first_divergence_char"]["at_or_before_char_100"] == 2

    def test_an_unregistered_condition_is_refused(self):
        with pytest.raises(ProbeError):
            summary("temp_0_but_nicer", outcome(1, "a", "a"))

    def test_an_empty_condition_is_an_error(self):
        with pytest.raises(ProbeError):
            summarize_condition("standing_temp1_same_process", [])


class TestLocateDivergence:
    """The four states, each asserted separately."""

    def test_reproducing_in_both_conditions_is_reported_as_neither(self):
        clean = {"identity_rate": 1.0}
        assert locate_divergence(clean, clean).startswith("neither")

    def test_within_process_only(self):
        assert (
            locate_divergence({"identity_rate": 0.5}, {"identity_rate": 1.0})
            == "within-process only"
        )

    def test_across_process_only(self):
        # The state a single same-process condition cannot see. If the
        # probe reported only §3.2.3, this run would read as clean.
        assert (
            locate_divergence({"identity_rate": 1.0}, {"identity_rate": 0.5})
            == "across-process only"
        )

    def test_both(self):
        assert (
            locate_divergence({"identity_rate": 0.9}, {"identity_rate": 0.5})
            == "both"
        )

    def test_a_missing_condition_is_not_reported_as_a_clean_result(self):
        assert locate_divergence({"identity_rate": 1.0}, None).startswith(
            "not determined"
        )


class TestRunCondition:
    def test_generation_order_is_round_major_not_prompt_major(self):
        # One round is one server process in the fresh-process condition.
        # Prompt-major ordering would put a prompt's ten repeats inside one
        # process and make the condition measure nothing it claims to.
        seen: list[int] = []
        prompts = [
            Prompt(turn=turn, text=f"p{turn}", sha256="x", characters=2)
            for turn in (1, 2, 3)
        ]

        def complete(text: str) -> str:
            seen.append(int(text[1:]))
            return text

        run_condition(prompts, complete, repeats=2)
        assert seen == [1, 2, 3, 1, 2, 3]

    def test_every_prompt_gets_every_repeat(self):
        prompts = [
            Prompt(turn=turn, text=f"p{turn}", sha256="x", characters=2)
            for turn in (1, 2)
        ]
        outcomes = run_condition(prompts, lambda text: text, repeats=4)
        assert [len(row.outputs) for row in outcomes] == [4, 4]


class TestBuildReport:
    def _conditions(self, standing: float, within: float, across: float) -> dict:
        return {
            "standing_temp1_same_process": {"identity_rate": standing},
            "greedy_temp0_same_process": {"identity_rate": within},
            "greedy_temp0_fresh_process": {"identity_rate": across},
        }

    def test_the_hypothesis_is_supported_only_when_greedy_reproduces_in_both(self):
        report = build_report([], self._conditions(0.0, 1.0, 1.0), runtime={})
        assert report["sampling_amplifier_hypothesis"] == "SUPPORTED"

    def test_greedy_reproducing_in_one_condition_does_not_support_it(self):
        # The §5 surrogate row: "temp 0 reproduces" can pass for a reason
        # unrelated to the argmax. Within-process alone must not carry it.
        report = build_report([], self._conditions(0.0, 1.0, 0.4), runtime={})
        assert report["sampling_amplifier_hypothesis"].startswith("NOT SUPPORTED")

    def test_a_reproducing_standing_runtime_leaves_the_hypothesis_untested(self):
        # If temp 1 reproduced on this prompt set there is no divergence
        # for greedy to remove, and claiming support would be claiming a
        # cure for a symptom that never appeared.
        report = build_report([], self._conditions(1.0, 1.0, 1.0), runtime={})
        assert report["sampling_amplifier_hypothesis"].startswith("NOT TESTED")

    def test_a_missing_condition_marks_the_report_incomplete(self):
        conditions = self._conditions(0.0, 1.0, 1.0)
        del conditions["greedy_temp0_fresh_process"]
        report = build_report([], conditions, runtime={})
        assert report["status"] == "INCOMPLETE"
        assert report["missing_conditions"] == ["greedy_temp0_fresh_process"]
        assert report["sampling_amplifier_hypothesis"] is None

    def test_the_report_restates_what_phase_1_does_not_authorize(self):
        report = build_report([], self._conditions(0.0, 1.0, 1.0), runtime={})
        assert "does not change the standing runtime" in (
            report["what_this_does_not_authorize"]
        )
        assert "Phase 2 runs at temp 1" in report["what_this_does_not_authorize"]

    def test_the_report_round_trips_as_json(self, tmp_path):
        report = build_report([], self._conditions(0.2, 1.0, 1.0), runtime={})
        path = write_report(report, tmp_path / "phase_1.json")
        assert json.loads(path.read_text(encoding="utf-8")) == report


class TestPromptSelection:
    def test_the_committed_prompt_set_is_drawn_from_arm_d_windows(self):
        prompts = select_prompts()
        assert len(prompts) == PROMPT_COUNT
        assert PROMPT_SOURCE.is_dir()

    def test_the_selection_spans_the_run_rather_than_its_tail(self):
        # Window length runs from 757 characters to about 32,000. A probe
        # drawn from late turns alone would measure one prompt length and
        # report it as a property of the runtime.
        prompts = select_prompts()
        assert prompts[0].turn == 1
        assert prompts[-1].turn == 121
        assert min(p.characters for p in prompts) < 2_000
        assert max(p.characters for p in prompts) > 30_000

    def test_the_selection_is_stable_across_invocations(self):
        assert [p.turn for p in select_prompts()] == [
            p.turn for p in select_prompts()
        ]

    def test_each_prompt_carries_the_digest_of_its_committed_text(self):
        import hashlib

        for prompt in select_prompts():
            path = PROMPT_SOURCE / f"turn_{prompt.turn:03d}.txt"
            expected = hashlib.sha256(
                path.read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest()
            assert prompt.sha256 == expected

    def test_fewer_than_two_prompts_is_refused(self):
        with pytest.raises(ProbeError):
            select_prompts(count=1)

    def test_a_missing_source_is_an_error_not_an_empty_set(self, tmp_path):
        with pytest.raises(ProbeError):
            select_prompts(source=tmp_path)


class TestRegisteredParameters:
    def test_the_registered_minimums_are_what_the_module_defaults_to(self):
        assert PROMPT_COUNT >= 20
        assert REPEATS == 10

    def test_all_three_registered_conditions_are_declared(self):
        assert CONDITIONS == (
            "standing_temp1_same_process",
            "greedy_temp0_same_process",
            "greedy_temp0_fresh_process",
        )
