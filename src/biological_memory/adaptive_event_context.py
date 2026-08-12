"""DMR-001B adaptive event-context formation.

DMR-001 stopped at G3 because an absolute drift threshold has no transferable
scale. Its operating point moved by a factor of ten between two corpora, the
size cap took over 70% of the partitioning, and the event-size distribution
collapsed to a point mass at the cap.

This component changes two things and nothing else.

1. **The bar is relative.** A boundary opens when drift reaches a percentile of
   the conversation's own recent drift history, so the rule carries no
   corpus-specific constant.
2. **Cap closures are typed.** The cap still closes an event, so the partition
   shape is unchanged, but the closure is recorded as `capped` and does not
   count as a boundary claim. The mechanism only claims what it detected.

The float32 arithmetic, normalization, and vector hashing are imported from
DMR-001's frozen component rather than reimplemented, so a control cannot win
or lose on numerics and DMR-001's artifacts stay reproducible. Nothing in
`event_context.py` is modified.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .event_context import (
    EventContextError,
    dot,
    normalize,
    vector_bytes,
    vector_sha256,
)

STORE_SCHEMA = "dmr001b-adaptive-event-context-v1"
EVENT_ID_PREFIX = "dmr-event-v2"
VECTOR_DIMENSION = 1024
HEX_DIGITS = frozenset("0123456789abcdef")

BOUNDARY_REASONS = ("stream_start", "hard", "adaptive", "capped", "continue")
CLAIMING_REASONS = frozenset({"stream_start", "hard", "adaptive"})


class AdaptiveEventContextError(EventContextError):
    """Any violation of the DMR-001B formation contract."""


def _require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or not set(value) <= HEX_DIGITS:
        raise AdaptiveEventContextError(f"{label} must be a lowercase hex SHA-256")
    return value


def _as_vector(embedding: Any) -> np.ndarray:
    vector = np.asarray(embedding, dtype=np.float32)
    if vector.shape != (VECTOR_DIMENSION,):
        raise AdaptiveEventContextError(
            f"Embedding must have {VECTOR_DIMENSION} dimensions, got {vector.shape}"
        )
    if not np.all(np.isfinite(vector)):
        raise AdaptiveEventContextError("Embedding contains a non-finite value")
    return vector


def percentile(ordered: Sequence[float], fraction: float) -> float:
    """Linear-interpolated percentile over a pre-sorted sequence.

    Deterministic and free of any library percentile convention, so a NumPy or
    SciPy version change cannot silently move a boundary.
    """
    if not ordered:
        raise AdaptiveEventContextError("Percentile of an empty history")
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


@dataclass(frozen=True)
class AdaptiveFormerConfig:
    """The locked parameters. They live in the pre-registration and nowhere else."""

    drift_percentile: float
    history_window: int
    warmup: int
    min_event_size: int
    max_event_size: int

    def __post_init__(self) -> None:
        if not 0.0 < self.drift_percentile < 1.0:
            raise AdaptiveEventContextError("drift_percentile must lie in (0, 1)")
        if self.history_window < 2:
            raise AdaptiveEventContextError("history_window must be at least 2")
        if self.warmup < 1 or self.warmup > self.history_window:
            raise AdaptiveEventContextError("warmup must lie in [1, history_window]")
        if self.min_event_size < 1:
            raise AdaptiveEventContextError("min_event_size must be at least 1")
        if self.max_event_size < self.min_event_size:
            raise AdaptiveEventContextError("max_event_size must be at least min_event_size")

    @classmethod
    def from_design(cls, payload: Mapping[str, Any]) -> "AdaptiveFormerConfig":
        parameters = payload["parameters"]
        return cls(
            drift_percentile=float(parameters["drift_percentile"]),
            history_window=int(parameters["history_window"]),
            warmup=int(parameters["warmup"]),
            min_event_size=int(parameters["min_event_size"]),
            max_event_size=int(parameters["max_event_size"]),
        )


def design_sha256_of(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def load_design(path: Path) -> tuple[str, AdaptiveFormerConfig, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    anchor = _require_hash(payload["design_sha256"], "design_sha256")
    actual = design_sha256_of(path.parent / payload["design_source"])
    if actual != anchor:
        raise AdaptiveEventContextError(
            "Design anchor mismatch. The pre-registration on disk does not hash to the "
            f"recorded value.\n  expected: {anchor}\n  actual  : {actual}"
        )
    return anchor, AdaptiveFormerConfig.from_design(payload), payload


@dataclass(frozen=True)
class AdaptiveFormationDecision:
    episode_hash: str
    session_hash: str
    turn_index: int
    event_id: str
    event_position: int
    boundary_score: float
    boundary_threshold: float
    history_size: int
    boundary_reason: str
    claims_boundary: bool
    hard_boundary: bool
    adaptive_boundary: bool
    capped_boundary: bool
    new_event: bool
    open_event_size_before: int
    design_sha256: str
    prototype_sha256: str
    context_sha256: str


@dataclass(frozen=True)
class AdaptiveEventRecord:
    event_id: str
    design_sha256: str
    session_hash: str
    first_episode_hash: str
    start_turn: int
    end_turn: int
    member_count: int
    prototype_sha256: str
    context_sha256: str
    close_reason: str


@dataclass(frozen=True)
class AdaptiveEventMember:
    event_id: str
    episode_hash: str
    event_position: int
    boundary_score: float
    boundary_reason: str


@dataclass(frozen=True)
class AdaptiveSnapshot:
    design_sha256: str
    events: tuple[AdaptiveEventRecord, ...]
    members: tuple[AdaptiveEventMember, ...]
    decisions: tuple[AdaptiveFormationDecision, ...]

    def canonical_json(self) -> str:
        return (
            json.dumps(
                {
                    "schema": STORE_SCHEMA,
                    "design_sha256": self.design_sha256,
                    "events": [asdict(record) for record in self.events],
                    "members": [asdict(member) for member in self.members],
                    "decisions": [asdict(decision) for decision in self.decisions],
                },
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def claimed_boundaries(self) -> set[int]:
        """Only the boundaries the mechanism asserts. Cap closures are excluded."""
        return {
            index
            for index, decision in enumerate(self.decisions)
            if decision.claims_boundary
        }

    def all_closures(self) -> set[int]:
        return {
            index for index, decision in enumerate(self.decisions) if decision.new_event
        }

    def validate(self) -> dict[str, Any]:
        if len(self.members) != len(self.decisions):
            raise AdaptiveEventContextError("Member count does not match decision count")
        by_event: dict[str, list[AdaptiveEventMember]] = {}
        for member in self.members:
            by_event.setdefault(member.event_id, []).append(member)
        seen: set[str] = set()
        for record in self.events:
            members = by_event.get(record.event_id)
            if not members:
                raise AdaptiveEventContextError(f"Event has no members: {record.event_id}")
            if [m.event_position for m in members] != list(range(len(members))):
                raise AdaptiveEventContextError(
                    f"Event positions are not contiguous from zero: {record.event_id}"
                )
            if len(members) != record.member_count:
                raise AdaptiveEventContextError(f"Member count mismatch: {record.event_id}")
            if members[0].episode_hash != record.first_episode_hash:
                raise AdaptiveEventContextError(f"First member mismatch: {record.event_id}")
            for member in members:
                if member.episode_hash in seen:
                    raise AdaptiveEventContextError(
                        f"Episode belongs to more than one event: {member.episode_hash}"
                    )
                seen.add(member.episode_hash)
        if set(by_event) != {record.event_id for record in self.events}:
            raise AdaptiveEventContextError("Member table references an unknown event")
        sessions = [record.session_hash for record in self.events]
        for index in range(1, len(sessions)):
            if sessions[index] != sessions[index - 1] and sessions[index] in sessions[:index]:
                raise AdaptiveEventContextError("A session was reopened after it closed")
        return {
            "events": len(self.events),
            "members": len(self.members),
            "episodes": len(seen),
            "sessions": len(set(sessions)),
            "claimed_boundaries": len(self.claimed_boundaries()),
            "capped_closures": sum(
                1 for decision in self.decisions if decision.boundary_reason == "capped"
            ),
        }


class AdaptiveEventContextFormer:
    """Causal, deterministic, label-blind formation with a self-scaling bar."""

    def __init__(
        self,
        *,
        design_sha256: str,
        config: AdaptiveFormerConfig,
        store: "AdaptiveEventContextStore | None" = None,
    ) -> None:
        self._design_sha256 = _require_hash(design_sha256, "design_sha256")
        self._config = config
        self._store = store

        self._session: str | None = None
        self._closed_sessions: set[str] = set()
        self._last_turn: int | None = None
        self._seen_episodes: set[str] = set()
        self._history: deque[float] = deque(maxlen=config.history_window)

        self._event_id: str | None = None
        self._first_episode: str | None = None
        self._start_turn: int | None = None
        self._end_turn: int | None = None
        self._member_sum: np.ndarray | None = None
        self._prototype: np.ndarray | None = None
        self._context: np.ndarray | None = None
        self._size = 0

        self._events: list[AdaptiveEventRecord] = []
        self._members: list[AdaptiveEventMember] = []
        self._decisions: list[AdaptiveFormationDecision] = []

    # -- public contract ---------------------------------------------------

    def observe(
        self,
        *,
        episode_hash: str,
        session_hash: str,
        turn_index: int,
        embedding: Any,
    ) -> AdaptiveFormationDecision:
        identity = _require_hash(episode_hash, "episode_hash")
        session = _require_hash(session_hash, "session_hash")
        if not isinstance(turn_index, int) or isinstance(turn_index, bool):
            raise AdaptiveEventContextError("turn_index must be an int")
        if turn_index < 0:
            raise AdaptiveEventContextError("turn_index must be non-negative")
        if identity in self._seen_episodes:
            raise AdaptiveEventContextError(f"Episode observed twice in one pass: {identity}")
        if session in self._closed_sessions:
            raise AdaptiveEventContextError(f"Session was already closed: {session}")
        if self._session == session and self._last_turn is not None:
            if turn_index <= self._last_turn:
                raise AdaptiveEventContextError(
                    "Turns must arrive in strictly increasing order within a session: "
                    f"{turn_index} after {self._last_turn}"
                )

        vector = normalize(_as_vector(embedding))
        hard = self._session is not None and session != self._session
        if hard:
            # Drift scale is a property of one conversation. Carrying it across a
            # session boundary would reintroduce exactly the cross-corpus
            # transfer DMR-001 failed on.
            self._history = deque(maxlen=self._config.history_window)

        drift = 0.0 if self._prototype is None else 1.0 - dot(vector, self._prototype)
        warm = len(self._history) >= self._config.warmup
        threshold = (
            percentile(sorted(self._history), self._config.drift_percentile)
            if warm
            else math.inf
        )
        size_before = self._size
        adaptive = (
            self._prototype is not None
            and warm
            and size_before >= self._config.min_event_size
            and drift >= threshold
        )
        capped = (
            self._prototype is not None and size_before >= self._config.max_event_size
        )
        opening = self._prototype is None or hard or adaptive or capped

        if opening:
            reason = (
                "stream_start"
                if self._prototype is None
                else "hard"
                if hard
                else "adaptive"
                if adaptive
                else "capped"
            )
            if self._event_id is not None:
                self._close_open_event(reason)
            if hard and self._session is not None:
                self._closed_sessions.add(self._session)
            self._open_event(identity, session, turn_index, vector)
            position = 0
        else:
            reason = "continue"
            position = self._extend_event(vector)

        if self._prototype is not None and not hard and self._decisions:
            self._history.append(drift)

        self._session = session
        self._last_turn = turn_index
        self._end_turn = turn_index
        self._seen_episodes.add(identity)

        assert self._event_id is not None
        assert self._prototype is not None and self._context is not None
        decision = AdaptiveFormationDecision(
            episode_hash=identity,
            session_hash=session,
            turn_index=turn_index,
            event_id=self._event_id,
            event_position=position,
            boundary_score=drift,
            boundary_threshold=threshold,
            history_size=len(self._history),
            boundary_reason=reason,
            claims_boundary=reason in CLAIMING_REASONS,
            hard_boundary=bool(hard),
            adaptive_boundary=bool(adaptive),
            capped_boundary=bool(capped),
            new_event=bool(opening),
            open_event_size_before=size_before,
            design_sha256=self._design_sha256,
            prototype_sha256=vector_sha256(self._prototype),
            context_sha256=vector_sha256(self._context),
        )
        self._decisions.append(decision)
        self._members.append(
            AdaptiveEventMember(
                event_id=self._event_id,
                episode_hash=identity,
                event_position=position,
                boundary_score=drift,
                boundary_reason=reason,
            )
        )
        if self._store is not None:
            self._store.record(
                decision, self._open_record("open"), self._prototype, self._context
            )
        return decision

    def snapshot(self) -> AdaptiveSnapshot:
        events = list(self._events)
        if self._event_id is not None:
            events.append(self._open_record("stream_end"))
        snapshot = AdaptiveSnapshot(
            design_sha256=self._design_sha256,
            events=tuple(events),
            members=tuple(self._members),
            decisions=tuple(self._decisions),
        )
        snapshot.validate()
        return snapshot

    def finish(self) -> AdaptiveSnapshot:
        if self._event_id is not None and self._store is not None:
            record = self._open_record("stream_end")
            assert self._prototype is not None and self._context is not None
            self._store.close_event(record, self._prototype, self._context)
        return self.snapshot()

    def context_vector(self) -> np.ndarray:
        if self._context is None:
            raise AdaptiveEventContextError("No episode has been observed yet")
        return self._context.copy()

    # -- state transitions -------------------------------------------------

    def _open_event(
        self, identity: str, session: str, turn_index: int, vector: np.ndarray
    ) -> None:
        self._event_id = hashlib.sha256(
            (
                EVENT_ID_PREFIX + "\0" + self._design_sha256 + "\0" + session + "\0" + identity
            ).encode("utf-8")
        ).hexdigest()
        self._first_episode = identity
        self._start_turn = turn_index
        self._end_turn = turn_index
        self._member_sum = vector.copy()
        self._size = 1
        self._prototype = normalize(self._member_sum)
        self._context = vector.copy()

    def _extend_event(self, vector: np.ndarray) -> int:
        assert self._member_sum is not None and self._context is not None
        self._member_sum = self._member_sum + vector
        self._size += 1
        self._prototype = normalize(self._member_sum / np.float32(self._size))
        # rho is fixed at 0.5, carried unchanged from DMR-001 where the
        # development context AUC selected it. DMR-001B changes the boundary
        # rule only.
        self._context = normalize(
            np.float32(0.5) * self._context + np.float32(0.5) * vector
        )
        return self._size - 1

    def _open_record(self, close_reason: str) -> AdaptiveEventRecord:
        assert (
            self._event_id is not None
            and self._first_episode is not None
            and self._start_turn is not None
            and self._end_turn is not None
            and self._prototype is not None
            and self._context is not None
            and self._session is not None
        )
        return AdaptiveEventRecord(
            event_id=self._event_id,
            design_sha256=self._design_sha256,
            session_hash=self._session,
            first_episode_hash=self._first_episode,
            start_turn=self._start_turn,
            end_turn=self._end_turn,
            member_count=self._size,
            prototype_sha256=vector_sha256(self._prototype),
            context_sha256=vector_sha256(self._context),
            close_reason=close_reason,
        )

    def _close_open_event(self, reason: str) -> None:
        record = self._open_record(reason)
        self._events.append(record)
        if self._store is not None:
            assert self._prototype is not None and self._context is not None
            self._store.close_event(record, self._prototype, self._context)


# ---------------------------------------------------------------------------
# Sidecar store
# ---------------------------------------------------------------------------

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS event_records (
        event_id TEXT PRIMARY KEY,
        design_sha256 TEXT NOT NULL,
        session_hash TEXT NOT NULL,
        first_episode_hash TEXT NOT NULL,
        start_turn INTEGER NOT NULL,
        end_turn INTEGER NOT NULL,
        member_count INTEGER NOT NULL,
        prototype_f32 BLOB NOT NULL,
        prototype_sha256 TEXT NOT NULL,
        context_f32 BLOB NOT NULL,
        context_sha256 TEXT NOT NULL,
        close_reason TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_members (
        event_id TEXT NOT NULL,
        episode_hash TEXT NOT NULL UNIQUE,
        event_position INTEGER NOT NULL,
        boundary_score REAL NOT NULL,
        boundary_reason TEXT NOT NULL,
        PRIMARY KEY(event_id, event_position)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS boundary_decisions (
        episode_hash TEXT PRIMARY KEY,
        session_hash TEXT NOT NULL,
        turn_index INTEGER NOT NULL,
        event_id TEXT NOT NULL,
        event_position INTEGER NOT NULL,
        boundary_score REAL NOT NULL,
        boundary_threshold REAL NOT NULL,
        history_size INTEGER NOT NULL,
        boundary_reason TEXT NOT NULL,
        claims_boundary INTEGER NOT NULL,
        hard_boundary INTEGER NOT NULL,
        adaptive_boundary INTEGER NOT NULL,
        capped_boundary INTEGER NOT NULL,
        new_event INTEGER NOT NULL,
        open_event_size_before INTEGER NOT NULL,
        design_sha256 TEXT NOT NULL,
        prototype_sha256 TEXT NOT NULL,
        context_sha256 TEXT NOT NULL
    )
    """,
)


class AdaptiveEventContextStore:
    """Atomic, replay-safe sidecar. Immutable episode rows are never rewritten."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.isolation_level = None
        for statement in _DDL:
            self._connection.execute(statement)

    @classmethod
    def in_memory(cls) -> "AdaptiveEventContextStore":
        return cls(sqlite3.connect(":memory:"))

    @classmethod
    def open(cls, path: Path) -> "AdaptiveEventContextStore":
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(sqlite3.connect(str(path)))

    def record(
        self,
        decision: AdaptiveFormationDecision,
        event: AdaptiveEventRecord,
        prototype: np.ndarray,
        context: np.ndarray,
    ) -> None:
        existing = self._connection.execute(
            "SELECT event_id, event_position, boundary_score, boundary_reason "
            "FROM event_members WHERE episode_hash = ?",
            (decision.episode_hash,),
        ).fetchone()
        if existing is not None:
            stored = (existing[0], existing[1], float(existing[2]), existing[3])
            replay = (
                decision.event_id,
                decision.event_position,
                float(decision.boundary_score),
                decision.boundary_reason,
            )
            if stored != replay:
                raise AdaptiveEventContextError(
                    f"Conflicting replay for episode {decision.episode_hash}: "
                    f"stored {stored} replayed {replay}"
                )
            return

        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._upsert_event(event, prototype, context)
            self._connection.execute(
                "INSERT INTO event_members VALUES (?,?,?,?,?)",
                (
                    decision.event_id,
                    decision.episode_hash,
                    decision.event_position,
                    float(decision.boundary_score),
                    decision.boundary_reason,
                ),
            )
            self._connection.execute(
                "INSERT INTO boundary_decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    decision.episode_hash,
                    decision.session_hash,
                    decision.turn_index,
                    decision.event_id,
                    decision.event_position,
                    float(decision.boundary_score),
                    float(decision.boundary_threshold),
                    decision.history_size,
                    decision.boundary_reason,
                    int(decision.claims_boundary),
                    int(decision.hard_boundary),
                    int(decision.adaptive_boundary),
                    int(decision.capped_boundary),
                    int(decision.new_event),
                    decision.open_event_size_before,
                    decision.design_sha256,
                    decision.prototype_sha256,
                    decision.context_sha256,
                ),
            )
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        self._connection.execute("COMMIT")

    def close_event(
        self, event: AdaptiveEventRecord, prototype: np.ndarray, context: np.ndarray
    ) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._upsert_event(event, prototype, context)
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        self._connection.execute("COMMIT")

    def _upsert_event(
        self, event: AdaptiveEventRecord, prototype: np.ndarray, context: np.ndarray
    ) -> None:
        if event.prototype_sha256 != vector_sha256(prototype):
            raise AdaptiveEventContextError("Prototype hash does not match its bytes")
        if event.context_sha256 != vector_sha256(context):
            raise AdaptiveEventContextError("Context hash does not match its bytes")
        self._connection.execute(
            "INSERT INTO event_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(event_id) DO UPDATE SET "
            "end_turn=excluded.end_turn, member_count=excluded.member_count, "
            "prototype_f32=excluded.prototype_f32, prototype_sha256=excluded.prototype_sha256, "
            "context_f32=excluded.context_f32, context_sha256=excluded.context_sha256, "
            "close_reason=excluded.close_reason",
            (
                event.event_id,
                event.design_sha256,
                event.session_hash,
                event.first_episode_hash,
                event.start_turn,
                event.end_turn,
                event.member_count,
                vector_bytes(prototype),
                event.prototype_sha256,
                vector_bytes(context),
                event.context_sha256,
                event.close_reason,
            ),
        )

    def counts(self) -> dict[str, int]:
        return {
            "events": self._connection.execute(
                "SELECT count(*) FROM event_records"
            ).fetchone()[0],
            "members": self._connection.execute(
                "SELECT count(*) FROM event_members"
            ).fetchone()[0],
            "capped_closures": self._connection.execute(
                "SELECT count(*) FROM event_records WHERE close_reason = 'capped'"
            ).fetchone()[0],
        }


def form(
    episodes: Iterable[Mapping[str, Any]],
    *,
    design_sha256: str,
    config: AdaptiveFormerConfig,
    store: AdaptiveEventContextStore | None = None,
) -> AdaptiveSnapshot:
    former = AdaptiveEventContextFormer(
        design_sha256=design_sha256, config=config, store=store
    )
    for episode in episodes:
        former.observe(
            episode_hash=episode["episode_hash"],
            session_hash=episode["session_hash"],
            turn_index=int(episode["turn_index"]),
            embedding=episode["embedding"],
        )
    return former.finish()
