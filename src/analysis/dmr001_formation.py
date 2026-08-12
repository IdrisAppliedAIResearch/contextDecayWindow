"""DMR-001 formation runs and measurement.

Runs every registered arm through the locked component over a corpus split and
computes the measures the pre-registration names. Nothing here selects a
parameter; the design is already locked and its anchor is checked before a
formation run starts.
"""

from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from src.analysis.dmr001_corpus import Session
from src.analysis.dmr001_exploration import boundary_agreement, distribution
from src.biological_memory.event_context import (
    BoundaryPolicy,
    C_ALL,
    C_PAIR,
    C_SESSION,
    EventContextSnapshot,
    FormerConfig,
    OnlineEventContextFormer,
    T_EVENT,
    dot,
    periodic_policy,
)

PERIODIC_PERIODS = (2, 4, 8, 16, 32, 64)
TOLERANCES = (0, 1, 2)


def registered_arms() -> list[BoundaryPolicy]:
    return [
        T_EVENT,
        C_SESSION,
        C_ALL,
        C_PAIR,
        *[periodic_policy(period) for period in PERIODIC_PERIODS],
    ]


@dataclass(frozen=True)
class ArmResult:
    policy: str
    snapshot: EventContextSnapshot
    contexts: tuple[np.ndarray, ...]
    boundary_indices: tuple[int, ...]
    event_sizes: tuple[int, ...]
    session_of_event: tuple[str, ...]

    def digest(self) -> str:
        return self.snapshot.digest()


def run_arm(
    sessions: Sequence[Session],
    *,
    design_sha256: str,
    config: FormerConfig,
    policy: BoundaryPolicy,
) -> ArmResult:
    former = OnlineEventContextFormer(
        design_sha256=design_sha256, config=config, policy=policy
    )
    contexts: list[np.ndarray] = []
    for session in sessions:
        for episode in session.episodes:
            former.observe(
                episode_hash=episode.episode_hash,
                session_hash=session.session_hash,
                turn_index=episode.turn_number,
                embedding=episode.vector(),
            )
            contexts.append(former.context_vector())
    snapshot = former.snapshot()
    return ArmResult(
        policy=policy.name,
        snapshot=snapshot,
        contexts=tuple(contexts),
        boundary_indices=tuple(
            index for index, decision in enumerate(snapshot.decisions) if decision.new_event
        ),
        event_sizes=tuple(record.member_count for record in snapshot.events),
        session_of_event=tuple(record.session_hash for record in snapshot.events),
    )


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------


def annotated_boundaries(sessions: Sequence[Session]) -> set[int]:
    """Stream indices that open an annotated block, session starts included."""
    indices: set[int] = set()
    offset = 0
    for session in sessions:
        indices.add(offset)
        for local in session.annotated_boundaries():
            indices.add(offset + local)
        offset += session.episode_count
    return indices


# ---------------------------------------------------------------------------
# Measures
# ---------------------------------------------------------------------------


def agreement_report(result: ArmResult, annotated: set[int], length: int) -> dict[str, Any]:
    return {
        str(tolerance): boundary_agreement(
            set(result.boundary_indices),
            annotated,
            tolerance=tolerance,
            stream_length=length,
        )
        for tolerance in TOLERANCES
    }


def size_report(result: ArmResult, sessions: Sequence[Session]) -> dict[str, Any]:
    sizes = list(result.event_sizes)
    per_session_total: dict[str, int] = {
        session.session_hash: session.episode_count for session in sessions
    }
    largest_share = 0.0
    for record in result.snapshot.events:
        total = per_session_total[record.session_hash]
        largest_share = max(largest_share, record.member_count / total)
    reasons: dict[str, int] = {}
    for decision in result.snapshot.decisions:
        if decision.new_event:
            reasons[decision.boundary_reason] = reasons.get(decision.boundary_reason, 0) + 1
    return {
        "event_count": len(sizes),
        "distribution": distribution([float(size) for size in sizes]),
        "singleton_fraction": sum(1 for size in sizes if size == 1) / len(sizes),
        "forced_fraction": reasons.get("forced", 0) / len(sizes),
        "drift_fraction": reasons.get("drift", 0) / len(sizes),
        "hard_fraction": reasons.get("hard", 0) / len(sizes),
        "largest_event_share_of_session": largest_share,
        "open_reasons": dict(sorted(reasons.items())),
    }


def context_separation(
    result: ArmResult,
    sessions: Sequence[Session],
    *,
    lag_max: int,
) -> dict[str, Any]:
    """Within-block versus across-boundary similarity of the stored contexts.

    The raw normalized episode vectors give the control. A context state that
    only matches the vectors it is built from has added nothing.
    """
    context_aucs: list[float] = []
    raw_aucs: list[float] = []
    per_session: list[dict[str, Any]] = []
    offset = 0
    raw = _raw_vectors(sessions)

    for session in sessions:
        annotated = set(session.annotated_boundaries())
        within_ctx: list[float] = []
        across_ctx: list[float] = []
        within_raw: list[float] = []
        across_raw: list[float] = []
        for i in range(session.episode_count):
            for j in range(i + 1, min(i + lag_max + 1, session.episode_count)):
                crossed = any(boundary in annotated for boundary in range(i + 1, j + 1))
                context_value = dot(result.contexts[offset + i], result.contexts[offset + j])
                raw_value = dot(raw[offset + i], raw[offset + j])
                (across_ctx if crossed else within_ctx).append(context_value)
                (across_raw if crossed else within_raw).append(raw_value)
        if within_ctx and across_ctx:
            context_auc = _auc(within_ctx, across_ctx)
            raw_auc = _auc(within_raw, across_raw)
            context_aucs.append(context_auc)
            raw_aucs.append(raw_auc)
            per_session.append(
                {
                    "session_sha256": session.session_hash,
                    "context_auc": context_auc,
                    "raw_auc": raw_auc,
                    "within_pairs": len(within_ctx),
                    "across_pairs": len(across_ctx),
                }
            )
        offset += session.episode_count

    return {
        "lag_max": lag_max,
        "sessions_scored": len(context_aucs),
        "context_auc_macro": statistics.fmean(context_aucs) if context_aucs else float("nan"),
        "raw_auc_macro": statistics.fmean(raw_aucs) if raw_aucs else float("nan"),
        "context_minus_raw": (
            statistics.fmean(context_aucs) - statistics.fmean(raw_aucs)
            if context_aucs
            else float("nan")
        ),
        "context_auc_min_session": min(context_aucs) if context_aucs else float("nan"),
        "per_session": per_session,
    }


def _raw_vectors(sessions: Sequence[Session]) -> list[np.ndarray]:
    from src.biological_memory.event_context import normalize

    vectors: list[np.ndarray] = []
    for session in sessions:
        for episode in session.episodes:
            vectors.append(normalize(np.asarray(episode.vector(), dtype=np.float32)))
    return vectors


def _auc(within: Sequence[float], across: Sequence[float]) -> float:
    ordered = sorted(across)
    total = 0.0
    for value in within:
        lower = _bisect_left(ordered, value)
        upper = _bisect_right(ordered, value)
        total += lower + 0.5 * (upper - lower)
    return total / (len(within) * len(across))


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
# Split runner
# ---------------------------------------------------------------------------


def run_split(
    sessions: Sequence[Session],
    *,
    design_sha256: str,
    config: FormerConfig,
    lag_max: int,
) -> dict[str, Any]:
    annotated = annotated_boundaries(sessions)
    length = sum(session.episode_count for session in sessions)
    arms: dict[str, Any] = {}
    results: dict[str, ArmResult] = {}

    for policy in registered_arms():
        result = run_arm(
            sessions, design_sha256=design_sha256, config=config, policy=policy
        )
        results[policy.name] = result
        arms[policy.name] = {
            "policy": policy.name,
            "kind": policy.kind,
            "period": policy.period,
            "snapshot_digest": result.digest(),
            "agreement": agreement_report(result, annotated, length),
            "sizes": size_report(result, sessions),
            "boundary_count": len(result.boundary_indices),
        }

    treatment = results["T_EVENT"]
    arms["T_EVENT"]["context_separation"] = context_separation(
        treatment, sessions, lag_max=lag_max
    )
    arms["T_EVENT"]["identical_to"] = sorted(
        name
        for name, result in results.items()
        if name != "T_EVENT"
        and set(result.boundary_indices) == set(treatment.boundary_indices)
    )
    arms["T_EVENT"]["boundary_set_digest"] = hashlib.sha256(
        ",".join(str(index) for index in treatment.boundary_indices).encode("utf-8")
    ).hexdigest()

    return {
        "episodes": length,
        "sessions": len(sessions),
        "annotated_boundaries": len(annotated),
        "annotated_internal_boundaries": len(annotated) - len(sessions),
        "arms": arms,
    }
