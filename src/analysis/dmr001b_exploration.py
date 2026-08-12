"""DMR-001B Part 1 exploration: adaptive drift thresholds and typed cap closures.

DMR-001 stopped because an absolute drift threshold has no transferable scale:
0.70 fired on 18.5% of eligible development episodes and 1.2% of holdout
episodes, so the size cap did 70% of the partitioning. This module explores
two changes.

1. **Relative threshold.** The bar is derived from the conversation's own
   recent drift history rather than being a constant. Three rule families are
   swept; none is chosen here.
2. **Typed cap closure.** The cap still closes an event, so the partition shape
   is unchanged, but a cap closure is recorded as `capped` and is not counted
   as a boundary claim. The mechanism only claims boundaries it detected.

Both corpora were read by DMR-001, so this is diagnostic work under the arc's
invariant 7. No confirmatory claim is available and none is made.
"""

from __future__ import annotations

import hashlib
import math
import statistics
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from src.analysis.dmr001_corpus import Session
from src.analysis.dmr001_exploration import (
    boundary_agreement,
    distribution,
    exact_dot,
    normalize_f32,
    as_f32,
)

EXPLORATION_SCHEMA = "dmr001b-part1-v1"

RULE_FAMILIES = ("fixed", "percentile", "robust_z", "ratio")
CLAIMING_REASONS = frozenset({"stream_start", "hard", "adaptive"})


@dataclass(frozen=True)
class AdaptiveConfig:
    """One candidate rule. `max_event_size=None` removes the cap entirely."""

    rule: str
    param: float
    window: int
    warmup: int
    min_event_size: int
    max_event_size: int | None
    rho: float = 0.5

    def label(self) -> str:
        cap = "nocap" if self.max_event_size is None else f"cap{self.max_event_size}"
        return f"{self.rule}:{self.param:g}:w{self.window}:u{self.warmup}:{cap}"


def _percentile(ordered: Sequence[float], fraction: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def adaptive_threshold(history: Sequence[float], config: AdaptiveConfig) -> float:
    """The bar this conversation's own recent drift implies. Causal by construction."""
    if config.rule == "fixed":
        return config.param
    ordered = sorted(history)
    if config.rule == "percentile":
        return _percentile(ordered, config.param)
    if config.rule == "robust_z":
        median = _percentile(ordered, 0.5)
        deviations = sorted(abs(value - median) for value in history)
        mad = _percentile(deviations, 0.5)
        return median + config.param * mad
    if config.rule == "ratio":
        return config.param * statistics.fmean(history)
    raise ValueError(f"Unknown rule family: {config.rule}")


@dataclass(frozen=True)
class AdaptiveDecision:
    stream_index: int
    session_hash: str
    drift: float
    threshold: float
    open_event_size_before: int
    hard_boundary: bool
    adaptive_boundary: bool
    capped_boundary: bool
    new_event: bool
    boundary_reason: str
    claims_boundary: bool


def run_adaptive_former(
    episodes: Sequence[tuple[str, str, np.ndarray]],
    config: AdaptiveConfig,
) -> list[AdaptiveDecision]:
    """Replay the candidate rule over an ordered stream of normalized episodes.

    Drift history is per session and is fed by every observed drift, including
    those inside events the rule later closed. That is a feedback loop the
    fixed rule did not have: the rule's own boundaries change which drifts it
    sees. Any pre-registration of this design owes PF7 an absorbing-state proof.
    """
    decisions: list[AdaptiveDecision] = []
    current_session: str | None = None
    history: deque[float] = deque(maxlen=config.window)
    member_sum: np.ndarray | None = None
    prototype: np.ndarray | None = None
    open_size = 0

    for index, (session_hash, _identity, vector) in enumerate(episodes):
        size_before = open_size
        hard = current_session is not None and session_hash != current_session
        if hard:
            history = deque(maxlen=config.window)

        drift = 0.0 if prototype is None else 1.0 - exact_dot(vector, prototype)
        threshold = (
            adaptive_threshold(list(history), config)
            if len(history) >= config.warmup
            else float("inf")
        )
        adaptive = (
            prototype is not None
            and size_before >= config.min_event_size
            and len(history) >= config.warmup
            and drift >= threshold
        )
        capped = (
            config.max_event_size is not None
            and prototype is not None
            and size_before >= config.max_event_size
        )
        opening = prototype is None or hard or adaptive or capped

        if opening:
            reason = (
                "stream_start"
                if prototype is None
                else "hard"
                if hard
                else "adaptive"
                if adaptive
                else "capped"
            )
            member_sum = vector.copy()
            open_size = 1
            prototype = normalize_f32(member_sum)
        else:
            reason = "continue"
            assert member_sum is not None
            member_sum = member_sum + vector
            open_size += 1
            prototype = normalize_f32(member_sum / np.float32(open_size))

        if prototype is not None and not hard and index > 0:
            history.append(drift)
        current_session = session_hash

        decisions.append(
            AdaptiveDecision(
                stream_index=index,
                session_hash=session_hash,
                drift=drift,
                threshold=threshold,
                open_event_size_before=size_before,
                hard_boundary=bool(hard),
                adaptive_boundary=bool(adaptive),
                capped_boundary=bool(capped),
                new_event=bool(opening),
                boundary_reason=reason,
                claims_boundary=reason in CLAIMING_REASONS,
            )
        )
    return decisions


def event_sizes(decisions: Sequence[AdaptiveDecision]) -> list[int]:
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


def summarize(
    decisions: Sequence[AdaptiveDecision],
    annotated: set[int],
    *,
    tolerance: int,
    stream_length: int,
) -> dict[str, Any]:
    """Agreement counted two ways: claims only, and every closure.

    The claims-only figure is the honest one - it scores the mechanism on the
    boundaries it asserts. The all-closures figure is DMR-001's accounting and
    is kept so the two can be compared directly.
    """
    claims = {d.stream_index for d in decisions if d.claims_boundary}
    closures = {d.stream_index for d in decisions if d.new_event}
    sizes = event_sizes(decisions)
    reasons = Counter(d.boundary_reason for d in decisions if d.new_event)
    return {
        "event_count": len(sizes),
        "claimed_boundaries": len(claims),
        "capped_closures": reasons["capped"],
        "adaptive_boundaries": reasons["adaptive"],
        "capped_fraction_of_events": reasons["capped"] / len(sizes),
        "adaptive_fire_rate": reasons["adaptive"] / max(1, stream_length),
        "singleton_fraction": sum(1 for size in sizes if size == 1) / len(sizes),
        "size_distribution": distribution([float(size) for size in sizes]),
        "agreement_claims_only": boundary_agreement(
            claims, annotated, tolerance=tolerance, stream_length=stream_length
        ),
        "agreement_all_closures": boundary_agreement(
            closures, annotated, tolerance=tolerance, stream_length=stream_length
        ),
    }


def family_streams(sessions: Sequence[Session]) -> dict[str, list[Session]]:
    """Group the corpus by conversation family, which is its user script."""
    families: dict[str, list[Session]] = {}
    for session in sessions:
        families.setdefault(session.script_sha256, []).append(session)
    named: dict[str, list[Session]] = {}
    for script, members in families.items():
        length = members[0].episode_count
        named[f"family_{length}_{script[:8]}"] = members
    return dict(sorted(named.items()))


def normalized_stream(sessions: Sequence[Session]) -> list[tuple[str, str, np.ndarray]]:
    return [
        (session.session_hash, episode.episode_hash, normalize_f32(as_f32(episode.vector())))
        for session in sessions
        for episode in session.episodes
    ]


def annotated_boundary_indices(sessions: Sequence[Session]) -> set[int]:
    indices: set[int] = set()
    offset = 0
    for session in sessions:
        indices.add(offset)
        for local in session.annotated_boundaries():
            indices.add(offset + local)
        offset += session.episode_count
    return indices


def decision_digest(decisions: Sequence[AdaptiveDecision]) -> str:
    digest = hashlib.sha256()
    for decision in decisions:
        digest.update(
            (
                f"{decision.stream_index}|{decision.drift!r}|{decision.threshold!r}|"
                f"{decision.boundary_reason}|{int(decision.claims_boundary)}\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()
