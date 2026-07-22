"""Add Study 005 raw-episode and distilled-memory storage."""

import sqlite3


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def apply_migration(conn: sqlite3.Connection) -> None:
    """Apply additive Study 005 storage without changing Study 004 LTM rows."""
    episode_columns = _column_names(conn, "episodes")
    if "role" not in episode_columns:
        conn.execute(
            "ALTER TABLE episodes ADD COLUMN role TEXT NOT NULL "
            "DEFAULT 'conversation'"
        )
    if "text" not in episode_columns:
        conn.execute(
            "ALTER TABLE episodes ADD COLUMN text TEXT NOT NULL DEFAULT ''"
        )
        conn.execute(
            "UPDATE episodes SET text = "
            "'User: ' || user_message || char(10) || "
            "'Assistant: ' || assistant_message "
            "WHERE text = ''"
        )
    if "dreamed" not in episode_columns:
        conn.execute(
            "ALTER TABLE episodes ADD COLUMN dreamed INTEGER NOT NULL DEFAULT 0"
        )

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS distilled_ltm (
            id                     TEXT PRIMARY KEY,
            source_episode_id      TEXT NOT NULL,
            topic_id               TEXT NOT NULL,
            topic_label            TEXT NOT NULL,
            text                   TEXT,
            embedding              vec_float32(1024),
            source_episode_ids     TEXT NOT NULL,
            source_turns           TEXT NOT NULL,
            collapsed_episode_ids  TEXT NOT NULL,
            salience               INTEGER NOT NULL,
            dream_event            INTEGER NOT NULL,
            event_type             TEXT NOT NULL,
            status                 TEXT NOT NULL,
            created_at             TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dream_events (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            turn                   INTEGER NOT NULL,
            topic_id               TEXT NOT NULL,
            topic_label            TEXT NOT NULL,
            event_type             TEXT NOT NULL,
            extractor              TEXT NOT NULL,
            episodes_evaluated     INTEGER NOT NULL,
            survivors              INTEGER NOT NULL,
            records_written        INTEGER NOT NULL,
            marker_written         INTEGER NOT NULL,
            duplicates_collapsed   INTEGER NOT NULL,
            inference_calls        INTEGER NOT NULL,
            logged_at              TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_episodes_topic_dreamed
        ON episodes(topic_id, dreamed);

        CREATE INDEX IF NOT EXISTS idx_distilled_ltm_topic
        ON distilled_ltm(topic_id);

        CREATE INDEX IF NOT EXISTS idx_distilled_ltm_source
        ON distilled_ltm(source_episode_id);
        """
    )
    conn.commit()
