"""Tests for Amendment 001 Phase 2.

A noise-band measurement is unusually easy to make say what you want:
loosen a boundary, drop an outlier, pool rater spread into run spread, or
apply the band to the results you want dissolved and not the ones you
want kept. Every one of those has a test here that fails if it happens.
"""

from __future__ import annotations

import json

import pytest

from src.analysis.amendment_001_noise_band import (
    DECISION_RULE,
    DECISION_RULE_SHA256,
    NoiseBandError,
    QUESTIONS,
    RECORDED_GAPS,
    REPLICATES,
    apply_uniformly,
    assert_decision_rule,
    build_report,
    measure_band,
    per_question_variability,
    rater_disagreement,
    read_band,
    seal_replicates,
    write_report,
)

LABELS = ("run_alpha", "run_beta", "run_gamma", "run_delta", "run_epsilon")


def flat_scores(totals):
    """Five replicates whose totals are `totals`, spread over Q1..Q13."""

    scores = {}
    for label, total in zip(LABELS, totals):
        per_question = {question: 0.0 for question in QUESTIONS}
        remaining = total
        for question in QUESTIONS:
            take = min(1.0, remaining)
            per_question[question] = take
            remaining = round(remaining - take, 4)
        scores[label] = per_question
    return scores


def aggregated_for(scores, agreement="unanimous"):
    per_item = {}
    for label, per_question in scores.items():
        for question, value in per_question.items():
            per_item[f"{label}:{question}"] = {
                "blind_label": label,
                "question": question,
                "rater_values": [value, value, value],
                "value": value,
                "agreement": agreement,
                "conflict": agreement == "split",
            }
    return {"per_item": per_item}


class TestDecisionRule:
    def test_the_committed_rule_matches_the_pinned_digest(self):
        assert assert_decision_rule() == DECISION_RULE_SHA256

    def test_an_edited_rule_raises_rather_than_reporting(self, tmp_path):
        # The whole point of committing §4.3 before scoring. A rule that
        # can be edited after the number is known is not a rule.
        forged = tmp_path / "DECISION_RULE.md"
        forged.write_text("band < 99: everything stands\n", encoding="utf-8")
        with pytest.raises(NoiseBandError, match="changed after it was committed"):
            assert_decision_rule(forged)

    def test_a_missing_rule_is_an_error_not_a_default(self, tmp_path):
        with pytest.raises(NoiseBandError):
            assert_decision_rule(tmp_path / "absent.md")

    def test_the_rule_file_is_the_one_the_module_points_at(self):
        assert DECISION_RULE.is_file()


class TestMeasureBand:
    def test_the_band_is_the_full_range(self):
        band = measure_band({"a": 8.0, "b": 7.0, "c": 9.0, "d": 8.5, "e": 8.0})
        assert band.width == 2.0
        assert band.minimum == 7.0
        assert band.maximum == 9.0

    def test_no_run_is_trimmed(self):
        # An outlier is the measurement, not noise in it.
        band = measure_band({"a": 8.0, "b": 8.0, "c": 8.0, "d": 8.0, "e": 2.0})
        assert band.width == 6.0
        assert list(band.totals) == [2.0, 8.0, 8.0, 8.0, 8.0]

    def test_every_individual_total_survives_into_the_record(self):
        record = measure_band({"a": 8.0, "b": 7.5, "c": 8.0}).as_record()
        assert record["individual_totals"] == [7.5, 8.0, 8.0]
        assert "n = 5 estimates a standard deviation poorly" in (
            record["standard_deviation_caveat"]
        )

    def test_one_run_cannot_produce_a_band(self):
        with pytest.raises(NoiseBandError):
            measure_band({"a": 8.0})


class TestReadBand:
    @pytest.mark.parametrize("width", [0.0, 0.25, 0.49])
    def test_below_half_a_point_the_verdicts_stand(self, width):
        assert read_band(width)["row"] == "< 0.5"

    @pytest.mark.parametrize("width", [0.5, 1.0, 1.5])
    def test_the_middle_row_is_inclusive_at_both_edges(self, width):
        # Pinned in DECISION_RULE.md before the number was known. A band
        # landing on exactly 1.5 must not be read the convenient way.
        assert read_band(width)["row"] == "0.5 - 1.5"

    @pytest.mark.parametrize("width", [1.51, 2.0, 6.0])
    def test_above_one_and_a_half_the_paper_needs_structural_revision(self, width):
        row = read_band(width)
        assert row["row"] == "> 1.5"
        assert "structural revision" in row["paper_action"]

    def test_the_middle_row_does_not_dissolve_the_three_point_results(self):
        assert "Study 009's 3.0 and the 3.5 series improvement" in (
            read_band(1.0)["consequence"]
        )


class TestApplyUniformly:
    def test_all_four_recorded_gaps_are_applied(self):
        applied = apply_uniformly(1.0)
        assert len(applied) == len(RECORDED_GAPS) == 4

    def test_the_program_s_own_kills_are_dissolved_by_a_one_point_band(self):
        applied = {row["result"]: row for row in apply_uniformly(1.0)}
        assert not applied["Study 011 B1, C vs D"]["exceeds_band"]
        assert applied["LV-001 targeted regression"]["exceeds_band"]

    def test_the_headline_improvement_gets_the_same_expression(self):
        # The direction that would be tempting to exempt.
        applied = {row["result"]: row for row in apply_uniformly(4.0)}
        assert not applied[
            "The corrected treatment series, 8.5 to 12.0"
        ]["exceeds_band"]
        assert not applied["Study 009 same-seed contrast, S vs L"]["exceeds_band"]

    def test_sign_does_not_change_the_comparison(self):
        # -2.0 and +2.0 are the same distance from zero. A comparison that
        # used the signed value would exempt every regression.
        applied = {row["result"]: row for row in apply_uniformly(2.5)}
        assert not applied["LV-001 targeted regression"]["exceeds_band"]

    def test_exceeding_the_band_is_not_reported_as_demonstrated(self):
        applied = apply_uniformly(0.0)
        for row in applied:
            assert row["re_read_as"].startswith("not excluded by the band")


class TestPerQuestionVariability:
    def test_stable_questions_are_counted_apart_from_moving_ones(self):
        scores = {
            label: {question: 1.0 for question in QUESTIONS} for label in LABELS
        }
        scores["run_alpha"]["Q7"] = 0.0
        scores["run_beta"]["Q11"] = 0.0
        result = per_question_variability(scores)
        assert result["questions_that_moved"] == ["Q7", "Q11"]
        assert result["questions_stable_count"] == 11
        assert result["concentration"] == "concentrated"

    def test_a_band_spread_across_the_rubric_is_labelled_differently(self):
        scores = {
            label: {question: 1.0 for question in QUESTIONS} for label in LABELS
        }
        for question in QUESTIONS[:6]:
            scores["run_alpha"][question] = 0.0
        result = per_question_variability(scores)
        assert result["concentration"] == "spread across the rubric"

    def test_a_missing_question_is_an_error_not_a_zero(self):
        scores = {
            label: {question: 1.0 for question in QUESTIONS} for label in LABELS
        }
        del scores["run_alpha"]["Q5"]
        with pytest.raises(NoiseBandError, match="Q5"):
            per_question_variability(scores)


class TestRaterDisagreement:
    def test_rater_spread_is_reported_per_replicate(self):
        scores = flat_scores([8.0] * 5)
        result = rater_disagreement(aggregated_for(scores))
        assert set(result["per_replicate"]) == set(LABELS)
        assert result["per_replicate"]["run_alpha"]["unanimous_rate"] == 1.0

    def test_rater_spread_is_not_pooled_into_the_band(self):
        # The band is computed from totals only; nothing in the band
        # record can be reached from rater disagreement.
        scores = flat_scores([8.0, 8.0, 8.0, 8.0, 8.0])
        report = build_report(
            scores,
            aggregated_for(scores, agreement="split"),
            runs=[],
            decision_rule_sha256=DECISION_RULE_SHA256,
        )
        assert report["band"]["band"] == 0.0
        assert report["rater_disagreement"]["per_replicate"]["run_alpha"]["split"] == 13

    def test_the_family_departure_travels_with_the_number(self):
        scores = flat_scores([8.0] * 5)
        result = rater_disagreement(aggregated_for(scores))
        assert "understates the band" in result["family_departure"]

    def test_aggregated_scores_without_item_detail_are_refused(self):
        with pytest.raises(NoiseBandError):
            rater_disagreement({"blind_scores": {}})


class TestSealReplicates:
    def _run(self, tmp_path, name, body):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "responses.md").write_text(body, encoding="utf-8")
        return directory

    def test_labels_follow_the_digest_order_not_the_run_order(self, tmp_path):
        runs = {
            f"r{index}": self._run(tmp_path, f"r{index}", f"body {index}")
            for index in range(5)
        }
        mapping = seal_replicates(runs)["mapping"]
        assert set(mapping.values()) == set(runs)
        assert len(set(mapping)) == 5

    def test_sealing_is_deterministic(self, tmp_path):
        runs = {
            f"r{index}": self._run(tmp_path, f"r{index}", f"body {index}")
            for index in range(5)
        }
        assert seal_replicates(runs) == seal_replicates(runs)

    def test_two_identical_replicates_are_a_harness_fault(self, tmp_path):
        # On a runtime that cannot reproduce a run, two byte-identical
        # responses mean the second run did not happen.
        runs = {
            "r1": self._run(tmp_path, "r1", "same"),
            "r2": self._run(tmp_path, "r2", "same"),
        }
        with pytest.raises(NoiseBandError, match="harness fault"):
            seal_replicates(runs)

    def test_a_missing_responses_file_is_refused(self, tmp_path):
        (tmp_path / "r1").mkdir()
        with pytest.raises(NoiseBandError):
            seal_replicates({"r1": tmp_path / "r1"})


class TestBuildReport:
    def test_fewer_than_n_replicates_stops_rather_than_estimating(self):
        # §4.3's last row: report and stop. Do not estimate from fewer.
        scores = flat_scores([8.0] * 5)
        del scores["run_epsilon"]
        with pytest.raises(NoiseBandError, match="report and stop"):
            build_report(
                scores,
                aggregated_for(scores),
                runs=[],
                decision_rule_sha256=DECISION_RULE_SHA256,
            )

    def test_the_non_rescue_clause_is_in_the_artifact(self):
        scores = flat_scores([8.0, 7.0, 8.0, 9.0, 8.0])
        report = build_report(
            scores,
            aggregated_for(scores),
            runs=[],
            decision_rule_sha256=DECISION_RULE_SHA256,
        )
        assert "may not be cited in support" in report["non_rescue_clause"]
        assert "K-first" in report["non_rescue_clause"]

    def test_the_offline_results_are_listed_as_unaffected(self):
        scores = flat_scores([8.0] * 5)
        report = build_report(
            scores,
            aggregated_for(scores),
            runs=[],
            decision_rule_sha256=DECISION_RULE_SHA256,
        )
        assert any("IC-001" in row for row in report["unaffected_by_the_band"])

    def test_totals_are_computed_from_the_per_question_scores(self):
        scores = flat_scores([8.0, 7.0, 9.0, 8.5, 8.0])
        report = build_report(
            scores,
            aggregated_for(scores),
            runs=[],
            decision_rule_sha256=DECISION_RULE_SHA256,
        )
        assert report["individual_totals_by_replicate"]["run_beta"] == 7.0
        assert report["band"]["band"] == 2.0

    def test_the_report_round_trips_as_json(self, tmp_path):
        scores = flat_scores([8.0] * 5)
        report = build_report(
            scores,
            aggregated_for(scores),
            runs=[],
            decision_rule_sha256=DECISION_RULE_SHA256,
        )
        path = write_report(report, tmp_path / "band_verdict.json")
        assert json.loads(path.read_text(encoding="utf-8")) == report

    def test_the_registered_replicate_count_is_five(self):
        assert REPLICATES == 5
