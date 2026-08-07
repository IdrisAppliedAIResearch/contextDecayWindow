"""Tests for Study 011 section 4.1's achievability derivation."""

from __future__ import annotations

import json

import pytest

from src.analysis import study_011_achievability as ach


# --------------------------------------------------------------------------
# The probe map is the part most likely to be wrong and least likely to fail
# loudly, so it is asserted against the committed script rather than trusted.
# --------------------------------------------------------------------------


def test_thirteen_questions_occupy_nine_windows() -> None:
    probe_map = ach.assert_probe_map()
    assert probe_map["probe_window_count"] == 9
    assert probe_map["rubric_question_count"] == 13
    assert probe_map["probe_windows"] == [112, 113, 114, 115, 116, 117, 118, 119, 120]


def test_questions_sharing_a_turn_are_named() -> None:
    shared = ach.assert_probe_map()["questions_sharing_a_window"]
    assert shared == {
        "114": ["Q12", "Q3"],
        "117": ["Q6", "Q9"],
        "118": ["Q10", "Q7"],
    }


def test_q13_spans_turns_and_owns_no_window() -> None:
    probe_map = ach.assert_probe_map()
    assert "Q13" not in ach.QUESTION_TURNS
    assert probe_map["spanning_questions"]["Q13"]["turns"] == list(range(112, 121))


def test_probe_map_rejects_a_turn_outside_the_script(monkeypatch) -> None:
    monkeypatch.setitem(ach.QUESTION_TURNS, "Q1", 42)
    with pytest.raises(ach.AchievabilityError, match="not among the script"):
        ach.assert_probe_map()


# --------------------------------------------------------------------------
# Source configuration
# --------------------------------------------------------------------------


def test_source_configuration_records_the_budget_difference() -> None:
    records = ach.load_context_records()
    configuration = ach.assert_source_configuration(records)
    assert configuration["k_threshold"] == 0.48
    assert configuration["n_cap"] == 32
    assert configuration["source_payload_budget"] == 60_595
    assert configuration["study_011_budget_chars"] == 32_000
    assert configuration["budget_differs_from_source"] is True


def test_a_wrong_threshold_stops_the_derivation(monkeypatch) -> None:
    monkeypatch.setattr(ach, "EXPECTED_K_THRESHOLD", 0.70)
    with pytest.raises(ach.AchievabilityError, match="K threshold"):
        ach.assert_source_configuration(ach.load_context_records())


def test_a_missing_probe_turn_stops_the_derivation() -> None:
    records = ach.load_context_records()
    del records[117]
    with pytest.raises(ach.AchievabilityError, match="absent from the context log"):
        ach.assert_source_configuration(records)


# --------------------------------------------------------------------------
# The K-only distinction. An episode that is also a recency candidate
# renders in recent_context, so counting it as a K delivery credits the
# similarity tier with material recency would have carried anyway.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def derivation() -> dict:
    return ach.derive(ach.load_context_records(), ach.load_episodes())


def test_two_windows_have_no_k_candidate_at_all(derivation: dict) -> None:
    assert derivation["windows_without_any_k_candidate"] == [118, 119]


def test_no_arm_can_deliver_k_where_no_candidate_exists(derivation: dict) -> None:
    for row in derivation["rows"]:
        if row["probe_turn"] in (118, 119):
            for arm in ach.ARMS:
                assert row["arms"][arm]["k_only_delivered_count"] == 0


def test_arm_a_delivers_no_k_only_episode_anywhere(derivation: dict) -> None:
    assert derivation["ceilings"]["A"]["ceiling_k_only"] == 0


def test_arm_a_still_delivers_episodes_that_are_k_candidates(
    derivation: dict,
) -> None:
    """G1's "0 K episodes" is false under any-K semantics.

    With K disabled the recency window still carries episodes that would
    have cleared the threshold. A gate reading "0 K episodes" against the
    candidate list fails by construction; it must read the K path.
    """

    assert derivation["ceilings"]["A"]["ceiling_any_k"] > 0


def test_k_first_ceiling_exceeds_the_deployed_order(derivation: dict) -> None:
    assert (
        derivation["ceilings"]["C"]["ceiling_k_only"]
        > derivation["ceilings"]["D"]["ceiling_k_only"]
    )


def test_the_deployed_order_reaches_only_turn_114(derivation: dict) -> None:
    """IC-001 measured 0 at its eight probes; 114 was not one of them."""

    assert derivation["ceilings"]["D"]["windows_with_k_only_delivery"] == [114]


def test_isolated_ltm_matches_joint_k_first_on_this_store(derivation: dict) -> None:
    assert (
        derivation["ceilings"]["B"]["ceiling_k_only"]
        == derivation["ceilings"]["C"]["ceiling_k_only"]
    )


def test_a_window_whose_only_k_candidate_duplicates_recency_adds_nothing(
    derivation: dict,
) -> None:
    row = next(row for row in derivation["rows"] if row["probe_turn"] == 115)
    assert row["k_candidate_count"] == 1
    assert row["k_only_candidate_count"] == 0
    assert row["arms"]["C"]["k_only_delivered_count"] == 0


def test_every_arm_stays_inside_the_registered_budget(derivation: dict) -> None:
    for row in derivation["rows"]:
        for arm in ach.ARMS:
            assert row["arms"][arm]["serialized_chars"] <= ach.BUDGET_CHARS


def test_the_module_sets_no_threshold(derivation: dict) -> None:
    assert "T" not in derivation
    assert "t_is_not_set_here" in derivation


# --------------------------------------------------------------------------
# Whole run
# --------------------------------------------------------------------------


def test_run_writes_artifacts_and_makes_no_model_call(tmp_path) -> None:
    result = ach.run(tmp_path)
    output = tmp_path / "achievability"
    assert result["status"] == "COMPLETE"

    audit = json.loads((output / "no_model_call_audit.json").read_text())
    assert audit["status"] == "PASS"
    assert audit["attempted_calls"] == []
    assert audit["guarded_entry_points"]
    assert audit["this_run_loaded_a_model"] is False

    manifest = json.loads((output / "artifact_manifest.json").read_text())
    assert set(manifest["artifacts"]) == {
        "achievability.json",
        "k_availability.csv",
        "no_model_call_audit.json",
        "run_header.json",
    }


def test_a_run_that_loads_a_model_fails(monkeypatch, tmp_path) -> None:
    """The audit must catch a load, not merely a resident model.

    Another test in the session can leave a model in the provider module,
    so "a model is loaded" is not by itself a defect. "This run loaded
    one" is.
    """

    states = iter([False, True])
    monkeypatch.setattr(
        ach, "_provider_model_loaded", lambda: next(states, True)
    )
    with pytest.raises(ach.AchievabilityError, match="model or embedding call"):
        ach.run(tmp_path)


def test_run_is_deterministic(tmp_path) -> None:
    first = ach.run(tmp_path / "one")
    second = ach.run(tmp_path / "two")
    assert first["rows"] == second["rows"]
    assert first["ceilings"] == second["ceilings"]
