"""The append-only episode store and its budgeted context constructor.

The store is verbatim and append-only: episodes are never updated or
deleted, and ``context()`` never writes. The row shape and the embedded
pair text (``User: {user}\\nAssistant: {assistant}``) are carried unchanged
from the source repository's permissive store.

Durability (CC-004). The store runs at ``synchronous=FULL`` under
SQLite's rollback journal, both set explicitly rather than inherited, so
the durability point is stated rather than implied:

    **when ``append("assistant", ...)`` returns, the episode is on disk.**

SQLite has fsynced the journal and the database before the enclosing
commit completes, so a process killed at any point after that call
returns cannot lose the turn. The episode row and the clearing of the
pending user message happen in one transaction, which is what makes a
kill mid-append leave the turn either wholly present or wholly absent and
never half-written.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ._config import EpisodicConfig
from ._embedding import (
    PinnedEmbedder,
    SENTINEL_TEXT,
    embed_solo,
    vector_sha256,
)
from ._errors import (
    CallShapeError,
    ConfigMismatchError,
    EmbeddingDriftError,
    EpisodicError,
    StoreCorruptError,
    TurnOrderError,
)
from ._report import ContextReport

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    id                TEXT PRIMARY KEY,
    turn_number       INTEGER NOT NULL UNIQUE,
    user_message      TEXT NOT NULL,
    assistant_message TEXT NOT NULL,
    embedding         BLOB NOT NULL,
    created_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS episodic_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class EpisodeStore:
    """Append-only conversational memory with pure context construction.

    Opening a store runs two gates before anything else:

    1. **Config identity.** The config serializes to JSON and is stored on
       first open. Reopening with a different config raises
       ``ConfigMismatchError`` unless ``override_config=True``, which
       replaces the stored config - an explicit break, because a store's
       numbers are only meaningful under the config that produced them.
    2. **Embedder identity (H1).** A fixed sentinel string is embedded
       under the pinned call shape and the vector hash is asserted against
       the one stored on first open. Drift raises ``CallShapeError``
       naming the hazard: the carried model's vectors depend on the call
       shape, not just the text, so a changed hash means every stored
       embedding and every new query embedding live in different spaces.
    """

    def __init__(
        self,
        path: str | Path,
        config: EpisodicConfig | None = None,
        *,
        embedder=None,
        override_config: bool = False,
    ) -> None:
        self.config = config if config is not None else EpisodicConfig()
        self._embedder = embedder if embedder is not None else PinnedEmbedder()
        self._conn = sqlite3.connect(str(path))
        # Stated, not inherited: every acknowledged append is fsynced before
        # it is acknowledged. SQLite's own default is already FULL, but a
        # durability guarantee that depends on a library default is a
        # guarantee nobody can audit (CC-004 requirement 2.2.1).
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA journal_mode=DELETE")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._check_integrity()
        self._check_config(override_config)
        self._check_model_identity()
        self._check_call_shape()

    # -- open-time gates ---------------------------------------------------

    def _check_integrity(self) -> None:
        """Reject a corrupt store on open instead of serving from it.

        SQLite's journal makes a torn write recoverable, not impossible:
        a file damaged out from under the database - truncated, partially
        overwritten, restored from an inconsistent copy - still opens and
        will happily answer queries from the pages that survived. This
        turns that into a loud failure at open, which is the only place a
        caller can still do something about it.
        """
        try:
            row = self._conn.execute("PRAGMA quick_check").fetchone()
        except sqlite3.DatabaseError as error:
            raise StoreCorruptError(
                f"Store failed to open as a SQLite database: {error}"
            ) from error
        if row is None or str(row[0]).lower() != "ok":
            raise StoreCorruptError(
                "Store failed its integrity check and was not opened: "
                f"{row[0] if row else 'no result'}. The database is damaged; "
                "restore it from a checkpoint rather than reading around it."
            )

    def _check_config(self, override_config: bool) -> None:
        stored = self._meta_get("config")
        current = self.config.to_json()
        if stored is None or override_config:
            self._meta_set("config", current)
            return
        if stored != current:
            raise ConfigMismatchError(
                "Store was created under a different config. A store's "
                "numbers are only meaningful under the config that produced "
                "them; pass override_config=True only to rebind it "
                f"deliberately.\n  stored:  {stored}\n  offered: {current}"
            )

    def _check_model_identity(self) -> None:
        model_sha = getattr(self._embedder, "model_sha256", None)
        if model_sha is not None and model_sha != self.config.embedder_sha256:
            raise CallShapeError(
                "Embedder artifact does not match the pinned model hash: "
                f"config pins {self.config.embedder_sha256}, the embedder "
                f"reports {model_sha}"
            )

    def _check_call_shape(self) -> None:
        observed = vector_sha256(embed_solo(self._embedder, SENTINEL_TEXT))
        stored = self._meta_get("sentinel_sha256")
        if stored is None:
            self._meta_set("sentinel_sha256", observed)
            return
        if stored != observed:
            raise CallShapeError(
                "Embedding call-shape sentinel drifted: the sentinel text no "
                "longer embeds to the vector stored with this store "
                f"(stored {stored[:12]}..., observed {observed[:12]}...). "
                "The carried model returns different vectors for the same "
                "text under different call shapes or runtimes (DX-001), so "
                "stored and fresh embeddings are no longer comparable. Fix "
                "the embedder or rebuild the store; do not suppress this."
            )

    # -- the public API ----------------------------------------------------

    def append(self, role: str, content: str) -> None:
        """Record one message verbatim; a user+assistant pair is an episode."""
        if role not in ("user", "assistant"):
            raise EpisodicError(f"Unknown role: {role!r}")
        pending = self._meta_get("pending_user")
        if role == "user":
            if pending is not None:
                raise TurnOrderError(
                    "Two user messages in a row; the store records strict "
                    "user/assistant alternation"
                )
            self._meta_set("pending_user", content)
            return
        if pending is None:
            raise TurnOrderError("Assistant message without a user message")
        turn = self._episode_count() + 1
        embedding = embed_solo(
            self._embedder,
            f"User: {pending}\nAssistant: {content}",
        )
        self._conn.execute(
            """
            INSERT INTO episodes (
                id, turn_number, user_message, assistant_message,
                embedding, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                turn,
                pending,
                content,
                embedding.tobytes(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.execute(
            "DELETE FROM episodic_meta WHERE key = 'pending_user'"
        )
        self._conn.commit()

    def context(self, query: str, budget: int) -> tuple[str, ContextReport]:
        from ._context import build_context

        return build_context(
            episodes=self._all_episodes(),
            query_embedding=embed_solo(self._embedder, query),
            budget=budget,
            config=self.config,
        )

    def verify_embeddings(self, *, raise_on_drift: bool = True) -> dict:
        """Re-embed every stored episode and compare against what is stored.

        The embedding "cache" is not a cache: vectors live in the episode
        row, so they survive a restart by construction and there is nothing
        to rebuild. What can still go wrong is the store outliving the
        conditions that produced it - a different model artifact, a
        different runtime, a different call shape - and this is how a
        caller checks rather than assumes.

        The sentinel gate on open catches drift using one fixed string.
        This checks all of them, which is slower and stronger: it is the
        difference between "the embedder still answers the same on one
        input" and "every vector in this store is still reproducible".

        Returns a summary; raises ``EmbeddingDriftError`` on the first
        mismatch unless ``raise_on_drift=False``, in which case the
        mismatching turn numbers come back in the summary.
        """
        rows = self._conn.execute(
            """
            SELECT turn_number, user_message, assistant_message, embedding
            FROM episodes ORDER BY turn_number ASC
            """
        ).fetchall()

        mismatches: list[int] = []
        for turn, user, assistant, stored in rows:
            recomputed = embed_solo(
                self._embedder, f"User: {user}\nAssistant: {assistant}"
            )
            if recomputed.tobytes() != stored:
                mismatches.append(int(turn))
                if raise_on_drift:
                    raise EmbeddingDriftError(
                        f"Stored embedding for turn {turn} does not reproduce "
                        "from its own source text. Stored vectors and fresh "
                        "query vectors are no longer in the same space, so "
                        "every cosine in this store is unreliable. Rebuild "
                        "the store under the pinned embedder; do not "
                        "suppress this."
                    )

        return {
            "episodes_checked": len(rows),
            "mismatches": tuple(mismatches),
            "bit_identical": not mismatches,
        }

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "EpisodeStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # -- internals ---------------------------------------------------------

    def _all_episodes(self) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding
            FROM episodes
            ORDER BY turn_number ASC, id ASC
            """
        ).fetchall()
        return [
            {
                "id": row[0],
                "turn_number": row[1],
                "user_message": row[2],
                "assistant_message": row[3],
                "embedding": row[4],
            }
            for row in rows
        ]

    def _episode_count(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        )

    def _meta_get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM episodic_meta WHERE key = ?",
            (key,),
        ).fetchone()
        return None if row is None else str(row[0])

    def _meta_set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO episodic_meta (key, value) VALUES (?, ?)",
            (key, value),
        )
        self._conn.commit()
