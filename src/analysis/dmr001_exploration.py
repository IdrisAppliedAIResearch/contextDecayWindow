"""DMR-001 Part 1 exploration.

This module characterizes the proposed formation mechanism empirically before
anything is locked. It is deliberately a standalone reimplementation of the
drift and context arithmetic: after the pre-registration is committed,
`src/biological_memory/event_context.py` implements the mechanism
independently and PF2 asserts the two agree exactly on a real trace. Agreement
between two independent implementations is the evidence; a shared helper would
have made the check vacuous.

Nothing here reads an answer key, a rubric, a retrieval log, or a score.
Annotation domains are read only to describe distributions; no threshold is
selected on the holdout split.
"""

from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np

from src.analysis.dmr001_corpus import (
    EMBEDDING_DIMENSION,
    Session,
    split_of,
)

EXPLORATION_SCHEMA = "dmr001-part1-v1"


# ---------------------------------------------------------------------------
# Deterministic float32 vector arithmetic
#
# Element-wise float32 operations are exactly reproducible. Reductions are not:
# a BLAS dot product may reassociate across lanes, threads, or machines. Every
# reduction below therefore goes through math.fsum over float64 products, which
# is exactly rounded and independent of summation order, so a replay on another
# process or another machine produces the same bits.
# ---------------------------------------------------------------------------


def as_f32(values: Iterable[float]) -> np.ndarray:
    vector = np.asarray(list(values), dtype=np.float32)
    if vector.shape != (EMBEDDING_DIMENSION,):
        raise ValueError("Expected a 1024-dimensional vector")
    return vector


def exact_dot(left: np.ndarray, right: np.ndarray) -> float:
    return math.fsum(float(a) * float(b) for a, b in zip(left.tolist(), right.tolist()))


def exact_norm(vector: np.ndarray) -> float:
    return math.sqrt(exact_dot(vector, vector))


def normalize_f32(vector: np.ndarray) -> np.ndarray:
    norm = exact_norm(vector)
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("Cannot normalize a zero or non-finite vector")
    return (vector.astype(np.float64) / norm).astype(np.float32)


def vector_sha256(vector: np.ndarray) -> str:
    if vector.dtype != np.float32:
        raise ValueError("Vector hashes are defined over float32 bytes")
    return hashlib.sha256(vector.astype("<f4").tobytes()).hexdigest()


# ---------------------------------------------------------------------------
# Exploratory former
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExploratoryConfig:
    rho: float
    drift_threshold: float
    min_event_size: int
    max_event_size: int


@dataclass(frozen=True)
class ExploratoryDecision:
    stream_index: int
    session_hash: str
    episode_hash: str
    drift: float
    open_event_size_before: int
    hard_boundary: bool
    drift_boundary: bool
    forced_boundary: bool
    new_event: bool
    event_ordinal: int
    event_position: int
    boundary_reason: str
    prototype_sha256: str
    context_sha256: str


def run_exploratory_former(
    episodes: Sequence[tuple[str, str, np.ndarray]],
    config: ExploratoryConfig,
) -> list[ExploratoryDecision]:
    """Replay the proposed rule over an ordered stream of normalized episodes.

    `episodes` carries (session_hash, episode_hash, normalized float32 vector)
    in append order. The rule is causal: nothing after the current index is
    read.
    """
    decisions: list[ExploratoryDecision] = []
    current_session: str | None = None
    member_sum: np.ndarray | None = None
    prototype: np.ndarray | None = None
    context: np.ndarray | None = None
    open_size = 0
    event_ordinal = -1

    for index, (session_hash, identity, vector) in enumerate(episodes):
        size_before = open_size
        hard = current_session is not None and session_hash != current_session
        if prototype is None:
            drift = 0.0
        else:
            drift = 1.0 - exact_dot(vector, prototype)
        drift_boundary = (
            prototype is not None
            and open_size >= config.min_event_size
            and drift >= config.drift_threshold
        )
        forced = open_size >= config.max_event_size
        new_event = bool(hard or drift_boundary or forced)
        opening = prototype is None or new_event

        if opening:
            reason = (
                "stream_start"
                if prototype is None
                else "hard"
                if hard
                else "drift"
                if drift_boundary
                else "forced"
            )
            event_ordinal += 1
            member_sum = vector.copy()
            open_size = 1
            prototype = normalize_f32(member_sum)
            context = vector.copy()
            position = 0
        else:
            reason = "continue"
            assert member_sum is not None and context is not None
            member_sum = member_sum + vector
            open_size += 1
            prototype = normalize_f32(member_sum / np.float32(open_size))
            context = normalize_f32(
                np.float32(config.rho) * context + np.float32(1.0 - config.rho) * vector
            )
            position = open_size - 1

        current_session = session_hash
        decisions.append(
            ExploratoryDecision(
                stream_index=index,
                session_hash=session_hash,
                episode_hash=identity,
                drift=drift,
                open_event_size_before=size_before,
                hard_boundary=bool(hard),
                drift_boundary=bool(drift_boundary),
                forced_boundary=bool(forced),
                new_event=bool(opening),
                event_ordinal=event_ordinal,
                event_position=position,
                boundary_reason=reason,
                prototype_sha256=vector_sha256(prototype),
                context_sha256=vector_sha256(context),
            )
        )
    return decisions


# ---------------------------------------------------------------------------
# Stream assembly
# ---------------------------------------------------------------------------


def normalized_stream(sessions: Sequence[Session]) -> list[tuple[str, str, np.ndarray]]:
    stream: list[tuple[str, str, np.ndarray]] = []
    for session in sessions:
        for episode in session.episodes:
            stream.append(
                (
                    session.session_hash,
                    episode.episode_hash,
                    normalize_f32(as_f32(episode.vector())),
                )
            )
    return stream


def annotated_boundary_indices(sessions: Sequence[Session]) -> set[int]:
    """Stream indices that open a new annotated event, session starts included."""
    indices: set[int] = set()
    offset = 0
    for session in sessions:
        indices.add(offset)
        for local in session.annotated_boundaries():
            indices.add(offset + local)
        offset += session.episode_count
    return indices


def session_start_indices(sessions: Sequence[Session]) -> set[int]:
    indices: set[int] = set()
    offset = 0
    for session in sessions:
        indices.add(offset)
        offset += session.episode_count
    return indices


# ---------------------------------------------------------------------------
# Distribution helpers
# ---------------------------------------------------------------------------


def distribution(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"count": 0}

    def percentile(fraction: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = fraction * (len(ordered) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[int(position)]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    return {
        "count": len(ordered),
        "min": ordered[0],
        "p01": percentile(0.01),
        "p05": percentile(0.05),
        "p10": percentile(0.10),
        "p25": percentile(0.25),
        "median": percentile(0.50),
        "p75": percentile(0.75),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
        "stdev": statistics.pstdev(ordered) if len(ordered) > 1 else 0.0,
        "histogram_edges": [round(edge / 20.0, 2) for edge in range(0, 21)],
        "histogram_counts": _histogram(ordered),
    }


def _histogram(ordered: Sequence[float]) -> list[int]:
    counts = [0] * 20
    for value in ordered:
        index = int(value * 20.0)
        index = max(0, min(19, index))
        counts[index] += 1
    return counts


def event_spans(decisions: Sequence[ExploratoryDecision]) -> list[int]:
    sizes: list[int] = []
    current = 0
    for decision in decisions:
        if decision.new_event:
            if current:
                sizes.append(current)
            current = 1
        else:
            current += 1
    if current:
        sizes.append(current)
    return sizes


def boundary_agreement(
    predicted: set[int],
    annotated: set[int],
    *,
    tolerance: int,
    stream_length: int,
) -> dict[str, Any]:
    """Tolerance-aware boundary precision, recall, and F1.

    A predicted boundary counts as a hit when an annotated boundary lies within
    `tolerance` stream positions, and each annotated boundary can be matched at
    most once. Counting matches greedily in stream order keeps the result
    deterministic and stops one prediction from covering several annotations.
    """
    unmatched = sorted(annotated)
    matched_predictions = 0
    used: set[int] = set()
    for index in sorted(predicted):
        candidate = None
        for annotation in unmatched:
            if annotation in used:
                continue
            if abs(annotation - index) <= tolerance:
                candidate = annotation
                break
        if candidate is not None:
            used.add(candidate)
            matched_predictions += 1
    precision = matched_predictions / len(predicted) if predicted else 0.0
    recall = len(used) / len(annotated) if annotated else 0.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if (precision + recall) > 0.0
        else 0.0
    )
    return {
        "predicted": len(predicted),
        "annotated": len(annotated),
        "matched": matched_predictions,
        "recalled": len(used),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tolerance": tolerance,
        "stream_length": stream_length,
    }


def predicted_boundaries(decisions: Sequence[ExploratoryDecision]) -> set[int]:
    return {decision.stream_index for decision in decisions if decision.new_event}


def periodic_boundaries(stream_length: int, period: int, starts: set[int]) -> set[int]:
    """Fixed periodic chopping that still respects session starts."""
    if period < 1:
        raise ValueError("Period must be positive")
    boundaries = set(starts)
    ordered_starts = sorted(starts) + [stream_length]
    for begin, end in zip(ordered_starts, ordered_starts[1:]):
        boundaries.update(range(begin + period, end, period))
    return boundaries


def decision_digest(decisions: Sequence[ExploratoryDecision]) -> str:
    digest = hashlib.sha256()
    for decision in decisions:
        digest.update(
            (
                f"{decision.stream_index}|{decision.episode_hash}|"
                f"{decision.drift!r}|{int(decision.hard_boundary)}"
                f"{int(decision.drift_boundary)}{int(decision.forced_boundary)}"
                f"|{decision.event_ordinal}|{decision.event_position}|"
                f"{decision.boundary_reason}|{decision.prototype_sha256}|"
                f"{decision.context_sha256}\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()
