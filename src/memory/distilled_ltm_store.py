"""Persistence and provenance checks for Study 005 distilled memory."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone

import numpy as np


CONTENT_STATUS = "content"
NO_SALIENT_FACT_STATUS = "present_no_salient_fact"


def get_undreamed_episodes_by_topic(
    conn: sqlite3.Connection,
    topic_id: str,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            id, topic_id, user_message, assistant_message, embedding,
            turn_number, ground_truth_domain, role, text, dreamed
        FROM episodes
        WHERE topic_id = ? AND dreamed = 0
        ORDER BY turn_number, created_at, id
        """,
        (topic_id,),
    ).fetchall()
    columns = [
        "id",
        "topic_id",
        "user_message",
        "assistant_message",
        "embedding",
        "turn_number",
        "ground_truth_domain",
        "role",
        "text",
        "dreamed",
    ]
    return [dict(zip(columns, row)) for row in rows]


def write_distilled_record(
    conn: sqlite3.Connection,
    *,
    source_episode: dict,
    topic_id: str,
    topic_label: str,
    source_episode_ids: list[str],
    source_turns: list[int],
    collapsed_episode_ids: list[str],
    salience: int,
    dream_event: int,
    event_type: str,
) -> str:
    distilled_id = str(uuid.uuid4())
    text = source_episode["text"]
    embedding = np.frombuffer(
        source_episode["embedding"], dtype=np.float32
    ).tobytes()
    conn.execute(
        """
        INSERT INTO distilled_ltm (
            id, source_episode_id, topic_id, topic_label, text, embedding,
            source_episode_ids, source_turns, collapsed_episode_ids,
            salience, dream_event, event_type, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            distilled_id,
            source_episode["id"],
            topic_id,
            topic_label,
            text,
            embedding,
            json.dumps(source_episode_ids, separators=(",", ":")),
            json.dumps(source_turns, separators=(",", ":")),
            json.dumps(collapsed_episode_ids, separators=(",", ":")),
            salience,
            dream_event,
            event_type,
            CONTENT_STATUS,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return distilled_id


def write_no_salient_fact_marker(
    conn: sqlite3.Connection,
    *,
    source_episode: dict,
    topic_id: str,
    topic_label: str,
    salience: int,
    dream_event: int,
    event_type: str,
) -> str:
    distilled_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO distilled_ltm (
            id, source_episode_id, topic_id, topic_label, text, embedding,
            source_episode_ids, source_turns, collapsed_episode_ids,
            salience, dream_event, event_type, status, created_at
        ) VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            distilled_id,
            source_episode["id"],
            topic_id,
            topic_label,
            json.dumps([source_episode["id"]], separators=(",", ":")),
            json.dumps([source_episode["turn_number"]], separators=(",", ":")),
            "[]",
            salience,
            dream_event,
            event_type,
            NO_SALIENT_FACT_STATUS,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return distilled_id


def mark_episodes_dreamed(
    conn: sqlite3.Connection,
    episode_ids: list[str],
) -> None:
    if not episode_ids:
        return
    conn.executemany(
        "UPDATE episodes SET dreamed = 1 WHERE id = ?",
        [(episode_id,) for episode_id in episode_ids],
    )


def log_dream_event(
    conn: sqlite3.Connection,
    *,
    turn: int,
    topic_id: str,
    topic_label: str,
    event_type: str,
    extractor: str,
    episodes_evaluated: int,
    survivors: int,
    records_written: int,
    marker_written: bool,
    duplicates_collapsed: int,
    inference_calls: int,
) -> None:
    conn.execute(
        """
        INSERT INTO dream_events (
            turn, topic_id, topic_label, event_type, extractor,
            episodes_evaluated, survivors, records_written, marker_written,
            duplicates_collapsed, inference_calls, logged_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            turn,
            topic_id,
            topic_label,
            event_type,
            extractor,
            episodes_evaluated,
            survivors,
            records_written,
            int(marker_written),
            duplicates_collapsed,
            inference_calls,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def get_distilled_records(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            id, source_episode_id, topic_id, topic_label, text, embedding,
            source_episode_ids, source_turns, collapsed_episode_ids,
            salience, dream_event, event_type, status, created_at
        FROM distilled_ltm
        ORDER BY dream_event, topic_label, salience DESC, source_episode_id
        """
    ).fetchall()
    columns = [
        "id",
        "source_episode_id",
        "topic_id",
        "topic_label",
        "text",
        "embedding",
        "source_episode_ids",
        "source_turns",
        "collapsed_episode_ids",
        "salience",
        "dream_event",
        "event_type",
        "status",
        "created_at",
    ]
    result = []
    for row in rows:
        item = dict(zip(columns, row))
        for key in (
            "source_episode_ids",
            "source_turns",
            "collapsed_episode_ids",
        ):
            item[key] = json.loads(item[key])
        result.append(item)
    return result


def get_distilled_retrieval_rows(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            distilled.id,
            distilled.source_episode_id,
            distilled.dream_event,
            distilled.event_type,
            distilled.salience,
            distilled.source_episode_ids,
            distilled.source_turns,
            distilled.embedding,
            episodes.turn_number,
            episodes.user_message,
            episodes.assistant_message,
            COALESCE(episodes.topic_id, distilled.topic_id),
            COALESCE(topics.label, distilled.topic_label)
        FROM distilled_ltm AS distilled
        LEFT JOIN episodes
            ON episodes.id = distilled.source_episode_id
        LEFT JOIN topics
            ON topics.id = episodes.topic_id
        WHERE distilled.status = ?
        ORDER BY distilled.dream_event, distilled.id
        """,
        (CONTENT_STATUS,),
    ).fetchall()
    columns = [
        "distilled_id",
        "id",
        "dream_event",
        "event_type",
        "salience",
        "source_episode_ids",
        "source_turns",
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
        item["source_episode_ids"] = json.loads(item["source_episode_ids"])
        item["source_turns"] = json.loads(item["source_turns"])
        item["user_message"] = item["user_message"] or ""
        item["assistant_message"] = item["assistant_message"] or ""
        result.append(item)
    return result


def get_source_texts(
    conn: sqlite3.Connection,
    source_episode_ids: list[str],
) -> dict[str, str]:
    if not source_episode_ids:
        return {}
    placeholders = ",".join("?" for _ in source_episode_ids)
    rows = conn.execute(
        f"SELECT id, text FROM episodes WHERE id IN ({placeholders})",
        source_episode_ids,
    ).fetchall()
    return {episode_id: text for episode_id, text in rows}


def is_record_faithful(conn: sqlite3.Connection, record: dict) -> bool:
    if record["status"] != CONTENT_STATUS:
        return True
    sources = get_source_texts(conn, record["source_episode_ids"])
    return any(
        record["text"] in source_text
        for source_text in sources.values()
    )


def assert_record_faithful(
    conn: sqlite3.Connection,
    distilled_id: str,
) -> None:
    record = next(
        (
            item
            for item in get_distilled_records(conn)
            if item["id"] == distilled_id
        ),
        None,
    )
    if record is None:
        raise ValueError(f"Unknown distilled record: {distilled_id}")
    if not is_record_faithful(conn, record):
        raise AssertionError(
            "Distilled record text is not a verbatim source-episode span"
        )


def get_distilled_record_count(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM distilled_ltm WHERE status = ?",
            (CONTENT_STATUS,),
        ).fetchone()[0]
    )
