from __future__ import annotations

import hashlib

import numpy as np
import pytest

from episodic import EmbeddingCache, EmbeddingCacheError
from src.analysis.e006_p3_tier4a_capture import (
    CARRIED_EMBEDDING_SHA256,
    LockedQuery,
    load_locked_queries,
    populate_cache,
)


class FakeEmbedder:
    model_sha256 = CARRIED_EMBEDDING_SHA256

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        vector = np.arange(1, 1025, dtype=np.float32)
        return vector * (1.0 + len(text) / 1000.0)


def test_locked_inventory_has_48_unique_queries_in_registered_order() -> None:
    queries = load_locked_queries()

    assert len(queries) == 48
    assert len({query.text for query in queries}) == 48
    assert list(queries) == sorted(
        queries, key=lambda row: (row.corpus_id, row.query_id)
    )


def test_capture_is_solo_normalized_and_read_only_reusable(tmp_path) -> None:
    queries = tuple(
        LockedQuery("c", f"q{index}", text, tmp_path / "queries.json")
        for index, text in enumerate(("alpha", "beta"))
    )
    delegate = FakeEmbedder()
    path = tmp_path / "capture.sqlite"

    record, rows = populate_cache(queries, path, delegate)

    assert delegate.calls == 2
    assert record["entries"] == 2
    assert [row["query_id"] for row in rows] == ["q0", "q1"]
    assert all(row["dtype"] == "float32" for row in rows)
    with EmbeddingCache(
        path,
        mode="reuse",
        expected_file_sha256=record["file_sha256"],
        expected_content_sha256=record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        vector = cache("alpha")
        assert np.linalg.norm(vector) == pytest.approx(1.0)
        assert hashlib.sha256(vector.tobytes()).hexdigest() == rows[0][
            "vector_sha256"
        ]
        with pytest.raises(EmbeddingCacheError, match="no model call"):
            cache("missing")


def test_capture_refuses_to_overwrite(tmp_path) -> None:
    path = tmp_path / "capture.sqlite"
    path.write_bytes(b"retained")

    with pytest.raises(EmbeddingCacheError, match="Refusing to overwrite"):
        populate_cache(
            (LockedQuery("c", "q", "alpha", tmp_path / "q.json"),),
            path,
            FakeEmbedder(),
        )
