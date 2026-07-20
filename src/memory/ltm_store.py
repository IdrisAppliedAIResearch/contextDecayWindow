"""Persistence helpers for the Study 003 long-term-memory write path."""

import sqlite3
from datetime import datetime, timezone
from typing import Optional

import numpy as np


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
) -> None:
    """Write one per-topic-change promotion summary row."""
    promotion_rate = (
        episodes_promoted / episodes_evaluated if episodes_evaluated else 0.0
    )
    conn.execute(
        """
        INSERT INTO ltm_promotion_log (
            turn, topic, episodes_evaluated, episodes_promoted, promotion_rate, logged_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            turn,
            topic,
            episodes_evaluated,
            episodes_promoted,
            promotion_rate,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def get_ltm_centroid(conn: sqlite3.Connection) -> Optional[np.ndarray]:
    """Return the mean 1,024-dimensional LTM embedding, or None when empty."""
    rows = conn.execute("SELECT embedding FROM ltm_episodes").fetchall()
    if not rows:
        return None
    embeddings = np.stack([
        np.frombuffer(row[0], dtype=np.float32) for row in rows
    ])
    return np.mean(embeddings, axis=0, dtype=np.float32)


def get_ltm_episode_count(conn: sqlite3.Connection) -> int:
    """Return the number of promoted LTM episodes."""
    return int(conn.execute("SELECT COUNT(*) FROM ltm_episodes").fetchone()[0])
