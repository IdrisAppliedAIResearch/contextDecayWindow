"""What the N tier actually selects, measured against the committed runs.

Study 011's pre-registration calls the N tier a "recency window" and names
Arm A "recency only". Both descriptions come from the tier's rendered
block, `<recent_context>`, not from its ordering key. The ordering key is
`logical_n_key` in `src/memory/context_matched_stm.py`, and it sorts the
*whole store* by

    (has ever been delivered, turn last delivered, source turn, id)

ascending. Never-delivered episodes sort first; among those already
delivered, the one delivered longest ago sorts first; ties break toward
the *oldest* source turn. Nothing in that key reads recency of formation
except as a last-resort tiebreak, and it reads it backwards.

This module tests that reading against the four committed runs. It is
offline and deterministic: no model call, no embedding call, no mechanism
change. The N ranking is replayed by importing `logical_n_key` from the
deployed engine and applying it to the store state reconstructed from
`retrieval_events`, then compared byte-for-byte against the candidate ids
the live run logged. A replay that reproduces every turn is the licence
for every other number here; a replay that does not invalidates all of
them, and `verify_replay` is checked first for that reason.

Rubric artifacts are not read here and this module is not on any
mechanism path.
"""

from __future__ import annotations

import json
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.memory.context_matched_stm import logical_n_key

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
RUN_ROOT = STUDY_ROOT / "runs"

# Arm D ran from the control worktree on the deployed engine, so its run
# directory is named for that engine rather than for the arm.
ARM_RUN_DIRS = {
    "A": RUN_ROOT / "study_011_live_a" / "arm_a",
    "B": RUN_ROOT / "study_011_live_b" / "arm_b",
    "C": RUN_ROOT / "study_011_live_c" / "arm_c",
    "D": RUN_ROOT / "study_011_live_d" / "context_matched_stm",
}

# The thirteen rubric questions occupy nine retrieval windows; these are
# the turns at which a question is actually asked.
PROBE_TURNS = (112, 113, 114, 115, 116, 117, 118, 119, 120)


class NTierAnalysisError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArmRun:
    arm: str
    run_dir: Path
    rows: list[dict]
    episodes: list[dict]
    events: list[tuple[int, str]]

    @property
    def turn_of(self) -> dict[str, int]:
        return {
            episode["id"]: episode["turn_number"] for episode in self.episodes
        }


def load_arm(arm: str, run_dir: Path) -> ArmRun:
    log_path = run_dir / "logs" / "context_match.jsonl"
    db_path = run_dir / "study.db"
    if not log_path.exists():
        raise NTierAnalysisError(f"missing context log for arm {arm}: {log_path}")
    if not db_path.exists():
        raise NTierAnalysisError(f"missing store for arm {arm}: {db_path}")
    rows = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    episodes, events = read_store(db_path)
    return ArmRun(
        arm=arm,
        run_dir=run_dir,
        rows=rows,
        episodes=episodes,
        events=events,
    )


def read_store(db_path: Path) -> tuple[list[dict], list[tuple[int, str]]]:
    """Read episode identities and delivery events, read-only.

    Embeddings are deliberately not read: nothing here depends on a
    vector, which is what makes the analysis deterministic across the
    embedding-call-shape trap recorded in the ledger.
    """
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        episodes = [
            {"id": str(row[0]), "turn_number": int(row[1])}
            for row in conn.execute("SELECT id, turn_number FROM episodes")
        ]
        events = [
            (int(row[0]), str(row[1]))
            for row in conn.execute(
                "SELECT turn_number, episode_id FROM retrieval_events"
            )
        ]
    finally:
        conn.close()
    episodes.sort(key=lambda episode: (episode["turn_number"], episode["id"]))
    return episodes, events


def store_before(episodes: list[dict], turn: int) -> list[dict]:
    """The episodes visible to retrieval at `turn`.

    An episode is written after its own turn completes, so the store at
    turn t holds turns strictly below t.
    """
    return [episode for episode in episodes if episode["turn_number"] < turn]


def generations_before(
    events: list[tuple[int, str]],
    turn: int,
) -> dict[str, int]:
    """Replay of `get_last_retrieval_generations` as of `turn`.

    The engine reads this map before logging the current turn's own
    deliveries, so events at or after `turn` are not yet visible.
    """
    generations: dict[str, int] = {}
    for event_turn, episode_id in events:
        if event_turn < turn:
            previous = generations.get(episode_id)
            if previous is None or event_turn > previous:
                generations[episode_id] = event_turn
    return generations


def replay_n_candidates(
    episodes: list[dict],
    events: list[tuple[int, str]],
    turn: int,
    n_cap: int,
) -> list[str]:
    """The N candidate list the deployed key produces, from store state."""
    store = store_before(episodes, turn)
    generations = generations_before(events, turn)
    ranked = sorted(
        store,
        key=lambda episode: logical_n_key(episode, generations),
    )
    return [episode["id"] for episode in ranked][:n_cap]


def verify_replay(run: ArmRun) -> dict:
    """Byte-identity of the replayed ranking against the live log.

    Turns whose store is empty are not testable and are reported as such
    rather than counted as passes.
    """
    matched = 0
    testable = 0
    mismatches: list[dict] = []
    for row in run.rows:
        turn = int(row["turn_number"])
        n_cap = int(row["n_cap"])
        if n_cap == 0 or not store_before(run.episodes, turn):
            continue
        testable += 1
        replayed = replay_n_candidates(run.episodes, run.events, turn, n_cap)
        logged = list(row["n_candidate_ids"])
        if replayed == logged:
            matched += 1
        elif len(mismatches) < 5:
            mismatches.append(
                {
                    "turn": turn,
                    "replayed_head": replayed[:4],
                    "logged_head": logged[:4],
                }
            )
    return {
        "turns_testable": testable,
        "turns_matched": matched,
        "identical": testable > 0 and matched == testable,
        "mismatches": mismatches,
    }


def recency_window(store: list[dict], size: int) -> list[str]:
    """What a genuine recency window of `size` would have selected."""
    ranked = sorted(
        store,
        key=lambda episode: (-episode["turn_number"], episode["id"]),
    )
    return [episode["id"] for episode in ranked][:size]


def recency_contrast(run: ArmRun) -> dict:
    """How far the N tier sits from the recency window it is named for.

    Measured twice: over the candidate list, which is the tier's ranking
    decision, and over what was delivered after packing, which is what
    the model saw.
    """
    candidate_overlaps: list[float] = []
    delivered_overlaps: list[float] = []
    identical_candidate_turns = 0
    identical_delivered_turns = 0
    store_fits_turns = 0
    probes_delivering_previous_turn = 0
    probes = 0
    turns = 0
    per_probe: dict[str, dict] = {}
    for row in run.rows:
        turn = int(row["turn_number"])
        n_cap = int(row["n_cap"])
        store = store_before(run.episodes, turn)
        if n_cap == 0 or not store:
            continue
        turns += 1
        # While the store is no larger than the cap the tier takes all of
        # it, so it is trivially identical to a window of that size. This
        # is the regime in which the "recency window" label is true, and
        # it is why the label survived.
        if len(store) <= n_cap:
            store_fits_turns += 1
        candidates = list(row["n_candidate_ids"])
        delivered = list(row["delivered_n_ids"])
        true_candidates = recency_window(store, len(candidates))
        true_delivered = recency_window(store, len(delivered))
        candidate_overlap = _overlap(candidates, true_candidates)
        delivered_overlap = _overlap(delivered, true_delivered)
        candidate_overlaps.append(candidate_overlap)
        delivered_overlaps.append(delivered_overlap)
        if set(candidates) == set(true_candidates):
            identical_candidate_turns += 1
        if delivered and set(delivered) == set(true_delivered):
            identical_delivered_turns += 1
        if turn in PROBE_TURNS:
            probes += 1
            delivered_turns = sorted(
                run.turn_of[episode_id] for episode_id in delivered
            )
            # The immediately preceding turn is the one episode that has
            # never been delivered, so the novelty term at the head of the
            # sort key admits it every time. It is the entire basis of the
            # tier's apparent recency.
            if turn - 1 in delivered_turns:
                probes_delivering_previous_turn += 1
            per_probe[str(turn)] = {
                "delivered_source_turns": delivered_turns,
                "recency_would_have_delivered": sorted(
                    run.turn_of[episode_id] for episode_id in true_delivered
                ),
                "delivered_overlap_with_recency": delivered_overlap,
            }
    return {
        "turns_measured": turns,
        "mean_candidate_overlap_with_recency": _mean(candidate_overlaps),
        "mean_delivered_overlap_with_recency": _mean(delivered_overlaps),
        "turns_where_candidates_equal_recency": identical_candidate_turns,
        "turns_where_delivered_equals_recency": identical_delivered_turns,
        "turns_where_store_fits_within_n_cap": store_fits_turns,
        "probe_turns_measured": probes,
        "probe_turns_delivering_the_immediately_previous_turn": (
            probes_delivering_previous_turn
        ),
        "at_probe_turns": per_probe,
    }


def age_profile(run: ArmRun) -> dict:
    """Age of what the tier delivered, in turns since the source turn.

    A window of size `cap` cannot deliver anything older than `cap` turns.
    The share that is older is the share a window could not have produced.
    """
    ages: list[int] = []
    older_than_cap = 0
    delivered_total = 0
    for row in run.rows:
        turn = int(row["turn_number"])
        n_cap = int(row["n_cap"])
        if n_cap == 0:
            continue
        for episode_id in row["delivered_n_ids"]:
            source_turn = run.turn_of.get(episode_id)
            if source_turn is None:
                continue
            age = turn - source_turn
            ages.append(age)
            delivered_total += 1
            if age > n_cap:
                older_than_cap += 1
    if not ages:
        return {"delivered_total": 0}
    return {
        "delivered_total": delivered_total,
        "min_age_turns": min(ages),
        "median_age_turns": statistics.median(ages),
        "mean_age_turns": round(statistics.fmean(ages), 2),
        "max_age_turns": max(ages),
        "delivered_older_than_n_cap": older_than_cap,
        "share_older_than_n_cap": round(older_than_cap / delivered_total, 4),
    }


def rotation_profile(run: ArmRun) -> dict:
    """Whether delivery sweeps the store or dwells on part of it.

    A recency window revisits the same tail repeatedly and never reaches
    the head. A least-recently-delivered rotation reaches everything and
    spreads deliveries evenly.
    """
    counts: dict[str, int] = {episode["id"]: 0 for episode in run.episodes}
    first_delivery_was_novel = 0
    delivered_events = 0
    for row in run.rows:
        if int(row["n_cap"]) == 0:
            continue
        for episode_id in row["delivered_n_ids"]:
            if episode_id in counts:
                if counts[episode_id] == 0:
                    first_delivery_was_novel += 1
                counts[episode_id] += 1
                delivered_events += 1
    # Only episodes that existed early enough to be reachable are counted
    # against coverage; an episode formed at the final turn never had a
    # turn in which it could be delivered.
    last_turn = max(int(row["turn_number"]) for row in run.rows)
    reachable = [
        episode["id"]
        for episode in run.episodes
        if episode["turn_number"] < last_turn
    ]
    reached = [episode_id for episode_id in reachable if counts[episode_id] > 0]
    delivered_counts = [counts[episode_id] for episode_id in reachable]
    return {
        "store_size": len(run.episodes),
        "reachable_episodes": len(reachable),
        "episodes_ever_delivered": len(reached),
        "coverage_of_reachable": (
            round(len(reached) / len(reachable), 4) if reachable else 0.0
        ),
        "delivery_events": delivered_events,
        "min_deliveries_per_reachable_episode": (
            min(delivered_counts) if delivered_counts else 0
        ),
        "max_deliveries_per_reachable_episode": (
            max(delivered_counts) if delivered_counts else 0
        ),
        "distinct_episodes_first_delivered": first_delivery_was_novel,
    }


def novelty_priority(run: ArmRun) -> dict:
    """How much of each turn's delivery is material never delivered before.

    This is the leading term of the sort key. If it dominates, the tier
    is a coverage sweep whatever its block is called.
    """
    novel = 0
    total = 0
    for row in run.rows:
        if int(row["n_cap"]) == 0:
            continue
        generations = row.get("n_candidate_last_generations") or {}
        for episode_id in row["delivered_n_ids"]:
            total += 1
            if generations.get(episode_id) is None:
                novel += 1
    return {
        "delivered_total": total,
        "delivered_never_delivered_before": novel,
        "share_novel": round(novel / total, 4) if total else 0.0,
    }


def k_overlap(run: ArmRun) -> dict:
    """K's candidates against N's, and whether K was ever starved.

    Additive means a K candidate the N tier did not already nominate.
    A turn is starved when additive material existed and none of it was
    delivered.
    """
    candidates = 0
    duplicates = 0
    turns_with_candidates = 0
    turns_delivering_k_only = 0
    starved_turns: list[int] = []
    for row in run.rows:
        k_ids = list(row["k_candidate_ids"])
        n_ids = set(row["n_candidate_ids"])
        candidates += len(k_ids)
        duplicates += len(row["n_k_duplicate_ids"])
        if k_ids:
            turns_with_candidates += 1
        if int(row["k_only_delivered_count"]) > 0:
            turns_delivering_k_only += 1
        additive = [episode_id for episode_id in k_ids if episode_id not in n_ids]
        if additive and int(row["k_only_delivered_count"]) == 0:
            starved_turns.append(int(row["turn_number"]))
    return {
        "turns": len(run.rows),
        "k_candidates_total": candidates,
        "k_candidates_already_nominated_by_n": duplicates,
        "share_already_nominated_by_n": (
            round(duplicates / candidates, 4) if candidates else 0.0
        ),
        "k_candidates_additive": candidates - duplicates,
        "turns_with_at_least_one_k_candidate": turns_with_candidates,
        "turns_delivering_a_k_only_episode": turns_delivering_k_only,
        "turns_starved": len(starved_turns),
        "starved_turns": starved_turns,
    }


def engine_ordering_probe() -> dict:
    """Which order each engine actually produces, on one known store.

    Two engines matter. Study 011 ran `logical_n_key`. Study 009 — the
    study whose Arm S the pre-registration says Arm A replicates — ran
    `StmRetrievalEngine._n_retrieve`, a wall-clock decay on
    `last_retrieved_at` sorted descending.

    The probe is a three-episode store constructed so that the three
    candidate readings give three different answers, so the result cannot
    be ambiguous:

    * a recency window returns the newest source turn first;
    * least-recently-delivered returns the one delivered longest ago
      first;
    * most-recently-delivered returns the freshly delivered one first.

    Never-delivered material sorts first under both engines, so the
    ordering is decided entirely by the two that have been delivered.
    """
    from src.memory.stm_retrieval_engine import (
        N_RETRIEVAL_CAP,
        StmRetrievalEngine,
    )

    now = datetime.now(timezone.utc)
    episodes = [
        {
            "id": "oldest-never-delivered",
            "turn_number": 1,
            "last_retrieved_at": None,
        },
        {
            "id": "newest-delivered-recently",
            "turn_number": 9,
            "last_retrieved_at": (now - timedelta(hours=1)).isoformat(),
        },
        {
            "id": "middle-delivered-long-ago",
            "turn_number": 5,
            "last_retrieved_at": (now - timedelta(hours=48)).isoformat(),
        },
    ]
    readings = {
        "recency_of_formation": [
            "newest-delivered-recently",
            "middle-delivered-long-ago",
            "oldest-never-delivered",
        ],
        "least_recently_delivered": [
            "oldest-never-delivered",
            "middle-delivered-long-ago",
            "newest-delivered-recently",
        ],
        "most_recently_delivered": [
            "oldest-never-delivered",
            "newest-delivered-recently",
            "middle-delivered-long-ago",
        ],
    }

    carried, _ = StmRetrievalEngine._n_retrieve(episodes)
    events = [(4, "middle-delivered-long-ago"), (9, "newest-delivered-recently")]
    study_011 = replay_n_candidates(
        [dict(episode) for episode in episodes],
        events,
        turn=10,
        n_cap=3,
    )
    return {
        "readings": readings,
        "study_009_engine": {
            "path": "src/memory/stm_retrieval_engine.py::_n_retrieve",
            "n_cap": N_RETRIEVAL_CAP,
            "ranking_returned": list(carried),
            "matches_reading": _match_reading(list(carried), readings),
        },
        "study_011_engine": {
            "path": "src/memory/context_matched_stm.py::logical_n_key",
            "n_cap": 32,
            "ranking_returned": list(study_011),
            "matches_reading": _match_reading(study_011, readings),
        },
    }


def _match_reading(ranking: list[str], readings: dict[str, list[str]]) -> str:
    for name, expected in readings.items():
        if ranking == expected:
            return name
    return "none of the three"


def analyze_arm(arm: str, run_dir: Path) -> dict:
    run = load_arm(arm, run_dir)
    replay = verify_replay(run)
    result = {
        "arm": arm,
        "run_dir": _repo_relative(run_dir),
        "turns": len(run.rows),
        "n_cap": int(run.rows[-1]["n_cap"]),
        "replay": replay,
        "k_overlap": k_overlap(run),
    }
    if int(run.rows[-1]["n_cap"]) == 0:
        result["n_tier"] = "disabled in this arm"
        return result
    if not replay["identical"]:
        result["n_tier"] = (
            "replay did not reproduce the live ranking; downstream "
            "measurements are withheld"
        )
        return result
    result.update(
        {
            "recency_contrast": recency_contrast(run),
            "age_profile": age_profile(run),
            "rotation_profile": rotation_profile(run),
            "novelty_priority": novelty_priority(run),
        }
    )
    return result


def analyze(arm_run_dirs: dict[str, Path] | None = None) -> dict:
    dirs = arm_run_dirs if arm_run_dirs is not None else ARM_RUN_DIRS
    arms = {arm: analyze_arm(arm, run_dir) for arm, run_dir in dirs.items()}
    return {
        "what_this_measures": (
            "whether the N tier is the recency window the pre-registration "
            "names, or a least-recently-delivered rotation over the whole "
            "store"
        ),
        "ordering_key": (
            "logical_n_key: (has ever been delivered, turn last delivered, "
            "source turn, id) ascending, over every episode in the store"
        ),
        "arms": arms,
        "engine_ordering_probe": engine_ordering_probe(),
        "verdict": _verdict(arms),
    }


def _verdict(arms: dict[str, dict]) -> dict:
    with_n = [
        arm for arm, result in arms.items() if result.get("recency_contrast")
    ]
    replayed = [
        arm for arm, result in arms.items() if result["replay"]["identical"]
    ]
    overlaps = [
        arms[arm]["recency_contrast"]["mean_delivered_overlap_with_recency"]
        for arm in with_n
    ]
    older = [
        arms[arm]["age_profile"]["share_older_than_n_cap"] for arm in with_n
    ]
    coverage = [
        arms[arm]["rotation_profile"]["coverage_of_reachable"] for arm in with_n
    ]
    return {
        "arms_with_an_n_tier": with_n,
        "arms_whose_ranking_replays_exactly": replayed,
        "max_mean_delivered_overlap_with_recency": (
            max(overlaps) if overlaps else None
        ),
        "min_share_delivered_older_than_n_cap": min(older) if older else None,
        "min_coverage_of_reachable_store": min(coverage) if coverage else None,
        "is_a_recency_window": (
            bool(overlaps) and max(overlaps) >= 0.9
        ),
    }


def _overlap(selected: list[str], reference: list[str]) -> float:
    if not selected:
        return 0.0
    return round(len(set(selected) & set(reference)) / len(set(selected)), 4)


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 4) if values else 0.0


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
