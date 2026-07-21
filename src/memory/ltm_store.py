"""Persistence helpers for the Study 003 long-term-memory write path."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class LtmSnapshot:
    """Frozen global and canonical-topic references for one promotion batch."""

    global_centroid: Optional[np.ndarray]
    topic_centroids: dict[str, np.ndarray]
    episode_count: int


def promote_episode(
    conn: sqlite3.Connection,
    episode_id: str,
    promoted_at_turn: int,
    topic: str,
    trigger_type: str,
    triggered_filter: Optional[str],
    novelty_score: float,
    repetition_score: float,
    association_score: float,
    emotional_score: float,
    weighted_score: float,
    content: str,
    embedding: np.ndarray,
) -> int | None:
    """Write one promoted STM episode and return its LTM row id, if newly promoted."""
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO ltm_episodes (
            episode_id, promoted_at_turn, topic, trigger_type, triggered_filter,
            novelty_score, repetition_score, association_score, emotional_score,
            weighted_score, content, embedding, promoted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            episode_id,
            promoted_at_turn,
            topic,
            trigger_type,
            triggered_filter,
            novelty_score,
            repetition_score,
            association_score,
            emotional_score,
            weighted_score,
            content,
            np.asarray(embedding, dtype=np.float32).tobytes(),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid) if cursor.rowcount else None


def is_episode_promoted(conn: sqlite3.Connection, episode_id: str) -> bool:
    """Return whether an STM episode has already been durably promoted."""
    return conn.execute(
        "SELECT 1 FROM ltm_episodes WHERE episode_id = ?", (episode_id,)
    ).fetchone() is not None


def log_promotion_event(
    conn: sqlite3.Connection,
    turn: int,
    topic: str,
    episodes_evaluated: int,
    episodes_promoted: int,
    event_type: str = "transition",
) -> None:
    """Write one per-topic-change promotion summary row."""
    promotion_rate = (
        episodes_promoted / episodes_evaluated if episodes_evaluated else 0.0
    )
    conn.execute(
        """
        INSERT INTO ltm_promotion_log (
            turn, topic, episodes_evaluated, episodes_promoted, promotion_rate,
            logged_at, event_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            turn,
            topic,
            episodes_evaluated,
            episodes_promoted,
            promotion_rate,
            datetime.now(timezone.utc).isoformat(),
            event_type,
        ),
    )
    conn.commit()


def get_ltm_centroid(conn: sqlite3.Connection) -> Optional[np.ndarray]:
    """Return the mean 1,024-dimensional LTM embedding, or None when empty."""
    return get_ltm_snapshot(conn).global_centroid


def get_ltm_topic_centroids(conn: sqlite3.Connection) -> dict[str, np.ndarray]:
    """Return centroids grouped by each row's current canonical STM topic."""
    return get_ltm_snapshot(conn).topic_centroids


def get_ltm_snapshot(conn: sqlite3.Connection) -> LtmSnapshot:
    """Read all batch-start LTM references in one immutable database snapshot.

    Promoted rows retain their original topic label, while their source STM
    episodes are reassigned when consolidation merges topics. Joining through
    the source episode therefore resolves each row through the current
    canonical mapping. Rows without a source episode fall back to their stored
    label for backward-compatible analysis of lightweight fixtures.
    """
    rows = conn.execute(
        """
        SELECT ltm.topic, ltm.embedding, episodes.topic_id
        FROM ltm_episodes AS ltm
        LEFT JOIN episodes ON episodes.id = ltm.episode_id
        ORDER BY ltm.id
        """
    ).fetchall()
    if not rows:
        return LtmSnapshot(None, {}, 0)

    all_embeddings: list[np.ndarray] = []
    grouped_embeddings: dict[str, list[np.ndarray]] = {}
    for stored_topic, embedding_blob, canonical_topic_id in rows:
        embedding = np.frombuffer(embedding_blob, dtype=np.float32)
        all_embeddings.append(embedding)
        group_key = canonical_topic_id or f"stored:{stored_topic}"
        grouped_embeddings.setdefault(group_key, []).append(embedding)

    global_centroid = np.mean(
        np.stack(all_embeddings), axis=0, dtype=np.float32
    )
    topic_centroids = {
        topic_id: np.mean(np.stack(embeddings), axis=0, dtype=np.float32)
        for topic_id, embeddings in grouped_embeddings.items()
    }
    return LtmSnapshot(global_centroid, topic_centroids, len(rows))


def get_ltm_episode_count(conn: sqlite3.Connection) -> int:
    """Return the number of promoted LTM episodes."""
    return int(conn.execute("SELECT COUNT(*) FROM ltm_episodes").fetchone()[0])


def get_ltm_retrieval_rows(conn: sqlite3.Connection) -> list[dict]:
    """Return LTM rows with current canonical topic and source episode content."""
    rows = conn.execute(
        """
        SELECT
            ltm.episode_id,
            ltm.promoted_at_turn,
            ltm.topic,
            ltm.trigger_type,
            ltm.triggered_filter,
            ltm.embedding,
            episodes.turn_number,
            episodes.user_message,
            episodes.assistant_message,
            episodes.topic_id,
            topics.label
        FROM ltm_episodes AS ltm
        LEFT JOIN episodes ON episodes.id = ltm.episode_id
        LEFT JOIN topics ON topics.id = episodes.topic_id
        ORDER BY ltm.id
        """
    ).fetchall()
    columns = [
        "id",
        "promoted_at_turn",
        "stored_topic",
        "trigger_type",
        "triggered_filter",
        "embedding",
        "turn_number",
        "user_message",
        "assistant_message",
        "topic_id",
        "topic_label",
    ]
    result = []
    for row in rows:
        item = dict(zip(columns, row))
        item["topic_label"] = item["topic_label"] or item["stored_topic"]
        item["user_message"] = item["user_message"] or ""
        item["assistant_message"] = item["assistant_message"] or ""
        result.append(item)
    return result
