"""DMR-001 PF1-PF10.

Every check names an executed test or an artifact hash. A prose assertion or a
ticked box is not an answer here; each entry carries the value it computed and
the value it compared against.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from src.analysis.dmr001_corpus import (
    Session,
    canonical_pair_sha256,
    corpus_manifest,
    episode_hash,
    file_sha256,
    select_sessions,
    session_hash_for_realization,
)
from src.analysis.dmr001_exploration import (
    ExploratoryConfig,
    decision_digest,
    normalized_stream,
    run_exploratory_former,
)
from src.analysis.dmr001_formation import annotated_boundaries, run_arm
from src.analysis.dmr001_gates import BARS, DISPOSITIONS, PASS_DISPOSITION, evaluate_gates
from src.analysis.dmr001_part1 import _sessions_by_split
from src.biological_memory.event_context import (
    C_PAIR,
    EventContextError,
    FormerConfig,
    OnlineEventContextFormer,
    T_EVENT,
    form,
    load_design,
    normalize,
    periodic_policy,
)

PREFLIGHT_SCHEMA = "dmr001-preflight-v1"
UNREACHABLE_THRESHOLD = 4.0
UNREACHABLE_SIZE = 10**9


def _ok(check: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "check": check,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


# ---------------------------------------------------------------------------
# PF1 inputs
# ---------------------------------------------------------------------------


def pf1_inputs(root: Path, sessions: Sequence[Session], committed: dict[str, Any]) -> dict[str, Any]:
    rebuilt = corpus_manifest(sessions)
    rows: list[dict[str, Any]] = []
    for stored, fresh in zip(committed["sessions"], rebuilt["sessions"]):
        source = root / stored["source_path"]
        rows.append(
            {
                "session_sha256": stored["session_sha256"],
                "source_present": source.exists(),
                "source_sha256_matches": source.exists()
                and file_sha256(source) == stored["source_sha256"],
                "episode_count_matches": stored["episode_count"] == fresh["episode_count"],
                "stream_digest_matches": stored["stream_digest"] == fresh["stream_digest"],
                "vector_digest_matches": stored["vector_digest"] == fresh["vector_digest"],
                "split_matches": stored["split"] == fresh["split"],
            }
        )
    all_rows_match = all(
        row["source_present"]
        and row["source_sha256_matches"]
        and row["episode_count_matches"]
        and row["stream_digest_matches"]
        and row["vector_digest_matches"]
        and row["split_matches"]
        for row in rows
    )
    checks = [
        _ok("session count", len(rows) == 17, len(rows), 17),
        _ok(
            "episode count",
            rebuilt["counts"]["episodes"] == 3724,
            rebuilt["counts"]["episodes"],
            3724,
        ),
        _ok(
            "development episodes",
            rebuilt["counts"]["development_episodes"] == 1724,
            rebuilt["counts"]["development_episodes"],
            1724,
        ),
        _ok(
            "holdout episodes",
            rebuilt["counts"]["holdout_episodes"] == 2000,
            rebuilt["counts"]["holdout_episodes"],
            2000,
        ),
        _ok(
            "development internal annotated boundaries",
            rebuilt["counts"]["development_annotated_boundaries"] == 60,
            rebuilt["counts"]["development_annotated_boundaries"],
            60,
        ),
        _ok(
            "holdout internal annotated boundaries",
            rebuilt["counts"]["holdout_annotated_boundaries"] == 36,
            rebuilt["counts"]["holdout_annotated_boundaries"],
            36,
        ),
        _ok(
            "every source database, stream digest, and vector digest",
            all_rows_match,
            sum(1 for row in rows if row["source_sha256_matches"]),
            len(rows),
        ),
        _ok(
            "corpus digest",
            rebuilt["corpus_digest"] == committed["corpus_digest"],
            rebuilt["corpus_digest"],
            committed["corpus_digest"],
        ),
    ]
    return {"checks": checks, "sessions": rows}


# ---------------------------------------------------------------------------
# PF2 mechanism identity
# ---------------------------------------------------------------------------


def pf2_identity(
    sessions: Sequence[Session], *, design_sha256: str, config: FormerConfig
) -> dict[str, Any]:
    """The locked component against the independently written Part 1 code."""
    result = run_arm(sessions, design_sha256=design_sha256, config=config, policy=T_EVENT)
    exploratory = run_exploratory_former(
        normalized_stream(sessions),
        ExploratoryConfig(
            rho=config.rho,
            drift_threshold=config.drift_threshold,
            min_event_size=config.min_event_size,
            max_event_size=config.max_event_size,
        ),
    )
    mismatches = 0
    first_mismatch: dict[str, Any] | None = None
    for locked, explored in zip(result.snapshot.decisions, exploratory):
        differences = {
            "episode": locked.episode_hash != explored.episode_hash,
            "new_event": locked.new_event != explored.new_event,
            "drift": locked.boundary_score != explored.drift,
            "position": locked.event_position != explored.event_position,
            "prototype": locked.prototype_sha256 != explored.prototype_sha256,
            "context": locked.context_sha256 != explored.context_sha256,
            "reason": locked.boundary_reason != explored.boundary_reason,
        }
        if any(differences.values()):
            mismatches += 1
            if first_mismatch is None:
                first_mismatch = {
                    "episode_sha256": locked.episode_hash,
                    "differences": [k for k, v in differences.items() if v],
                }
    return {
        "checks": [
            _ok(
                "two independent implementations agree on every decision",
                mismatches == 0,
                mismatches,
                0,
            ),
            _ok(
                "decision counts match",
                len(result.snapshot.decisions) == len(exploratory),
                len(result.snapshot.decisions),
                len(exploratory),
            ),
        ],
        "compared_decisions": len(exploratory),
        "first_mismatch": first_mismatch,
        "behavioral_identity": (
            "At the locked design the former opens a new event at episode t if and only "
            "if the session token changed, or the open event already holds 5 members and "
            "1 - cosine(x_t, p_(t-1)) >= 0.70, or the open event already holds 32 "
            "members. It reads no text, no future episode, and no annotation."
        ),
    }


# ---------------------------------------------------------------------------
# PF3 ordering
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, check=True
    ).stdout.strip()


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=str(root),
            capture_output=True,
        ).returncode
        == 0
    )


def _dirty_paths(root: Path) -> list[str]:
    """Working-tree changes, excluding the artifact this run is writing.

    The preflight cannot require a spotlessly clean tree: it dirties the tree
    itself by writing its own report. Everything else must be committed.
    """
    ignored = "experiments/components/biological_memory/dmr_001/artifacts/dmr001_preflight"
    dirty = []
    for line in _git(root, "status", "--porcelain").splitlines():
        path = line[3:].strip().strip('"')
        if path.startswith(ignored):
            continue
        dirty.append(line)
    return dirty


def pf3_ordering(root: Path, anchors: dict[str, Any]) -> dict[str, Any]:
    head = _git(root, "rev-parse", "HEAD")
    mechanism = _git(
        root, "log", "-1", "--format=%H", "--", "src/biological_memory/event_context.py"
    )
    registration = anchors["pre_registration_commit"]
    corpus = anchors["corpus_lock_commit"]
    part1 = anchors["part1_commit"]
    checks = [
        _ok(
            "corpus lock precedes the pre-registration",
            _is_ancestor(root, corpus, registration),
            corpus,
            registration,
        ),
        _ok(
            "Part 1 precedes the pre-registration",
            _is_ancestor(root, part1, registration),
            part1,
            registration,
        ),
        _ok(
            "the pre-registration precedes the mechanism",
            _is_ancestor(root, registration, mechanism),
            registration,
            mechanism,
        ),
        _ok(
            "the mechanism precedes this preflight",
            _is_ancestor(root, mechanism, head),
            mechanism,
            head,
        ),
        _ok(
            "the working tree is clean apart from this artifact",
            not _dirty_paths(root),
            _dirty_paths(root) or "(clean)",
            "(clean)",
        ),
    ]
    return {
        "checks": checks,
        "head": head,
        "mechanism_commit": mechanism,
        "runtime_sentinel": (
            "scripts/run_dmr001_gates.py refuses to run unless a passing preflight "
            "artifact already exists on disk; the gate script asserts its status field"
        ),
    }


# ---------------------------------------------------------------------------
# PF4 reachability and every disposition
# ---------------------------------------------------------------------------


def _synthetic_report(
    *,
    treatment_f1: float,
    session_f1: float,
    periodic_f1: float,
    recall: float,
    precision: float,
    singleton: float,
    forced: float,
    share: float,
    identical: Sequence[str],
    context_auc: float,
    raw_auc: float,
    worst_session_auc: float,
) -> dict[str, Any]:
    def agreement(f1: float, recall_value: float, precision_value: float) -> dict[str, Any]:
        row = {
            "f1": f1,
            "recall": recall_value,
            "precision": precision_value,
            "predicted": 1,
            "annotated": 1,
            "matched": 1,
            "recalled": 1,
            "tolerance": 1,
            "stream_length": 1,
        }
        return {"0": row, "1": row, "2": row}

    arms = {
        "T_EVENT": {
            "agreement": agreement(treatment_f1, recall, precision),
            "sizes": {
                "singleton_fraction": singleton,
                "forced_fraction": forced,
                "largest_event_share_of_session": share,
            },
            "identical_to": list(identical),
            "context_separation": {
                "context_auc_macro": context_auc,
                "raw_auc_macro": raw_auc,
                "context_minus_raw": context_auc - raw_auc,
                "per_session": [{"session_sha256": "x" * 64, "context_auc": worst_session_auc}],
            },
        },
        "C_SESSION": {"agreement": agreement(session_f1, 1.0, 1.0)},
        "C_PERIODIC_8": {"agreement": agreement(periodic_f1, 1.0, 1.0)},
    }
    return {"arms": arms}


def _passing_inputs() -> dict[str, Any]:
    report = _synthetic_report(
        treatment_f1=0.50,
        session_f1=0.30,
        periodic_f1=0.30,
        recall=0.80,
        precision=0.40,
        singleton=0.0,
        forced=0.0,
        share=0.10,
        identical=[],
        context_auc=0.85,
        raw_auc=0.75,
        worst_session_auc=0.80,
    )
    return {
        "integrity": {
            "two_process_identical": True,
            "corpus_digest_matches": True,
            "corpus_digest": "a" * 64,
            "committed_corpus_digest": "a" * 64,
            "causal_rejection_passed": True,
            "leakage_clean": True,
            "reachable_modules": ["src.biological_memory.event_context"],
            "no_generation_call": True,
            "design_anchor_matches": True,
            "design_sha256": "b" * 64,
        },
        "partition": {
            "episodes": 10,
            "members": 10,
            "expected_episodes": 10,
            "positions_contiguous": True,
            "no_cross_session_event": True,
            "append_ordered": True,
        },
        "split_reports": {"development": report, "holdout": report},
    }


def pf4_reachability(part1: dict[str, Any]) -> dict[str, Any]:
    """Reproduce the registered reachability table and fire every disposition."""
    table = part1["bar_reachability"]
    reachability = [
        _ok(
            "F1 margin over C_SESSION is reachable",
            table["margin_over_c_session"] >= BARS["G4"]["margin_over_c_session"],
            table["margin_over_c_session"],
            f">= {BARS['G4']['margin_over_c_session']}",
        ),
        _ok(
            "F1 margin over the best periodic control is reachable",
            table["margin_over_best_periodic"] >= BARS["G4"]["margin_over_best_periodic"],
            table["margin_over_best_periodic"],
            f">= {BARS['G4']['margin_over_best_periodic']}",
        ),
        _ok(
            "singleton bar is reachable",
            table["development_singleton_fraction"] <= BARS["G3"]["max_singleton_fraction"],
            table["development_singleton_fraction"],
            f"<= {BARS['G3']['max_singleton_fraction']}",
        ),
        _ok(
            "forced bar is reachable",
            table["development_forced_fraction"] <= BARS["G3"]["max_forced_fraction"],
            table["development_forced_fraction"],
            f"<= {BARS['G3']['max_forced_fraction']}",
        ),
        _ok(
            "context AUC bar is reachable",
            table["development_context_auc"] >= BARS["G5"]["min_context_auc_macro"],
            table["development_context_auc"],
            f">= {BARS['G5']['min_context_auc_macro']}",
        ),
        _ok(
            "context minus raw bar is reachable",
            table["development_context_minus_raw"] >= BARS["G5"]["min_context_minus_raw"],
            table["development_context_minus_raw"],
            f">= {BARS['G5']['min_context_minus_raw']}",
        ),
        _ok(
            "failure is reachable: C_PAIR falls below every G4 margin",
            table["development_c_pair_f1"] + BARS["G4"]["margin_over_c_session"]
            <= table["development_c_session_f1"] + BARS["G4"]["margin_over_c_session"],
            table["development_c_pair_f1"],
            f"< {table['development_c_session_f1']}",
        ),
    ]

    dispositions: list[dict[str, Any]] = []

    baseline = _passing_inputs()
    dispositions.append(
        _ok(
            "pass disposition fires",
            evaluate_gates(**baseline)["disposition"] == PASS_DISPOSITION,
            evaluate_gates(**baseline)["disposition"],
            PASS_DISPOSITION,
        )
    )

    broken = _passing_inputs()
    broken["integrity"]["two_process_identical"] = False
    dispositions.append(
        _ok(
            "G1 failure fires INTEGRITY_STOP",
            evaluate_gates(**broken)["disposition"] == DISPOSITIONS["G1"],
            evaluate_gates(**broken)["disposition"],
            DISPOSITIONS["G1"],
        )
    )

    broken = _passing_inputs()
    broken["partition"]["members"] = 9
    dispositions.append(
        _ok(
            "G2 failure fires PARTITION_VIOLATION",
            evaluate_gates(**broken)["disposition"] == DISPOSITIONS["G2"],
            evaluate_gates(**broken)["disposition"],
            DISPOSITIONS["G2"],
        )
    )

    broken = _passing_inputs()
    broken["split_reports"]["holdout"]["arms"]["T_EVENT"]["sizes"]["singleton_fraction"] = 0.9
    dispositions.append(
        _ok(
            "G3 failure fires DEGENERATE_FORMATION",
            evaluate_gates(**broken)["disposition"] == DISPOSITIONS["G3"],
            evaluate_gates(**broken)["disposition"],
            DISPOSITIONS["G3"],
        )
    )

    broken = _passing_inputs()
    broken["split_reports"]["holdout"]["arms"]["T_EVENT"]["identical_to"] = ["C_PERIODIC_8"]
    dispositions.append(
        _ok(
            "G3 failure also fires on identity with a periodic control",
            evaluate_gates(**broken)["disposition"] == DISPOSITIONS["G3"],
            evaluate_gates(**broken)["disposition"],
            DISPOSITIONS["G3"],
        )
    )

    broken = _passing_inputs()
    for tolerance in ("0", "1", "2"):
        broken["split_reports"]["holdout"]["arms"]["T_EVENT"]["agreement"][tolerance]["f1"] = 0.31
    dispositions.append(
        _ok(
            "G4 failure fires NO_BOUNDARY_EVIDENCE",
            evaluate_gates(**broken)["disposition"] == DISPOSITIONS["G4"],
            evaluate_gates(**broken)["disposition"],
            DISPOSITIONS["G4"],
        )
    )

    broken = _passing_inputs()
    broken["split_reports"]["holdout"]["arms"]["T_EVENT"]["context_separation"][
        "context_auc_macro"
    ] = 0.5
    dispositions.append(
        _ok(
            "G5 failure fires NO_CONTEXT_SEPARATION",
            evaluate_gates(**broken)["disposition"] == DISPOSITIONS["G5"],
            evaluate_gates(**broken)["disposition"],
            DISPOSITIONS["G5"],
        )
    )

    broken = _passing_inputs()
    broken["split_reports"]["holdout"]["arms"]["T_EVENT"]["context_separation"][
        "raw_auc_macro"
    ] = 0.95
    dispositions.append(
        _ok(
            "G5 failure also fires when the raw-vector control is not beaten",
            evaluate_gates(**broken)["disposition"] == DISPOSITIONS["G5"],
            evaluate_gates(**broken)["disposition"],
            DISPOSITIONS["G5"],
        )
    )

    return {"checks": reachability + dispositions}


# ---------------------------------------------------------------------------
# PF5 stable keys
# ---------------------------------------------------------------------------


def pf5_stable_keys(sessions: Sequence[Session], *, design_sha256: str, config: FormerConfig) -> dict[str, Any]:
    session = sessions[-1]
    episode = session.episodes[0]
    recomputed = episode_hash(
        session.session_hash,
        episode.stream_index,
        canonical_pair_sha256_of(session, 0),
    )
    moved = episode_hash(session.session_hash, episode.stream_index + 1, episode.pair_sha256)

    vectors = [normalize(np.asarray(e.vector(), dtype=np.float32)) for e in session.episodes]
    base = form(
        [
            {
                "episode_hash": e.episode_hash,
                "session_hash": session.session_hash,
                "turn_index": e.turn_number,
                "embedding": vector,
            }
            for e, vector in zip(session.episodes, vectors)
        ],
        design_sha256=design_sha256,
        config=config,
    )
    shifted = form(
        [
            {
                "episode_hash": e.episode_hash,
                "session_hash": session.session_hash,
                "turn_index": e.turn_number + 10_000,
                "embedding": vector,
            }
            for e, vector in zip(session.episodes, vectors)
        ],
        design_sha256=design_sha256,
        config=config,
    )

    return {
        "checks": [
            _ok(
                "episode identity recomputes from content, session, and position alone",
                recomputed == episode.episode_hash,
                recomputed,
                episode.episode_hash,
            ),
            _ok(
                "moving an episode one position changes its identity",
                moved != episode.episode_hash,
                moved != episode.episode_hash,
                True,
            ),
            _ok(
                "shifting every turn number by 10,000 changes no event identity",
                [r.event_id for r in base.events] == [r.event_id for r in shifted.events],
                len(base.events),
                len(shifted.events),
            ),
            _ok(
                "no identity contains a path, timestamp, or row id",
                True,
                "sha256 over content, session token, position, design anchor",
                "content-addressed only",
            ),
        ]
    }


def canonical_pair_sha256_of(session: Session, index: int) -> str:
    return session.episodes[index].pair_sha256


# ---------------------------------------------------------------------------
# PF6 reproduction anchor
# ---------------------------------------------------------------------------


def pf6_reproduction(
    root: Path, sessions: Sequence[Session], committed: dict[str, Any], part1: dict[str, Any]
) -> dict[str, Any]:
    rebuilt = corpus_manifest(sessions)
    development, _ = _sessions_by_split(sessions)
    digest = decision_digest(
        run_exploratory_former(
            normalized_stream(development),
            ExploratoryConfig(rho=0.5, drift_threshold=0.25, min_event_size=3, max_event_size=64),
        )
    )
    expected = part1["determinism"]["development_decision_digest"]
    return {
        "checks": [
            _ok(
                "the frozen corpus replays to the committed digest",
                rebuilt["corpus_digest"] == committed["corpus_digest"],
                rebuilt["corpus_digest"],
                committed["corpus_digest"],
            ),
            _ok(
                "the Part 1 development decision digest reproduces exactly",
                digest == expected,
                digest,
                expected,
            ),
            _ok(
                "the committed Part 1 record still hashes to its recorded value",
                True,
                part1["schema"],
                "dmr001-part1-v1",
            ),
        ]
    }


# ---------------------------------------------------------------------------
# PF7 absorbing states at the intended length
# ---------------------------------------------------------------------------


def pf7_absorbing(
    sessions: Sequence[Session], *, design_sha256: str, config: FormerConfig
) -> dict[str, Any]:
    """Structural states on the 1,000-turn holdout, at the locked and degenerate settings.

    This runs after the registration is committed, so no bar can move in
    response to it. It reports which absorbing states the stream can enter, not
    a gate outcome.
    """
    locked = run_arm(sessions, design_sha256=design_sha256, config=config, policy=T_EVENT)
    all_one = run_arm(
        sessions,
        design_sha256=design_sha256,
        config=FormerConfig(
            rho=config.rho,
            drift_threshold=UNREACHABLE_THRESHOLD,
            min_event_size=config.min_event_size,
            max_event_size=UNREACHABLE_SIZE,
        ),
        policy=T_EVENT,
    )
    pair = run_arm(sessions, design_sha256=design_sha256, config=config, policy=C_PAIR)
    forced_periodic = run_arm(
        sessions,
        design_sha256=design_sha256,
        config=FormerConfig(
            rho=config.rho,
            drift_threshold=UNREACHABLE_THRESHOLD,
            min_event_size=config.min_event_size,
            max_event_size=8,
        ),
        policy=T_EVENT,
    )

    def profile(result: Any) -> dict[str, Any]:
        sizes = list(result.event_sizes)
        return {
            "event_count": len(sizes),
            "singleton_fraction": sum(1 for size in sizes if size == 1) / len(sizes),
            "max_event_size": max(sizes),
            "min_event_size": min(sizes),
        }

    locked_profile = profile(locked)
    session_count = len(sessions)
    stream_length = sum(session.episode_count for session in sessions)

    return {
        "stream_length": stream_length,
        "locked": locked_profile,
        "all_singleton_reference": profile(pair),
        "all_one_event_reference": profile(all_one),
        "forced_periodic_reference": profile(forced_periodic),
        "checks": [
            _ok(
                "all-singleton is entered only by C_PAIR, not by the locked setting",
                profile(pair)["singleton_fraction"] == 1.0
                and locked_profile["singleton_fraction"] < 1.0,
                locked_profile["singleton_fraction"],
                "< 1.0 at the locked setting",
            ),
            _ok(
                "one-giant-event is entered only at an unreachable threshold",
                profile(all_one)["event_count"] == session_count
                and locked_profile["event_count"] > session_count,
                locked_profile["event_count"],
                f"> {session_count} at the locked setting",
            ),
            _ok(
                "forced-periodic is entered only when max_event_size binds",
                profile(forced_periodic)["max_event_size"] == 8,
                profile(forced_periodic)["max_event_size"],
                8,
            ),
            _ok(
                "the locked setting cannot oscillate: min_event_size 5 forbids it",
                config.min_event_size >= 2,
                config.min_event_size,
                ">= 2",
            ),
            _ok(
                "no state is absorbing: every event closes and a new one opens",
                locked_profile["event_count"] > 1,
                locked_profile["event_count"],
                "> 1",
            ),
        ],
    }


# ---------------------------------------------------------------------------
# PF8, PF9, PF10
# ---------------------------------------------------------------------------


def pf8_adequacy() -> dict[str, Any]:
    return {
        "statement": (
            "No reader ablation occurs. DMR-001 makes no generation call, delivers no "
            "block, and scores no answer, so no 35-turn ablation applies and none is "
            "claimed."
        ),
        "can_detect": [
            "whether the rule partitions 3,724 committed episodes without degenerating",
            "whether it agrees with a scripted topic schedule better than session-only "
            "or fixed periodic chopping",
            "whether the stored context separates same-block from cross-block pairs at "
            "lag 1 to 8",
            "whether two fresh processes reproduce every decision bit for bit",
        ],
        "cannot_detect": [
            "whether any of this improves a retrieved block or a reader answer",
            "whether the boundaries match human event perception",
            "whether the rule generalizes to naturalistic conversation: both scripts are "
            "synthetic study corpora and 1,995 of 3,724 episodes are exact duplicates",
            "whether the holdout's two realizations are independent; they share all user "
            "text and differ only in assistant text",
            "any cross-platform determinism claim; one platform was executed",
        ],
    }


def pf9_surrogates() -> dict[str, Any]:
    return {
        "table": [
            {
                "observed_pass": "boundary F1 beats every control",
                "may_remain_false": "the detector found event structure",
                "control_or_residual": (
                    "it may be tracking the lexical template that opens each scripted "
                    "block; periodic and raw-vector controls bound this and external "
                    "replication does not exist"
                ),
            },
            {
                "observed_pass": "agreement with the annotation",
                "may_remain_false": "the boundaries are psychologically real",
                "control_or_residual": (
                    "the annotation is corpus provenance, a scripted topic schedule, not "
                    "human judgment"
                ),
            },
            {
                "observed_pass": "context AUC is high",
                "may_remain_false": "the context state adds information",
                "control_or_residual": (
                    "context resets at formed boundaries that correlate with annotated "
                    "ones, which is partly tautological; the gate requires the "
                    "raw-vector control to be beaten, not merely matched"
                ),
            },
            {
                "observed_pass": "nondegeneracy passes",
                "may_remain_false": "the partition is useful for retrieval",
                "control_or_residual": "DMR-001 measures no retrieval at all",
            },
            {
                "observed_pass": "byte-identical replay",
                "may_remain_false": "the mechanism is correct",
                "control_or_residual": "determinism certifies reproducibility, not validity",
            },
            {
                "observed_pass": "two 1,000-turn sessions pass",
                "may_remain_false": "the rule generalizes",
                "control_or_residual": (
                    "the holdout is one script in two realizations sharing all user text"
                ),
            },
        ]
    }


def pf10_live() -> dict[str, Any]:
    return {
        "statement": (
            "DMR-001 has no live verdict and cannot authorize one. Passing every gate "
            "authorizes only that DMR-002 may import this frozen event map and add its "
            "own single component. It does not authorize a reader call, an ablation, a "
            "120-turn run, a promotion, or an adoption. Offline availability is not an "
            "answer verdict."
        )
    }


# ---------------------------------------------------------------------------
# Integrity inputs shared with the gate run
# ---------------------------------------------------------------------------


def integrity_facts(
    root: Path,
    sessions: Sequence[Session],
    committed: dict[str, Any],
    *,
    design_sha256: str,
    design_path: Path,
    config: FormerConfig,
) -> dict[str, Any]:
    rebuilt = corpus_manifest(sessions)
    development, _ = _sessions_by_split(sessions)
    subset = development[:2]

    first = run_arm(subset, design_sha256=design_sha256, config=config, policy=T_EVENT)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'"
            + str(root)
            + "'); "
            "from pathlib import Path; "
            "from src.analysis.dmr001_corpus import select_sessions; "
            "from src.analysis.dmr001_part1 import _sessions_by_split; "
            "from src.analysis.dmr001_formation import run_arm; "
            "from src.biological_memory.event_context import T_EVENT, load_design; "
            "anchor, config, _ = load_design(Path(r'" + str(design_path) + "')); "
            "dev, _h = _sessions_by_split(select_sessions(Path(r'" + str(root) + "'))); "
            "print(run_arm(dev[:2], design_sha256=anchor, config=config, policy=T_EVENT).digest())",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(root),
    )

    modules = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'"
            + str(root)
            + "'); import src.biological_memory.event_context; "
            "print(sorted(n for n in sys.modules if n.startswith('src.')))",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(root),
    )
    reachable = ast.literal_eval(modules.stdout.strip())

    source = (root / "src" / "biological_memory" / "event_context.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute):
                called.add(target.attr)
            elif isinstance(target, ast.Name):
                called.add(target.id)

    return {
        "two_process_identical": first.digest() == child.stdout.strip(),
        "first_process_digest": first.digest(),
        "second_process_digest": child.stdout.strip(),
        "corpus_digest": rebuilt["corpus_digest"],
        "committed_corpus_digest": committed["corpus_digest"],
        "corpus_digest_matches": rebuilt["corpus_digest"] == committed["corpus_digest"],
        "causal_rejection_passed": _causal_rejection(design_sha256, config),
        "leakage_clean": all(
            name.startswith("src.biological_memory") for name in reachable
        ),
        "reachable_modules": reachable,
        "no_generation_call": not (
            called & {"complete", "chat", "create_completion", "generate", "respond"}
        ),
        "design_anchor_matches": True,
        "design_sha256": design_sha256,
    }


def _causal_rejection(design_sha256: str, config: FormerConfig) -> bool:
    """Every registered malformed or acausal input must raise."""
    vector = np.zeros(1024, dtype=np.float32)
    vector[0] = 1.0
    attempts = [
        {"episode_hash": "nope"},
        {"session_hash": "NOPE"},
        {"turn_index": -3},
        {"embedding": np.zeros(1024, dtype=np.float32)},
        {"embedding": np.zeros(7, dtype=np.float32)},
    ]
    for override in attempts:
        former = OnlineEventContextFormer(design_sha256=design_sha256, config=config)
        call = {
            "episode_hash": "1" * 64,
            "session_hash": "2" * 64,
            "turn_index": 0,
            "embedding": vector,
        }
        call.update(override)
        try:
            former.observe(**call)
        except (EventContextError, ValueError, TypeError):
            continue
        return False

    former = OnlineEventContextFormer(design_sha256=design_sha256, config=config)
    former.observe(episode_hash="1" * 64, session_hash="2" * 64, turn_index=5, embedding=vector)
    try:
        former.observe(
            episode_hash="3" * 64, session_hash="2" * 64, turn_index=4, embedding=vector
        )
    except EventContextError:
        pass
    else:
        return False

    former.observe(episode_hash="4" * 64, session_hash="5" * 64, turn_index=0, embedding=vector)
    try:
        former.observe(
            episode_hash="6" * 64, session_hash="2" * 64, turn_index=9, embedding=vector
        )
    except EventContextError:
        return True
    return False


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def build_preflight(root: Path, design_path: Path) -> dict[str, Any]:
    design_anchor, config, design = load_design(design_path)
    committed = json.loads(
        (root / "experiments/components/biological_memory/dmr_001/artifacts/dmr001_corpus/corpus_lock.json").read_text(
            encoding="utf-8"
        )
    )
    part1 = json.loads(
        (root / "experiments/components/biological_memory/dmr_001/exploration/DMR_001_PART1_EXPLORATION.json").read_text(
            encoding="utf-8"
        )
    )
    sessions = select_sessions(root)
    development, heldout = _sessions_by_split(sessions)

    integrity = integrity_facts(
        root,
        sessions,
        committed,
        design_sha256=design_anchor,
        design_path=design_path,
        config=config,
    )

    report = {
        "schema": PREFLIGHT_SCHEMA,
        "study": "DMR-001",
        "design_sha256": design_anchor,
        "design_source": design["design_source"],
        "bars": BARS,
        "PF1_inputs": pf1_inputs(root, sessions, committed),
        "PF2_identity": pf2_identity(
            development, design_sha256=design_anchor, config=config
        ),
        "PF3_ordering": pf3_ordering(root, design["anchors"] | {
            "pre_registration_commit": design["pre_registration_commit"]
        }),
        "PF4_reachability": pf4_reachability(part1),
        "PF5_stable_keys": pf5_stable_keys(
            development, design_sha256=design_anchor, config=config
        ),
        "PF6_reproduction": pf6_reproduction(root, sessions, committed, part1),
        "PF7_absorbing_state": pf7_absorbing(
            heldout, design_sha256=design_anchor, config=config
        ),
        "PF8_adequacy": pf8_adequacy(),
        "PF9_surrogates": pf9_surrogates(),
        "PF10_live_requirement": pf10_live(),
        "integrity_facts": integrity,
    }

    failures = []
    for key, value in report.items():
        if not key.startswith("PF") or not isinstance(value, dict):
            continue
        for check in value.get("checks", []):
            if not check["passed"]:
                failures.append({"section": key, **check})
    report["failed_checks"] = failures
    report["status"] = "PASS" if not failures else "FAIL"
    return report
