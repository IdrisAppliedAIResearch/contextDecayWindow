"""Tests for Study 011's three-pass score aggregation."""

from __future__ import annotations

import json

import pytest

from src.analysis import study_011_score_aggregation as agg

LABELS = ("arm_W", "arm_X", "arm_Y", "arm_Z")
QUESTIONS = agg.QUESTIONS


def _packets(no_answer: set[str] | None = None) -> dict:
    no_answer = no_answer or set()
    items = []
    for label in LABELS:
        for question in QUESTIONS:
            item_id = f"{label}_{question}"
            items.append(
                {
                    "item_id": item_id,
                    "blind_label": label,
                    "question": question,
                    "answer": "text",
                    "no_answer": item_id in no_answer,
                }
            )
    return {"items": items}


def _pass(packets: dict, value=1.0, *, rater="m", overrides=None) -> dict:
    overrides = overrides or {}
    return {
        "rater": rater,
        "calibration": {"passed": True, "disagreements": []},
        "scores": {
            row["item_id"]: {
                "primary": overrides.get(row["item_id"], value),
                "strict": overrides.get(row["item_id"], value),
                "rationale": "because",
            }
            for row in packets["items"]
        },
    }


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Calibration is a gate
# --------------------------------------------------------------------------


def test_a_failed_calibration_stops_aggregation(tmp_path) -> None:
    packets = _packets()
    bad = _pass(packets)
    bad["calibration"] = {"passed": False, "disagreements": ["cal_no_answer"]}
    paths = [
        _write(tmp_path, "p1.json", _pass(packets)),
        _write(tmp_path, "p2.json", _pass(packets)),
        _write(tmp_path, "p3.json", bad),
    ]
    with pytest.raises(agg.AggregationError, match="never waived"):
        agg.load_passes(paths)


def test_fewer_than_three_raters_stops_aggregation(tmp_path) -> None:
    packets = _packets()
    paths = [
        _write(tmp_path, "p1.json", _pass(packets)),
        _write(tmp_path, "p2.json", _pass(packets)),
    ]
    with pytest.raises(agg.AggregationError, match="requires three raters"):
        agg.load_passes(paths)


def test_a_missing_pass_file_stops_aggregation(tmp_path) -> None:
    with pytest.raises(agg.AggregationError, match="missing rater pass"):
        agg.load_passes([tmp_path / "absent.json"])


# --------------------------------------------------------------------------
# Combining
# --------------------------------------------------------------------------


def test_unanimity_is_recorded() -> None:
    assert agg.combine_item([1.0, 1.0, 1.0]) == {
        "value": 1.0,
        "agreement": "unanimous",
        "conflict": False,
    }


def test_two_of_three_carries_the_item() -> None:
    result = agg.combine_item([1.0, 1.0, 0.0])
    assert result["value"] == 1.0
    assert result["agreement"] == "majority"
    assert result["conflict"] is False


def test_three_different_values_is_a_surfaced_conflict() -> None:
    result = agg.combine_item([1.0, 0.5, 0.0])
    assert result["agreement"] == "split"
    assert result["conflict"] is True


def test_a_conflict_is_listed_not_silently_averaged() -> None:
    packets = _packets()
    item = packets["items"][0]["item_id"]
    passes = [
        _pass(packets, 1.0),
        _pass(packets, 0.5, overrides={item: 0.5}),
        _pass(packets, 0.0, overrides={item: 0.0}),
    ]
    passes[1]["scores"][item]["primary"] = 0.5
    passes[2]["scores"][item]["primary"] = 0.0
    result = agg.aggregate(passes, packets)
    assert item in result["conflicts"]


# --------------------------------------------------------------------------
# The rules that cannot be overridden by agreement
# --------------------------------------------------------------------------


def test_raters_cannot_score_an_answerless_item_above_zero() -> None:
    item = f"{LABELS[0]}_Q1"
    packets = _packets(no_answer={item})
    passes = [_pass(packets, 1.0) for _ in range(3)]
    with pytest.raises(agg.AggregationError, match="never scored above zero"):
        agg.aggregate(passes, packets)


def test_an_unscored_item_stops_aggregation() -> None:
    packets = _packets()
    passes = [_pass(packets) for _ in range(3)]
    del passes[2]["scores"][packets["items"][0]["item_id"]]
    with pytest.raises(agg.AggregationError, match="did not score item"):
        agg.aggregate(passes, packets)


# --------------------------------------------------------------------------
# Blinding and disclosure
# --------------------------------------------------------------------------


def test_aggregation_keeps_labels_blind() -> None:
    packets = _packets()
    result = agg.aggregate([_pass(packets) for _ in range(3)], packets)
    assert set(result["blind_scores"]) == set(LABELS)
    assert "mapping_not_opened" in result


def test_the_same_family_departure_is_disclosed() -> None:
    packets = _packets()
    result = agg.aggregate([_pass(packets) for _ in range(3)], packets)
    note = result["rater_family_note"]
    assert "single family" in note
    assert "departure from the registered design" in note


def test_agreement_is_labelled_as_evidence_about_raters() -> None:
    packets = _packets()
    result = agg.aggregate([_pass(packets) for _ in range(3)], packets)
    assert "not about the arms" in result["agreement"]["this_measures_the_raters"]


def test_unsealing_attaches_arm_identities() -> None:
    packets = _packets()
    aggregated = agg.aggregate([_pass(packets) for _ in range(3)], packets)
    mapping = {
        "mapping": {"arm_W": "A", "arm_X": "B", "arm_Y": "C", "arm_Z": "D"}
    }
    unsealed = agg.unseal(aggregated, mapping)
    assert set(unsealed["scores"]) == {"A", "B", "C", "D"}
    assert unsealed["totals_out_of_13"] == {arm: 13.0 for arm in "ABCD"}
