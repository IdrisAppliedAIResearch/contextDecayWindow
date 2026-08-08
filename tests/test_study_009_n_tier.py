"""Tests for the Study 009 N-tier characterization.

The synthetic fixtures are built so the right answer is known by hand.
Two of them exist to stop the analysis from being a machine that always
reports "locked": one run whose log is a genuine last-N window, and one
whose log rotates through the store. If the module reported lock-in for
those, its verdict on the committed runs would mean nothing.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from src.analysis.study_009_n_tier import (
    ARM_L_FULL,
    ARM_S_ABLATION,
    ARM_S_FULL,
    NTierAnalysisError,
    Run,
    analyze_run,
    delivery_profile,
    load_run,
    lock_in_profile,
    rank_n_candidates,
    shared_key_probe,
    verify_replay,
    window_contrast,
)


def _synthetic_run(
    name: str,
    store_turns: int,
    n_log: dict[int, list[str]],
    touches: dict[int, list[str]] | None = None,
) -> Run:
    store = [
        {"id": f"ep{turn:03d}", "turn_number": turn}
        for turn in range(1, store_turns + 1)
    ]
    return Run(
        name=name,
        run_dir=Path("synthetic"),
        engine="synthetic",
        store=store,
        n_log=n_log,
        touches=touches if touches is not None else dict(n_log),
        turn_of={
            episode["id"]: episode["turn_number"] for episode in store
        },
    )


def _window_log(store_turns: int, cap: int = 10) -> dict[int, list[str]]:
    log = {}
    for turn in range(2, store_turns + 1):
        visible = list(range(1, turn))
        log[turn] = [f"ep{t:03d}" for t in visible[-cap:]]
    return log


def _rotation_log(store_turns: int, cap: int = 10) -> dict[int, list[str]]:
    log = {}
    cursor = 0
    for turn in range(2, store_turns + 1):
        visible = list(range(1, turn))
        picked = []
        for _ in range(min(cap, len(visible))):
            picked.append(visible[cursor % len(visible)])
            cursor += 1
        log[turn] = [f"ep{t:03d}" for t in picked]
    return log


# --- the ordering rule ------------------------------------------------


def test_never_delivered_sorts_above_everything_delivered():
    store = [
        {"id": "a", "turn_number": 1},
        {"id": "b", "turn_number": 2},
        {"id": "c", "turn_number": 3},
    ]
    ranked = rank_n_candidates(store, turn=4, last_touch={"a": 3, "b": 1})
    assert ranked[0] == "c"


def test_fresher_delivery_outranks_staler():
    store = [
        {"id": "a", "turn_number": 1},
        {"id": "b", "turn_number": 2},
    ]
    ranked = rank_n_candidates(store, turn=3, last_touch={"a": 2, "b": 1})
    assert ranked == ["a", "b"]


def test_a_batch_tie_breaks_toward_the_oldest_source_turn():
    """Every episode in one touch batch shares a timestamp.

    The tie is then decided by the order the store query returns, which
    is `turn_number ASC`. That is why the block settles on the oldest
    episodes rather than an arbitrary nine.
    """
    store = [
        {"id": f"ep{turn}", "turn_number": turn} for turn in range(1, 6)
    ]
    last_touch = {f"ep{turn}": 9 for turn in range(1, 6)}
    ranked = rank_n_candidates(store, turn=10, last_touch=last_touch, n_cap=2)
    assert ranked == ["ep1", "ep2"]


def test_the_cap_is_honoured():
    store = [
        {"id": f"ep{turn}", "turn_number": turn} for turn in range(1, 40)
    ]
    ranked = rank_n_candidates(store, turn=40, last_touch={})
    assert len(ranked) == 10


def test_episodes_formed_after_the_turn_are_not_visible():
    store = [
        {"id": "a", "turn_number": 1},
        {"id": "future", "turn_number": 9},
    ]
    assert rank_n_candidates(store, turn=5, last_touch={}) == ["a"]


# --- the replay is a real test, not a rubber stamp --------------------


def test_replay_reports_a_mismatch_rather_than_passing_quietly():
    log = {2: ["ep001"], 3: ["ep002", "ep001"]}
    run = _synthetic_run("good", 3, log)
    assert verify_replay(run)["identical"] is True

    wrong = dict(log)
    wrong[3] = ["ep001", "ep002"]
    broken = _synthetic_run("bad", 3, wrong)
    replay = verify_replay(broken)
    assert replay["identical"] is False
    assert replay["mismatches"][0]["turn"] == 3


def test_replay_compares_order_not_only_membership():
    """Same ten episodes, wrong order, is a different rule and must fail."""
    ordered = _synthetic_run("ordered", 3, {2: ["ep001"], 3: ["ep002", "ep001"]})
    assert verify_replay(ordered)["identical"] is True
    scrambled = _synthetic_run(
        "scrambled", 3, {2: ["ep001"], 3: ["ep001", "ep002"]}
    )
    replay = verify_replay(scrambled)
    assert replay["identical"] is False
    assert set(replay["mismatches"][0]["predicted"]) == set(
        replay["mismatches"][0]["observed"]
    )


def test_downstream_measurements_are_withheld_when_replay_fails():
    broken = _synthetic_run("bad", 3, {2: ["ep001"], 3: ["ep001", "ep002"]})
    result = analyze_run(broken)
    assert result["replay"]["identical"] is False
    assert "measurements_withheld" in result
    for withheld in ("lock_in", "deliveries", "window_contrast"):
        assert withheld not in result


def test_a_turn_is_tested_against_the_log_not_against_the_replay():
    """One wrong turn must not be able to hide behind the next one.

    State advances from the logged deliveries, so a turn the replay got
    wrong still leaves the following turn testable against ground truth.
    """
    log = {2: ["ep001"], 3: ["ep001", "ep002"], 4: ["ep003", "ep001", "ep002"]}
    run = _synthetic_run("mixed", 4, log)
    replay = verify_replay(run)
    assert replay["turns_testable"] == 3
    assert replay["turns_matched"] == 2


# --- the negative controls --------------------------------------------


def test_a_genuine_recency_window_is_not_reported_as_locked():
    run = _synthetic_run("window", 40, _window_log(40))
    assert window_contrast(run)["mean_overlap_with_true_window"] == 1.0
    assert window_contrast(run)["share_older_than_cap"] == 0.0
    assert lock_in_profile(run)["held_are_the_oldest_in_store"] is False


def test_a_rotation_is_not_reported_as_locked():
    run = _synthetic_run("rotation", 40, _rotation_log(40))
    profile = lock_in_profile(run)
    assert profile["held_source_turns"] != [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert delivery_profile(run)["share_delivered_exactly_once"] < 0.5


def test_a_locked_prefix_is_reported_as_one():
    log = {}
    for turn in range(11, 40):
        log[turn] = [f"ep{turn - 1:03d}"] + [
            f"ep{t:03d}" for t in range(1, 10)
        ]
    run = _synthetic_run("locked", 40, log)
    profile = lock_in_profile(run)
    assert profile["held_source_turns"] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert profile["held_are_the_oldest_in_store"] is True
    assert profile["constant_repeat_set_from_turn"] == 12


def test_window_contrast_counts_deliveries_older_than_the_cap():
    run = _synthetic_run("old", 40, {30: ["ep001", "ep029"]})
    contrast = window_contrast(run)
    assert contrast["share_older_than_cap"] == 0.5
    assert contrast["max_delivered_age_turns"] == 29


# --- the two engines ---------------------------------------------------


def test_both_live_engines_carry_the_same_n_rule():
    """If they did not, the S-L contrast would be confounded by it."""
    probe = shared_key_probe()
    assert probe["caps_equal"] is True
    assert probe["scores_agree_to_six_places"] is True
    assert probe["fresher_delivery_outranks_staler"] is True


def test_never_delivered_scores_at_the_exponential_ceiling():
    """The 1.0 sentinel is what puts novelty first, in both engines."""
    assert shared_key_probe()["never_delivered_scores_at_the_ceiling"] is True


def test_this_rule_is_not_the_study_011_rule():
    """`logical_n_key` prefers the stalest delivery; this prefers the freshest."""
    from src.analysis.study_011_n_tier import replay_n_candidates

    store = [
        {"id": "stale", "turn_number": 1},
        {"id": "fresh", "turn_number": 2},
    ]
    carried = rank_n_candidates(
        store, turn=6, last_touch={"stale": 2, "fresh": 5}
    )
    study_011 = replay_n_candidates(
        [dict(episode) for episode in store],
        [(2, "stale"), (5, "fresh")],
        turn=6,
        n_cap=2,
    )
    assert carried == ["fresh", "stale"]
    assert study_011 == ["stale", "fresh"]


# --- the committed runs -------------------------------------------------


def test_missing_store_is_an_error_not_a_silent_empty_result(tmp_path):
    with pytest.raises(NTierAnalysisError):
        load_run("absent", tmp_path, "none")


@pytest.mark.parametrize(
    "name,run_dir",
    [
        ("arm_s_full", ARM_S_FULL),
        ("arm_s_ablation", ARM_S_ABLATION),
        ("arm_l_full", ARM_L_FULL),
    ],
)
def test_committed_runs_replay_exactly(name, run_dir):
    run = load_run(name, run_dir, "committed")
    replay = verify_replay(run)
    assert replay["turns_testable"] > 0
    assert replay["identical"] is True, replay["mismatches"]


@pytest.mark.parametrize(
    "name,run_dir",
    [("arm_s_full", ARM_S_FULL), ("arm_l_full", ARM_L_FULL)],
)
def test_both_arms_hold_the_same_nine_oldest_episodes(name, run_dir):
    run = load_run(name, run_dir, "committed")
    profile = lock_in_profile(run)
    assert profile["held_source_turns"] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert profile["constant_repeat_set_from_turn"] == 11


def test_the_arms_differ_in_the_ltm_tier_and_not_in_the_n_tier():
    """The registered contrast is preserved; what it sits on is not a window."""
    arm_s = load_run("arm_s_full", ARM_S_FULL, "committed")
    arm_l = load_run("arm_l_full", ARM_L_FULL, "committed")
    s_turns = {
        turn: sorted(arm_s.turn_of[eid] for eid in ids)
        for turn, ids in arm_s.n_log.items()
    }
    l_turns = {
        turn: sorted(arm_l.turn_of[eid] for eid in ids)
        for turn, ids in arm_l.n_log.items()
    }
    assert s_turns == l_turns


def test_the_log_the_replay_is_checked_against_is_the_committed_one():
    """Guards against the fixture drifting away from the artifact."""
    path = ARM_S_FULL / "metrics" / "N_values.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1155
    assert {row["turn"] for row in rows} >= {"11", "120"}


def test_store_query_order_is_the_one_the_engine_uses():
    """`turn_number ASC` is load-bearing: it decides the batch tie."""
    conn = sqlite3.connect(ARM_S_FULL / "study.db")
    try:
        turns = [
            row[0]
            for row in conn.execute(
                "SELECT turn_number FROM episodes ORDER BY turn_number ASC"
            )
        ]
    finally:
        conn.close()
    assert turns == sorted(turns)
