"""Tests for the Study 011 N-tier characterization.

The synthetic fixtures are built so the right answer is known by hand:
a store whose delivery history is written directly, and a contrasting
store where the tier genuinely does behave as a recency window. The
second is what stops the analysis from being a machine that always
reports "not a window".
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.analysis.study_011_n_tier import (
    NTierAnalysisError,
    analyze,
    analyze_arm,
    generations_before,
    k_overlap,
    load_arm,
    recency_window,
    replay_n_candidates,
    rotation_profile,
    store_before,
    verify_replay,
)


def _write_run(
    run_dir: Path,
    *,
    episodes: list[tuple[str, int]],
    events: list[tuple[int, str]],
    rows: list[dict],
) -> Path:
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    db_path = run_dir / "study.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE episodes (id TEXT PRIMARY KEY, turn_number INTEGER)"
    )
    conn.execute(
        "CREATE TABLE retrieval_events ("
        "id INTEGER PRIMARY KEY, turn_number INTEGER, episode_id TEXT)"
    )
    conn.executemany("INSERT INTO episodes VALUES (?, ?)", episodes)
    conn.executemany(
        "INSERT INTO retrieval_events (turn_number, episode_id) VALUES (?, ?)",
        events,
    )
    conn.commit()
    conn.close()
    (run_dir / "logs" / "context_match.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    return run_dir


def _row(turn: int, n_cap: int, n_candidates: list[str], **kwargs) -> dict:
    row = {
        "turn_number": turn,
        "n_cap": n_cap,
        "n_candidate_ids": n_candidates,
        "delivered_n_ids": kwargs.get("delivered", list(n_candidates)),
        "k_candidate_ids": kwargs.get("k_candidates", []),
        "n_k_duplicate_ids": kwargs.get("duplicates", []),
        "k_only_delivered_count": kwargs.get("k_only_delivered", 0),
        "n_candidate_last_generations": kwargs.get("generations", {}),
    }
    return row


def test_generations_before_excludes_the_current_turn():
    events = [(2, "a"), (5, "a"), (4, "b")]
    assert generations_before(events, 5) == {"a": 2, "b": 4}
    assert generations_before(events, 6) == {"a": 5, "b": 4}
    assert generations_before(events, 1) == {}


def test_store_before_is_strictly_below_the_turn():
    episodes = [
        {"id": "a", "turn_number": 1},
        {"id": "b", "turn_number": 2},
        {"id": "c", "turn_number": 3},
    ]
    assert [e["id"] for e in store_before(episodes, 3)] == ["a", "b"]
    assert store_before(episodes, 1) == []


def test_never_delivered_sorts_ahead_of_delivered_and_oldest_first():
    """The head of the sort key, stated as a test rather than as prose."""
    episodes = [
        {"id": "old-undelivered", "turn_number": 1},
        {"id": "new-undelivered", "turn_number": 9},
        {"id": "recently-delivered", "turn_number": 8},
    ]
    events = [(7, "recently-delivered")]
    ranked = replay_n_candidates(episodes, events, turn=10, n_cap=3)
    assert ranked == [
        "old-undelivered",
        "new-undelivered",
        "recently-delivered",
    ]


def test_recency_window_takes_the_highest_source_turns():
    store = [
        {"id": "a", "turn_number": 1},
        {"id": "b", "turn_number": 5},
        {"id": "c", "turn_number": 3},
    ]
    assert recency_window(store, 2) == ["b", "c"]


def test_replay_reports_a_mismatch_rather_than_passing_quietly(tmp_path):
    """A replay that disagrees with the log must fail loudly.

    Without this the identity check is a surrogate: it would report
    success on any run whose log it failed to reproduce.
    """
    episodes = [("a", 1), ("b", 2)]
    rows = [_row(3, 2, ["b", "a"])]
    run_dir = _write_run(
        tmp_path / "bad", episodes=episodes, events=[], rows=rows
    )
    run = load_arm("X", run_dir)
    replay = verify_replay(run)
    assert replay["identical"] is False
    assert replay["turns_testable"] == 1
    assert replay["turns_matched"] == 0
    assert replay["mismatches"][0]["turn"] == 3


def test_replay_matches_when_the_log_follows_the_deployed_key(tmp_path):
    episodes = [("a", 1), ("b", 2)]
    rows = [_row(3, 2, ["a", "b"])]
    run_dir = _write_run(
        tmp_path / "good", episodes=episodes, events=[], rows=rows
    )
    replay = verify_replay(load_arm("X", run_dir))
    assert replay["identical"] is True
    assert replay["turns_matched"] == 1


def test_downstream_measurements_are_withheld_when_replay_fails(tmp_path):
    episodes = [("a", 1), ("b", 2)]
    rows = [_row(3, 2, ["b", "a"])]
    run_dir = _write_run(
        tmp_path / "withheld", episodes=episodes, events=[], rows=rows
    )
    result = analyze_arm("X", run_dir)
    assert "recency_contrast" not in result
    assert "withheld" in result["n_tier"]


def test_a_genuine_recency_window_is_reported_as_one(tmp_path):
    """The contrast must be able to return the opposite answer.

    Here the log records a true recency window, so the analysis has to
    say so; the deployed runs then mean something.
    """
    episodes = [(f"e{i}", i) for i in range(1, 11)]
    rows = []
    for turn in range(4, 11):
        window = [f"e{i}" for i in range(turn - 1, turn - 3, -1)]
        rows.append(_row(turn, 2, window))
    run_dir = _write_run(
        tmp_path / "window", episodes=episodes, events=[], rows=rows
    )
    run = load_arm("W", run_dir)
    from src.analysis.study_011_n_tier import recency_contrast

    contrast = recency_contrast(run)
    assert contrast["mean_delivered_overlap_with_recency"] == 1.0
    assert (
        contrast["turns_where_delivered_equals_recency"]
        == contrast["turns_measured"]
    )


def test_rotation_profile_ignores_episodes_formed_too_late(tmp_path):
    """An episode formed on the last turn never had a turn to be picked.

    Counting it against coverage would understate the sweep for a reason
    that has nothing to do with the ranking.
    """
    episodes = [("a", 1), ("b", 2), ("last", 3)]
    rows = [_row(2, 2, ["a"]), _row(3, 2, ["a", "b"])]
    run_dir = _write_run(
        tmp_path / "rot", episodes=episodes, events=[], rows=rows
    )
    profile = rotation_profile(load_arm("R", run_dir))
    assert profile["store_size"] == 3
    assert profile["reachable_episodes"] == 2
    assert profile["coverage_of_reachable"] == 1.0
    assert profile["max_deliveries_per_reachable_episode"] == 2


def test_k_overlap_counts_a_starved_turn_only_when_material_was_additive(
    tmp_path,
):
    episodes = [("a", 1), ("b", 2)]
    rows = [
        # K nominates only what N already nominated: not starvation.
        _row(3, 2, ["a", "b"], k_candidates=["a"], duplicates=["a"]),
        # K nominates something outside N and none of it lands: starved.
        _row(4, 2, ["a"], k_candidates=["b"], duplicates=[]),
        # Additive material that does land: not starved.
        _row(
            5,
            2,
            ["a"],
            k_candidates=["b"],
            duplicates=[],
            k_only_delivered=1,
        ),
    ]
    run_dir = _write_run(
        tmp_path / "k", episodes=episodes, events=[], rows=rows
    )
    overlap = k_overlap(load_arm("K", run_dir))
    assert overlap["k_candidates_total"] == 3
    assert overlap["k_candidates_already_nominated_by_n"] == 1
    assert overlap["k_candidates_additive"] == 2
    assert overlap["starved_turns"] == [4]


def test_load_arm_refuses_a_missing_run(tmp_path):
    with pytest.raises(NTierAnalysisError):
        load_arm("A", tmp_path / "nowhere")


@pytest.mark.parametrize("arm", ["A", "C", "D"])
def test_committed_runs_replay_exactly(arm):
    """The licence for every other number in the artifact."""
    from src.analysis.study_011_n_tier import ARM_RUN_DIRS

    replay = verify_replay(load_arm(arm, ARM_RUN_DIRS[arm]))
    assert replay["turns_testable"] == 120
    assert replay["identical"] is True


def test_neither_engine_orders_by_recency_of_formation():
    """Scope check, and the reason Arm A does not replicate Study 009.

    Study 009 ran the wall-clock decay engine; Study 011 ran the turn
    generation key. Neither reads recency of formation, and they disagree
    with each other about the episodes already delivered: the older engine
    prefers the freshly delivered one, the newer prefers the stale one.
    """
    from src.analysis.study_011_n_tier import engine_ordering_probe

    probe = engine_ordering_probe()
    carried = probe["study_009_engine"]
    current = probe["study_011_engine"]
    assert carried["matches_reading"] == "most_recently_delivered"
    assert current["matches_reading"] == "least_recently_delivered"
    assert carried["n_cap"] != current["n_cap"]


def test_committed_runs_are_not_recency_windows():
    result = analyze()
    verdict = result["verdict"]
    assert verdict["arms_whose_ranking_replays_exactly"] == ["A", "C", "D"]
    assert verdict["is_a_recency_window"] is False
    # A window of size n_cap cannot reach anything older than n_cap turns.
    assert verdict["min_share_delivered_older_than_n_cap"] > 0.3
    # And the rotation reaches the whole store, which a window never does.
    assert verdict["min_coverage_of_reachable_store"] == 1.0
