"""Initialize the Study 003 long-term-memory tables."""

import argparse
import sqlite3

import sqlite_vec


def apply_migration(conn: sqlite3.Connection) -> None:
    """Create Study 003 LTM tables if they do not already exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ltm_episodes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id          TEXT NOT NULL,
            promoted_at_turn    INTEGER NOT NULL,
            topic               TEXT NOT NULL,
            trigger_type        TEXT NOT NULL,
            triggered_filter    TEXT,
            novelty_score       REAL NOT NULL,
            repetition_score    REAL NOT NULL,
            association_score   REAL NOT NULL,
            emotional_score     REAL NOT NULL,
            weighted_score      REAL NOT NULL,
            content             TEXT NOT NULL,
            embedding           vec_float32(1024) NOT NULL,
            promoted_at         TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ltm_promotion_log (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            turn                INTEGER NOT NULL,
            topic               TEXT NOT NULL,
            episodes_evaluated  INTEGER NOT NULL,
            episodes_promoted   INTEGER NOT NULL,
            promotion_rate      REAL NOT NULL,
            logged_at           TEXT NOT NULL
        );
    """)
    conn.commit()


def _connect(database_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database_path", help="SQLite database to migrate")
    args = parser.parse_args()

    conn = _connect(args.database_path)
    try:
        apply_migration(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
