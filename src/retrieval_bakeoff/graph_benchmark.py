from __future__ import annotations

import gc
import math
import time

import numpy as np

from .config import SEED
from .graph import AssociativeGraphIndex


SCALES = (120, 1_000, 10_000, 100_000)
WARMUPS = 5
REPETITIONS = 25


def run_incremental_update_benchmark(
    graph: AssociativeGraphIndex,
) -> dict:
    per_scale = []
    for scale in SCALES:
        vectors, topics, retained, synthetic_count = _scaled_store(
            graph,
            scale,
        )
        result = _benchmark_scale(
            vectors,
            topics,
            retained,
            seed=SEED,
        )
        per_scale.append(
            {
                "scale": scale,
                "real_rows": scale - synthetic_count,
                "synthetic_rows": synthetic_count,
                "synthetic_padded": synthetic_count > 0,
                **result,
            }
        )
        del vectors, topics, retained
        gc.collect()

    slopes = {}
    for component in ("E1", "E2", "E3", "E4"):
        x = np.log10(
            np.asarray([row["scale"] for row in per_scale], dtype=np.float64)
        )
        y = np.log10(
            np.asarray(
                [row[f"{component}_median_ns"] for row in per_scale],
                dtype=np.float64,
            )
        )
        slope, intercept = np.polyfit(x, y, 1)
        slopes[component] = {
            "log10_slope": float(slope),
            "log10_intercept": float(intercept),
            "passes_at_most_1_10": float(slope) <= 1.10,
        }
    return {
        "seed": SEED,
        "warmups": WARMUPS,
        "measured_repetitions": REPETITIONS,
        "scales": per_scale,
        "component_slopes": slopes,
    }


def _scaled_store(
    graph: AssociativeGraphIndex,
    scale: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    rng = np.random.default_rng(SEED)
    real_count = min(scale, len(graph.matrix))
    vectors = np.empty((scale, graph.matrix.shape[1]), dtype=np.float32)
    vectors[:real_count] = graph.matrix[:real_count]

    topic_values = [
        candidate.topic_id or ""
        for candidate in graph.candidates
    ]
    unique_topics = {
        topic: index
        for index, topic in enumerate(
            sorted({topic for topic in topic_values if topic})
        )
    }
    real_topics = np.asarray(
        [unique_topics.get(topic, -1) for topic in topic_values],
        dtype=np.int32,
    )
    topics = np.empty(scale, dtype=np.int32)
    topics[:real_count] = real_topics[:real_count]

    retained = np.empty((scale, 8), dtype=np.float32)
    retained[:real_count] = graph.e3_neighbor_scores[:real_count]

    synthetic_count = scale - real_count
    if synthetic_count:
        sampled = rng.integers(0, len(graph.matrix), size=synthetic_count)
        topic_pool = real_topics[real_topics >= 0]
        if not len(topic_pool):
            raise AssertionError("Synthetic E4 padding needs a non-empty topic")
        topics[real_count:] = rng.choice(
            topic_pool,
            size=synthetic_count,
            replace=True,
        )
        retained[real_count:] = graph.e3_neighbor_scores[sampled]
        for start in range(0, synthetic_count, 2_000):
            stop = min(synthetic_count, start + 2_000)
            base = graph.matrix[sampled[start:stop]]
            noise = rng.normal(
                0.0,
                0.01,
                size=base.shape,
            ).astype(np.float32)
            padded = base + noise
            norms = np.linalg.norm(padded, axis=1, keepdims=True)
            np.divide(
                padded,
                norms,
                out=padded,
                where=norms != 0,
            )
            vectors[real_count + start : real_count + stop] = padded
    return vectors, topics, retained, synthetic_count


def _benchmark_scale(
    vectors: np.ndarray,
    topics: np.ndarray,
    retained: np.ndarray,
    *,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    total = WARMUPS + REPETITIONS
    sampled = rng.integers(0, len(vectors), size=total)
    updates = vectors[sampled].copy()
    noise = rng.normal(0.0, 0.01, size=updates.shape).astype(np.float32)
    updates += noise
    norms = np.linalg.norm(updates, axis=1, keepdims=True)
    np.divide(updates, norms, out=updates, where=norms != 0)
    nonempty_topics = topics[topics >= 0]
    if not len(nonempty_topics):
        raise AssertionError("E4 benchmark requires a non-empty real topic")
    update_topics = rng.choice(nonempty_topics, size=total, replace=True)
    context_members = [
        rng.choice(len(vectors), size=9, replace=False)
        for _ in range(total)
    ]

    timings = {component: [] for component in ("E1", "E2", "E3", "E4")}
    e1_buffer = np.empty(2, dtype=np.int64)
    e4_buffer = np.empty(len(vectors), dtype=np.int64)
    working_retained = np.empty_like(retained)
    for repetition in range(total):
        measured = repetition >= WARMUPS

        start = time.perf_counter_ns()
        e1_buffer[0] = len(vectors) - 1
        e1_buffer[1] = len(vectors)
        elapsed = time.perf_counter_ns() - start
        if measured:
            timings["E1"].append(elapsed)

        members = [len(vectors), *context_members[repetition].tolist()]
        context_pairs = [
            (
                min(members[left], members[right]),
                max(members[left], members[right]),
            )
            for left in range(10)
            for right in range(left + 1, 10)
        ]
        counters = {pair: 0 for pair in context_pairs}
        start = time.perf_counter_ns()
        for pair in context_pairs:
            counters[pair] += 1
        elapsed = time.perf_counter_ns() - start
        if measured:
            timings["E2"].append(elapsed)

        np.copyto(working_retained, retained)
        update = updates[repetition]
        start = time.perf_counter_ns()
        scores = vectors @ update
        neighbor_count = min(8, len(scores))
        if neighbor_count:
            np.argpartition(scores, -neighbor_count)[-neighbor_count:]
        entering = scores > working_retained[:, 0]
        if np.any(entering):
            indices = np.flatnonzero(entering)
            working_retained[indices, 0] = scores[indices]
            working_retained[indices] = np.sort(
                working_retained[indices],
                axis=1,
            )
        elapsed = time.perf_counter_ns() - start
        if measured:
            timings["E3"].append(elapsed)

        start = time.perf_counter_ns()
        matches = np.flatnonzero(topics == update_topics[repetition])
        e4_buffer[: len(matches)] = matches
        elapsed = time.perf_counter_ns() - start
        if measured:
            timings["E4"].append(elapsed)

    result = {}
    for component, values in timings.items():
        median = float(np.median(np.asarray(values, dtype=np.float64)))
        result[f"{component}_median_ns"] = max(median, 1.0)
        result[f"{component}_samples_ns"] = values
    result["vector_bytes"] = int(vectors.nbytes)
    result["retained_neighbor_bytes"] = int(retained.nbytes)
    result["topic_bytes"] = int(topics.nbytes)
    result["total_base_bytes"] = int(
        vectors.nbytes + retained.nbytes + topics.nbytes
    )
    result["total_base_mib"] = result["total_base_bytes"] / math.pow(1024, 2)
    return result
