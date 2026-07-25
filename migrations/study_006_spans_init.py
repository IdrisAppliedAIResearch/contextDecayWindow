"""Add Study 006 span-level provenance and scoring columns.

Additive only. Study 005 rows keep their meaning: ``salience`` remains the
absolute entity+numeric count, and the density-scaled score Study 006 selects on
is stored alongside it in ``salience_score`` so both policies' outputs can sit in
one store without either being reinterpreted.
"""

import sqlite3


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def apply_migration(conn: sqlite3.Connection) -> None:
    distilled_columns = _column_names(conn, "distilled_ltm")
    for name, definition in (
        ("role", "TEXT"),
        ("span_start", "INTEGER"),
        ("span_end", "INTEGER"),
        ("word_count", "INTEGER"),
        ("named_entities", "INTEGER"),
        ("numeric_tokens", "INTEGER"),
        ("base", "INTEGER"),
        ("density", "REAL"),
        ("salience_score", "REAL"),
        ("segmenter", "TEXT"),
    ):
        if name not in distilled_columns:
            conn.execute(
                f"ALTER TABLE distilled_ltm ADD COLUMN {name} {definition}"
            )

    dream_event_columns = _column_names(conn, "dream_events")
    for name, definition in (
        ("segmenter", "TEXT"),
        ("spans_evaluated", "INTEGER"),
        ("spans_eligible", "INTEGER"),
        ("salience_floor", "REAL"),
    ):
        if name not in dream_event_columns:
            conn.execute(
                f"ALTER TABLE dream_events ADD COLUMN {name} {definition}"
            )

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS span_inventory (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            dream_event        INTEGER NOT NULL,
            topic_id           TEXT NOT NULL,
            topic_label        TEXT NOT NULL,
            episode_id         TEXT NOT NULL,
            turn_number        INTEGER NOT NULL,
            role               TEXT NOT NULL,
            span_start         INTEGER NOT NULL,
            span_end           INTEGER NOT NULL,
            text               TEXT NOT NULL,
            word_count         INTEGER NOT NULL,
            named_entities     INTEGER NOT NULL,
            numeric_tokens     INTEGER NOT NULL,
            base               INTEGER NOT NULL,
            density            REAL NOT NULL,
            salience_score     REAL NOT NULL,
            eligible           INTEGER NOT NULL,
            rejection_reason   TEXT,
            selected           INTEGER NOT NULL DEFAULT 0,
            collapsed_into     TEXT,
            logged_at          TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_span_inventory_event
        ON span_inventory(dream_event, topic_id);
        """
    )
    conn.commit()
