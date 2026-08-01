"""The append-only episode store and its budgeted context constructor.

The store is verbatim and append-only: episodes are never updated or
deleted, and ``context()`` never writes. The row shape and the embedded
pair text (``User: {user}\\nAssistant: {assistant}``) are carried unchanged
from the source repository's permissive store.
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
    EpisodicError,
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
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._check_config(override_config)
        self._check_model_identity()
        self._check_call_shape()

    # -- open-time gates ---------------------------------------------------

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
