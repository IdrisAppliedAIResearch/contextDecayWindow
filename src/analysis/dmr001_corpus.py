"""DMR-001 corpus selection and frozen episode-stream identity.

The DMR-001 former consumes an existing episode unit without changing its text,
embedding call shape, durability, or append order. This module locates every
committed episode stream that qualifies, assigns content-addressed identities,
and freezes the selection so later stages replay exactly the same bytes.

Selection is mechanical. It never reads an answer key, a rubric, a retrieval
log, or a score, and it never looks at a formation outcome.
"""

from __future__ import annotations

import glob
import hashlib
import json
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

CORPUS_SCHEMA = "dmr001-corpus-v1"
EMBEDDING_DIMENSION = 1024
EMBEDDING_BYTES = EMBEDDING_DIMENSION * 4
MINIMUM_TURNS = 30


class CorpusError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_pair_sha256(user: str, assistant: str) -> str:
    """Content identity of one stored user-plus-assistant episode.

    The serialization is ASCII-escaped canonical JSON so the identity survives
    checkout line-ending rewrites and locale differences. This is the same
    shape SUP-001 used for episode content identity.
    """
    payload = json.dumps(
        [["user", user], ["assistant", assistant]],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(payload)


def session_hash_for_realization(realization_sha256: str) -> str:
    """Session identity token, minted by the corpus lock, not by the former.

    The token is content-addressed: it carries no path, timestamp, UUID, or
    row id. The former treats it as an opaque equality token exactly as a live
    deployment would treat a session id minted when the session opens. See the
    pre-registration's identity revision for the residual this leaves.
    """
    return _sha256(("dmr-session-v1\0" + realization_sha256).encode("utf-8"))


def episode_hash(session_hash: str, stream_index: int, pair_sha256: str) -> str:
    """Append-only episode identity: session, position in the stream, content.

    Part 1 found 844 of 1,000 episodes in the 1,000-turn endurance stream are
    exact content duplicates of an earlier episode, so content text alone
    cannot identify a stored row. Position makes the identity unique per append
    while keeping it content-addressed and replay-stable.
    """
    if stream_index < 0:
        raise CorpusError("Stream index must be non-negative")
    payload = (
        "dmr-episode-v1\0" + session_hash + "\0" + str(stream_index) + "\0" + pair_sha256
    ).encode("utf-8")
    return _sha256(payload)


@dataclass(frozen=True)
class Episode:
    stream_index: int
    turn_number: int
    session_hash: str
    episode_hash: str
    pair_sha256: str
    annotation_domain: str
    embedding_bytes: bytes

    def vector(self) -> tuple[float, ...]:
        return struct.unpack("<%df" % EMBEDDING_DIMENSION, self.embedding_bytes)


@dataclass(frozen=True)
class Session:
    session_hash: str
    script_sha256: str
    realization_sha256: str
    source_path: str
    source_sha256: str
    episode_count: int
    episodes: tuple[Episode, ...]

    def stream_digest(self) -> str:
        return _sha256("\n".join(e.episode_hash for e in self.episodes).encode("utf-8"))

    def vector_digest(self) -> str:
        digest = hashlib.sha256()
        for episode in self.episodes:
            digest.update(episode.embedding_bytes)
        return digest.hexdigest()

    def annotated_boundaries(self) -> tuple[int, ...]:
        """Stream indices whose annotation domain differs from the predecessor.

        This is measurement-only provenance recorded by the corpus scripts. It
        is never passed to the former and never used to select a threshold on
        the holdout split.
        """
        return tuple(
            index
            for index in range(1, len(self.episodes))
            if self.episodes[index].annotation_domain
            != self.episodes[index - 1].annotation_domain
        )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_rows(path: Path) -> list[tuple[Any, ...]] | None:
    uri = "file:" + path.as_posix() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return None
    try:
        return connection.execute(
            "select turn_number, ground_truth_domain, user_message, assistant_message, "
            "embedding from episodes order by turn_number"
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        connection.close()


def _qualifies(rows: Sequence[tuple[Any, ...]]) -> bool:
    if len(rows) < MINIMUM_TURNS:
        return False
    if [row[0] for row in rows] != list(range(1, len(rows) + 1)):
        return False
    if any(row[1] is None or row[1] == "" for row in rows):
        return False
    if any(row[2] is None or row[3] is None for row in rows):
        return False
    if any(not isinstance(row[4], bytes) or len(row[4]) != EMBEDDING_BYTES for row in rows):
        return False
    return True


def discover_candidates(repository_root: Path) -> Iterator[tuple[Path, list[tuple[Any, ...]]]]:
    """Yield every committed episode stream that meets the structural filter.

    A candidate must have at least 30 episodes, contiguous turn numbers from 1,
    a non-empty annotation domain on every episode, both message texts, and a
    1024-dimensional float32 embedding on every episode.
    """
    pattern = str(repository_root / "experiments" / "**" / "study.db")
    for raw in sorted(glob.glob(pattern, recursive=True)):
        path = Path(raw)
        rows = _read_rows(path)
        if rows is None or not _qualifies(rows):
            continue
        yield path, rows


def _script_sha256(rows: Sequence[tuple[Any, ...]]) -> str:
    return _sha256("\n".join(row[2] for row in rows).encode("utf-8"))


def _realization_sha256(pair_hashes: Sequence[str]) -> str:
    return _sha256("\n".join(pair_hashes).encode("utf-8"))


def select_sessions(repository_root: Path) -> list[Session]:
    """Apply the registered selection rule and return the frozen corpus.

    1. Keep every structurally qualifying stream.
    2. Group by user-script identity and drop any script that is a strict
       prefix of another script. Checkpoints and rehearsals of a longer run are
       prefixes, so this keeps one maximal stream per distinct conversation.
    3. Within a surviving script, keep one session per distinct realization
       (the ordered user-plus-assistant content), choosing the smallest source
       path so the choice is stable and does not depend on scan order.
    4. Order the corpus by descending episode count, then by session hash.
    """
    scripts: dict[str, tuple[str, ...]] = {}
    grouped: dict[str, dict[str, tuple[Path, list[tuple[Any, ...]], str]]] = {}

    for path, rows in discover_candidates(repository_root):
        script = _script_sha256(rows)
        scripts.setdefault(script, tuple(row[2] for row in rows))
        pair_hashes = [canonical_pair_sha256(row[2], row[3]) for row in rows]
        realization = _realization_sha256(pair_hashes)
        bucket = grouped.setdefault(script, {})
        existing = bucket.get(realization)
        relative = path.relative_to(repository_root).as_posix()
        if existing is None or relative < existing[2]:
            bucket[realization] = (path, rows, relative)

    maximal = {
        script
        for script in scripts
        if not any(
            other != script
            and len(scripts[script]) < len(scripts[other])
            and scripts[other][: len(scripts[script])] == scripts[script]
            for other in scripts
        )
    }

    sessions: list[Session] = []
    for script in sorted(maximal):
        for realization, (path, rows, relative) in sorted(grouped[script].items()):
            session_hash = session_hash_for_realization(realization)
            episodes = []
            for index, row in enumerate(rows):
                pair = canonical_pair_sha256(row[2], row[3])
                episodes.append(
                    Episode(
                        stream_index=index,
                        turn_number=int(row[0]),
                        session_hash=session_hash,
                        episode_hash=episode_hash(session_hash, index, pair),
                        pair_sha256=pair,
                        annotation_domain=str(row[1]),
                        embedding_bytes=bytes(row[4]),
                    )
                )
            sessions.append(
                Session(
                    session_hash=session_hash,
                    script_sha256=script,
                    realization_sha256=realization,
                    source_path=relative,
                    source_sha256=file_sha256(path),
                    episode_count=len(episodes),
                    episodes=tuple(episodes),
                )
            )

    sessions.sort(key=lambda session: (-session.episode_count, session.session_hash))
    _assert_unique(sessions)
    return sessions


def _assert_unique(sessions: Sequence[Session]) -> None:
    session_hashes = [session.session_hash for session in sessions]
    if len(set(session_hashes)) != len(session_hashes):
        raise CorpusError("Session identity collision in the selected corpus")
    seen: set[str] = set()
    for session in sessions:
        for episode in session.episodes:
            if episode.episode_hash in seen:
                raise CorpusError("Episode identity collision in the selected corpus")
            seen.add(episode.episode_hash)


def split_of(session: Session, holdout_script: str) -> str:
    return "holdout" if session.script_sha256 == holdout_script else "development"


def holdout_script_sha256(sessions: Sequence[Session]) -> str:
    """The single longest script is the sealed holdout; everything else is dev.

    The rule is fixed before any formation outcome is computed and puts the
    binding evaluation on the longest committed conversation.
    """
    if not sessions:
        raise CorpusError("Empty corpus")
    longest = max(session.episode_count for session in sessions)
    scripts = {
        session.script_sha256 for session in sessions if session.episode_count == longest
    }
    if len(scripts) != 1:
        raise CorpusError("Holdout script is ambiguous at the longest episode count")
    return scripts.pop()


def corpus_manifest(sessions: Sequence[Session]) -> dict[str, Any]:
    holdout = holdout_script_sha256(sessions)
    rows = []
    for session in sessions:
        rows.append(
            {
                "session_sha256": session.session_hash,
                "script_sha256": session.script_sha256,
                "realization_sha256": session.realization_sha256,
                "source_path": session.source_path,
                "source_sha256": session.source_sha256,
                "episode_count": session.episode_count,
                "stream_digest": session.stream_digest(),
                "vector_digest": session.vector_digest(),
                "annotated_boundary_count": len(session.annotated_boundaries()),
                "annotation_domains": sorted(
                    {episode.annotation_domain for episode in session.episodes}
                ),
                "split": split_of(session, holdout),
            }
        )
    development = [row for row in rows if row["split"] == "development"]
    heldout = [row for row in rows if row["split"] == "holdout"]
    return {
        "schema": CORPUS_SCHEMA,
        "embedding": {
            "dimension": EMBEDDING_DIMENSION,
            "dtype": "float32",
            "byte_order": "little",
            "source": "pinned episode embedding stored by the committed run",
        },
        "holdout_script_sha256": holdout,
        "selection_rule": (
            "structurally qualifying committed episode streams, prefix-maximal by "
            "user script, one session per distinct realization, longest script sealed "
            "as the holdout"
        ),
        "counts": {
            "sessions": len(rows),
            "episodes": sum(row["episode_count"] for row in rows),
            "development_sessions": len(development),
            "development_episodes": sum(row["episode_count"] for row in development),
            "holdout_sessions": len(heldout),
            "holdout_episodes": sum(row["episode_count"] for row in heldout),
            "annotated_boundaries": sum(row["annotated_boundary_count"] for row in rows),
            "development_annotated_boundaries": sum(
                row["annotated_boundary_count"] for row in development
            ),
            "holdout_annotated_boundaries": sum(
                row["annotated_boundary_count"] for row in heldout
            ),
        },
        "sessions": rows,
        "corpus_digest": _sha256(
            "\n".join(
                row["session_sha256"] + ":" + row["stream_digest"] + ":" + row["vector_digest"]
                for row in rows
            ).encode("utf-8")
        ),
    }


def write_json(path: Path, payload: dict[str, Any], *, allow_overwrite: bool = False) -> str:
    if path.exists() and not allow_overwrite:
        raise FileExistsError(f"Refusing to overwrite artifact: {path}")
    text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return _sha256(text.encode("utf-8"))
