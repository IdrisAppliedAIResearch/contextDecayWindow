import sqlite3
import uuid
from datetime import datetime, timezone


def store_episode(
    conn: sqlite3.Connection,
    user_message: str,
    assistant_message: str,
    embedding,
    turn_number: int,
    ground_truth_domain: str | None = None,
) -> str:
    episode_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    text = f"User: {user_message}\nAssistant: {assistant_message}"

    conn.execute(
        """
        INSERT INTO episodes (
            id, topic_id, user_message, assistant_message,
            embedding, turn_number, ground_truth_domain, created_at,
            last_retrieved_at, retrieval_count, role, text, dreamed
        ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, NULL, 0, ?, ?, 0)
        """,
        (
            episode_id,
            user_message,
            assistant_message,
            embedding.tobytes(),
            turn_number,
            ground_truth_domain,
            created_at,
            "conversation",
            text,
        ),
    )
    conn.commit()
    return episode_id


def get_episode_by_id(conn: sqlite3.Connection, episode_id: str):
    cursor = conn.execute(
        "SELECT id, topic_id, user_message, assistant_message, "
        "embedding, turn_number, ground_truth_domain, created_at, last_retrieved_at, "
        "retrieval_count, role, text, dreamed FROM episodes WHERE id = ?",
        (episode_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [
        "id", "topic_id", "user_message", "assistant_message",
        "embedding", "turn_number", "ground_truth_domain", "created_at", "last_retrieved_at",
        "retrieval_count", "role", "text", "dreamed",
    ]
    return dict(zip(columns, row))


def get_episodes_by_topic(conn: sqlite3.Connection, topic_id: str) -> list[dict]:
    """Return a topic's episodes in their original conversation order."""
    cursor = conn.execute(
        "SELECT id, topic_id, user_message, assistant_message, "
        "embedding, turn_number, ground_truth_domain, created_at, last_retrieved_at, "
        "retrieval_count, role, text, dreamed FROM episodes WHERE topic_id = ? "
        "ORDER BY turn_number, created_at",
        (topic_id,),
    )
    columns = [
        "id", "topic_id", "user_message", "assistant_message",
        "embedding", "turn_number", "ground_truth_domain", "created_at", "last_retrieved_at",
        "retrieval_count", "role", "text", "dreamed",
    ]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def update_episode_topic(conn: sqlite3.Connection, episode_id: str, topic_id: str) -> None:
    conn.execute(
        "UPDATE episodes SET topic_id = ? WHERE id = ?",
        (topic_id, episode_id),
    )
    conn.commit()
