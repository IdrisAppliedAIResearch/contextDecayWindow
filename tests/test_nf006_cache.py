from __future__ import annotations

import numpy as np

from analysis.nf006_cache import load_vectors, verify_cache
from retrieval_bakeoff.config import EMBEDDING_DIMENSION


def test_load_vectors_separates_query_and_statement(tmp_path) -> None:
    import sqlite3

    path = tmp_path / "cache.db"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE vectors (
            kind TEXT, identity TEXT, text_sha256 TEXT, text TEXT,
            embedding BLOB, vector_sha256 TEXT,
            PRIMARY KEY (kind, identity)
        )
        """
    )
    value = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    connection.execute(
        "INSERT INTO vectors VALUES (?, ?, ?, ?, ?, ?)",
        ("query", "q", "t", "query", value.tobytes(), "v"),
    )
    connection.execute(
        "INSERT INTO vectors VALUES (?, ?, ?, ?, ?, ?)",
        ("statement", "s", "t", "statement", value.tobytes(), "v"),
    )
    connection.commit()
    connection.close()
    queries, statements = load_vectors(path)
    assert set(queries) == {"q"}
    assert set(statements) == {"s"}


def test_verify_cache_rejects_missing_manifest(tmp_path) -> None:
    cache = tmp_path / "missing.db"
    manifest = tmp_path / "missing.json"
    try:
        verify_cache(cache, manifest)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("An absent seal must fail closed")
