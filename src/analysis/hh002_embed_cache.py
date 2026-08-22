"""Disk-backed embedding cache for HH-002.

The run spans hours and several process restarts, and the embedding endpoint
on this account refills at roughly sixty calls a minute.  Losing the cache on
restart costs an hour and buys nothing: the same text sent to the same model in
the same one-per-call shape is the same request.

Keyed by ``(model, sha256(text), shape)``.  ``shape`` distinguishes a vector
that arrived from a single-text request from one that arrived inside a batch,
because this programme has measured those to differ - see
``embedding-call-shape-changes-results``.  A cached single-text vector is
therefore never served to a caller that asked for batch semantics, or the
reverse.
"""

from __future__ import annotations

import array
import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Sequence

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vectors (
    model TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    shape TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL,
    PRIMARY KEY (model, text_sha256, shape)
);
"""


class EmbedCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute(_SCHEMA)
        self._connection.commit()

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, model: str, text: str, shape: str) -> list[float] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT vector FROM vectors WHERE model=? AND text_sha256=? "
                "AND shape=?",
                (model, self._key(text), shape),
            ).fetchone()
        if row is None:
            return None
        values = array.array("f")
        values.frombytes(row[0])
        return list(values)

    def put(
        self, model: str, text: str, shape: str, vector: Sequence[float]
    ) -> None:
        blob = array.array("f", vector).tobytes()
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO vectors "
                "(model, text_sha256, shape, dim, vector) VALUES (?,?,?,?,?)",
                (model, self._key(text), shape, len(vector), blob),
            )
            self._connection.commit()

    def put_many(
        self,
        model: str,
        shape: str,
        pairs: Iterable[tuple[str, Sequence[float]]],
    ) -> None:
        rows = [
            (model, self._key(text), shape, len(vector),
             array.array("f", vector).tobytes())
            for text, vector in pairs
        ]
        if not rows:
            return
        with self._lock:
            self._connection.executemany(
                "INSERT OR REPLACE INTO vectors "
                "(model, text_sha256, shape, dim, vector) VALUES (?,?,?,?,?)",
                rows,
            )
            self._connection.commit()

    def count(self) -> int:
        with self._lock:
            return int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM vectors"
                ).fetchone()[0]
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()


__all__ = ["EmbedCache"]
