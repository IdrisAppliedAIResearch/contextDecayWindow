"""Persistent, content-hashed embedding vectors.

The model artifact and solo-call sentinel certify how vectors are requested.
They do not certify the exact bytes returned for every text.  This cache is
the stronger run-reproduction boundary: populate once, record both digests,
then reopen read-only and refuse every miss.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import numpy as np

from ._embedding import EMBEDDING_DIMENSION, embed_solo
from ._errors import EmbeddingCacheError

_CACHE_VERSION = "episodic-embedding-cache-v1"
_CALL_SHAPE = "solo"
_DTYPE = "float32"
_COMMIT_INTERVAL = 256
_SCHEMA = """
CREATE TABLE cache (
    text TEXT PRIMARY KEY,
    embedding BLOB NOT NULL
);
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_digest(value: str, *, name: str) -> str:
    normalized = str(value).lower()
    if len(normalized) != 64:
        raise EmbeddingCacheError(f"{name} must be a SHA-256 hex digest")
    try:
        bytes.fromhex(normalized)
    except ValueError as error:
        raise EmbeddingCacheError(
            f"{name} must be a SHA-256 hex digest"
        ) from error
    return normalized


def _update_length_prefixed(digest, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, byteorder="big", signed=False))
    digest.update(value)


class EmbeddingCache:
    """A write-once/populate or strictly read-only vector cache.

    ``populate`` refuses an existing path and delegates only cache misses.
    ``reuse`` requires the expected file and canonical content digests,
    opens SQLite read-only, and raises on a miss without calling a model.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        mode: str,
        embedder=None,
        expected_file_sha256: str | None = None,
        expected_content_sha256: str | None = None,
        expected_model_sha256: str | None = None,
        legacy_v0: bool = False,
    ) -> None:
        if mode not in {"populate", "reuse"}:
            raise EmbeddingCacheError(
                f"Embedding cache mode must be populate or reuse, got {mode!r}"
            )
        self.path = Path(path).resolve()
        self.mode = mode
        self._embedder = embedder
        self.hits = 0
        self.misses = 0
        self._closed = False
        self._sealed_file_sha256: str | None = None
        self._sealed_content_sha256: str | None = None
        self._sealed_entries: int | None = None

        if mode == "populate":
            if legacy_v0:
                raise EmbeddingCacheError(
                    "legacy_v0 is valid only for read-only reuse"
                )
            if embedder is None:
                raise EmbeddingCacheError(
                    "Populate mode requires an embedding delegate"
                )
            if self.path.exists():
                raise EmbeddingCacheError(
                    f"Refusing to overwrite embedding cache: {self.path}"
                )
            model_sha = getattr(embedder, "model_sha256", None)
            if model_sha is None:
                raise EmbeddingCacheError(
                    "Embedding delegate must expose model_sha256"
                )
            self._model_sha256 = _validate_digest(
                str(model_sha), name="delegate model_sha256"
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.path))
            self._conn.execute("PRAGMA synchronous=FULL")
            self._conn.execute("PRAGMA journal_mode=DELETE")
            self._conn.executescript(_SCHEMA)
            self._conn.executemany(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                (
                    ("cache_version", _CACHE_VERSION),
                    ("model_sha256", self._model_sha256),
                    ("call_shape", _CALL_SHAPE),
                    ("dtype", _DTYPE),
                    ("dimension", str(EMBEDDING_DIMENSION)),
                ),
            )
            self._conn.commit()
            return

        if not self.path.is_file():
            raise EmbeddingCacheError(
                f"Embedding cache is missing: {self.path}"
            )
        if expected_file_sha256 is None or expected_content_sha256 is None:
            raise EmbeddingCacheError(
                "Reuse mode requires expected file and content SHA-256"
            )
        expected_file = _validate_digest(
            expected_file_sha256, name="expected_file_sha256"
        )
        observed_file = _file_sha256(self.path)
        if observed_file != expected_file:
            raise EmbeddingCacheError(
                "Embedding cache file hash mismatch: "
                f"{observed_file} != {expected_file}"
            )

        uri = f"file:{self.path.as_posix()}?mode=ro"
        self._conn = sqlite3.connect(uri, uri=True)
        metadata = self._metadata()
        self._validate_metadata(metadata, legacy_v0=legacy_v0)
        self._model_sha256 = metadata["model_sha256"]
        expected_model = (
            str(getattr(embedder, "model_sha256"))
            if embedder is not None
            and getattr(embedder, "model_sha256", None) is not None
            else expected_model_sha256
        )
        if expected_model is None:
            self._conn.close()
            raise EmbeddingCacheError(
                "Reuse mode requires a delegate or expected_model_sha256"
            )
        expected_model = _validate_digest(
            expected_model, name="expected_model_sha256"
        )
        if self._model_sha256 != expected_model:
            self._conn.close()
            raise EmbeddingCacheError(
                "Embedding cache model hash mismatch: "
                f"{self._model_sha256} != {expected_model}"
            )

        expected_content = _validate_digest(
            expected_content_sha256, name="expected_content_sha256"
        )
        observed_content = self._content_sha256(legacy_v0=legacy_v0)
        if observed_content != expected_content:
            self._conn.close()
            raise EmbeddingCacheError(
                "Embedding cache content hash mismatch: "
                f"{observed_content} != {expected_content}"
            )
        self._sealed_file_sha256 = observed_file
        self._sealed_content_sha256 = observed_content
        self._sealed_entries = self._entry_count()

    @classmethod
    def inspect_legacy_v0(
        cls,
        path: str | Path,
        *,
        expected_file_sha256: str,
        expected_model_sha256: str,
    ) -> dict:
        """Bind a retained pre-contract cache to its canonical content hash."""

        resolved = Path(path).resolve()
        expected_file = _validate_digest(
            expected_file_sha256, name="expected_file_sha256"
        )
        observed_file = _file_sha256(resolved)
        if observed_file != expected_file:
            raise EmbeddingCacheError(
                "Embedding cache file hash mismatch: "
                f"{observed_file} != {expected_file}"
            )
        connection = sqlite3.connect(
            f"file:{resolved.as_posix()}?mode=ro", uri=True
        )
        inspector = cls.__new__(cls)
        inspector.path = resolved
        inspector._conn = connection
        try:
            metadata = inspector._metadata()
            inspector._validate_metadata(metadata, legacy_v0=True)
            expected_model = _validate_digest(
                expected_model_sha256, name="expected_model_sha256"
            )
            if metadata["model_sha256"] != expected_model:
                raise EmbeddingCacheError(
                    "Embedding cache model hash mismatch: "
                    f"{metadata['model_sha256']} != {expected_model}"
                )
            content_sha = inspector._content_sha256(legacy_v0=True)
            entries = inspector._entry_count()
        finally:
            connection.close()
        return {
            "path": str(resolved),
            "bytes": resolved.stat().st_size,
            "file_sha256": observed_file,
            "content_sha256": content_sha,
            "entries": entries,
            "model_sha256": metadata["model_sha256"],
            "call_shape": _CALL_SHAPE,
            "dtype": _DTYPE,
            "dimension": EMBEDDING_DIMENSION,
            "legacy_v0": True,
        }

    @property
    def model_sha256(self) -> str:
        return self._model_sha256

    @property
    def cache_size(self) -> int:
        if self._sealed_entries is not None:
            return self._sealed_entries
        return self._entry_count()

    @property
    def file_sha256(self) -> str:
        if self._sealed_file_sha256 is not None:
            return self._sealed_file_sha256
        if not self.path.is_file():
            raise EmbeddingCacheError("Embedding cache file does not exist")
        return _file_sha256(self.path)

    @property
    def content_sha256(self) -> str:
        if self._sealed_content_sha256 is not None:
            return self._sealed_content_sha256
        return self._content_sha256()

    def record(self) -> dict:
        """Return complete provenance for a sealed or currently open cache."""

        if self.mode == "populate" and not self._closed:
            self._conn.commit()
        return {
            "path": str(self.path),
            "bytes": self.path.stat().st_size,
            "file_sha256": self.file_sha256,
            "content_sha256": self.content_sha256,
            "entries": self.cache_size,
            "hits": self.hits,
            "misses": self.misses,
            "model_sha256": self.model_sha256,
            "call_shape": _CALL_SHAPE,
            "dtype": _DTYPE,
            "dimension": EMBEDDING_DIMENSION,
            "mode": self.mode,
        }

    def __call__(self, text: str) -> np.ndarray:
        row = self._conn.execute(
            "SELECT embedding FROM cache WHERE text = ?", (text,)
        ).fetchone()
        if row is not None:
            self.hits += 1
            return self._decode_vector(row[0])
        if self.mode == "reuse":
            raise EmbeddingCacheError(
                "Read-only embedding cache miss; no model call is allowed"
            )

        vector = embed_solo(self._embedder, text)
        raw = np.asarray(vector, dtype=np.float32).tobytes()
        self._conn.execute(
            "INSERT INTO cache (text, embedding) VALUES (?, ?)", (text, raw)
        )
        self.misses += 1
        if self.misses % _COMMIT_INTERVAL == 0:
            self._conn.commit()
        return self._decode_vector(raw)

    def close(self) -> None:
        if self._closed:
            return
        if self.mode == "populate":
            self._conn.commit()
            self._sealed_content_sha256 = self._content_sha256()
        self._sealed_entries = self._entry_count()
        self._conn.close()
        if self.mode == "populate":
            self._sealed_file_sha256 = _file_sha256(self.path)
        self._closed = True

    def __enter__(self) -> "EmbeddingCache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _metadata(self) -> dict[str, str]:
        try:
            return dict(
                self._conn.execute(
                    "SELECT key, value FROM metadata"
                ).fetchall()
            )
        except sqlite3.DatabaseError as error:
            raise EmbeddingCacheError(
                f"Embedding cache metadata is unreadable: {error}"
            ) from error

    @staticmethod
    def _validate_metadata(
        metadata: dict[str, str], *, legacy_v0: bool = False
    ) -> None:
        expected = {
            "call_shape": _CALL_SHAPE,
            "dtype": _DTYPE,
            "dimension": str(EMBEDDING_DIMENSION),
        }
        if not legacy_v0:
            expected["cache_version"] = _CACHE_VERSION
        elif "cache_version" in metadata:
            raise EmbeddingCacheError(
                "legacy_v0 cache unexpectedly declares cache_version"
            )
        for key, value in expected.items():
            if metadata.get(key) != value:
                raise EmbeddingCacheError(
                    f"Embedding cache metadata {key!r} differs: "
                    f"{metadata.get(key)!r} != {value!r}"
                )
        _validate_digest(
            metadata.get("model_sha256", ""), name="cached model_sha256"
        )

    def _content_sha256(self, *, legacy_v0: bool = False) -> str:
        metadata = self._metadata()
        self._validate_metadata(metadata, legacy_v0=legacy_v0)
        digest = hashlib.sha256()
        _update_length_prefixed(digest, _CACHE_VERSION.encode("utf-8"))
        for key in ("model_sha256", "call_shape", "dtype", "dimension"):
            _update_length_prefixed(digest, key.encode("utf-8"))
            _update_length_prefixed(digest, metadata[key].encode("utf-8"))
        rows = self._conn.execute(
            "SELECT text, embedding FROM cache"
        ).fetchall()
        for text, raw in sorted(rows, key=lambda row: row[0].encode("utf-8")):
            self._decode_vector(raw)
            _update_length_prefixed(digest, text.encode("utf-8"))
            _update_length_prefixed(digest, bytes(raw))
        return digest.hexdigest()

    def _entry_count(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        )

    @staticmethod
    def _decode_vector(raw: bytes) -> np.ndarray:
        expected_bytes = EMBEDDING_DIMENSION * np.dtype(np.float32).itemsize
        if len(raw) != expected_bytes:
            raise EmbeddingCacheError(
                f"Cached vector has {len(raw)} bytes; expected {expected_bytes}"
            )
        return np.frombuffer(raw, dtype=np.float32).copy().reshape(
            EMBEDDING_DIMENSION
        )
