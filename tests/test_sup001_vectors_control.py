from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from episodic import EmbeddingCache, EmbeddingCacheError
from src.analysis.sup001_benchmark import build
from src.analysis.sup001_control import compute_control
from src.analysis.sup001_vectors import (
    CARRIED_EMBEDDING_SHA256,
    VectorText,
    load_vector_texts,
    populate_cache,
)


class FakeEmbedder:
    model_sha256 = CARRIED_EMBEDDING_SHA256

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        vector = np.arange(1, 1025, dtype=np.float32)
        vector[len(text) % 1024] += 1000.0
        return vector


def test_locked_vector_inventory_is_complete_and_unique() -> None:
    rows = load_vector_texts()
    assert len(rows) == 352
    assert sum(row.kind == "episode" for row in rows) == 256
    assert sum(row.kind == "query" for row in rows) == 96
    assert len({row.text for row in rows}) == 352


def test_vector_capture_is_solo_normalized_and_read_only(tmp_path) -> None:
    rows = (VectorText("episode", "e", "alpha"), VectorText("query", "q", "beta"))
    delegate = FakeEmbedder()
    path = tmp_path / "vectors.sqlite"
    record, vectors = populate_cache(rows, path, delegate)
    assert delegate.calls == 2
    assert record["entries"] == 2
    assert all(row["unit_norm"] == pytest.approx(1.0) for row in vectors)
    with EmbeddingCache(
        path,
        mode="reuse",
        expected_file_sha256=record["file_sha256"],
        expected_content_sha256=record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        assert np.linalg.norm(cache("alpha")) == pytest.approx(1.0)
        with pytest.raises(EmbeddingCacheError, match="no model call"):
            cache("missing")


def test_control_ranks_all_candidates_and_exactly_packs_top_eight() -> None:
    mechanism, _key = build()
    vectors = {}
    for index, row in enumerate(load_vector_texts()):
        vector = np.zeros(16, dtype=np.float32)
        vector[index % 16] = 1.0
        vectors[row.text] = vector
    result = compute_control(mechanism, vectors.__getitem__)
    assert len(result["queries"]) == 96
    assert all(len(row["population"]) == 256 for row in result["queries"])
    assert all(len(row["selected_ids"]) == 8 for row in result["queries"])
    assert all(row["serialized_chars"] <= 32_000 for row in result["queries"])
    first = result["queries"][0]
    assert first["selected"] == sorted(
        first["population"], key=lambda row: (-row["cosine"], row["episode_sha256"])
    )[:8]


def test_corpus_launcher_works_without_pythonpath(tmp_path) -> None:
    output = tmp_path / "corpus"
    environment = {key: value for key, value in __import__("os").environ.items() if key != "PYTHONPATH"}
    completed = subprocess.run(
        [sys.executable, "scripts/run_sup001_corpus_lock.py", "--output-dir", str(output)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert json.loads(completed.stdout)["status"] == "PASS"
