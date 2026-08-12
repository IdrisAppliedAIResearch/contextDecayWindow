"""DMR-001C corpus: LongMemEval haystacks as blind multi-session streams.

DMR-001 and DMR-001B both scored against corpus provenance - a scripted topic
schedule written by the study scripts. This corpus replaces that with real
session seams: each LongMemEval haystack is an ordered assembly of genuinely
distinct conversations, so a session change is a real change of conversation
rather than a scheduled topic label.

The former is deliberately **blind** to those seams. It receives one session
token for the whole stream, so the hard-boundary predicate can never fire and
every boundary it opens is one it detected. Session provenance is measurement
only and is never passed to the mechanism.

No answer, evidence marker, question, or date is read by anything here.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

CORPUS_SCHEMA = "dmr001c-corpus-v1"
EMBEDDING_DIMENSION = 1024
EMBEDDING_BYTES = EMBEDDING_DIMENSION * 4

DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
DATASET_BYTES = 277383467
DATASET_COMMIT = "98d7416c24c778c2fee6e6f3006e7a073259d48f"

SEED = "5005"
STRATA = (
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "temporal-reasoning",
    "knowledge-update",
    "multi-session",
)
RANK_LOW = 31
RANK_HIGH = 40
MIN_SESSIONS = 8
MIN_EPISODES = 64


class CorpusError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def episode_text(user: str, assistant: str) -> str:
    """The program's carried episode rendering, and the embedding cache key."""
    return f"User: {user}\nAssistant: {assistant}"


def pair_sha256(user: str, assistant: str) -> str:
    payload = json.dumps(
        [["user", user], ["assistant", assistant]],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(payload)


def stream_token(question_id: str) -> str:
    """One opaque token for the whole haystack.

    The former sees this and nothing else about provenance, so it cannot know
    where one source conversation ends and the next begins.
    """
    return _sha256(("dmr-stream-v1\0" + question_id).encode("utf-8"))


def episode_identity(token: str, index: int, pair: str) -> str:
    return _sha256(
        ("dmr-episode-v1\0" + token + "\0" + str(index) + "\0" + pair).encode("utf-8")
    )


def selection_rank(stratum: str, question_id: str) -> str:
    return _sha256((SEED + "\0" + stratum + "\0" + question_id).encode("utf-8"))


@dataclass(frozen=True)
class Episode:
    stream_index: int
    episode_hash: str
    pair_sha256: str
    source_session_index: int
    embedding_bytes: bytes

    def vector(self) -> tuple[float, ...]:
        return struct.unpack("<%df" % EMBEDDING_DIMENSION, self.embedding_bytes)


@dataclass(frozen=True)
class Stream:
    question_id: str
    stratum: str
    stream_token: str
    episodes: tuple[Episode, ...]
    source_session_count: int

    @property
    def episode_count(self) -> int:
        return len(self.episodes)

    def seam_indices(self) -> tuple[int, ...]:
        """Stream positions where the source conversation changes. Measurement only."""
        return tuple(
            index
            for index in range(1, len(self.episodes))
            if self.episodes[index].source_session_index
            != self.episodes[index - 1].source_session_index
        )

    def stream_digest(self) -> str:
        return _sha256("\n".join(e.episode_hash for e in self.episodes).encode("utf-8"))

    def vector_digest(self) -> str:
        digest = hashlib.sha256()
        for episode in self.episodes:
            digest.update(episode.embedding_bytes)
        return digest.hexdigest()


def strict_exchanges(session: Sequence[dict[str, Any]]) -> list[tuple[str, str]] | None:
    """Pair a session into strict adjacent user/assistant exchanges, or reject it.

    Irregular sessions are reported and excluded, never repaired. EC-001's
    amendment 001 recorded the same class of session on this benchmark.
    """
    pairs: list[tuple[str, str]] = []
    index = 0
    while index + 1 < len(session):
        first, second = session[index], session[index + 1]
        if first.get("role") != "user" or second.get("role") != "assistant":
            return None
        pairs.append((first.get("content", ""), second.get("content", "")))
        index += 2
    if index != len(session):
        return None
    return pairs


def verify_dataset(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if size != DATASET_BYTES or actual != DATASET_SHA256:
        raise CorpusError(
            "Dataset identity mismatch.\n"
            f"  expected {DATASET_BYTES} bytes / {DATASET_SHA256}\n"
            f"  actual   {size} bytes / {actual}"
        )
    return {"path": str(path), "bytes": size, "sha256": actual, "commit": DATASET_COMMIT}


def selected_question_ids(items: Sequence[dict[str, Any]]) -> list[tuple[str, str]]:
    """Ranks 31-40 within each stratum, by seeded content hash.

    EC-001 registered ranks 1-20 and SAL-001 ranks 21-30. This slice does not
    overlap either, so no item enters DMR-001C that a previous study already
    reported on.
    """
    chosen: list[tuple[str, str]] = []
    for stratum in STRATA:
        ranked = sorted(
            (item["question_id"] for item in items if item["question_type"] == stratum),
            key=lambda qid: selection_rank(stratum, qid),
        )
        chosen.extend((stratum, qid) for qid in ranked[RANK_LOW - 1 : RANK_HIGH])
    return chosen


def load_cache(path: Path) -> dict[str, bytes]:
    connection = sqlite3.connect("file:" + path.as_posix() + "?mode=ro", uri=True)
    try:
        return {text: bytes(blob) for text, blob in connection.execute(
            "SELECT text, embedding FROM cache"
        )}
    finally:
        connection.close()


def build_streams(
    items: Sequence[dict[str, Any]], cache: dict[str, bytes]
) -> tuple[list[Stream], dict[str, Any]]:
    by_id = {item["question_id"]: item for item in items}
    streams: list[Stream] = []
    excluded = {
        "irregular_sessions": 0,
        "uncached_episodes": 0,
        "streams_below_minimum": [],
    }

    for stratum, question_id in selected_question_ids(items):
        item = by_id[question_id]
        token = stream_token(question_id)
        episodes: list[Episode] = []
        kept_sessions = 0
        usable = True
        for session_index, session in enumerate(item["haystack_sessions"]):
            pairs = strict_exchanges(session)
            if pairs is None:
                excluded["irregular_sessions"] += 1
                continue
            session_episodes: list[Episode] = []
            for user, assistant in pairs:
                blob = cache.get(episode_text(user, assistant))
                if blob is None or len(blob) != EMBEDDING_BYTES:
                    excluded["uncached_episodes"] += 1
                    usable = False
                    break
                pair = pair_sha256(user, assistant)
                index = len(episodes) + len(session_episodes)
                session_episodes.append(
                    Episode(
                        stream_index=index,
                        episode_hash=episode_identity(token, index, pair),
                        pair_sha256=pair,
                        source_session_index=session_index,
                        embedding_bytes=blob,
                    )
                )
            if not usable:
                break
            if session_episodes:
                episodes.extend(session_episodes)
                kept_sessions += 1
        if not usable:
            excluded["streams_below_minimum"].append(
                {"question_id": question_id, "reason": "uncached episode"}
            )
            continue
        if kept_sessions < MIN_SESSIONS or len(episodes) < MIN_EPISODES:
            excluded["streams_below_minimum"].append(
                {
                    "question_id": question_id,
                    "reason": f"{kept_sessions} sessions, {len(episodes)} episodes",
                }
            )
            continue
        streams.append(
            Stream(
                question_id=question_id,
                stratum=stratum,
                stream_token=token,
                episodes=tuple(episodes),
                source_session_count=kept_sessions,
            )
        )

    streams.sort(key=lambda stream: stream.stream_token)
    return streams, excluded


def corpus_manifest(
    streams: Sequence[Stream], dataset: dict[str, Any], excluded: dict[str, Any]
) -> dict[str, Any]:
    rows = [
        {
            "stream_token": stream.stream_token,
            "stratum": stream.stratum,
            "episode_count": stream.episode_count,
            "source_session_count": stream.source_session_count,
            "seam_count": len(stream.seam_indices()),
            "stream_digest": stream.stream_digest(),
            "vector_digest": stream.vector_digest(),
        }
        for stream in streams
    ]
    return {
        "schema": CORPUS_SCHEMA,
        "dataset": dataset,
        "selection": {
            "seed": SEED,
            "strata": list(STRATA),
            "ranks": [RANK_LOW, RANK_HIGH],
            "note": "EC-001 took ranks 1-20 and SAL-001 ranks 21-30; this slice overlaps neither",
            "minimum_sessions": MIN_SESSIONS,
            "minimum_episodes": MIN_EPISODES,
        },
        "blinding": (
            "one stream token per haystack, so the hard-boundary predicate can never "
            "fire and every boundary the former opens is one it detected; source "
            "session indices are measurement only"
        ),
        "excluded": excluded,
        "counts": {
            "streams": len(rows),
            "episodes": sum(row["episode_count"] for row in rows),
            "seams": sum(row["seam_count"] for row in rows),
            "source_sessions": sum(row["source_session_count"] for row in rows),
        },
        "streams": rows,
        "corpus_digest": _sha256(
            "\n".join(
                row["stream_token"] + ":" + row["stream_digest"] + ":" + row["vector_digest"]
                for row in rows
            ).encode("utf-8")
        ),
    }


def load_corpus(dataset_path: Path, cache_path: Path) -> tuple[list[Stream], dict[str, Any]]:
    dataset = verify_dataset(dataset_path)
    items = json.loads(dataset_path.read_text(encoding="utf-8"))
    cache = load_cache(cache_path)
    streams, excluded = build_streams(items, cache)
    return streams, corpus_manifest(streams, dataset, excluded)
