"""Tests for the DX-002 context growth diagnostic.

The statistical helpers carry the weight of the Branch A/B/C/D decision, so
they are tested against closed-form cases where the answer is known
independently of this implementation.
"""

from __future__ import annotations

import math
import random

import pytest

from src.analysis.dx002_context_growth import (
    ASSISTANT_CUE,
    MATERIALITY_FLOOR_CHARS,
    PART_ORDER,
    classify_series,
    decompose_prompt,
    decompose_prompt_ordered,
    durbin_watson,
    has_saturated,
    ols_slope,
    p95_growth,
    recompact_block,
    student_t_quantile,
    theil_sen_slope,
)

PROMPT = (
    "You are an assistant.\n\n"
    "<pinned_rules/>\n\n"
    "<recent_context>\n"
    '  <episode turn="2" topic="t1">\n'
    "    <user_message>hello</user_message>\n"
    "    <assistant_message>hi</assistant_message>\n"
    "  </episode>\n"
    "</recent_context>\n\n"
    "<retrieved_stm/>\n\n"
    "<retrieved_ltm>\n"
    '  <episode turn="1" topic="t1" similarity="0.5">\n'
    "    <user_message>first</user_message>\n"
    "    <assistant_message>reply</assistant_message>\n"
    "  </episode>\n"
    "</retrieved_ltm>\n\n"
    "<current_turn>\n"
    "  <user_message>now</user_message>\n"
    "</current_turn>"
    + ASSISTANT_CUE
)


class TestDecomposition:
    def test_pieces_cover_every_character(self):
        pieces = decompose_prompt_ordered(PROMPT)
        assert "".join(piece for _, piece in pieces) == PROMPT

    def test_every_piece_is_a_known_part(self):
        for name, _ in decompose_prompt_ordered(PROMPT):
            assert name in PART_ORDER

    def test_parts_sum_to_the_prompt_length(self):
        parts = decompose_prompt(PROMPT)
        assert sum(len(value) for value in parts.values()) == len(PROMPT)

    def test_blocks_are_captured_whole(self):
        parts = decompose_prompt(PROMPT)
        assert parts["pinned_rules"] == "<pinned_rules/>"
        assert parts["retrieved_stm"] == "<retrieved_stm/>"
        assert parts["recent_context"].startswith("<recent_context>")
        assert parts["recent_context"].endswith("</recent_context>")
        assert parts["assistant_cue"] == ASSISTANT_CUE

    def test_missing_block_is_zero_not_absent(self):
        """Arm S carries no LTM block; the series must be 0, not missing."""
        without_ltm = PROMPT.replace(
            PROMPT[
                PROMPT.index("<retrieved_ltm>") : PROMPT.index(
                    "</retrieved_ltm>"
                )
                + len("</retrieved_ltm>")
                + 2
            ],
            "",
        )
        parts = decompose_prompt(without_ltm)
        assert parts["retrieved_ltm"] == ""
        assert sum(len(value) for value in parts.values()) == len(without_ltm)

    def test_prompt_with_no_blocks_is_all_preamble(self):
        parts = decompose_prompt("just text")
        assert parts["preamble"] == "just text"
        assert sum(len(value) for value in parts.values()) == len("just text")


class TestCompactRerender:
    def test_content_survives_the_rerender(self):
        parts = decompose_prompt(PROMPT)
        compact, count = recompact_block("retrieved_ltm", parts["retrieved_ltm"])
        assert count == 1
        assert "first" in compact and "reply" in compact
        assert compact.startswith("<retrieved_ltm>")

    def test_rerender_is_smaller_than_the_historical_block(self):
        parts = decompose_prompt(PROMPT)
        compact, _ = recompact_block("retrieved_ltm", parts["retrieved_ltm"])
        assert len(compact) < len(parts["retrieved_ltm"])

    def test_empty_block_renders_as_the_self_closing_tag(self):
        compact, count = recompact_block("retrieved_ltm", "")
        assert (compact, count) == ("<retrieved_ltm/>", 0)


class TestOlsSlope:
    def test_recovers_an_exact_line(self):
        xs = [float(i) for i in range(50)]
        ys = [3.0 * x + 7.0 for x in xs]
        fit = ols_slope(xs, ys)
        assert fit["slope_chars_per_turn"] == pytest.approx(3.0)
        assert fit["intercept_chars"] == pytest.approx(7.0)
        assert fit["r_squared"] == pytest.approx(1.0)

    def test_flat_series_interval_contains_zero(self):
        xs = [float(i) for i in range(100)]
        ys = [100.0 + (1.0 if i % 2 else -1.0) for i in range(100)]
        fit = ols_slope(xs, ys)
        assert fit["includes_zero"]

    def test_steep_series_interval_excludes_zero(self):
        xs = [float(i) for i in range(100)]
        ys = [50.0 * x + (1.0 if i % 2 else -1.0) for i, x in enumerate(xs)]
        fit = ols_slope(xs, ys)
        assert not fit["includes_zero"]
        assert fit["slope_chars_per_turn"] > 0

    def test_too_few_points_raises(self):
        with pytest.raises(ValueError):
            ols_slope([1.0, 2.0], [1.0, 2.0])


class TestStudentT:
    @pytest.mark.parametrize(
        "df,expected",
        [(1, 12.7062), (10, 2.2281), (30, 2.0423), (298, 1.9679)],
    )
    def test_matches_published_quantiles(self, df, expected):
        assert student_t_quantile(0.975, df) == pytest.approx(expected, abs=1e-3)

    def test_approaches_the_normal_quantile(self):
        assert student_t_quantile(0.975, 100000) == pytest.approx(1.96, abs=1e-3)


class TestTheilSen:
    def test_recovers_an_exact_line(self):
        xs = [float(i) for i in range(20)]
        ys = [2.0 * x - 5.0 for x in xs]
        assert theil_sen_slope(xs, ys) == pytest.approx(2.0)

    def test_resists_a_single_extreme_point(self):
        """The reason Theil-Sen is reported next to OLS."""
        xs = [float(i) for i in range(40)]
        ys = [10.0 for _ in xs]
        ys[-1] = 100_000.0
        assert theil_sen_slope(xs, ys) == pytest.approx(0.0)
        assert ols_slope(xs, ys)["slope_chars_per_turn"] > 10.0


def _series(p95_values: list[float], delta_pct: float = 0.0) -> dict:
    """A minimal series shaped like `_summarise_series` output."""
    return {
        "constant": False,
        "blocks": [
            {"first_turn": i * 100 + 1, "last_turn": (i + 1) * 100,
             "mean": value, "max": value, "p95": value}
            for i, value in enumerate(p95_values)
        ],
        "terminal_window": {
            "includes_zero": True,
            "slope_chars_per_turn": 0.0,
            "degenerate_constant_series": False,
        },
        "window_over_window": {"comparable": True, "delta_pct": delta_pct},
    }


class TestSaturation:
    def test_final_record_means_not_saturated(self):
        assert not has_saturated(_series([10, 20, 30, 40, 50]))

    def test_plateau_is_saturated(self):
        assert has_saturated(_series([100, 99, 98, 98, 97]))

    def test_peak_in_the_middle_is_saturated(self):
        assert has_saturated(_series([10, 60, 30, 40, 50]))

    def test_flat_series_is_saturated(self):
        assert has_saturated(_series([50, 50, 50, 50, 50]))

    def test_too_few_buckets_defaults_to_saturated(self):
        assert has_saturated(_series([10, 20]))

    def test_growth_is_measured_across_the_lookback(self):
        assert p95_growth(_series([10, 20, 30, 40, 50])) == 40.0


class TestClassifySeries:
    def test_large_rise_is_climbing(self):
        """The measured retrieved_stm shape."""
        verdict = classify_series(
            _series([25_253, 33_312, 41_556, 35_110, 48_491], delta_pct=33.0)
        )
        assert verdict["climbing"]
        assert verdict["material"]
        assert not verdict["saturated"]

    def test_trivial_rise_is_not_climbing(self):
        """The measured current_turn shape: a record, but five characters."""
        verdict = classify_series(
            _series([226, 228, 228, 228, 231], delta_pct=0.5)
        )
        assert not verdict["climbing"]
        assert not verdict["material"]
        assert verdict["rising"]

    def test_materiality_floor_is_one_percent_of_the_budget(self):
        assert MATERIALITY_FLOOR_CHARS == 320

    def test_rise_just_over_the_floor_is_climbing(self):
        verdict = classify_series(_series([0, 0, 0, 0, 320], delta_pct=1.0))
        assert verdict["climbing"]

    def test_rise_just_under_the_floor_is_not(self):
        verdict = classify_series(_series([0, 0, 0, 0, 319], delta_pct=1.0))
        assert not verdict["climbing"]

    def test_saturated_series_is_not_climbing_however_large(self):
        verdict = classify_series(
            _series([90_000, 80_000, 70_000, 60_000, 50_000], delta_pct=-5.0)
        )
        assert not verdict["climbing"]


class TestDurbinWatson:
    def test_independent_residuals_sit_near_two(self):
        rng = random.Random(5005)
        xs = [float(i) for i in range(400)]
        ys = [100.0 + rng.gauss(0.0, 1.0) for _ in xs]
        assert 1.5 < durbin_watson(xs, ys) < 2.5

    def test_strong_positive_autocorrelation_sits_low(self):
        xs = [float(i) for i in range(400)]
        ys, value = [], 0.0
        for _ in xs:
            value += 1.0
            ys.append(value)
            if value > 20:
                value = 0.0
        assert durbin_watson(xs, ys) < 1.0


class TestCommittedRun:
    """The diagnostic against the real committed artifacts."""

    @pytest.fixture(scope="class")
    def result(self):
        from src.analysis.dx002_context_growth import RUN_ROOT, analyse

        if not RUN_ROOT.exists():
            pytest.skip("Study 010 run artifacts are not present")
        return analyse()

    def test_all_gates_pass(self, result):
        assert result["gates"]["G1_byte_exact_reconstruction"]
        assert result["gates"]["G2_telemetry_matches_committed"]
        assert result["gates"]["G3_dr001_compact_replay"]
        assert result["gates"]["G4_inputs_unchanged"]
        assert result["status"] == "PASS"

    def test_g3_replays_dr001_committed_figures(self, result):
        checks = {
            check["turn"]: check
            for arm in result["arms"]
            for check in arm["gates"]["compact_replay_checks"]
        }
        assert checks[999]["observed_chars"] == 37_619
        assert checks[1000]["observed_chars"] == 37_545

    def test_both_arms_cover_one_thousand_turns(self, result):
        assert [arm["turns"] for arm in result["arms"]] == [1000, 1000]

    def test_peak_matches_the_committed_context_audit(self, result):
        """27,154 and 17,541 are on the record; the decomposition must agree."""
        peaks = {
            arm["arm"]: (arm["series"]["total"]["max"] - len(ASSISTANT_CUE))
            // 4
            for arm in result["arms"]
        }
        assert peaks["arm_l"] == 27_154
        assert peaks["arm_s"] == 17_541

    def test_decision_branch_is_one_of_the_registered_four(self, result):
        assert result["decision"]["branch"] in {"A", "B", "C", "D"}

    def test_ltm_saturates_and_stm_does_not(self, result):
        """The finding, pinned: H-A for the budgeted block, H-B beside it."""
        verdicts = result["decision"]["series_verdicts"]
        assert verdicts["arm_l.retrieved_ltm"]["saturated"]
        assert not verdicts["arm_l.retrieved_ltm"]["climbing"]
        assert verdicts["arm_l.retrieved_stm"]["climbing"]
        assert verdicts["arm_s.retrieved_stm"]["climbing"]

    def test_branch_b_names_the_unbudgeted_component(self, result):
        assert result["decision"]["branch"] == "B"
        assert result["decision"]["climbing_parts"] == [
            "arm_l.retrieved_stm",
            "arm_s.retrieved_stm",
        ]

    def test_recency_window_is_not_the_leak(self, result):
        """The other named H-B candidate, ruled out."""
        verdicts = result["decision"]["series_verdicts"]
        assert not verdicts["arm_l.recent_context"]["climbing"]
        assert not verdicts["arm_s.recent_context"]["climbing"]

    def test_rule_pinning_contributed_nothing_and_says_so(self, result):
        for arm in result["arms"]:
            pinning = arm["rule_pinning"]
            assert pinning["rule_detections"] == 0
            assert pinning["pinned_rules_constant"]
            assert not pinning["contributes_growth"]
            assert not pinning["measurable"]

    def test_compact_render_still_exceeds_budget(self, result):
        """The measured case for CC-003: cheaper tags do not fix selection."""
        arm_l = next(a for a in result["arms"] if a["arm"] == "arm_l")
        budget = arm_l["ltm_vs_budget"]
        assert budget["compact_turns_over_budget"] > 500
        assert budget["compact_max_chars"] > budget["budget_chars"]

    def test_slopes_are_finite(self, result):
        for arm in result["arms"]:
            for name in (*PART_ORDER, "total"):
                window = arm["series"][name]["terminal_window"]
                assert math.isfinite(window["slope_chars_per_turn"])
