from __future__ import annotations

import importlib.metadata
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from statistics import median

import hnswlib
import numpy as np

from .config import EMBEDDING_DIMENSION, SEED
from .embedding import normalize_embedding
from .models import Candidate


SCALES = (120, 1_000, 10_000, 100_000)
HNSW_VERSION = "0.8.0"
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 200
HNSW_EF_SEARCH = 64
RECALL_K = (10, 50)
WARMUP_QUERY_INDICES = tuple(range(5))
MEASURED_QUERY_INDICES = (*range(5, 24), *range(6))


@dataclass
class ScaledVectorStore:
    scale: int
    vectors: np.ndarray
    real_candidate_ids: tuple[str, ...]
    sampled_source_indices: np.ndarray

    @property
    def real_count(self) -> int:
        return len(self.real_candidate_ids)

    @property
    def synthetic_count(self) -> int:
        return self.scale - self.real_count

    def provenance_rows(self):
        for index, candidate_id in enumerate(self.real_candidate_ids):
            yield {
                "scale": self.scale,
                "row_index": index,
                "synthetic": False,
                "sampled_source_index": None,
                "source_candidate_id": candidate_id,
            }
        for offset, source_index in enumerate(self.sampled_source_indices):
            yield {
                "scale": self.scale,
                "row_index": self.real_count + offset,
                "synthetic": True,
                "sampled_source_index": int(source_index),
                "source_candidate_id": self.real_candidate_ids[int(source_index)],
            }


def build_scaled_vector_store(
    candidates: list[Candidate],
    scale: int,
) -> ScaledVectorStore:
    if scale not in SCALES:
        raise ValueError(f"Unregistered ANN scale: {scale}")
    if len(candidates) < SCALES[0]:
        raise ValueError("ANN base corpus must contain at least 120 vectors")
    missing = [
        candidate.candidate_id
        for candidate in candidates
        if candidate.embedding is None
    ]
    if missing:
        raise ValueError(f"ANN candidates lack embeddings: {missing[:5]}")

    base_matrix = np.vstack(
        [
            normalize_embedding(np.asarray(candidate.embedding))
            for candidate in candidates
        ]
    ).astype(np.float32, copy=False)
    real_count = min(scale, len(base_matrix))
    vectors = np.empty((scale, EMBEDDING_DIMENSION), dtype=np.float32)
    vectors[:real_count] = base_matrix[:real_count]
    real_candidate_ids = tuple(
        candidate.candidate_id for candidate in candidates[:real_count]
    )

    synthetic_count = scale - real_count
    sampled = np.empty(0, dtype=np.int32)
    if synthetic_count:
        rng = np.random.default_rng(SEED)
        sampled = rng.integers(
            0,
            real_count,
            size=synthetic_count,
            dtype=np.int32,
        )
        for start in range(0, synthetic_count, 2_000):
            stop = min(synthetic_count, start + 2_000)
            padded = base_matrix[sampled[start:stop]].copy()
            padded += rng.normal(
                0.0,
                0.01,
                size=padded.shape,
            ).astype(np.float32)
            norms = np.linalg.norm(padded, axis=1, keepdims=True)
            np.divide(padded, norms, out=padded, where=norms != 0)
            vectors[real_count + start : real_count + stop] = padded
    return ScaledVectorStore(
        scale=scale,
        vectors=vectors,
        real_candidate_ids=real_candidate_ids,
        sampled_source_indices=sampled,
    )


def benchmark_ann(
    store: ScaledVectorStore,
    query_vectors: list[np.ndarray],
    index_directory: Path,
) -> dict:
    observed_version = importlib.metadata.version("hnswlib")
    if observed_version != HNSW_VERSION:
        raise AssertionError(
            f"hnswlib {observed_version} does not match {HNSW_VERSION}"
        )
    if len(query_vectors) != 24:
        raise ValueError("ANN benchmark requires 24 locked query vectors")
    queries = np.vstack(
        [normalize_embedding(vector) for vector in query_vectors]
    ).astype(np.float32, copy=False)
    index_directory.mkdir(parents=True, exist_ok=True)
    index_path = index_directory / f"hnsw_{store.scale}.bin"

    build_start = time.perf_counter()
    index = hnswlib.Index(space="cosine", dim=EMBEDDING_DIMENSION)
    index.init_index(
        max_elements=store.scale,
        M=HNSW_M,
        ef_construction=HNSW_EF_CONSTRUCTION,
        random_seed=SEED,
    )
    index.set_num_threads(1)
    index.add_items(
        store.vectors,
        np.arange(store.scale, dtype=np.int64),
        num_threads=1,
    )
    index.set_ef(HNSW_EF_SEARCH)
    build_ms = (time.perf_counter() - build_start) * 1000.0
    index.save_index(str(index_path))
    index_bytes = index_path.stat().st_size

    exact_neighbors = [
        _exact_top_k(store.vectors, query, RECALL_K[-1])
        for query in queries
    ]
    hnsw_neighbors = [
        _hnsw_top_k(index, query, RECALL_K[-1])
        for query in queries
    ]
    per_query = []
    recall_totals = {k: 0 for k in RECALL_K}
    for query_index, (exact, approximate) in enumerate(
        zip(exact_neighbors, hnsw_neighbors, strict=True)
    ):
        row = {"query_index": query_index}
        for k in RECALL_K:
            matches = len(set(exact[:k]) & set(approximate[:k]))
            recall_totals[k] += matches
            row[f"matches_at_{k}"] = matches
            row[f"recall_at_{k}"] = matches / k
        per_query.append(row)

    exact_timings = _time_queries(
        lambda query: _exact_top_k(
            store.vectors,
            query,
            RECALL_K[-1],
        ),
        queries,
    )
    hnsw_timings = _time_queries(
        lambda query: _hnsw_top_k(index, query, RECALL_K[-1]),
        queries,
    )
    result = {
        "scale": store.scale,
        "real_rows": store.real_count,
        "synthetic_rows": store.synthetic_count,
        "synthetic_padded": store.synthetic_count > 0,
        "seed": SEED,
        "space": "cosine",
        "dimension": EMBEDDING_DIMENSION,
        "M": HNSW_M,
        "ef_construction": HNSW_EF_CONSTRUCTION,
        "ef_search": HNSW_EF_SEARCH,
        "thread_count": 1,
        "hnswlib_version": observed_version,
        "build_ms": build_ms,
        "index_bytes": index_bytes,
        "vector_bytes": int(store.vectors.nbytes),
        "bytes_per_vector": index_bytes / store.scale,
        "exact_query_median_ns": float(median(exact_timings)),
        "hnsw_query_median_ns": float(median(hnsw_timings)),
        "exact_query_samples_ns": exact_timings,
        "hnsw_query_samples_ns": hnsw_timings,
        "warmup_query_indices": list(WARMUP_QUERY_INDICES),
        "measured_query_indices": list(MEASURED_QUERY_INDICES),
        "per_query_recall": per_query,
    }
    for k in RECALL_K:
        exact_recall = Fraction(recall_totals[k], len(queries) * k)
        result[f"recall_at_{k}"] = float(exact_recall)
        result[f"recall_at_{k}_exact"] = str(exact_recall)
    return result


def _exact_top_k(
    vectors: np.ndarray,
    query: np.ndarray,
    k: int,
) -> list[int]:
    if not 0 < k <= len(vectors):
        raise ValueError("Exact search k is outside the vector store")
    scores = vectors @ query
    threshold = np.partition(scores, len(scores) - k)[len(scores) - k]
    pool = np.flatnonzero(scores >= threshold)
    order = np.lexsort((pool, -scores[pool]))
    return [int(index) for index in pool[order[:k]]]


def _hnsw_top_k(index, query: np.ndarray, k: int) -> list[int]:
    labels, _ = index.knn_query(query, k=k, num_threads=1)
    return [int(label) for label in labels[0]]


def _time_queries(search, queries: np.ndarray) -> list[int]:
    for query_index in WARMUP_QUERY_INDICES:
        search(queries[query_index])
    timings = []
    for query_index in MEASURED_QUERY_INDICES:
        start = time.perf_counter_ns()
        search(queries[query_index])
        timings.append(time.perf_counter_ns() - start)
    if len(timings) != 25:
        raise AssertionError("ANN timing schedule did not produce 25 samples")
    return timings
