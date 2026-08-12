"""DMR-001 post-stop characterization.

DMR-001 stopped at G3. Nothing here changes a bar, a parameter, or the
disposition; it describes what the failed partition actually did so the arc
records why the mechanism failed rather than only that it did.

Every number in this module is descriptive and post-stop. None of it may be
cited as a gate result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from src.analysis.dmr001_corpus import Session, select_sessions
from src.analysis.dmr001_exploration import distribution
from src.analysis.dmr001_formation import annotated_boundaries, run_arm
from src.analysis.dmr001_part1 import _sessions_by_split
from src.biological_memory.event_context import FormerConfig, T_EVENT, load_design

POSTSTOP_SCHEMA = "dmr001-poststop-v1"


def matched_by_reason(
    sessions: Sequence[Session],
    *,
    design_sha256: str,
    config: FormerConfig,
    tolerance: int,
) -> dict[str, Any]:
    """Which predicate produced the boundaries that actually matched?

    A partition can agree with the annotation for two very different reasons:
    the drift detector found the transition, or a fixed size cap happened to
    land near one. Splitting the matches by predicate separates them.
    """
    result = run_arm(sessions, design_sha256=design_sha256, config=config, policy=T_EVENT)
    annotated = sorted(annotated_boundaries(sessions))
    predicted = [
        (index, decision.boundary_reason)
        for index, decision in enumerate(result.snapshot.decisions)
        if decision.new_event
    ]

    used: set[int] = set()
    matched: dict[str, int] = {}
    total: dict[str, int] = {}
    for index, reason in predicted:
        total[reason] = total.get(reason, 0) + 1
        for candidate in annotated:
            if candidate in used:
                continue
            if abs(candidate - index) <= tolerance:
                used.add(candidate)
                matched[reason] = matched.get(reason, 0) + 1
                break

    return {
        "tolerance": tolerance,
        "predicted_by_reason": dict(sorted(total.items())),
        "matched_by_reason": dict(sorted(matched.items())),
        "precision_by_reason": {
            reason: matched.get(reason, 0) / count for reason, count in sorted(total.items())
        },
        "annotated": len(annotated),
        "recalled": len(used),
        "share_of_matches_from_drift": (
            matched.get("drift", 0) / len(used) if used else float("nan")
        ),
        "share_of_boundaries_from_forced": (
            total.get("forced", 0) / len(predicted) if predicted else float("nan")
        ),
    }


def drift_profile(
    sessions: Sequence[Session], *, design_sha256: str, config: FormerConfig
) -> dict[str, Any]:
    """How often the drift predicate could fire at all on this split."""
    result = run_arm(sessions, design_sha256=design_sha256, config=config, policy=T_EVENT)
    drifts = [decision.boundary_score for decision in result.snapshot.decisions]
    eligible = [
        decision.boundary_score
        for decision in result.snapshot.decisions
        if decision.open_event_size_before >= config.min_event_size
    ]
    above = [value for value in eligible if value >= config.drift_threshold]
    # Drift is measured against the open event's prototype, not the previous
    # episode, so a repeated episode inside a mixed event does NOT give zero
    # drift. This counts near-zero drift against the prototype and must not be
    # read as a count of duplicate episode text.
    near_zero = [value for value in drifts if value < 1e-6]
    return {
        "drift_distribution": distribution(drifts),
        "episodes": len(drifts),
        "eligible_for_drift_predicate": len(eligible),
        "eligible_above_threshold": len(above),
        "eligible_above_threshold_fraction": len(above) / len(eligible) if eligible else 0.0,
        "near_zero_drift_against_prototype": len(near_zero),
        "near_zero_drift_fraction": len(near_zero) / len(drifts),
    }


def build_poststop(root: Path, design_path: Path, gate_path: Path) -> dict[str, Any]:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate["verdict"]["passed"]:
        raise RuntimeError("Post-stop characterization applies only to a stopped study")

    design_anchor, config, design = load_design(design_path)
    tolerance = int(design["parameters"]["boundary_tolerance"])
    sessions = select_sessions(root)
    development, heldout = _sessions_by_split(sessions)

    splits = {}
    for name, split in (("development", development), ("holdout", heldout)):
        splits[name] = {
            "matches": matched_by_reason(
                split, design_sha256=design_anchor, config=config, tolerance=tolerance
            ),
            "drift": drift_profile(split, design_sha256=design_anchor, config=config),
        }

    short_sessions = [
        {
            "session_sha256": session.session_hash,
            "episode_count": session.episode_count,
            "max_share_a_single_event_could_avoid": min(
                1.0, config.max_event_size / session.episode_count
            ),
        }
        for session in sessions
        if session.episode_count <= config.max_event_size * 4
    ]

    return {
        "schema": POSTSTOP_SCHEMA,
        "study": "DMR-001",
        "status": "POST_STOP_DESCRIPTIVE_ONLY",
        "disposition": gate["verdict"]["disposition"],
        "stopped_at": gate["verdict"]["stopped_at"],
        "design_sha256": design_anchor,
        "splits": splits,
        "bar_reachability_defect": {
            "bar": "G3 largest event share of its session <= 0.25",
            "problem": (
                "PF4 verified the singleton and forced-fraction bars reachable on "
                "development but never verified this one. A session shorter than four "
                "times max_event_size cannot satisfy it under any setting of the locked "
                "rule, so the bar was unreachable by construction on the shortest "
                "selected session."
            ),
            "short_sessions": short_sessions,
            "affects_disposition": False,
            "why_not": (
                "the holdout forced-fraction check fails independently at 0.703 against "
                "a bar of 0.35 that PF4 did verify reachable at 0.005, so G3 fails and "
                "the disposition is DEGENERATE_FORMATION with or without this check"
            ),
        },
    }
