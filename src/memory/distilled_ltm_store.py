"""Persistence and provenance checks for Study 005 distilled memory."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone

import numpy as np


CONTENT_STATUS = "content"
NO_SALIENT_FACT_STATUS = "present_no_salient_fact"


def _stable_distilled_id(
    *,
    topic_label: str,
    source_turns: list[int],
    source_text: str,
    dream_event: int,
    event_type: str,
    status: str,
) -> str:
    identity = json.dumps(
        {
            "dream_event": dream_event,
            "event_type": event_type,
            "source_text": source_text,
            "source_turns": source_turns,
            "status": status,
            "topic_label": topic_label,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))


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
    text = source_episode["text"]
    distilled_id = _stable_distilled_id(
        topic_label=topic_label,
        source_turns=source_turns,
        source_text=text,
        dream_event=dream_event,
        event_type=event_type,
        status=CONTENT_STATUS,
    )
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
    source_turns = [source_episode["turn_number"]]
    distilled_id = _stable_distilled_id(
        topic_label=topic_label,
        source_turns=source_turns,
        source_text=source_episode["text"],
        dream_event=dream_event,
        event_type=event_type,
        status=NO_SALIENT_FACT_STATUS,
    )
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
            json.dumps(source_turns, separators=(",", ":")),
            "[]",
            salience,
            dream_event,
            event_type,
            NO_SALIENT_FACT_STATUS,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return distilled_id


def write_distilled_span_record(
    conn: sqlite3.Connection,
    *,
    span_text: str,
    source_episode: dict,
    topic_id: str,
    topic_label: str,
    role: str,
    span_start: int,
    span_end: int,
    word_count: int,
    named_entities: int,
    numeric_tokens: int,
    base: int,
    density: float,
    salience_score: float,
    segmenter: str,
    embedding: np.ndarray,
    source_episode_ids: list[str],
    source_turns: list[int],
    collapsed_episode_ids: list[str],
    dream_event: int,
    event_type: str,
) -> str:
    """Persist one selected span with full span-level provenance.

    ``salience`` keeps Study 005's meaning (absolute base count) so the column is
    comparable across studies; the density-scaled score Study 006 ranks on is
    stored in ``salience_score``.
    """
    distilled_id = _stable_distilled_id(
        topic_label=topic_label,
        source_turns=source_turns,
        source_text=f"{span_start}:{span_end}:{role}:{span_text}",
        dream_event=dream_event,
        event_type=event_type,
        status=CONTENT_STATUS,
    )
    conn.execute(
        """
        INSERT INTO distilled_ltm (
            id, source_episode_id, topic_id, topic_label, text, embedding,
            source_episode_ids, source_turns, collapsed_episode_ids,
            salience, dream_event, event_type, status, created_at,
            role, span_start, span_end, word_count, named_entities,
            numeric_tokens, base, density, salience_score, segmenter
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            distilled_id,
            source_episode["id"],
            topic_id,
            topic_label,
            span_text,
            np.asarray(embedding, dtype=np.float32).tobytes(),
            json.dumps(source_episode_ids, separators=(",", ":")),
            json.dumps(source_turns, separators=(",", ":")),
            json.dumps(collapsed_episode_ids, separators=(",", ":")),
            base,
            dream_event,
            event_type,
            CONTENT_STATUS,
            datetime.now(timezone.utc).isoformat(),
            role,
            span_start,
            span_end,
            word_count,
            named_entities,
            numeric_tokens,
            base,
            density,
            salience_score,
            segmenter,
        ),
    )
    return distilled_id


def get_span_record(conn: sqlite3.Connection, distilled_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT id, source_episode_id, text, status, role, span_start, span_end
        FROM distilled_ltm WHERE id = ?
        """,
        (distilled_id,),
    ).fetchone()
    if row is None:
        return None
    columns = [
        "id",
        "source_episode_id",
        "text",
        "status",
        "role",
        "span_start",
        "span_end",
    ]
    return dict(zip(columns, row))


def assert_span_record_faithful(
    conn: sqlite3.Connection,
    distilled_id: str,
) -> None:
    """Assert the record reproduces its source *at the recorded offsets*.

    Stronger than the Study 005 substring check: a record whose text appears
    somewhere in the source but not at its own recorded offsets is a failure,
    because the offsets are what the provenance claim rests on.
    """
    record = get_span_record(conn, distilled_id)
    if record is None:
        raise ValueError(f"Unknown distilled record: {distilled_id}")
    if record["status"] != CONTENT_STATUS:
        return
    if record["span_start"] is None or record["span_end"] is None:
        raise AssertionError(
            "Span record is missing the character offsets its provenance "
            "claim depends on"
        )
    sources = get_source_texts(conn, [record["source_episode_id"]])
    source_text = sources.get(record["source_episode_id"])
    if source_text is None:
        raise AssertionError(
            "Span record references a source episode that is not in the "
            "raw store"
        )
    excerpt = source_text[record["span_start"]:record["span_end"]]
    if excerpt != record["text"]:
        raise AssertionError(
            "Distilled span text does not match its source at the recorded "
            "character offsets"
        )


def log_span_inventory(
    conn: sqlite3.Connection,
    *,
    dream_event: int,
    topic_id: str,
    topic_label: str,
    rows: list[dict],
) -> None:
    if not rows:
        return
    logged_at = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        """
        INSERT INTO span_inventory (
            dream_event, topic_id, topic_label, episode_id, turn_number,
            role, span_start, span_end, text, word_count, named_entities,
            numeric_tokens, base, density, salience_score, eligible,
            rejection_reason, selected, collapsed_into, logged_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                dream_event,
                topic_id,
                topic_label,
                row["episode_id"],
                row["turn_number"],
                row["role"],
                row["span_start"],
                row["span_end"],
                row["text"],
                row["word_count"],
                row["named_entities"],
                row["numeric_tokens"],
                row["base"],
                row["density"],
                row["salience_score"],
                int(row["eligible"]),
                row["rejection_reason"],
                int(row["selected"]),
                row.get("collapsed_into"),
                logged_at,
            )
            for row in rows
        ],
    )


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
    segmenter: str | None = None,
    spans_evaluated: int | None = None,
    spans_eligible: int | None = None,
    salience_floor: float | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO dream_events (
            turn, topic_id, topic_label, event_type, extractor,
            episodes_evaluated, survivors, records_written, marker_written,
            duplicates_collapsed, inference_calls, logged_at,
            segmenter, spans_evaluated, spans_eligible, salience_floor
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            segmenter,
            spans_evaluated,
            spans_eligible,
            salience_floor,
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
