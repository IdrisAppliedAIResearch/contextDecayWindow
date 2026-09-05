from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from analysis.beam001_gpu_embedding import (
    BeamEmbeddingError,
    CachedEmbedder,
    EMBEDDING_DIMENSION,
    EmbeddingCache,
    InputRecord,
    MODEL_SHA256,
    SENTINEL_TEXT,
)


def _vector(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(size=EMBEDDING_DIMENSION).astype(np.float32)


def test_cache_round_trip_and_read_only_miss(tmp_path: Path) -> None:
    path = tmp_path / "vectors.sqlite"
    record = InputRecord("question", "q1", "What happened?")
    expected = _vector(1)
    with EmbeddingCache(path) as cache:
        assert cache.put(record, 3, expected) is True
        assert cache.put(record, 3, expected) is False
        assert cache.verify()["vector_digest_mismatches"] == 0
    with EmbeddingCache(path, read_only=True) as cache:
        assert cache.get(record.text).tobytes() == expected.tobytes()
        with pytest.raises(BeamEmbeddingError, match="cache miss"):
            cache.get("missing")


def test_cached_embedder_implements_public_callable_protocol(tmp_path: Path) -> None:
    path = tmp_path / "vectors.sqlite"
    sentinel = InputRecord("sentinel", "sentinel", SENTINEL_TEXT)
    expected = _vector(2)
    with EmbeddingCache(path) as cache:
        cache.put(sentinel, 9, expected)
    embedder = CachedEmbedder(path)
    try:
        assert embedder.model_sha256 == MODEL_SHA256
        assert embedder(SENTINEL_TEXT).tobytes() == expected.tobytes()
    finally:
        embedder.close()


def test_cache_rejects_vector_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "vectors.sqlite"
    record = InputRecord("episode", "e1", "User: u\nAssistant: a")
    with EmbeddingCache(path) as cache:
        cache.put(record, 8, _vector(3))
        with pytest.raises(BeamEmbeddingError, match="overwrite"):
            cache.put(record, 8, _vector(4))
