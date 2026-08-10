"""Study 011 section 4.1: derive T's achievable ceiling offline.

The registration requires T to be measured before it is locked, and
measured from committed candidates rather than assumed. This module does
that and nothing else. It selects no threshold; it reports the ceiling
and the evidence, so that a value chosen later can be checked against
what is reachable.

Three facts drive the derivation, and all three are read from artifacts:

1. The thirteen rubric questions occupy **nine** probe windows, not
   thirteen. Q3 and Q12 share turn 114, Q6 and Q9 share 117, Q7 and Q10
   share 118, and Q13 is a compliance check spanning turns 112-120 with
   no window of its own. Questions sharing a turn share one retrieval
   window exactly, so a per-question count double-counts them.
2. A K episode can only reach a window if the window has a K candidate.
   Turns 118 and 119 have none at K = 0.48, so no packing order delivers
   K there, and no threshold can require it.
3. Reaching the window also means fitting in it. The ceiling is measured
   by packing each arm at the registered 32,000-character budget with
   the committed post-DR-001 renderer, not by counting candidates.

**The proxy limitation is the honest part.** Study 011's arms are live
runs whose stores do not exist yet. The only committed candidate
evidence is the corrected Tier 6 run's context log, and that run's store
was built under recency-first packing at a 60,595-character budget. Arm
B in particular has no recency window at all, so its store will diverge
from turn 1 and its candidates will not be these. Candidate *identity*
does not depend on the budget -- thresholding happens before packing --
so the ceiling transfers as a bound on this store. It is not a
prediction about Arm B's store. Section 9's registered risk covers the
case where the measured ceiling is low.

No model call, no embedding call, no vector recomputation. The packer is
IC-001's, imported unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from src.analysis.ic001_internal_packing import ModelCallGuard
from src.internal_packing.ic001 import (
    IC001Error,
    TierState,
    build_tier_state,
    pack_arm,
    path_accounting,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
PRE_REGISTRATION = STUDY_ROOT / "pre_registration.md"
RUN_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
)
CONTEXT_LOG = RUN_ROOT / "logs" / "context_match.jsonl"
DATABASE = RUN_ROOT / "study.db"
SETTINGS_LOCK = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "settings"
    / "tier6_corrected_121_settings_lock.json"
)
SCRIPT = REPO_ROOT / "experiments" / "study_005" / "script.json"
MEASUREMENT_SOURCE = Path(__file__).resolve()
MECHANISM_SOURCE = REPO_ROOT / "src" / "internal_packing" / "ic001.py"

BUDGET_CHARS = 32_000
EXPECTED_K_THRESHOLD = 0.48
EXPECTED_N_CAP = 32
SEED = 5005

# Rubric question to probe turn. Read from `experiments/study_002/
# rubric_filled.md`, which defines the arc instrument and is carried
# unchanged through Study 010. Measurement may use the rubric; mechanism
# may not, and nothing below is imported by mechanism code.
QUESTION_TURNS: dict[str, int] = {
    "Q1": 112,
    "Q2": 113,
    "Q3": 114,
    "Q4": 115,
    "Q5": 116,
    "Q6": 117,
    "Q7": 118,
    "Q8": 119,
    "Q9": 117,
    "Q10": 118,
    "Q11": 120,
    "Q12": 114,
}
# Q13 scores rule compliance across turns 112-120. It has no window of
# its own and cannot carry a delivery threshold.
SPANNING_QUESTIONS: dict[str, tuple[int, int]] = {"Q13": (112, 120)}
PROBE_TURNS: tuple[int, ...] = tuple(sorted(set(QUESTION_TURNS.values())))

# Study 011 arm -> (recency enabled, K enabled, IC-001 packing order key).
ARMS: dict[str, tuple[bool, bool, str]] = {
    "A": (True, False, "B0"),
    "B": (False, True, "B1"),
    "C": (True, True, "B1"),
    "D": (True, True, "B0"),
}
ARM_LABEL = {
    "A": "STM only (N = 32, K disabled)",
    "B": "LTM only (recency disabled, K = 0.48)",
    "C": "both, K-first",
    "D": "both, recency-first (deployed)",
}


class AchievabilityError(RuntimeError):
    """Raised when the derivation cannot be trusted."""


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------


def load_episodes() -> dict[str, dict]:
    connection = sqlite3.connect(
        f"file:{DATABASE.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                episodes.id,
                episodes.turn_number,
                episodes.user_message,
                episodes.assistant_message,
                COALESCE(episodes.ground_truth_domain, '') AS ground_truth_domain
            FROM episodes
            ORDER BY episodes.turn_number ASC, episodes.id ASC
            """
        ).fetchall()
    finally:
        connection.close()
    return {str(row["id"]): dict(row) for row in rows}


def load_context_records() -> dict[int, dict]:
    records = {}
    for line in CONTEXT_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        records[int(row["turn_number"])] = row
    return records


def assert_source_configuration(records: dict[int, dict]) -> dict:
    """Fail loudly if the source run is not the configuration we think.

    A ceiling measured on the wrong run is worse than no ceiling: it
    would look like evidence.
    """

    settings = json.loads(SETTINGS_LOCK.read_text(encoding="utf-8"))
    selected = settings["selected_settings"]
    if selected["k_threshold"] != EXPECTED_K_THRESHOLD:
        raise AchievabilityError(
            f"source run K threshold is {selected['k_threshold']}, "
            f"expected {EXPECTED_K_THRESHOLD}"
        )
    if selected["n_cap"] != EXPECTED_N_CAP:
        raise AchievabilityError(
            f"source run N cap is {selected['n_cap']}, expected {EXPECTED_N_CAP}"
        )
    missing = [turn for turn in PROBE_TURNS if turn not in records]
    if missing:
        raise AchievabilityError(f"probe turns absent from the context log: {missing}")
    thresholds = {records[turn]["k_threshold"] for turn in PROBE_TURNS}
    if thresholds != {EXPECTED_K_THRESHOLD}:
        raise AchievabilityError(
            f"context log K thresholds at the probes are {sorted(thresholds)}"
        )
    return {
        "n_cap": selected["n_cap"],
        "k_threshold": selected["k_threshold"],
        "source_payload_budget": selected["payload_budget"],
        "study_011_budget_chars": BUDGET_CHARS,
        "budget_differs_from_source": selected["payload_budget"] != BUDGET_CHARS,
        "candidate_order": settings["widening_rule"]["candidate_order"],
    }


def assert_probe_map() -> dict:
    """Check the question-to-turn map against the committed script."""

    script = json.loads(SCRIPT.read_text(encoding="utf-8"))
    rubric_turns = set(script["rubric_turns"])
    mapped = set(QUESTION_TURNS.values())
    unknown = sorted(mapped - rubric_turns)
    if unknown:
        raise AchievabilityError(
            f"probe turns not among the script's rubric turns: {unknown}"
        )
    span = SPANNING_QUESTIONS["Q13"]
    return {
        "script_rubric_turns": sorted(rubric_turns),
        "probe_windows": list(PROBE_TURNS),
        "probe_window_count": len(PROBE_TURNS),
        "rubric_question_count": len(QUESTION_TURNS) + len(SPANNING_QUESTIONS),
        "questions_sharing_a_window": {
            str(turn): sorted(
                question
                for question, mapped_turn in QUESTION_TURNS.items()
                if mapped_turn == turn
            )
            for turn in PROBE_TURNS
            if sum(1 for value in QUESTION_TURNS.values() if value == turn) > 1
        },
        "spanning_questions": {"Q13": {"turns": list(range(span[0], span[1] + 1))}},
        "note": (
            "Thirteen questions occupy nine windows. Questions sharing a "
            "turn share one retrieval window exactly, so a per-question "
            "threshold counts them more than once. Q13 has no window."
        ),
    }


# --------------------------------------------------------------------------
# Derivation
# --------------------------------------------------------------------------


def _state_for_arm(
    *,
    arm: str,
    record: dict,
    by_id: dict[str, dict],
) -> TierState:
    recency_on, k_on, _order = ARMS[arm]
    return build_tier_state(
        probe_turn=int(record["turn_number"]),
        n_candidate_ids=list(record["n_candidate_ids"]) if recency_on else [],
        k_candidate_ids=list(record["k_candidate_ids"]) if k_on else [],
        by_id=by_id,
    )


def window_row(
    *,
    turn: int,
    record: dict,
    by_id: dict[str, dict],
) -> dict:
    recency_ids = set(record["n_candidate_ids"])
    k_ids = list(record["k_candidate_ids"])
    k_only_ids = [identifier for identifier in k_ids if identifier not in recency_ids]

    row: dict = {
        "probe_turn": turn,
        "questions": sorted(
            question
            for question, mapped in QUESTION_TURNS.items()
            if mapped == turn
        ),
        "k_candidate_count": len(k_ids),
        "k_only_candidate_count": len(k_only_ids),
        "n_candidate_count": len(record["n_candidate_ids"]),
        "arms": {},
    }

    for arm in ARMS:
        _recency_on, _k_on, order = ARMS[arm]
        state = _state_for_arm(arm=arm, record=record, by_id=by_id)
        packed = pack_arm(state, arm=order, budget=BUDGET_CHARS)
        accounting = path_accounting(state, packed)
        delivered = set(packed.selected_ids)
        # An episode that is also a recency candidate renders in
        # recent_context, so it is not material the K tier added. The
        # K-only count is what "the similarity tier reached the window"
        # can honestly mean.
        k_delivered = [
            identifier for identifier in k_ids if identifier in delivered
        ]
        k_only_delivered = [
            identifier for identifier in k_only_ids if identifier in delivered
        ]
        row["arms"][arm] = {
            "order": order,
            "episodes_delivered": len(packed.selected_ids),
            "episodes_by_path": accounting["episodes_by_path"],
            "serialized_chars": packed.serialized_chars,
            "k_delivered_count": len(k_delivered),
            "k_only_delivered_count": len(k_only_delivered),
            "k_reaches_window": bool(k_only_delivered),
            "recency_delivered_count": accounting["episodes_by_path"]["recency"],
            "dropped_count": len(packed.dropped_ids),
        }
    return row


def derive(records: dict[int, dict], by_id: dict[str, dict]) -> dict:
    rows = [
        window_row(turn=turn, record=records[turn], by_id=by_id)
        for turn in PROBE_TURNS
    ]

    ceilings = {}
    for arm in ARMS:
        reached = [row["probe_turn"] for row in rows if row["arms"][arm]["k_reaches_window"]]
        any_k = [
            row["probe_turn"]
            for row in rows
            if row["arms"][arm]["k_delivered_count"] > 0
        ]
        # The registration states T as a count out of thirteen probes, so
        # the ceiling is reported in those units too. Questions sharing a
        # window move together by construction and Q13 never counts, so
        # the question count is a re-expression of the window count, not
        # an independent measurement.
        questions_reached = sorted(
            question
            for question, turn in QUESTION_TURNS.items()
            if turn in reached
        )
        ceilings[arm] = {
            "label": ARM_LABEL[arm],
            "windows_with_k_only_delivery": reached,
            "windows_with_any_k_delivery": any_k,
            "ceiling_k_only": len(reached),
            "ceiling_any_k": len(any_k),
            "window_total": len(rows),
            "questions_reached": questions_reached,
            "ceiling_k_only_questions": len(questions_reached),
            "question_total": len(QUESTION_TURNS) + len(SPANNING_QUESTIONS),
        }

    impossible = [
        row["probe_turn"] for row in rows if row["k_candidate_count"] == 0
    ]
    return {
        "rows": rows,
        "ceilings": ceilings,
        "windows_without_any_k_candidate": impossible,
        "binding_ceiling": {
            "definition": (
                "T counts probe windows at which the similarity tier "
                "delivers an episode the recency tier would not have "
                "delivered anyway. Arm C under K-first is the arm G3 "
                "constrains, so its K-only ceiling binds."
            ),
            "arm_c_k_only_ceiling": ceilings["C"]["ceiling_k_only"],
            "arm_b_any_k_ceiling": ceilings["B"]["ceiling_any_k"],
            "window_total": len(rows),
            "arm_c_k_only_ceiling_questions": ceilings["C"][
                "ceiling_k_only_questions"
            ],
            "question_total": len(QUESTION_TURNS) + len(SPANNING_QUESTIONS),
            "questions_that_can_never_count": sorted(
                [
                    question
                    for question, turn in QUESTION_TURNS.items()
                    if turn in [row["probe_turn"] for row in rows if row["k_candidate_count"] == 0]
                ]
                + list(SPANNING_QUESTIONS)
            ),
        },
        "t_is_not_set_here": (
            "This module measures the ceiling. It does not choose T. A "
            "value must be registered separately and must not exceed the "
            "ceiling recorded above."
        ),
    }


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------


def _provider_model_loaded() -> bool:
    provider = sys.modules.get("src.embeddings.provider")
    return provider is not None and getattr(provider, "_MODEL", None) is not None


def run(output_root: Path) -> dict:
    inputs = _hash_paths(_input_paths())

    # Whether a model is resident in the process is a fact about the
    # process, not about this run. Under the runner it is never loaded;
    # inside a test session another test may have left one behind. What
    # this derivation must certify is that *it* did not load or call one,
    # so the before/after pair is the property, not the after alone.
    loaded_before = _provider_model_loaded()

    with ModelCallGuard() as guard:
        records = load_context_records()
        by_id = load_episodes()
        configuration = assert_source_configuration(records)
        probe_map = assert_probe_map()
        derivation = derive(records, by_id)
        audit = guard.audit()

    # IC-001's audit couples its own amendment gate into the status; this
    # study has no amendment, so the call-count facts are what apply.
    loaded_after = _provider_model_loaded()
    call_free = (
        not audit["attempted_calls"]
        and loaded_after == loaded_before
        and bool(audit["guarded_entry_points"])
    )
    audit = {
        **audit,
        "status": "PASS" if call_free else "FAIL",
        "amendment_001": "not applicable to Study 011",
        "embedding_provider_model_loaded_before": loaded_before,
        "embedding_provider_model_loaded_after": loaded_after,
        "this_run_loaded_a_model": loaded_after and not loaded_before,
    }
    if not call_free:
        raise AchievabilityError(f"model or embedding call attempted: {audit}")

    output_dir = output_root / "achievability"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "status": "COMPLETE",
        "study": "011",
        "section": "4.1",
        "purpose": "achievable ceiling for T, measured before T is locked",
        "budget_chars": BUDGET_CHARS,
        "source_run": _repo_relative(RUN_ROOT),
        "source_configuration": configuration,
        "probe_map": probe_map,
        **derivation,
        "proxy_limitation": (
            "Measured on the corrected Tier 6 run's committed candidates. "
            "Study 011's arms are live runs whose stores do not exist yet; "
            "Arm B has no recency window and will diverge from turn 1. "
            "Candidate identity does not depend on the packing budget, so "
            "this bounds the ceiling on this store. It does not predict "
            "Arm B's store."
        ),
    }

    _write_json(output_dir / "achievability.json", result)
    _write_csv(
        output_dir / "k_availability.csv",
        [
            {
                "probe_turn": row["probe_turn"],
                "questions": " ".join(row["questions"]),
                "k_candidate_count": row["k_candidate_count"],
                "k_only_candidate_count": row["k_only_candidate_count"],
                "arm_b_k_delivered": row["arms"]["B"]["k_delivered_count"],
                "arm_c_k_only_delivered": row["arms"]["C"]["k_only_delivered_count"],
                "arm_d_k_only_delivered": row["arms"]["D"]["k_only_delivered_count"],
                "arm_c_serialized_chars": row["arms"]["C"]["serialized_chars"],
                "arm_d_serialized_chars": row["arms"]["D"]["serialized_chars"],
            }
            for row in derivation["rows"]
        ],
        (
            "probe_turn",
            "questions",
            "k_candidate_count",
            "k_only_candidate_count",
            "arm_b_k_delivered",
            "arm_c_k_only_delivered",
            "arm_d_k_only_delivered",
            "arm_c_serialized_chars",
            "arm_d_serialized_chars",
        ),
    )
    _write_json(output_dir / "no_model_call_audit.json", audit)
    _write_json(output_dir / "run_header.json", _run_header(inputs, result))
    _write_artifact_manifest(output_dir)
    return result


def _run_header(inputs: dict[str, str], result: dict) -> dict:
    return {
        "study": "011",
        "artifact": "section 4.1 achievability derivation",
        "pre_registration_sha256": _sha256(PRE_REGISTRATION),
        "design_commit": _git("rev-list", "-1", "HEAD", "--", str(PRE_REGISTRATION)),
        "execution_commit": _git("rev-parse", "HEAD"),
        "source_worktree_clean": not _git(
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            "src",
            "scripts",
            "tests",
            "episodic",
            str(PRE_REGISTRATION),
        ),
        "seed": SEED,
        "budget_chars": BUDGET_CHARS,
        "input_sha256": inputs,
        "packer": "src/internal_packing/ic001.py, imported unchanged",
        "model_calls": 0,
        "embedding_calls": 0,
        "ceilings": result["ceilings"],
    }


def _input_paths() -> list[Path]:
    return [
        DATABASE,
        CONTEXT_LOG,
        SETTINGS_LOCK,
        SCRIPT,
        MECHANISM_SOURCE,
        MEASUREMENT_SOURCE,
        PRE_REGISTRATION,
    ]


def _hash_paths(paths: Iterable[Path]) -> dict[str, str]:
    return {_repo_relative(path): _sha256(path) for path in sorted(paths)}


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_csv(path: Path, rows: Iterable[dict], fields: tuple[str, ...]) -> None:
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fields),
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_artifact_manifest(output_dir: Path) -> None:
    paths = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    _write_json(
        output_dir / "artifact_manifest.json",
        {
            "status": "COMPLETE",
            "artifacts": {
                path.relative_to(output_dir).as_posix(): _sha256(path)
                for path in paths
            },
        },
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=STUDY_ROOT / "gates",
        help="directory that receives the achievability/ output",
    )
    args = parser.parse_args(argv)
    try:
        result = run(args.output_root)
    except (AchievabilityError, IC001Error) as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1
    ceilings = result["ceilings"]
    print(f"probe windows: {result['probe_map']['probe_window_count']}")
    print(f"no K candidate at: {result['windows_without_any_k_candidate']}")
    for arm, values in ceilings.items():
        print(
            f"arm {arm} ({values['label']}): "
            f"K-only ceiling {values['ceiling_k_only']}/{values['window_total']} windows"
            f" = {values['ceiling_k_only_questions']}/{values['question_total']} questions, "
            f"any-K ceiling {values['ceiling_any_k']}/{values['window_total']} windows"
        )
    binding = result["binding_ceiling"]
    print(
        "questions that can never count: "
        f"{binding['questions_that_can_never_count']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
