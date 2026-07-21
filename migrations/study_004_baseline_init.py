"""Add Study 004 baseline-correction metadata to existing study databases."""

import sqlite3


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def apply_migration(conn: sqlite3.Connection) -> None:
    """Apply additive Study 004 columns without changing Study 003 rows."""
    if "ground_truth_domain" not in _column_names(conn, "episodes"):
        conn.execute("ALTER TABLE episodes ADD COLUMN ground_truth_domain TEXT")

    if "event_type" not in _column_names(conn, "ltm_promotion_log"):
        conn.execute(
            "ALTER TABLE ltm_promotion_log "
            "ADD COLUMN event_type TEXT NOT NULL DEFAULT 'transition'"
        )

    conn.commit()
