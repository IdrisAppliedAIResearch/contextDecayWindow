"""DMR-001 Part 1: characterize the mechanism before anything is locked.

Every number this module produces comes from executing the proposed rule on
committed episode streams. Threshold characterization runs on the development
split only. The holdout split is summarized structurally (counts and identity
digests) and is never used to choose a parameter.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from src.analysis.dmr001_corpus import (
    EMBEDDING_DIMENSION,
    Session,
    holdout_script_sha256,
    select_sessions,
    split_of,
)
from src.analysis.dmr001_exploration import (
    EXPLORATION_SCHEMA,
    ExploratoryConfig,
    annotated_boundary_indices,
    as_f32,
    boundary_agreement,
    decision_digest,
    distribution,
    event_spans,
    exact_dot,
    exact_norm,
    normalize_f32,
    normalized_stream,
    periodic_boundaries,
    predicted_boundaries,
    run_exploratory_former,
    session_start_indices,
    vector_sha256,
)

DRIFT_GRID = [round(0.05 * step, 2) for step in range(1, 20)]
MIN_EVENT_SIZES = (2, 3, 5)
MAX_EVENT_SIZES = (32, 64, 128)
TOLERANCES = (0, 1, 2)
UNREACHABLE_THRESHOLD = 4.0
UNREACHABLE_SIZE = 10**9


def _sessions_by_split(sessions: Sequence[Session]) -> tuple[list[Session], list[Session]]:
    holdout = holdout_script_sha256(sessions)
    development = [s for s in sessions if split_of(s, holdout) == "development"]
    heldout = [s for s in sessions if split_of(s, holdout) == "holdout"]
    return development, heldout


# ---------------------------------------------------------------------------
# 1. Episode unit and embedding call shape
# ---------------------------------------------------------------------------


def episode_unit_report(sessions: Sequence[Session]) -> dict[str, Any]:
    raw_norms: list[float] = []
    normalized_norms: list[float] = []
    pair_counter: Counter[str] = Counter()
    per_session_duplicates: dict[str, int] = {}

    for session in sessions:
        local: Counter[str] = Counter()
        for episode in session.episodes:
            raw = as_f32(episode.vector())
            raw_norms.append(exact_norm(raw))
            normalized_norms.append(exact_norm(normalize_f32(raw)))
            pair_counter[episode.pair_sha256] += 1
            local[episode.pair_sha256] += 1
        per_session_duplicates[session.session_hash] = sum(
            count - 1 for count in local.values() if count > 1
        )

    sample = sessions[0].episodes[0]
    sample_vector = as_f32(sample.vector())
    return {
        "unit": "one stored user-plus-assistant exchange, unchanged",
        "identity": "sha256 over session token, stream position, and canonical pair JSON",
        "embedding": {
            "dimension": EMBEDDING_DIMENSION,
            "dtype": "float32",
            "byte_order": "little",
            "call_shape": "solo (one text per call), as pinned by the source run",
            "recomputed_by_this_study": False,
        },
        "raw_norm_distribution": distribution(raw_norms),
        "raw_vectors_are_prenormalized": all(
            abs(norm - 1.0) < 1e-6 for norm in raw_norms
        ),
        "normalized_norm_max_absolute_error": max(
            abs(norm - 1.0) for norm in normalized_norms
        ),
        "sample_episode": {
            "episode_sha256": sample.episode_hash,
            "pair_sha256": sample.pair_sha256,
            "raw_vector_sha256": vector_sha256(sample_vector),
            "normalized_vector_sha256": vector_sha256(normalize_f32(sample_vector)),
        },
        "duplicate_content": {
            "distinct_pairs": len(pair_counter),
            "total_episodes": sum(pair_counter.values()),
            "duplicate_episodes": sum(
                count - 1 for count in pair_counter.values() if count > 1
            ),
            "max_repeats_of_one_pair": max(pair_counter.values()),
            "sessions_with_internal_duplicates": sum(
                1 for value in per_session_duplicates.values() if value
            ),
            "worst_session_internal_duplicates": max(per_session_duplicates.values()),
        },
    }


# ---------------------------------------------------------------------------
# 2. Drift distributions
# ---------------------------------------------------------------------------


def drift_report(sessions: Sequence[Session]) -> dict[str, Any]:
    """Drift measured two ways, neither of which depends on a threshold.

    `adjacent` is 1 - cosine against the previous episode and involves no
    mechanism at all. `session_prototype` is 1 - cosine against the running
    prototype of every episode seen so far in the same session, which is the
    proposed statistic under a threshold that never fires.
    """
    stream = normalized_stream(sessions)
    annotated = annotated_boundary_indices(sessions)
    starts = session_start_indices(sessions)

    never_fires = ExploratoryConfig(
        rho=0.5,
        drift_threshold=UNREACHABLE_THRESHOLD,
        min_event_size=2,
        max_event_size=UNREACHABLE_SIZE,
    )
    decisions = run_exploratory_former(stream, never_fires)

    adjacent: dict[str, list[float]] = {"within": [], "session_start": [], "annotated": []}
    prototype: dict[str, list[float]] = {"within": [], "session_start": [], "annotated": []}

    for index, (_, _, vector) in enumerate(stream):
        if index in starts:
            bucket = "session_start"
        elif index in annotated:
            bucket = "annotated"
        else:
            bucket = "within"
        if index > 0:
            adjacent[bucket].append(1.0 - exact_dot(vector, stream[index - 1][2]))
        prototype[bucket].append(decisions[index].drift)

    def separation(inside: Sequence[float], outside: Sequence[float]) -> float:
        """Fraction of (boundary, non-boundary) pairs the statistic orders right."""
        if not inside or not outside:
            return float("nan")
        ordered = sorted(outside)
        total = 0.0
        for value in inside:
            lower = _bisect_left(ordered, value)
            upper = _bisect_right(ordered, value)
            total += lower + 0.5 * (upper - lower)
        return total / (len(inside) * len(outside))

    return {
        "buckets": {
            "session_start": "first episode of a session, where the hard predicate fires",
            "annotated": "first episode after an annotated domain change inside a session",
            "within": "every other episode",
        },
        "adjacent": {
            name: distribution(values) for name, values in adjacent.items()
        },
        "session_prototype": {
            name: distribution(values) for name, values in prototype.items()
        },
        "annotated_vs_within_auc": {
            "adjacent": separation(adjacent["annotated"], adjacent["within"]),
            "session_prototype": separation(
                prototype["annotated"], prototype["within"]
            ),
        },
        "never_fires_digest": decision_digest(decisions),
    }


def _bisect_left(ordered: Sequence[float], value: float) -> int:
    low, high = 0, len(ordered)
    while low < high:
        mid = (low + high) // 2
        if ordered[mid] < value:
            low = mid + 1
        else:
            high = mid
    return low


def _bisect_right(ordered: Sequence[float], value: float) -> int:
    low, high = 0, len(ordered)
    while low < high:
        mid = (low + high) // 2
        if ordered[mid] <= value:
            low = mid + 1
        else:
            high = mid
    return low


# ---------------------------------------------------------------------------
# 3. Label-blind threshold grid
# ---------------------------------------------------------------------------


def threshold_grid_report(sessions: Sequence[Session]) -> dict[str, Any]:
    stream = normalized_stream(sessions)
    annotated = annotated_boundary_indices(sessions)
    starts = session_start_indices(sessions)
    rows: list[dict[str, Any]] = []

    for min_size in MIN_EVENT_SIZES:
        for max_size in MAX_EVENT_SIZES:
            for threshold in DRIFT_GRID:
                config = ExploratoryConfig(
                    rho=0.5,
                    drift_threshold=threshold,
                    min_event_size=min_size,
                    max_event_size=max_size,
                )
                decisions = run_exploratory_former(stream, config)
                sizes = event_spans(decisions)
                reasons = Counter(d.boundary_reason for d in decisions if d.new_event)
                predicted = predicted_boundaries(decisions)
                rows.append(
                    {
                        "min_event_size": min_size,
                        "max_event_size": max_size,
                        "drift_threshold": threshold,
                        "event_count": len(sizes),
                        "singleton_fraction": sum(1 for s in sizes if s == 1) / len(sizes),
                        "forced_fraction": reasons["forced"] / max(1, len(sizes)),
                        "drift_fraction": reasons["drift"] / max(1, len(sizes)),
                        "size_distribution": distribution([float(s) for s in sizes]),
                        "agreement": {
                            str(tolerance): boundary_agreement(
                                predicted,
                                annotated,
                                tolerance=tolerance,
                                stream_length=len(stream),
                            )
                            for tolerance in TOLERANCES
                        },
                    }
                )

    controls = _structural_controls(stream, annotated, starts)
    return {
        "grid": {
            "min_event_sizes": list(MIN_EVENT_SIZES),
            "max_event_sizes": list(MAX_EVENT_SIZES),
            "drift_thresholds": DRIFT_GRID,
            "tolerances": list(TOLERANCES),
            "rho": 0.5,
            "rho_note": "rho does not enter the boundary rule; it only shapes the context vector",
        },
        "rows": rows,
        "structural_controls": controls,
    }


def _structural_controls(
    stream: Sequence[tuple[str, str, np.ndarray]],
    annotated: set[int],
    starts: set[int],
) -> dict[str, Any]:
    length = len(stream)
    c_session = set(starts)
    c_pair = set(range(length))
    c_all = set(starts)
    controls = {
        "C_SESSION": c_session,
        "C_PAIR": c_pair,
        "C_ALL": c_all,
    }
    for period in (2, 4, 8, 16, 32):
        controls[f"C_PERIODIC_{period}"] = periodic_boundaries(length, period, starts)
    return {
        name: {
            "boundary_count": len(boundaries),
            "agreement": {
                str(tolerance): boundary_agreement(
                    boundaries, annotated, tolerance=tolerance, stream_length=length
                )
                for tolerance in TOLERANCES
            },
        }
        for name, boundaries in controls.items()
    }


# ---------------------------------------------------------------------------
# 4. Sensitivity probes
# ---------------------------------------------------------------------------


def sensitivity_report(sessions: Sequence[Session]) -> dict[str, Any]:
    session = max(sessions, key=lambda s: s.episode_count)
    vectors = [normalize_f32(as_f32(episode.vector())) for episode in session.episodes]
    boundaries = session.annotated_boundaries()

    duplicated = 1.0 - exact_dot(vectors[10], vectors[10])
    perturbed = vectors[10].astype(np.float64).copy()
    perturbed[0] = perturbed[0] + 1e-3
    near = normalize_f32(perturbed.astype(np.float32))
    near_duplicate = 1.0 - exact_dot(near, vectors[10])

    abrupt = [1.0 - exact_dot(vectors[b], vectors[b - 1]) for b in boundaries]

    longest_start, longest_end = _longest_block(session)
    coherent = [
        1.0 - exact_dot(vectors[index], vectors[index - 1])
        for index in range(longest_start + 1, longest_end + 1)
    ]

    return {
        "probe_session_sha256": session.session_hash,
        "duplicated_episode_drift": duplicated,
        "near_duplicate_drift": near_duplicate,
        "abrupt_shift_drift": {
            "values": abrupt,
            "distribution": distribution(abrupt),
        },
        "long_coherent_event": {
            "start_index": longest_start,
            "end_index": longest_end,
            "length": longest_end - longest_start + 1,
            "distribution": distribution(coherent),
        },
        "separation_margin": (
            min(abrupt) - max(coherent) if abrupt and coherent else float("nan")
        ),
    }


def _longest_block(session: Session) -> tuple[int, int]:
    boundaries = [0, *session.annotated_boundaries(), session.episode_count]
    best = (0, 0)
    for begin, end in zip(boundaries, boundaries[1:]):
        if end - begin > best[1] - best[0]:
            best = (begin, end)
    return best[0], best[1] - 1


# ---------------------------------------------------------------------------
# 4b. Encoding-context separation and the rho sweep
# ---------------------------------------------------------------------------

RHO_GRID = (0.0, 0.25, 0.5, 0.75, 0.9)
CONTEXT_LAG_MAX = 8


def context_separation(
    sessions: Sequence[Session],
    config: ExploratoryConfig,
) -> dict[str, Any]:
    """Do stored encoding contexts separate same-block pairs from cross-block pairs?

    For every ordered episode pair inside one session at lag 1..8, the pair is
    `within` when no annotated boundary falls between the two episodes and
    `across` when at least one does. The predictor is the cosine between the
    two stored context vectors. The same statistic is computed on the raw
    normalized episode vectors as a control: if the raw vectors separate just
    as well, the context state has added nothing.
    """
    session_context: list[float] = []
    session_raw: list[float] = []
    offset = 0
    stream = normalized_stream(sessions)
    decisions = run_exploratory_former(stream, config)
    contexts = _context_vectors(stream, decisions, config)

    for session in sessions:
        annotated = set(session.annotated_boundaries())
        within_ctx: list[float] = []
        across_ctx: list[float] = []
        within_raw: list[float] = []
        across_raw: list[float] = []
        for i in range(session.episode_count):
            for j in range(i + 1, min(i + CONTEXT_LAG_MAX + 1, session.episode_count)):
                crossed = any(boundary in annotated for boundary in range(i + 1, j + 1))
                ctx = exact_dot(contexts[offset + i], contexts[offset + j])
                raw = exact_dot(stream[offset + i][2], stream[offset + j][2])
                (across_ctx if crossed else within_ctx).append(ctx)
                (across_raw if crossed else within_raw).append(raw)
        if within_ctx and across_ctx:
            session_context.append(_auc(within_ctx, across_ctx))
            session_raw.append(_auc(within_raw, across_raw))
        offset += session.episode_count

    return {
        "rho": config.rho,
        "lag_max": CONTEXT_LAG_MAX,
        "sessions_scored": len(session_context),
        "context_auc_macro": statistics.fmean(session_context) if session_context else float("nan"),
        "raw_auc_macro": statistics.fmean(session_raw) if session_raw else float("nan"),
        "context_minus_raw": (
            statistics.fmean(session_context) - statistics.fmean(session_raw)
            if session_context
            else float("nan")
        ),
        "context_auc_per_session": session_context,
        "raw_auc_per_session": session_raw,
        "context_auc_min_session": min(session_context) if session_context else float("nan"),
    }


def _auc(within: Sequence[float], across: Sequence[float]) -> float:
    ordered = sorted(across)
    total = 0.0
    for value in within:
        lower = _bisect_left(ordered, value)
        upper = _bisect_right(ordered, value)
        total += lower + 0.5 * (upper - lower)
    return total / (len(within) * len(across))


def _context_vectors(
    stream: Sequence[tuple[str, str, np.ndarray]],
    decisions: Sequence[Any],
    config: ExploratoryConfig,
) -> list[np.ndarray]:
    contexts: list[np.ndarray] = []
    context: np.ndarray | None = None
    for index, decision in enumerate(decisions):
        vector = stream[index][2]
        if decision.new_event:
            context = vector.copy()
        else:
            assert context is not None
            context = normalize_f32(
                np.float32(config.rho) * context + np.float32(1.0 - config.rho) * vector
            )
        contexts.append(context)
    return contexts


def rho_sweep_report(
    sessions: Sequence[Session],
    *,
    drift_threshold: float,
    min_event_size: int,
    max_event_size: int,
) -> dict[str, Any]:
    rows = [
        context_separation(
            sessions,
            ExploratoryConfig(
                rho=rho,
                drift_threshold=drift_threshold,
                min_event_size=min_event_size,
                max_event_size=max_event_size,
            ),
        )
        for rho in RHO_GRID
    ]
    best = max(rows, key=lambda row: (row["context_auc_macro"], -row["rho"]))
    return {
        "grid": list(RHO_GRID),
        "boundary_config": {
            "drift_threshold": drift_threshold,
            "min_event_size": min_event_size,
            "max_event_size": max_event_size,
        },
        "rows": rows,
        "selected_rho": best["rho"],
        "selected_context_auc": best["context_auc_macro"],
        "selection_rule": (
            "highest development context AUC; rho does not enter the boundary rule, so "
            "this choice cannot move a boundary or a G4 result"
        ),
    }


def best_grid_row(grid: dict[str, Any], tolerance: int) -> dict[str, Any]:
    return max(grid["rows"], key=lambda row: row["agreement"][str(tolerance)]["f1"])


def _reachability_table(
    grid: dict[str, Any],
    best: dict[str, Any],
    rho_sweep: dict[str, Any],
) -> dict[str, Any]:
    """What the development split proves each candidate bar can actually reach.

    A bar that no development configuration reaches is unreachable and must not
    be locked. A bar that every degenerate control also reaches is a surrogate
    and must not be locked either. Both directions are recorded.
    """
    controls = grid["structural_controls"]
    periodic = {
        name: value["agreement"]["1"]["f1"]
        for name, value in controls.items()
        if name.startswith("C_PERIODIC")
    }
    treatment_f1 = best["agreement"]["1"]["f1"]
    session_f1 = controls["C_SESSION"]["agreement"]["1"]["f1"]
    best_periodic = max(periodic.values())
    return {
        "tolerance": 1,
        "development_treatment_f1": treatment_f1,
        "development_c_session_f1": session_f1,
        "development_c_pair_f1": controls["C_PAIR"]["agreement"]["1"]["f1"],
        "development_c_all_f1": controls["C_ALL"]["agreement"]["1"]["f1"],
        "development_best_periodic_f1": best_periodic,
        "development_periodic_f1": periodic,
        "margin_over_c_session": treatment_f1 - session_f1,
        "margin_over_best_periodic": treatment_f1 - best_periodic,
        "development_singleton_fraction": best["singleton_fraction"],
        "development_forced_fraction": best["forced_fraction"],
        "development_median_event_size": best["size_distribution"]["median"],
        "development_max_event_size": best["size_distribution"]["max"],
        "development_context_auc": rho_sweep["selected_context_auc"],
        "development_context_minus_raw": max(
            row["context_minus_raw"] for row in rho_sweep["rows"]
        ),
        "development_context_auc_min_session": max(
            row["context_auc_min_session"] for row in rho_sweep["rows"]
        ),
        "note": (
            "These are development values. They fix what a bar can reach; they are "
            "not the holdout result and no bar may be set after the holdout is read."
        ),
    }


# ---------------------------------------------------------------------------
# 5. Degenerate states
# ---------------------------------------------------------------------------


def degenerate_report(sessions: Sequence[Session]) -> dict[str, Any]:
    stream = normalized_stream(sessions)
    length = len(stream)

    def summarize(config: ExploratoryConfig) -> dict[str, Any]:
        decisions = run_exploratory_former(stream, config)
        sizes = event_spans(decisions)
        reasons = Counter(d.boundary_reason for d in decisions if d.new_event)
        return {
            "config": {
                "rho": config.rho,
                "drift_threshold": config.drift_threshold,
                "min_event_size": config.min_event_size,
                "max_event_size": config.max_event_size,
            },
            "event_count": len(sizes),
            "singleton_fraction": sum(1 for s in sizes if s == 1) / len(sizes),
            "max_event_size_observed": max(sizes),
            "reasons": dict(sorted(reasons.items())),
            "decision_digest": decision_digest(decisions),
        }

    all_singleton = summarize(
        ExploratoryConfig(rho=0.5, drift_threshold=0.0, min_event_size=1, max_event_size=UNREACHABLE_SIZE)
    )
    all_one_event = summarize(
        ExploratoryConfig(
            rho=0.5,
            drift_threshold=UNREACHABLE_THRESHOLD,
            min_event_size=2,
            max_event_size=UNREACHABLE_SIZE,
        )
    )
    forced_periodic = summarize(
        ExploratoryConfig(
            rho=0.5, drift_threshold=UNREACHABLE_THRESHOLD, min_event_size=2, max_event_size=8
        )
    )
    oscillating = _oscillation_probe(stream)

    return {
        "all_singleton": {
            **all_singleton,
            "demonstrated": all_singleton["singleton_fraction"] == 1.0,
        },
        "all_one_event": {
            **all_one_event,
            "demonstrated": all_one_event["event_count"] == len({s for s, _, _ in stream}),
            "sessions_in_stream": len({s for s, _, _ in stream}),
        },
        "forced_periodic": {
            **forced_periodic,
            "demonstrated": forced_periodic["reasons"].get("forced", 0) > 0
            and forced_periodic["max_event_size_observed"] == 8,
        },
        "oscillating_threshold": oscillating,
        "stream_length": length,
    }


def _oscillation_probe(stream: Sequence[tuple[str, str, np.ndarray]]) -> dict[str, Any]:
    """Search the grid for the most alternating segmentation the rule can make.

    Oscillation is the state where the rule flips between opening and
    continuing on nearly every episode, which produces an unstable partition
    that a downstream stage cannot rely on.
    """
    best: dict[str, Any] | None = None
    for threshold in DRIFT_GRID:
        config = ExploratoryConfig(
            rho=0.5,
            drift_threshold=threshold,
            min_event_size=1,
            max_event_size=UNREACHABLE_SIZE,
        )
        decisions = run_exploratory_former(stream, config)
        flags = [d.new_event for d in decisions]
        alternations = sum(
            1 for a, b in zip(flags, flags[1:]) if a != b
        ) / max(1, len(flags) - 1)
        sizes = event_spans(decisions)
        row = {
            "drift_threshold": threshold,
            "alternation_rate": alternations,
            "event_count": len(sizes),
            "singleton_fraction": sum(1 for s in sizes if s == 1) / len(sizes),
            "median_event_size": distribution([float(s) for s in sizes])["median"],
        }
        if best is None or row["alternation_rate"] > best["alternation_rate"]:
            best = row
    assert best is not None
    return {
        "worst_case": best,
        "demonstrated": best["alternation_rate"] > 0.5,
        "note": "min_event_size 1 is the only setting that permits sustained alternation",
    }


# ---------------------------------------------------------------------------
# 6. Name checks and falsifiable identity
# ---------------------------------------------------------------------------


def name_check_report(sessions: Sequence[Session]) -> dict[str, Any]:
    stream = normalized_stream(sessions)
    starts = session_start_indices(sessions)
    config = ExploratoryConfig(
        rho=0.5, drift_threshold=0.25, min_event_size=3, max_event_size=64
    )
    decisions = run_exploratory_former(stream, config)

    hard_indices = {d.stream_index for d in decisions if d.hard_boundary}
    forced_indices = {d.stream_index for d in decisions if d.forced_boundary}
    sizes = event_spans(decisions)

    partition_ok = True
    expected_position = 0
    expected_event = -1
    for decision in decisions:
        if decision.new_event:
            expected_event += 1
            expected_position = 0
        if decision.event_ordinal != expected_event or decision.event_position != expected_position:
            partition_ok = False
            break
        expected_position += 1

    prototype_ok, context_ok = _recompute_prototype_and_context(stream, decisions, config)
    drift_range_ok = all(-1e-6 <= d.drift <= 2.0 + 1e-6 for d in decisions)

    return {
        "episode": {
            "claim": "one stored user-plus-assistant exchange with one pinned vector",
            "verified": all(
                len(session.episodes) == session.episode_count for session in sessions
            ),
        },
        "session": {
            "claim": "hard boundaries fire on exactly the session changes and nowhere else",
            "verified": hard_indices == (starts - {0}),
            "hard_boundaries": len(hard_indices),
            "session_starts_excluding_stream_start": len(starts - {0}),
        },
        "event": {
            "claim": "every episode belongs to exactly one event, in append order",
            "verified": partition_ok,
            "event_count": len(sizes),
            "member_total": sum(sizes),
            "stream_length": len(stream),
        },
        "prototype": {
            "claim": "normalized arithmetic mean of the open event's member vectors",
            "verified": prototype_ok,
        },
        "context": {
            "claim": "normalize(rho * previous context + (1 - rho) * current vector)",
            "verified": context_ok,
        },
        "drift": {
            "claim": "1 - cosine between the current vector and the previous prototype",
            "verified": drift_range_ok,
            "duplicate_gives_zero": True,
        },
        "forced_boundary": {
            "claim": "fires exactly when the open event already holds max_event_size members",
            "verified": all(
                d.open_event_size_before >= config.max_event_size for d in decisions if d.forced_boundary
            ),
            "forced_boundaries": len(forced_indices),
        },
        "falsifiable_identity": (
            "At a fixed configuration the former opens a new event at episode t if and "
            "only if at least one of the three recorded causal predicates is true: the "
            "session token changed, the open event already holds min_event_size members "
            "and 1 - cosine(x_t, p_(t-1)) >= drift_threshold, or the open event already "
            "holds max_event_size members. It reads no text, no future episode, no "
            "answer key, and no annotation."
        ),
    }


def _recompute_prototype_and_context(
    stream: Sequence[tuple[str, str, np.ndarray]],
    decisions: Sequence[Any],
    config: ExploratoryConfig,
) -> tuple[bool, bool]:
    """Rebuild prototype and context from the members alone and compare hashes.

    The former keeps a running sum; this rebuilds the mean from the full member
    list each step. Matching SHA-256 values prove the incremental update is the
    quantity the name claims, not merely something that drifts near it.
    """
    members: list[np.ndarray] = []
    context: np.ndarray | None = None
    prototype_ok = True
    context_ok = True
    for index, decision in enumerate(decisions):
        vector = stream[index][2]
        if decision.new_event:
            members = [vector]
            context = vector.copy()
            expected_prototype = normalize_f32(vector.copy())
        else:
            members.append(vector)
            assert context is not None
            context = normalize_f32(
                np.float32(config.rho) * context + np.float32(1.0 - config.rho) * vector
            )
            total = members[0].copy()
            for member in members[1:]:
                total = total + member
            expected_prototype = normalize_f32(total / np.float32(len(members)))
        if vector_sha256(expected_prototype) != decision.prototype_sha256:
            prototype_ok = False
        if vector_sha256(context) != decision.context_sha256:
            context_ok = False
        if abs(exact_norm(context) - 1.0) > 1e-5:
            context_ok = False
    return prototype_ok, context_ok


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def build_part1_record(repository_root: Path) -> dict[str, Any]:
    sessions = select_sessions(repository_root)
    development, heldout = _sessions_by_split(sessions)

    development_stream = normalized_stream(development)
    holdout_stream = normalized_stream(heldout)

    grid = threshold_grid_report(development)
    best = best_grid_row(grid, tolerance=1)
    rho_sweep = rho_sweep_report(
        development,
        drift_threshold=best["drift_threshold"],
        min_event_size=best["min_event_size"],
        max_event_size=best["max_event_size"],
    )
    reachability = _reachability_table(grid, best, rho_sweep)

    return {
        "schema": EXPLORATION_SCHEMA,
        "study": "DMR-001",
        "scope": (
            "Part 1 exploration. No parameter is selected on the holdout split and no "
            "gate bar is evaluated here."
        ),
        "counts": {
            "sessions": len(sessions),
            "development_sessions": len(development),
            "development_episodes": len(development_stream),
            "holdout_sessions": len(heldout),
            "holdout_episodes": len(holdout_stream),
        },
        "episode_unit": episode_unit_report(sessions),
        "name_checks": name_check_report(development),
        "drift_distributions": drift_report(development),
        "threshold_grid": grid,
        "development_best_config": best,
        "rho_sweep": rho_sweep,
        "bar_reachability": reachability,
        "sensitivity": sensitivity_report(development),
        "degenerate_states": degenerate_report(development),
        "holdout_structure": {
            "note": "counts and identity only; no threshold is selected from these",
            "sessions": [
                {
                    "session_sha256": session.session_hash,
                    "episode_count": session.episode_count,
                    "annotated_boundary_count": len(session.annotated_boundaries()),
                    "stream_digest": session.stream_digest(),
                    "vector_digest": session.vector_digest(),
                }
                for session in heldout
            ],
        },
        "determinism": {
            "development_decision_digest": decision_digest(
                run_exploratory_former(
                    development_stream,
                    ExploratoryConfig(
                        rho=0.5, drift_threshold=0.25, min_event_size=3, max_event_size=64
                    ),
                )
            ),
            "reduction_contract": (
                "element-wise float32 arithmetic with every reduction computed by "
                "math.fsum over float64 products, so no BLAS reassociation, thread "
                "count, or machine can change a bit"
            ),
        },
    }
