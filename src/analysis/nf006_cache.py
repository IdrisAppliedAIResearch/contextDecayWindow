"""Sequential, content-addressed vector capture for NF-006."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sqlite3
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np

from analysis.nf006_inputs import PROBE_TURNS, sha256_file
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256, EMBEDDING_DIMENSION
from retrieval_bakeoff.embedding import CarriedEmbedder


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=1, sort_keys=True) + "\n"
    ).encode("utf-8")


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def vector_sha256(value: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(value, dtype=np.float32).tobytes()).hexdigest()


def capture_cache(
    *,
    probe_texts: Mapping[int, str],
    statements: Sequence[dict],
    model_path: Path,
    cache_path: Path,
    manifest_path: Path,
    progress: Callable[[int, int], None] | None = None,
) -> dict:
    if cache_path.exists() or manifest_path.exists():
        raise FileExistsError("Refusing to overwrite an NF-006 cache or manifest")
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    embedder = CarriedEmbedder(model_path)
    embedder.assert_carried_model()
    ordered_queries = sorted(set(probe_texts.values()))
    if len(ordered_queries) != len(PROBE_TURNS):
        raise AssertionError("Corrected probe batch must contain eight texts")
    ordered_statements = sorted(statements, key=lambda row: str(row["id"]))
    if len(ordered_statements) != 791:
        raise AssertionError("Statement capture requires exactly 791 units")

    connection = sqlite3.connect(cache_path)
    try:
        connection.execute(
            """
            CREATE TABLE vectors (
                kind TEXT NOT NULL,
                identity TEXT NOT NULL,
                text_sha256 TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                vector_sha256 TEXT NOT NULL,
                PRIMARY KEY (kind, identity)
            )
            """
        )
        query_vectors = embedder.embed_many(
            ordered_queries, batch_size=len(ordered_queries)
        )
        for text, value in zip(ordered_queries, query_vectors, strict=True):
            array = np.asarray(value, dtype=np.float32).reshape(EMBEDDING_DIMENSION)
            identity = text_sha256(text)
            connection.execute(
                "INSERT INTO vectors VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "query",
                    identity,
                    identity,
                    text,
                    array.tobytes(),
                    vector_sha256(array),
                ),
            )
        connection.commit()

        for index, row in enumerate(ordered_statements, start=1):
            text = str(row["text"])
            array = np.asarray(embedder(text), dtype=np.float32).reshape(
                EMBEDDING_DIMENSION
            )
            connection.execute(
                "INSERT INTO vectors VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "statement",
                    str(row["id"]),
                    text_sha256(text),
                    text,
                    array.tobytes(),
                    vector_sha256(array),
                ),
            )
            if index % 64 == 0:
                connection.commit()
            if progress is not None and (index % 32 == 0 or index == 791):
                progress(index, 791)
        connection.commit()
    finally:
        connection.close()

    rows = _rows(cache_path)
    content_manifest = [
        {
            "kind": row[0],
            "identity": row[1],
            "text_sha256": row[2],
            "vector_sha256": row[3],
        }
        for row in rows
    ]
    manifest = {
        "schema": "nf006-exact-vectors-v1",
        "status": "SEALED",
        "model_sha256": CARRIED_EMBEDDING_SHA256,
        "llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
        "call_shape": {
            "probe": "one lexicographically sorted eight-text batch",
            "statement": "791 sequential exact-solo calls in identity order",
            "parallelism": 1,
        },
        "probe_turns": list(PROBE_TURNS),
        "query_entries": sum(row[0] == "query" for row in rows),
        "statement_entries": sum(row[0] == "statement" for row in rows),
        "content_manifest_sha256": hashlib.sha256(
            canonical_bytes(content_manifest)
        ).hexdigest(),
        "probe_order_digest": hashlib.sha256(
            canonical_bytes([text_sha256(text) for text in ordered_queries])
        ).hexdigest(),
        "statement_order_digest": hashlib.sha256(
            canonical_bytes([str(row["id"]) for row in ordered_statements])
        ).hexdigest(),
        "cache_file_sha256": sha256_file(cache_path),
        "embedding_calls": 1 + len(ordered_statements),
        "generation_calls": 0,
    }
    manifest_path.write_bytes(canonical_bytes(manifest))
    return manifest


def load_vectors(
    cache_path: Path,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    connection = sqlite3.connect(
        f"file:{cache_path.resolve().as_posix()}?mode=ro&immutable=1", uri=True
    )
    try:
        rows = connection.execute(
            "SELECT kind, identity, embedding FROM vectors ORDER BY kind, identity"
        ).fetchall()
    finally:
        connection.close()
    queries: dict[str, np.ndarray] = {}
    statements: dict[str, np.ndarray] = {}
    for kind, identity, blob in rows:
        value = np.frombuffer(blob, dtype=np.float32).copy().reshape(
            EMBEDDING_DIMENSION
        )
        (queries if kind == "query" else statements)[str(identity)] = value
    return queries, statements


def verify_cache(cache_path: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = _rows(cache_path)
    content_manifest = [
        {
            "kind": row[0],
            "identity": row[1],
            "text_sha256": row[2],
            "vector_sha256": row[3],
        }
        for row in rows
    ]
    observed_content = hashlib.sha256(canonical_bytes(content_manifest)).hexdigest()
    checks = {
        "sealed": manifest.get("status") == "SEALED",
        "model": manifest.get("model_sha256") == CARRIED_EMBEDDING_SHA256,
        "file": manifest.get("cache_file_sha256") == sha256_file(cache_path),
        "content": manifest.get("content_manifest_sha256") == observed_content,
        "queries": sum(row[0] == "query" for row in rows) == 8,
        "statements": sum(row[0] == "statement" for row in rows) == 791,
    }
    return {"pass": all(checks.values()), "checks": checks, "manifest": manifest}


def _rows(path: Path) -> list[tuple[str, str, str, str]]:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True
    )
    try:
        return list(
            connection.execute(
                """
                SELECT kind, identity, text_sha256, vector_sha256
                FROM vectors ORDER BY kind, identity
                """
            )
        )
    finally:
        connection.close()
