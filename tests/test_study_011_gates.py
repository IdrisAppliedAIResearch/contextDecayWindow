"""Tests for Study 011 section 4's binding offline pre-test."""

from __future__ import annotations

import json

import pytest

from src.analysis import study_011_gates as gates
from src.analysis import study_011_achievability as ach


@pytest.fixture(scope="module")
def replay() -> dict:
    return gates.replay_arms(ach.load_context_records(), ach.load_episodes())


# --------------------------------------------------------------------------
# T and its units
# --------------------------------------------------------------------------


def test_t_is_the_locked_value() -> None:
    assert gates.T == 6


def test_t_does_not_exceed_the_measured_ceiling() -> None:
    derivation = ach.derive(ach.load_context_records(), ach.load_episodes())
    assert gates.T <= derivation["ceilings"]["C"]["ceiling_k_only_questions"]


def test_gates_report_both_units(replay: dict) -> None:
    result = gates.g3_joint_delivery(replay)
    assert result["delivery"]["window_count"] == 6
    assert result["delivery"]["question_count"] == 8


# --------------------------------------------------------------------------
# G1
# --------------------------------------------------------------------------


def test_g1_passes_on_the_stm_only_arm(replay: dict) -> None:
    result = gates.g1_stm_isolation(replay)
    assert result["status"] == "PASS"
    assert result["windows_without_a_recency_episode"] == []
    assert result["windows_with_a_k_path_episode"] == []


def test_g1_fails_if_a_k_path_episode_reaches_the_stm_arm(replay: dict) -> None:
    tampered = {arm: dict(windows) for arm, windows in replay.items()}
    turn = ach.PROBE_TURNS[0]
    tampered["A"] = dict(tampered["A"])
    tampered["A"][turn] = {**tampered["A"][turn], "k_only_delivered": ["x"]}
    assert gates.g1_stm_isolation(tampered)["status"] == "FAIL"


def test_g1_fails_if_the_recency_window_is_empty(replay: dict) -> None:
    tampered = {arm: dict(windows) for arm, windows in replay.items()}
    turn = ach.PROBE_TURNS[0]
    tampered["A"] = dict(tampered["A"])
    tampered["A"][turn] = {**tampered["A"][turn], "recency_delivered": 0}
    assert gates.g1_stm_isolation(tampered)["status"] == "FAIL"


# --------------------------------------------------------------------------
# G2 and G3
# --------------------------------------------------------------------------


def test_g2_passes_and_delivers_no_recency_episode(replay: dict) -> None:
    result = gates.g2_ltm_isolation(replay)
    assert result["status"] == "PASS"
    assert result["windows_with_a_recency_episode"] == []
    assert result["delivery"]["question_count"] >= gates.T


def test_g2_fails_when_a_recency_episode_leaks_in(replay: dict) -> None:
    tampered = {arm: dict(windows) for arm, windows in replay.items()}
    turn = ach.PROBE_TURNS[0]
    tampered["B"] = dict(tampered["B"])
    tampered["B"][turn] = {**tampered["B"][turn], "recency_delivered": 1}
    assert gates.g2_ltm_isolation(tampered)["status"] == "FAIL"


def test_g3_passes_on_the_joint_arm(replay: dict) -> None:
    assert gates.g3_joint_delivery(replay)["status"] == "PASS"


def test_g3_records_what_the_deployed_order_would_have_given(
    replay: dict,
) -> None:
    """The gate eleven studies did not run, against the order they ran."""

    result = gates.g3_joint_delivery(replay)
    deployed = result["deployed_order_for_comparison"]
    assert deployed["question_count"] < gates.T
    assert deployed["windows"] == [114]


def test_g3_fails_one_question_below_t(replay: dict) -> None:
    tampered = {arm: dict(windows) for arm, windows in replay.items()}
    tampered["C"] = dict(tampered["C"])
    # 114 and 117 carry two questions each; dropping both leaves four.
    for turn in (114, 117):
        tampered["C"][turn] = {**tampered["C"][turn], "k_only_delivered": []}
    result = gates.g3_joint_delivery(tampered)
    assert result["delivery"]["question_count"] == 4
    assert result["status"] == "FAIL"


# --------------------------------------------------------------------------
# G4. A non-subset that differs by one trivial episode would pass, so the
# overlap fraction is reported beside the verdict (section 7).
# --------------------------------------------------------------------------


def test_g4_passes_and_reports_overlap(replay: dict) -> None:
    result = gates.g4_path_non_identity(replay)
    assert result["status"] == "PASS"
    assert all("overlap_fraction" in row for row in result["per_window"])


def test_g4_fails_when_the_ltm_arm_is_a_subset_of_the_stm_arm(
    replay: dict,
) -> None:
    tampered = {arm: dict(windows) for arm, windows in replay.items()}
    tampered["B"] = dict(tampered["B"])
    for turn in ach.PROBE_TURNS:
        tampered["B"][turn] = {
            **tampered["B"][turn],
            "delivered_ids": list(tampered["A"][turn]["delivered_ids"][:1]),
        }
    assert gates.g4_path_non_identity(tampered)["status"] == "FAIL"


# --------------------------------------------------------------------------
# G5. Counts can match on different episodes, so identity and the payload
# digest are what the gate asserts.
# --------------------------------------------------------------------------


def test_g5_reproduces_the_committed_deployed_result(replay: dict) -> None:
    result = gates.g5_deployed_reproduction(replay)
    assert result["status"] == "PASS"
    assert all(result["checks"].values())
    assert result["replay"]["serialized_chars"] == 31_946
    assert result["replay"]["selected_episode_count"] == 8
    assert result["item_mismatches"] == []


def test_g5_fails_on_matching_counts_with_different_episodes(
    replay: dict,
) -> None:
    """The surrogate this gate exists to defeat."""

    tampered = {arm: dict(windows) for arm, windows in replay.items()}
    tampered["D"] = dict(tampered["D"])
    swapped = list(tampered["D"][gates.Q11_TURN]["selected_ids"])
    swapped[0], swapped[-1] = swapped[-1], swapped[0]
    tampered["D"][gates.Q11_TURN] = {
        **tampered["D"][gates.Q11_TURN],
        "selected_ids": swapped,
    }
    result = gates.g5_deployed_reproduction(tampered)
    assert result["status"] == "FAIL"
    assert result["checks"]["episode_identities"] is False
    # The count checks still pass, which is exactly the point.
    assert result["checks"]["selected_episode_count"] is True
    assert result["checks"]["fact_count"] is True


def test_g5_fails_when_the_payload_digest_moves(replay: dict) -> None:
    tampered = {arm: dict(windows) for arm, windows in replay.items()}
    tampered["D"] = dict(tampered["D"])
    tampered["D"][gates.Q11_TURN] = {
        **tampered["D"][gates.Q11_TURN],
        "payload_sha256": "0" * 64,
    }
    assert gates.g5_deployed_reproduction(tampered)["status"] == "FAIL"


def test_g5_names_the_target_as_a_repack_not_a_delivered_window(
    replay: dict,
) -> None:
    result = gates.g5_deployed_reproduction(replay)
    assert "60,285" in result["target_is"]
    assert "not that run's" in result["target_is"]


# --------------------------------------------------------------------------
# G7
# --------------------------------------------------------------------------


def test_g7_passes_with_no_violations() -> None:
    result = gates.g7_probe_order()
    assert result["status"] == "PASS"
    assert result["violations"] == []
    assert result["declared_plant_turn_drift"] == []


def test_g7_reports_earlier_mentions_without_failing() -> None:
    """A term mentioned before its canonical plant is not drift.

    "600" and "marine snow" appear at turns 92 and 94, ahead of the
    declared 100 and 102. That makes the fact available sooner, which is
    the opposite of the Study 010 failure this gate catches.
    """

    earlier = gates.g7_probe_order()["earlier_mentions_than_declared"]
    assert {row["needle"] for row in earlier} == {"600", "marine snow"}


def test_g7_catches_a_probe_whose_fact_is_never_planted(monkeypatch) -> None:
    monkeypatch.setitem(
        gates.TARGETED_ITEMS, "Q1", (112, ("a term the corpus never uses",))
    )
    result = gates.g7_probe_order()
    assert result["status"] == "FAIL"
    assert result["violations"] == ["Q1:a term the corpus never uses"]


def test_g7_catches_a_fact_planted_after_its_probe(monkeypatch) -> None:
    monkeypatch.setitem(gates.TARGETED_ITEMS, "Q1", (2, ("s460ml",)))
    assert gates.g7_probe_order()["status"] == "FAIL"


# --------------------------------------------------------------------------
# Whole run
# --------------------------------------------------------------------------


def test_run_passes_every_gate_and_makes_no_model_call(tmp_path) -> None:
    summary = gates.run(tmp_path)
    output = tmp_path / "pre_test"
    assert summary["status"] == "PASS"
    assert summary["failed_gates"] == []
    assert set(summary["gates"]) == set(gates.GATES)

    audit = json.loads((output / "no_model_call_audit.json").read_text())
    assert audit["status"] == "PASS"
    assert audit["this_run_loaded_a_model"] is False


def test_a_failing_gate_stops_the_study(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        gates,
        "g1_stm_isolation",
        lambda _replay: {"gate": "G1", "status": "FAIL"},
    )
    with pytest.raises(gates.GateFailure, match="binding gates failed"):
        gates.run(tmp_path)
    # The evidence is still written, so a stop is auditable.
    assert (tmp_path / "pre_test" / "g1.json").exists()
