"""What the N tier delivered in Study 009, measured against the committed runs.

Study 011's characterization established that the tier the arc calls a
recency window is not one. That work compared three ordering rules and
recorded the carried engine's key --- `StmRetrievalEngine._n_retrieve` in
`src/memory/stm_retrieval_engine.py` --- as "most recently delivered
first". The key is that. This module asks the next question, which the
key alone does not answer: what does that key *do* over a hundred and
twenty turns of a run that touches every episode it delivers?

The rule has three parts, and the third is the one that matters:

* `_compute_decay` returns **1.0** for `last_retrieved_at is None`, and
  1.0 is the maximum the exponential can reach. Never-delivered material
  therefore sorts first, exactly as under `logical_n_key`.
* Everything already delivered sorts by `exp(-0.1 * hours_since)`
  descending, so the *freshest* delivery outranks the stalest --- the
  inverse of `logical_n_key`.
* `retrieve()` touches every episode it delivered, in one call, with a
  single timestamp. So the tier refreshes precisely the episodes that
  keep it at the top of its own ordering.

The third part closes a loop. Once the store outgrows the cap of ten,
the episodes already in the block are the freshest in the store, so they
are selected again, so they are refreshed again. Ties within a batch
share one timestamp and break by store order, which
`get_all_episodes_with_embeddings` fixes as `turn_number ASC`. The block
is a fixed prefix of the conversation plus one slot for whatever has not
been delivered yet.

That is a prediction, and this module tests it by replay. The ordering is
reconstructed from delivery history alone --- no wall clock is needed,
because `exp(-0.1 * hours_since)` is monotone in `last_retrieved_at`, so
ranking by score descending is ranking by last-touch descending, with
never-touched pinned above both. State is advanced from the *logged*
delivery sets rather than from the replay's own predictions, so every
turn is an independent test and a wrong prediction cannot cascade into
one that happens to match.

A replay that reproduces every logged turn is the licence for every other
number here. A replay that does not invalidates all of them, and
`verify_replay` is checked first for that reason.

Offline and deterministic: no model call, no embedding call, no mechanism
change. Rubric artifacts are not read and this module is not on any
mechanism path.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from src.memory.stm_retrieval_engine import N_RETRIEVAL_CAP

REPO_ROOT = Path(__file__).resolve().parents[2]

# Arm L is not a Study 009 run. It is the accepted Study 007 LTM arm,
# preserved and carried in as the comparison; the Study 009 report says so
# and treats it as a limitation. It is read here from where it lives.
ARM_S_FULL = (
    REPO_ROOT
    / "experiments/study_009/runs/study_009_full_001/arm_s"
)
ARM_S_ABLATION = (
    REPO_ROOT
    / "experiments/study_009/runs/study_009_ablation_001/arm_s"
)
ARM_L_FULL = (
    REPO_ROOT
    / "experiments/study_007/runs/study_007_full_001/condition_c"
)

# The thirteen rubric questions are asked over these turns of the 121-turn
# script. The ablation run is 35 turns and reaches none of them.
PROBE_TURNS = (112, 113, 114, 115, 116, 117, 118, 119, 120, 121)


class NTierAnalysisError(RuntimeError):
    pass


@dataclass(frozen=True)
class Run:
    name: str
    run_dir: Path
    engine: str
    store: list[dict]
    n_log: dict[int, list[str]]
    touches: dict[int, list[str]]
    ltm_block: dict[int, set[str]] = field(default_factory=dict)
    probe_turns: tuple[int, ...] = ()
    turn_of: dict[str, int] = field(default_factory=dict)


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_store(db_path: Path) -> list[dict]:
    """The store in the order the deployed query returns it.

    `get_all_episodes_with_embeddings` orders by `turn_number ASC`, and
    that order is what breaks ties inside the decay sort, so it is part
    of the mechanism rather than a presentational detail. Embeddings are
    deliberately not read: nothing here needs them, and reading them
    would make the module depend on a provider.
    """
    if not db_path.exists():
        raise NTierAnalysisError(f"missing store: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, turn_number FROM episodes ORDER BY turn_number ASC"
        ).fetchall()
    finally:
        conn.close()
    return [{"id": str(row[0]), "turn_number": int(row[1])} for row in rows]


def store_signature(db_path: Path, turns_logged: int) -> dict:
    """The lock-in as it appears in the store, without any replay.

    `episodes.retrieval_count` is incremented once per touch, so a tier
    that holds the same nine episodes for a whole run leaves those nine
    with a count near the turn count and everything else near one. This
    is an observation, not a derivation: the counter is shared with the
    other tiers, so a matching signature is consistent with the locked
    prefix rather than proof of it. Only the replayed runs establish the
    rule. This is reported for the runs that predate it, whose logs
    record the rendered block in conversation order rather than the
    ranking, and which therefore cannot be replayed here.
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT turn_number, retrieval_count FROM episodes "
            "ORDER BY turn_number ASC"
        ).fetchall()
    finally:
        conn.close()
    counts = [int(row[1]) for row in rows]
    if len(counts) < 12 or turns_logged < 12:
        return {"signature_testable": False}
    head, tail = counts[:9], counts[9:]
    return {
        "signature_testable": True,
        "oldest_nine_retrieval_counts": head,
        "median_retrieval_count_of_the_rest": statistics.median(tail),
        "oldest_nine_all_near_the_turn_count": all(
            count >= 0.9 * turns_logged for count in head
        ),
        "rest_delivered_about_once": statistics.median(tail) <= 2,
    }


def load_n_log(run_dir: Path) -> dict[int, list[str]]:
    """What the N tier delivered each turn, in the order it ranked them."""
    rows = _read_csv(run_dir / "metrics" / "N_values.csv")
    if not rows:
        raise NTierAnalysisError(f"missing N log under {run_dir}")
    log: dict[int, list[str]] = {}
    for row in rows:
        log.setdefault(int(row["turn"]), []).append(row["episode_id"])
    return log


def load_touches(run_dir: Path) -> dict[int, list[str]]:
    """Every episode the run refreshed on each turn.

    `retrieve()` touches the union of what it put in the context, so the
    N block alone is not the whole of it: the K tier contributes, and in
    the LTM arm so does arbitration. All three are logged.
    """
    touched: dict[int, set[str]] = {}
    sources = (
        (run_dir / "metrics" / "N_values.csv", "episode_id"),
        (run_dir / "metrics" / "K_values.csv", "episode_id"),
        (run_dir / "logs" / "ltm_context_episodes.csv", "episode_id"),
    )
    for path, column in sources:
        for row in _read_csv(path):
            touched.setdefault(int(row["turn"]), set()).add(row[column])
    return {turn: sorted(ids) for turn, ids in touched.items()}


def load_ltm_block(run_dir: Path) -> dict[int, set[str]]:
    """Episodes arbitration rendered as LTM rather than as recent context.

    `RetrievalEngine.retrieve` removes an arbitration survivor from the
    recent block so it keeps its tagged placement, so the N log in an LTM
    arm is the candidate ranking *minus* that turn's survivors. Ignoring
    that would make the replay fail on turns where the mechanism did
    exactly what it says it does.
    """
    block: dict[int, set[str]] = {}
    for row in _read_csv(run_dir / "logs" / "ltm_context_episodes.csv"):
        block.setdefault(int(row["turn"]), set()).add(row["episode_id"])
    return block


def rank_n_candidates(
    store: list[dict],
    turn: int,
    last_touch: dict[str, int],
    n_cap: int = N_RETRIEVAL_CAP,
) -> list[str]:
    """The carried engine's N ranking, reconstructed for one turn.

    `_compute_decay` is strictly increasing in `last_retrieved_at` and
    returns 1.0 --- its supremum --- for never-delivered episodes, so
    sorting scores descending is sorting by

        (has never been delivered, turn last delivered, store position)

    with the first two descending and the last ascending. The wall clock
    drops out. Store position enters because a batch touch writes one
    timestamp to every episode in it, leaving them tied on the real key.
    """
    visible = [
        episode for episode in store if episode["turn_number"] < turn
    ]
    ordered = sorted(
        enumerate(visible),
        key=lambda pair: (
            0 if pair[1]["id"] not in last_touch else 1,
            -last_touch.get(pair[1]["id"], 0),
            pair[0],
        ),
    )
    return [episode["id"] for _, episode in ordered][:n_cap]


def verify_replay(run: Run) -> dict:
    """Does the reconstructed rule reproduce what the run logged?

    State advances from the logged delivery sets, not from the replay's
    own output, so each turn is tested against ground truth independently.
    Order is compared, not just membership: a rule that picks the right
    ten in the wrong order is a different rule.
    """
    last_touch: dict[str, int] = {}
    mismatches: list[dict] = []
    matched = 0
    raw_matched = 0
    for turn in sorted(run.n_log):
        ranked = rank_n_candidates(run.store, turn, last_touch)
        promoted = run.ltm_block.get(turn, set())
        predicted = [
            episode_id for episode_id in ranked if episode_id not in promoted
        ]
        observed = run.n_log[turn]
        if ranked == observed:
            raw_matched += 1
        if predicted == observed:
            matched += 1
        else:
            mismatches.append(
                {
                    "turn": turn,
                    "predicted": predicted,
                    "observed": observed,
                }
            )
        for episode_id in run.touches.get(turn, []):
            last_touch[episode_id] = turn
    return {
        "turns_testable": len(run.n_log),
        "turns_matched": matched,
        "turns_matching_before_arbitration_removal": raw_matched,
        "identical": matched == len(run.n_log) and bool(run.n_log),
        "mismatches": mismatches[:5],
    }


def lock_in_profile(run: Run) -> dict:
    """Which episodes the block holds, and from which turn it stops moving.

    The repeat set of a turn is what it delivered that it had delivered
    before. If the prediction is right, that set is constant from the
    turn the store outgrows the cap, and it is the oldest episodes in the
    conversation.
    """
    seen: set[str] = set()
    repeat_sets: dict[int, frozenset[str]] = {}
    for turn in sorted(run.n_log):
        delivered = run.n_log[turn]
        repeat_sets[turn] = frozenset(seen.intersection(delivered))
        seen.update(delivered)

    turns = sorted(repeat_sets)
    final = repeat_sets[turns[-1]]
    constant_from = None
    for index, turn in enumerate(turns):
        if all(repeat_sets[later] == final for later in turns[index:]):
            constant_from = turn
            break

    held_turns = sorted(run.turn_of[episode_id] for episode_id in final)
    return {
        "constant_repeat_set_from_turn": constant_from,
        "turns_after_that_point": (
            len([turn for turn in turns if constant_from is not None
                 and turn >= constant_from])
        ),
        "held_episode_count": len(final),
        "held_source_turns": held_turns,
        "held_are_the_oldest_in_store": (
            held_turns
            == sorted(
                episode["turn_number"] for episode in run.store
            )[: len(final)]
        ),
    }


def delivery_profile(run: Run) -> dict:
    counts: dict[str, int] = {}
    for delivered in run.n_log.values():
        for episode_id in delivered:
            counts[episode_id] = counts.get(episode_id, 0) + 1
    values = sorted(counts.values())
    return {
        "episodes_ever_delivered": len(counts),
        "store_size": len(run.store),
        "min_deliveries": values[0] if values else 0,
        "median_deliveries": statistics.median(values) if values else 0,
        "max_deliveries": values[-1] if values else 0,
        "episodes_delivered_exactly_once": sum(
            1 for value in values if value == 1
        ),
        "share_delivered_exactly_once": (
            round(sum(1 for value in values if value == 1) / len(values), 4)
            if values
            else 0.0
        ),
    }


def window_contrast(run: Run) -> dict:
    """The delivered block against a true recency window of the same size.

    The comparison is descriptive. It says what a last-N rule would have
    put in the block on the same turns; it says nothing about what such a
    rule would have scored, and no number here should be read that way.
    """
    overlaps: list[float] = []
    ages: list[int] = []
    older_than_cap = 0
    total = 0
    newest_present = 0
    for turn in sorted(run.n_log):
        delivered = run.n_log[turn]
        visible = [
            episode for episode in run.store
            if episode["turn_number"] < turn
        ]
        window = {
            episode["id"] for episode in visible[-N_RETRIEVAL_CAP:]
        }
        if delivered:
            overlaps.append(
                len(window.intersection(delivered)) / len(delivered)
            )
        if visible and visible[-1]["id"] in delivered:
            newest_present += 1
        for episode_id in delivered:
            age = turn - run.turn_of[episode_id]
            ages.append(age)
            total += 1
            if age > N_RETRIEVAL_CAP:
                older_than_cap += 1
    return {
        "mean_overlap_with_true_window": (
            round(statistics.mean(overlaps), 4) if overlaps else 0.0
        ),
        "mean_delivered_age_turns": (
            round(statistics.mean(ages), 2) if ages else 0.0
        ),
        "max_delivered_age_turns": max(ages) if ages else 0,
        "share_older_than_cap": (
            round(older_than_cap / total, 4) if total else 0.0
        ),
        "turns_delivering_the_newest_episode": newest_present,
        "turns_measured": len(run.n_log),
    }


def probe_turn_detail(run: Run) -> dict:
    """Source turns in the block on the turns the rubric questions are asked."""
    detail = {}
    for turn in run.probe_turns:
        if turn not in run.n_log:
            continue
        visible = [
            episode for episode in run.store
            if episode["turn_number"] < turn
        ]
        detail[str(turn)] = {
            "delivered_source_turns": sorted(
                run.turn_of[episode_id] for episode_id in run.n_log[turn]
            ),
            "a_true_window_would_have_delivered": sorted(
                episode["turn_number"]
                for episode in visible[-N_RETRIEVAL_CAP:]
            ),
        }
    return detail


def load_run(
    name: str,
    run_dir: Path,
    engine: str,
    probe_turns: tuple[int, ...] = (),
) -> Run:
    store = load_store(run_dir / "study.db")
    return Run(
        name=name,
        run_dir=run_dir,
        engine=engine,
        store=store,
        n_log=load_n_log(run_dir),
        touches=load_touches(run_dir),
        ltm_block=load_ltm_block(run_dir),
        probe_turns=probe_turns,
        turn_of={
            episode["id"]: episode["turn_number"] for episode in store
        },
    )


def analyze_run(run: Run) -> dict:
    replay = verify_replay(run)
    result = {
        "run": run.name,
        "run_dir": _repo_relative(run.run_dir),
        "engine": run.engine,
        "n_cap": N_RETRIEVAL_CAP,
        "replay": replay,
    }
    if not replay["identical"]:
        result["measurements_withheld"] = (
            "The replay did not reproduce the logged ranking, so the "
            "reconstructed rule is not established as the rule that ran "
            "and nothing downstream of it is reported."
        )
        return result
    result["lock_in"] = lock_in_profile(run)
    result["deliveries"] = delivery_profile(run)
    result["window_contrast"] = window_contrast(run)
    result["probe_turns"] = probe_turn_detail(run)
    return result


def shared_key_probe() -> dict:
    """Do the two live engines carry the same N rule, or only a similar one?

    Arm S ran `StmRetrievalEngine`; Arm L ran `RetrievalEngine`. If their
    N tiers differ, the S-L contrast is confounded by the difference and
    the comparison measures something other than the LTM tier. The check
    is by behaviour on shared inputs, not by reading the two files and
    judging them alike.
    """
    from src.memory.retrieval_engine import (
        N_RETRIEVAL_CAP as LTM_ARM_CAP,
        RetrievalEngine,
    )
    from src.memory.stm_retrieval_engine import StmRetrievalEngine

    probes = [
        None,
        "2026-07-26T21:50:29.744265+00:00",
        "2026-07-20T09:00:00.000000+00:00",
    ]
    stm_scores = [
        StmRetrievalEngine._compute_decay(value) for value in probes
    ]
    # `RetrievalEngine._compute_decay` is declared on the instance but
    # reads nothing from it, so it is called unbound rather than
    # constructing an engine and its dependencies.
    ltm_scores = [
        RetrievalEngine._compute_decay(None, value) for value in probes
    ]
    return {
        "stm_arm_cap": N_RETRIEVAL_CAP,
        "ltm_arm_cap": LTM_ARM_CAP,
        "caps_equal": N_RETRIEVAL_CAP == LTM_ARM_CAP,
        "never_delivered_scores_at_the_ceiling": (
            stm_scores[0] == 1.0 and ltm_scores[0] == 1.0
        ),
        "scores_agree_to_six_places": all(
            round(left, 6) == round(right, 6)
            for left, right in zip(stm_scores, ltm_scores)
        ),
        "fresher_delivery_outranks_staler": (
            stm_scores[1] > stm_scores[2] and ltm_scores[1] > ltm_scores[2]
        ),
    }


def discover_runs() -> list[Path]:
    """Every committed run directory that carries a store and an N log.

    The scan is deliberately indiscriminate. Rehearsals, ablations and
    failed launches are included and labelled rather than filtered, so
    the reader can see the rule's reach without taking this module's
    word for which runs counted.
    """
    found = []
    for db_path in sorted(REPO_ROOT.glob("experiments/study_0*/runs/*/*/study.db")):
        run_dir = db_path.parent
        if (run_dir / "metrics" / "N_values.csv").exists():
            found.append(run_dir)
    return found


def scan_run(run_dir: Path) -> dict:
    """One compact row: did the rule run here, and did the block lock?"""
    try:
        run = load_run(_repo_relative(run_dir), run_dir, "scanned")
    except NTierAnalysisError as error:
        return {"run_dir": _repo_relative(run_dir), "error": str(error)}
    replay = verify_replay(run)
    row = {
        "run_dir": _repo_relative(run_dir),
        "turns_logged": len(run.n_log),
        "store_size": len(run.store),
        "replay_identical": replay["identical"],
        "turns_matched": replay["turns_matched"],
        "store_signature": store_signature(
            run_dir / "study.db", len(run.n_log)
        ),
    }
    if not replay["identical"]:
        row["measurements_withheld"] = (
            "The reconstructed rule does not reproduce this run's log, "
            "so nothing is claimed about what its tier did."
        )
        return row
    lock_in = lock_in_profile(run)
    contrast = window_contrast(run)
    row["held_source_turns"] = lock_in["held_source_turns"]
    row["held_are_the_oldest_in_store"] = lock_in["held_are_the_oldest_in_store"]
    row["constant_repeat_set_from_turn"] = lock_in["constant_repeat_set_from_turn"]
    row["mean_overlap_with_true_window"] = contrast["mean_overlap_with_true_window"]
    row["share_older_than_cap"] = contrast["share_older_than_cap"]
    row["share_delivered_exactly_once"] = delivery_profile(run)[
        "share_delivered_exactly_once"
    ]
    return row


def generality_scan() -> dict:
    """How far the locked prefix reaches across the committed record."""
    rows = [scan_run(run_dir) for run_dir in discover_runs()]
    replayed = [row for row in rows if row.get("replay_identical")]
    locked = [
        row for row in replayed
        if row.get("held_are_the_oldest_in_store")
        and row.get("constant_repeat_set_from_turn") is not None
    ]
    signature = [
        row for row in rows
        if row.get("store_signature", {}).get("signature_testable")
        and row["store_signature"]["oldest_nine_all_near_the_turn_count"]
        and row["store_signature"]["rest_delivered_about_once"]
    ]
    return {
        "runs_scanned": len(rows),
        "runs_whose_ranking_replays_exactly": len(replayed),
        "runs_that_lock_onto_the_oldest_episodes": len(locked),
        "runs_carrying_the_store_signature": len(signature),
        "runs_carrying_the_signature_without_a_replay": sorted(
            row["run_dir"] for row in signature
            if not row.get("replay_identical")
        ),
        "runs_that_do_not_replay": [
            row["run_dir"] for row in rows if not row.get("replay_identical")
        ],
        "rows": rows,
    }


def build_report() -> dict:
    runs = [
        load_run(
            "arm_s_full",
            ARM_S_FULL,
            "src/memory/stm_retrieval_engine.py::StmRetrievalEngine",
            PROBE_TURNS,
        ),
        load_run(
            "arm_s_ablation",
            ARM_S_ABLATION,
            "src/memory/stm_retrieval_engine.py::StmRetrievalEngine",
        ),
        load_run(
            "arm_l_full",
            ARM_L_FULL,
            "src/memory/retrieval_engine.py::RetrievalEngine",
            PROBE_TURNS,
        ),
    ]
    analyses = [analyze_run(run) for run in runs]
    return {
        "what_this_measures": (
            "The N tier as it behaved in the runs that produced Study "
            "009's S-L contrast, replayed from the carried engine's "
            "ordering rule and checked against the committed logs."
        ),
        "what_this_does_not_measure": (
            "What a correctly-implemented recency window would have "
            "scored. No arm here ran one, and nothing in this file "
            "licenses a claim about that in either direction."
        ),
        "shared_key_probe": shared_key_probe(),
        "generality_scan": generality_scan(),
        "runs": analyses,
    }


def write_report(output_path: Path) -> dict:
    report = build_report()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
