from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from pathlib import Path

import numpy as np

from .config import EMBEDDING_DIMENSION
from .embedding import normalize_embedding


class EmbeddingCache:
    """Persistent mechanism-only cache keyed by model and UTF-8 text hashes."""

    def __init__(self, path: Path, model_sha256: str) -> None:
        self.path = path
        self.model_sha256 = model_sha256
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                model_sha256 TEXT NOT NULL,
                text_sha256 TEXT NOT NULL,
                dimension INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                PRIMARY KEY (model_sha256, text_sha256)
            )
            """
        )
        self._connection.commit()

    @staticmethod
    def _text_sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> np.ndarray | None:
        row = self._connection.execute(
            """
            SELECT dimension, embedding
            FROM embeddings
            WHERE model_sha256 = ? AND text_sha256 = ?
            """,
            (self.model_sha256, self._text_sha256(text)),
        ).fetchone()
        if row is None:
            return None
        dimension, blob = row
        if int(dimension) != EMBEDDING_DIMENSION:
            raise AssertionError("Cached embedding dimension does not match protocol")
        vector = np.frombuffer(blob, dtype=np.float32).copy()
        return normalize_embedding(vector)

    def put(self, text: str, vector: np.ndarray) -> np.ndarray:
        normalized = normalize_embedding(vector)
        self._connection.execute(
            """
            INSERT OR REPLACE INTO embeddings (
                model_sha256, text_sha256, dimension, embedding
            ) VALUES (?, ?, ?, ?)
            """,
            (
                self.model_sha256,
                self._text_sha256(text),
                EMBEDDING_DIMENSION,
                normalized.tobytes(),
            ),
        )
        return normalized

    def get_or_embed(
        self,
        text: str,
        embedder: Callable[[str], np.ndarray],
    ) -> np.ndarray:
        cached = self.get(text)
        if cached is not None:
            return cached
        vector = self.put(text, embedder(text))
        self._connection.commit()
        return vector

    def get_or_embed_many(
        self,
        texts: list[str],
        embedder: Callable[[str], np.ndarray],
    ) -> list[np.ndarray]:
        results: list[np.ndarray | None] = [self.get(text) for text in texts]
        missing_positions: dict[str, list[int]] = {}
        for index, (text, vector) in enumerate(zip(texts, results, strict=True)):
            if vector is None:
                missing_positions.setdefault(text, []).append(index)

        missing_texts = list(missing_positions)
        if missing_texts:
            batch = getattr(embedder, "embed_many", None)
            vectors = (
                batch(missing_texts)
                if callable(batch)
                else [embedder(text) for text in missing_texts]
            )
            if len(vectors) != len(missing_texts):
                raise AssertionError("Embedder returned the wrong batch size")
            for text, vector in zip(missing_texts, vectors, strict=True):
                normalized = self.put(text, vector)
                for index in missing_positions[text]:
                    results[index] = normalized
            self._connection.commit()

        if any(vector is None for vector in results):
            raise AssertionError("Embedding cache left an unresolved vector")
        return [np.asarray(vector, dtype=np.float32) for vector in results]

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "EmbeddingCache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
