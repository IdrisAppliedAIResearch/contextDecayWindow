"""DMR-001 online event-context formation.

`OnlineEventContextFormer` partitions an append-only episode stream into event
records using only past and current episodes. It reads no text, no future
episode, no annotation, and no answer key. It is the one new component of
DMR-001; the pre-registration at
`experiments/components/biological_memory/dmr_001/DMR_001_PRE_REGISTRATION.md`
is the sole authority for its parameters and governs wherever the prospective
implementation specification disagrees.

The arithmetic here is written independently of the Part 1 exploratory
implementation in `src/analysis/dmr001_exploration.py`. PF2 asserts the two
agree exactly on a real stream; a shared helper would have made that check
vacuous.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

STORE_SCHEMA = "dmr001-event-context-v1"
EVENT_ID_PREFIX = "dmr-event-v1"
VECTOR_DIMENSION = 1024
HEX_DIGITS = frozenset("0123456789abcdef")

BOUNDARY_REASONS = ("stream_start", "hard", "drift", "forced", "continue")
CLOSE_REASONS = ("hard", "drift", "forced", "stream_end", "open")
POLICY_KINDS = ("drift", "session", "pair", "periodic")


class EventContextError(RuntimeError):
    """Any violation of the registered formation contract."""


# ---------------------------------------------------------------------------
# Deterministic float32 arithmetic
#
# Element-wise float32 operations reproduce bit for bit. Reductions do not: a
# BLAS dot may reassociate across lanes, threads, or machines. Every reduction
# below goes through math.fsum over float64 products, which is exactly rounded
# and order-independent, so no thread count or CPU dispatch can move a bit.
# ---------------------------------------------------------------------------


def dot(left: np.ndarray, right: np.ndarray) -> float:
    return math.fsum(a * b for a, b in zip(left.tolist(), right.tolist()))


def norm(vector: np.ndarray) -> float:
    return math.sqrt(dot(vector, vector))


def normalize(vector: np.ndarray) -> np.ndarray:
    magnitude = norm(vector)
    if not math.isfinite(magnitude) or magnitude <= 0.0:
        raise EventContextError("Cannot normalize a zero-length or non-finite vector")
    return (vector.astype(np.float64) / magnitude).astype(np.float32)


def vector_bytes(vector: np.ndarray) -> bytes:
    if vector.dtype != np.float32 or vector.shape != (VECTOR_DIMENSION,):
        raise EventContextError("Stored vectors must be 1024-dimensional float32")
    return vector.astype("<f4").tobytes()


def vector_sha256(vector: np.ndarray) -> str:
    return hashlib.sha256(vector_bytes(vector)).hexdigest()


def _require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or not set(value) <= HEX_DIGITS:
        raise EventContextError(f"{label} must be a lowercase hex SHA-256")
    return value


def _as_vector(embedding: Any) -> np.ndarray:
    vector = np.asarray(embedding, dtype=np.float32)
    if vector.shape != (VECTOR_DIMENSION,):
        raise EventContextError(
            f"Embedding must have {VECTOR_DIMENSION} dimensions, got {vector.shape}"
        )
    if not np.all(np.isfinite(vector)):
        raise EventContextError("Embedding contains a non-finite value")
    return vector


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundaryPolicy:
    """One registered arm. Every arm is deterministic and label-blind."""

    name: str
    kind: str
    period: int | None = None

    def __post_init__(self) -> None:
        if self.kind not in POLICY_KINDS:
            raise EventContextError(f"Unknown boundary policy kind: {self.kind}")
        if self.kind == "periodic":
            if not isinstance(self.period, int) or self.period < 1:
                raise EventContextError("A periodic policy needs a positive period")
        elif self.period is not None:
            raise EventContextError("Only a periodic policy may carry a period")


T_EVENT = BoundaryPolicy(name="T_EVENT", kind="drift")
C_SESSION = BoundaryPolicy(name="C_SESSION", kind="session")
C_ALL = BoundaryPolicy(name="C_ALL", kind="session")
C_PAIR = BoundaryPolicy(name="C_PAIR", kind="pair")


def periodic_policy(period: int) -> BoundaryPolicy:
    return BoundaryPolicy(name=f"C_PERIODIC_{period}", kind="periodic", period=period)


@dataclass(frozen=True)
class FormerConfig:
    """The locked parameters. They live in the pre-registration and nowhere else."""

    rho: float
    drift_threshold: float
    min_event_size: int
    max_event_size: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.rho <= 1.0:
            raise EventContextError("rho must lie in [0, 1]")
        if not math.isfinite(self.drift_threshold) or self.drift_threshold < 0.0:
            raise EventContextError("drift_threshold must be finite and non-negative")
        if self.min_event_size < 1:
            raise EventContextError("min_event_size must be at least 1")
        if self.max_event_size < self.min_event_size:
            raise EventContextError("max_event_size must be at least min_event_size")

    @classmethod
    def from_design(cls, payload: Mapping[str, Any]) -> "FormerConfig":
        parameters = payload["parameters"]
        return cls(
            rho=float(parameters["rho"]),
            drift_threshold=float(parameters["drift_threshold"]),
            min_event_size=int(parameters["min_event_size"]),
            max_event_size=int(parameters["max_event_size"]),
        )


def load_design(path: Path) -> tuple[str, FormerConfig, dict[str, Any]]:
    """Read the locked design and return its anchor hash and parameters.

    The design file records the SHA-256 of the pre-registration with line
    endings normalized to LF. The former refuses to run unless the file on disk
    still hashes to that value, so a silently edited registration cannot
    produce event identities that look legitimate.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    anchor = _require_hash(payload["design_sha256"], "design_sha256")
    registration = path.parent / payload["design_source"]
    actual = design_sha256_of(registration)
    if actual != anchor:
        raise EventContextError(
            "Design anchor mismatch. The pre-registration on disk does not hash to "
            f"the value the design file records.\n  expected: {anchor}\n  actual  : {actual}"
        )
    return anchor, FormerConfig.from_design(payload), payload


def design_sha256_of(path: Path) -> str:
    raw = path.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalized).hexdigest()


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FormationDecision:
    episode_hash: str
    session_hash: str
    turn_index: int
    event_id: str
    event_position: int
    boundary_score: float
    boundary_reason: str
    hard_boundary: bool
    drift_boundary: bool
    forced_boundary: bool
    new_event: bool
    open_event_size_before: int
    drift_threshold: float
    design_sha256: str
    prototype_sha256: str
    context_sha256: str


@dataclass(frozen=True)
class EventRecord:
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
class EventMember:
    event_id: str
    episode_hash: str
    event_position: int
    boundary_score: float
    boundary_reason: str


@dataclass(frozen=True)
class EventContextSnapshot:
    design_sha256: str
    policy: str
    events: tuple[EventRecord, ...]
    members: tuple[EventMember, ...]
    decisions: tuple[FormationDecision, ...]

    def canonical_json(self) -> str:
        return (
            json.dumps(
                {
                    "schema": STORE_SCHEMA,
                    "design_sha256": self.design_sha256,
                    "policy": self.policy,
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

    def validate(self) -> dict[str, Any]:
        """G2 partition invariants, checked on the snapshot rather than assumed."""
        if len(self.members) != len(self.decisions):
            raise EventContextError("Member count does not match decision count")
        by_event: dict[str, list[EventMember]] = {}
        for member in self.members:
            by_event.setdefault(member.event_id, []).append(member)
        seen_episodes: set[str] = set()
        for record in self.events:
            members = by_event.get(record.event_id)
            if not members:
                raise EventContextError(f"Event has no members: {record.event_id}")
            positions = [member.event_position for member in members]
            if positions != list(range(len(members))):
                raise EventContextError(
                    f"Event positions are not contiguous from zero: {record.event_id}"
                )
            if len(members) != record.member_count:
                raise EventContextError(f"Member count mismatch: {record.event_id}")
            if members[0].episode_hash != record.first_episode_hash:
                raise EventContextError(f"First member mismatch: {record.event_id}")
            for member in members:
                if member.episode_hash in seen_episodes:
                    raise EventContextError(
                        f"Episode belongs to more than one event: {member.episode_hash}"
                    )
                seen_episodes.add(member.episode_hash)
        if set(by_event) != {record.event_id for record in self.events}:
            raise EventContextError("Member table references an unknown event")
        sessions = [record.session_hash for record in self.events]
        for index in range(1, len(sessions)):
            if sessions[index] == sessions[index - 1]:
                continue
            if sessions[index] in sessions[:index]:
                raise EventContextError("A session was reopened after it closed")
        return {
            "events": len(self.events),
            "members": len(self.members),
            "episodes": len(seen_episodes),
            "sessions": len(set(sessions)),
        }


# ---------------------------------------------------------------------------
# The former
# ---------------------------------------------------------------------------


class OnlineEventContextFormer:
    """Causal, deterministic, label-blind event formation over pinned vectors."""

    def __init__(
        self,
        *,
        design_sha256: str,
        config: FormerConfig,
        policy: BoundaryPolicy = T_EVENT,
        store: "EventContextStore | None" = None,
    ) -> None:
        self._design_sha256 = _require_hash(design_sha256, "design_sha256")
        self._config = config
        self._policy = policy
        self._store = store

        self._session: str | None = None
        self._closed_sessions: set[str] = set()
        self._last_turn: int | None = None
        self._seen_episodes: set[str] = set()

        self._event_id: str | None = None
        self._first_episode: str | None = None
        self._start_turn: int | None = None
        self._end_turn: int | None = None
        self._member_sum: np.ndarray | None = None
        self._prototype: np.ndarray | None = None
        self._context: np.ndarray | None = None
        self._size = 0
        self._session_position = 0

        self._events: list[EventRecord] = []
        self._members: list[EventMember] = []
        self._decisions: list[FormationDecision] = []

    # -- public contract ---------------------------------------------------

    def observe(
        self,
        *,
        episode_hash: str,
        session_hash: str,
        turn_index: int,
        embedding: Any,
    ) -> FormationDecision:
        identity = _require_hash(episode_hash, "episode_hash")
        session = _require_hash(session_hash, "session_hash")
        if not isinstance(turn_index, int) or isinstance(turn_index, bool):
            raise EventContextError("turn_index must be an int")
        if turn_index < 0:
            raise EventContextError("turn_index must be non-negative")
        if identity in self._seen_episodes:
            raise EventContextError(f"Episode observed twice in one pass: {identity}")
        if session in self._closed_sessions:
            raise EventContextError(f"Session was already closed: {session}")
        if self._session == session and self._last_turn is not None:
            if turn_index <= self._last_turn:
                raise EventContextError(
                    "Turns must arrive in strictly increasing order within a session: "
                    f"{turn_index} after {self._last_turn}"
                )

        vector = normalize(_as_vector(embedding))

        hard = self._session is not None and session != self._session
        drift = 0.0 if self._prototype is None else 1.0 - dot(vector, self._prototype)
        drift_boundary, forced = self._policy_predicates(drift)
        size_before = self._size
        opening = self._prototype is None or hard or drift_boundary or forced

        if opening:
            reason = (
                "stream_start"
                if self._prototype is None
                else "hard"
                if hard
                else "drift"
                if drift_boundary
                else "forced"
            )
            if self._event_id is not None:
                self._close_open_event(reason)
            if hard and self._session is not None:
                self._closed_sessions.add(self._session)
                self._session_position = 0
            self._open_event(identity, session, turn_index, vector)
            position = 0
        else:
            reason = "continue"
            position = self._extend_event(vector)

        self._session = session
        self._last_turn = turn_index
        self._end_turn = turn_index
        self._seen_episodes.add(identity)
        self._session_position += 1

        assert self._event_id is not None
        assert self._prototype is not None and self._context is not None
        decision = FormationDecision(
            episode_hash=identity,
            session_hash=session,
            turn_index=turn_index,
            event_id=self._event_id,
            event_position=position,
            boundary_score=drift,
            boundary_reason=reason,
            hard_boundary=bool(hard),
            drift_boundary=bool(drift_boundary),
            forced_boundary=bool(forced),
            new_event=bool(opening),
            open_event_size_before=size_before,
            drift_threshold=self._config.drift_threshold,
            design_sha256=self._design_sha256,
            prototype_sha256=vector_sha256(self._prototype),
            context_sha256=vector_sha256(self._context),
        )
        self._decisions.append(decision)
        self._members.append(
            EventMember(
                event_id=self._event_id,
                episode_hash=identity,
                event_position=position,
                boundary_score=drift,
                boundary_reason=reason,
            )
        )
        if self._store is not None:
            self._store.record(decision, self._open_record("open"), self._prototype, self._context)
        return decision

    def context_vector(self) -> np.ndarray:
        """A copy of the open event's encoding-context vector."""
        if self._context is None:
            raise EventContextError("No episode has been observed yet")
        return self._context.copy()

    def prototype_vector(self) -> np.ndarray:
        """A copy of the open event's prototype vector."""
        if self._prototype is None:
            raise EventContextError("No episode has been observed yet")
        return self._prototype.copy()

    def snapshot(self) -> EventContextSnapshot:
        events = list(self._events)
        if self._event_id is not None:
            events.append(self._open_record("stream_end"))
        snapshot = EventContextSnapshot(
            design_sha256=self._design_sha256,
            policy=self._policy.name,
            events=tuple(events),
            members=tuple(self._members),
            decisions=tuple(self._decisions),
        )
        snapshot.validate()
        return snapshot

    # -- boundary predicates ----------------------------------------------

    def _policy_predicates(self, drift: float) -> tuple[bool, bool]:
        if self._prototype is None:
            return False, False
        kind = self._policy.kind
        if kind == "drift":
            drift_boundary = (
                self._size >= self._config.min_event_size
                and drift >= self._config.drift_threshold
            )
            return drift_boundary, self._size >= self._config.max_event_size
        if kind == "session":
            return False, False
        if kind == "pair":
            return False, True
        assert self._policy.period is not None
        return False, self._session_position % self._policy.period == 0

    # -- state transitions -------------------------------------------------

    def _open_event(
        self, identity: str, session: str, turn_index: int, vector: np.ndarray
    ) -> None:
        self._event_id = hashlib.sha256(
            (
                EVENT_ID_PREFIX
                + "\0"
                + self._design_sha256
                + "\0"
                + session
                + "\0"
                + identity
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
        self._context = normalize(
            np.float32(self._config.rho) * self._context
            + np.float32(1.0 - self._config.rho) * vector
        )
        return self._size - 1

    def _open_record(self, close_reason: str) -> EventRecord:
        assert (
            self._event_id is not None
            and self._first_episode is not None
            and self._start_turn is not None
            and self._end_turn is not None
            and self._prototype is not None
            and self._context is not None
            and self._session is not None
        )
        if close_reason not in CLOSE_REASONS:
            raise EventContextError(f"Unknown close reason: {close_reason}")
        return EventRecord(
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

    def finish(self) -> EventContextSnapshot:
        """Close the last open event and flush it. Idempotent."""
        if self._event_id is not None and self._store is not None:
            record = self._open_record("stream_end")
            assert self._prototype is not None and self._context is not None
            self._store.close_event(record, self._prototype, self._context)
        return self.snapshot()


# ---------------------------------------------------------------------------
# Sidecar store
# ---------------------------------------------------------------------------

_EVENT_RECORDS_DDL = """
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
"""

_EVENT_MEMBERS_DDL = """
CREATE TABLE IF NOT EXISTS event_members (
    event_id TEXT NOT NULL,
    episode_hash TEXT NOT NULL UNIQUE,
    event_position INTEGER NOT NULL,
    boundary_score REAL NOT NULL,
    boundary_reason TEXT NOT NULL,
    PRIMARY KEY(event_id, event_position)
)
"""

_DECISIONS_DDL = """
CREATE TABLE IF NOT EXISTS boundary_decisions (
    episode_hash TEXT PRIMARY KEY,
    session_hash TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    event_position INTEGER NOT NULL,
    boundary_score REAL NOT NULL,
    boundary_reason TEXT NOT NULL,
    hard_boundary INTEGER NOT NULL,
    drift_boundary INTEGER NOT NULL,
    forced_boundary INTEGER NOT NULL,
    new_event INTEGER NOT NULL,
    open_event_size_before INTEGER NOT NULL,
    drift_threshold REAL NOT NULL,
    design_sha256 TEXT NOT NULL,
    prototype_sha256 TEXT NOT NULL,
    context_sha256 TEXT NOT NULL
)
"""


class EventContextStore:
    """Atomic, replay-safe sidecar. Immutable episode rows are never rewritten."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.isolation_level = None
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute(_EVENT_RECORDS_DDL)
        self._connection.execute(_EVENT_MEMBERS_DDL)
        self._connection.execute(_DECISIONS_DDL)

    @classmethod
    def open(cls, path: Path) -> "EventContextStore":
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(sqlite3.connect(str(path)))

    @classmethod
    def in_memory(cls) -> "EventContextStore":
        return cls(sqlite3.connect(":memory:"))

    def close(self) -> None:
        self._connection.close()

    # -- writes ------------------------------------------------------------

    def record(
        self,
        decision: FormationDecision,
        event: EventRecord,
        prototype: np.ndarray,
        context: np.ndarray,
    ) -> None:
        """Write one observed episode. One transaction, or nothing at all.

        Replaying an episode that is already stored with identical values is a
        no-op. Any differing value raises: a formation store must never
        silently reassign an episode to a different event.
        """
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
                raise EventContextError(
                    "Conflicting replay for episode "
                    f"{decision.episode_hash}: stored {stored} replayed {replay}"
                )
            return

        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._upsert_event(event, prototype, context)
            self._connection.execute(
                "INSERT INTO event_members "
                "(event_id, episode_hash, event_position, boundary_score, boundary_reason) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    decision.event_id,
                    decision.episode_hash,
                    decision.event_position,
                    float(decision.boundary_score),
                    decision.boundary_reason,
                ),
            )
            self._connection.execute(
                "INSERT INTO boundary_decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    decision.episode_hash,
                    decision.session_hash,
                    decision.turn_index,
                    decision.event_id,
                    decision.event_position,
                    float(decision.boundary_score),
                    decision.boundary_reason,
                    int(decision.hard_boundary),
                    int(decision.drift_boundary),
                    int(decision.forced_boundary),
                    int(decision.new_event),
                    decision.open_event_size_before,
                    float(decision.drift_threshold),
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
        self, event: EventRecord, prototype: np.ndarray, context: np.ndarray
    ) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._upsert_event(event, prototype, context)
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        self._connection.execute("COMMIT")

    def _upsert_event(
        self, event: EventRecord, prototype: np.ndarray, context: np.ndarray
    ) -> None:
        if event.prototype_sha256 != vector_sha256(prototype):
            raise EventContextError("Prototype hash does not match the prototype bytes")
        if event.context_sha256 != vector_sha256(context):
            raise EventContextError("Context hash does not match the context bytes")
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

    # -- reads -------------------------------------------------------------

    def events(self) -> list[EventRecord]:
        rows = self._connection.execute(
            "SELECT event_id, design_sha256, session_hash, first_episode_hash, start_turn, "
            "end_turn, member_count, prototype_sha256, context_sha256, close_reason "
            "FROM event_records ORDER BY start_turn, event_id"
        ).fetchall()
        return [
            EventRecord(
                event_id=row[0],
                design_sha256=row[1],
                session_hash=row[2],
                first_episode_hash=row[3],
                start_turn=row[4],
                end_turn=row[5],
                member_count=row[6],
                prototype_sha256=row[7],
                context_sha256=row[8],
                close_reason=row[9],
            )
            for row in rows
        ]

    def members(self) -> list[EventMember]:
        rows = self._connection.execute(
            "SELECT event_id, episode_hash, event_position, boundary_score, boundary_reason "
            "FROM event_members ORDER BY event_id, event_position"
        ).fetchall()
        return [
            EventMember(
                event_id=row[0],
                episode_hash=row[1],
                event_position=row[2],
                boundary_score=float(row[3]),
                boundary_reason=row[4],
            )
            for row in rows
        ]

    def digest(self) -> str:
        digest = hashlib.sha256()
        for row in self._connection.execute(
            "SELECT event_id, design_sha256, session_hash, first_episode_hash, start_turn, "
            "end_turn, member_count, prototype_sha256, context_sha256, close_reason "
            "FROM event_records ORDER BY event_id"
        ):
            digest.update(("|".join(str(value) for value in row) + "\n").encode("utf-8"))
        for row in self._connection.execute(
            "SELECT event_id, episode_hash, event_position, boundary_score, boundary_reason "
            "FROM event_members ORDER BY event_id, event_position"
        ):
            digest.update(("|".join(str(value) for value in row) + "\n").encode("utf-8"))
        return digest.hexdigest()


# ---------------------------------------------------------------------------
# Replay helper
# ---------------------------------------------------------------------------


def form(
    episodes: Iterable[Mapping[str, Any]],
    *,
    design_sha256: str,
    config: FormerConfig,
    policy: BoundaryPolicy = T_EVENT,
    store: EventContextStore | None = None,
) -> EventContextSnapshot:
    """Replay an ordered episode stream through one former and close it."""
    former = OnlineEventContextFormer(
        design_sha256=design_sha256, config=config, policy=policy, store=store
    )
    for episode in episodes:
        former.observe(
            episode_hash=episode["episode_hash"],
            session_hash=episode["session_hash"],
            turn_index=int(episode["turn_index"]),
            embedding=episode["embedding"],
        )
    return former.finish()


def event_boundary_indices(snapshot: EventContextSnapshot) -> set[int]:
    return {
        index
        for index, decision in enumerate(snapshot.decisions)
        if decision.new_event
    }


def event_sizes(snapshot: EventContextSnapshot) -> list[int]:
    return [record.member_count for record in snapshot.events]
