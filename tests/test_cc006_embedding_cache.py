import hashlib
import sqlite3

import numpy as np
import pytest

from episodic import EmbeddingCache, EmbeddingCacheError


class Delegate:
    model_sha256 = "a" * 64

    def __init__(self, *, offset: float = 0.0) -> None:
        self.calls = 0
        self.offset = offset

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        return np.full(1024, len(text) + self.offset, dtype=np.float32)


def file_sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def populated(path, texts=("alpha", "beta")) -> tuple[dict, Delegate]:
    delegate = Delegate()
    cache = EmbeddingCache(path, mode="populate", embedder=delegate)
    with cache:
        for text in texts:
            cache(text)
        content_sha = cache.content_sha256
        entries = cache.cache_size
    return {
        "file_sha256": cache.file_sha256,
        "content_sha256": content_sha,
        "entries": entries,
    }, delegate


def test_c1_populate_reuses_exact_vector_without_second_call(tmp_path) -> None:
    path = tmp_path / "cache.db"
    delegate = Delegate()
    cache = EmbeddingCache(path, mode="populate", embedder=delegate)
    with cache:
        first = cache("same")
        second = cache("same")
        assert cache.cache_size == 1
        assert cache.hits == 1
        assert cache.misses == 1
    assert delegate.calls == 1
    assert np.array_equal(first, second)


def test_c2_reuse_is_read_only_and_makes_zero_model_calls(tmp_path) -> None:
    path = tmp_path / "cache.db"
    record, _ = populated(path)
    delegate = Delegate(offset=99.0)
    with EmbeddingCache(
        path,
        mode="reuse",
        embedder=delegate,
        expected_file_sha256=record["file_sha256"],
        expected_content_sha256=record["content_sha256"],
    ) as cache:
        assert np.all(cache("alpha") == len("alpha"))
        assert np.all(cache("beta") == len("beta"))
        assert cache.misses == 0
    assert delegate.calls == 0


def test_c3_altered_vector_fails_canonical_content_assertion(tmp_path) -> None:
    path = tmp_path / "cache.db"
    record, _ = populated(path)
    with sqlite3.connect(path) as connection:
        raw = bytearray(
            connection.execute(
                "SELECT embedding FROM cache WHERE text = 'alpha'"
            ).fetchone()[0]
        )
        raw[0] ^= 1
        connection.execute(
            "UPDATE cache SET embedding = ? WHERE text = 'alpha'",
            (bytes(raw),),
        )
    with pytest.raises(EmbeddingCacheError, match="content hash mismatch"):
        EmbeddingCache(
            path,
            mode="reuse",
            expected_file_sha256=file_sha256(path),
            expected_content_sha256=record["content_sha256"],
            expected_model_sha256="a" * 64,
        )


def test_c4_wrong_file_hash_fails_before_sqlite_open(tmp_path) -> None:
    path = tmp_path / "not-sqlite.db"
    path.write_bytes(b"not sqlite")
    with pytest.raises(EmbeddingCacheError, match="file hash mismatch"):
        EmbeddingCache(
            path,
            mode="reuse",
            expected_file_sha256="0" * 64,
            expected_content_sha256="0" * 64,
            expected_model_sha256="a" * 64,
        )


def test_c5_reuse_miss_is_fatal_without_delegate_call(tmp_path) -> None:
    path = tmp_path / "cache.db"
    record, _ = populated(path, texts=("present",))
    delegate = Delegate()
    with EmbeddingCache(
        path,
        mode="reuse",
        embedder=delegate,
        expected_file_sha256=record["file_sha256"],
        expected_content_sha256=record["content_sha256"],
    ) as cache:
        with pytest.raises(EmbeddingCacheError, match="no model call"):
            cache("missing")
    assert delegate.calls == 0


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("call_shape", "batch", "call_shape"),
        ("dtype", "float64", "dtype"),
        ("dimension", "3", "dimension"),
    ],
)
def test_c6_fixed_metadata_mismatch_fails(
    tmp_path, key, value, message
) -> None:
    path = tmp_path / f"{key}.db"
    record, _ = populated(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE metadata SET value = ? WHERE key = ?", (value, key)
        )
    with pytest.raises(EmbeddingCacheError, match=message):
        EmbeddingCache(
            path,
            mode="reuse",
            expected_file_sha256=file_sha256(path),
            expected_content_sha256=record["content_sha256"],
            expected_model_sha256="a" * 64,
        )


def test_c6_model_metadata_mismatch_fails(tmp_path) -> None:
    path = tmp_path / "cache.db"
    record, _ = populated(path)
    with pytest.raises(EmbeddingCacheError, match="model hash mismatch"):
        EmbeddingCache(
            path,
            mode="reuse",
            expected_file_sha256=record["file_sha256"],
            expected_content_sha256=record["content_sha256"],
            expected_model_sha256="b" * 64,
        )


def test_c7_canonical_digest_ignores_insertion_and_sqlite_layout(tmp_path) -> None:
    first = tmp_path / "first.db"
    second = tmp_path / "second.db"
    first_record, _ = populated(first, texts=("alpha", "beta"))
    second_record, _ = populated(second, texts=("beta", "alpha"))
    assert first_record["content_sha256"] == second_record["content_sha256"]


def test_record_contains_both_hashes_and_provenance(tmp_path) -> None:
    path = tmp_path / "cache.db"
    cache = EmbeddingCache(path, mode="populate", embedder=Delegate())
    with cache:
        cache("alpha")
    record = cache.record()
    assert record["content_sha256"]
    assert record["file_sha256"]
    assert record["entries"] == 1
    assert record["call_shape"] == "solo"
    assert record["dtype"] == "float32"
    assert record["dimension"] == 1024


def test_c9_legacy_ec002_shape_is_adopted_read_only_with_both_hashes(
    tmp_path,
) -> None:
    path = tmp_path / "legacy.db"
    raw = np.full(1024, 3.0, dtype=np.float32).tobytes()
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE cache (
                text TEXT PRIMARY KEY,
                embedding BLOB NOT NULL
            );
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            (
                ("model_sha256", "a" * 64),
                ("call_shape", "solo"),
                ("dtype", "float32"),
                ("dimension", "1024"),
            ),
        )
        connection.execute(
            "INSERT INTO cache (text, embedding) VALUES (?, ?)",
            ("old", raw),
        )

    # First inspection computes the canonical digest against the exact
    # retained legacy bytes. The asserted reopen is the adoption boundary.
    adoption = EmbeddingCache.inspect_legacy_v0(
        path,
        expected_file_sha256=file_sha256(path),
        expected_model_sha256="a" * 64,
    )

    with EmbeddingCache(
        path,
        mode="reuse",
        expected_file_sha256=adoption["file_sha256"],
        expected_content_sha256=adoption["content_sha256"],
        expected_model_sha256="a" * 64,
        legacy_v0=True,
    ) as cache:
        assert np.array_equal(cache("old"), np.full(1024, 3.0, np.float32))
        assert cache.misses == 0
