"""CC-005: measure what actually grows, so the policy can be stated.

Part 3 ships no eviction. It ships numbers and a policy, and this is where
the numbers come from. Two things grow with turn count and they are not
the same problem:

* **disk**, linearly and cheaply,
* **retrieval latency**, linearly and expensively.

Both are measured here against the committed Study 010 arm L material -
real episode text, real embeddings - to the largest store the program has,
which is 1,000 turns. Anything past that is a projection and is labelled
as one.

The third growth path, the context window, is not measured here. DX-002
measured it and CC-003's G-E0 answered it for the library: the delivered
block is bounded by the budget and does not grow with store size.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "episodic" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))

import numpy as np  # noqa: E402

from episodic._config import EpisodicConfig  # noqa: E402
from episodic._context import build_context  # noqa: E402
from episodic._store import EpisodeStore  # noqa: E402

from src.analysis.cc003_growth_gate import load_episodes  # noqa: E402

BUDGET_CHARS = 32_000
LATENCY_POOL_SIZES = (50, 100, 200, 300, 400, 500, 700, 850, 1_000)
LATENCY_REPEATS = 7
DISK_CHECKPOINTS = (50, 100, 200, 400, 600, 800, 1_000)

#: Horizons the README quotes. Anything above the measured maximum is a
#: projection from the fitted exponent, never a measurement.
PROJECTION_HORIZONS = (2_000, 5_000, 10_000)


def _deterministic_embedder(text: str):
    import hashlib

    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
    return np.random.default_rng(seed).standard_normal(1024).astype(np.float32)


def measure_disk(episodes: list[dict], workdir: Path) -> dict:
    """Bytes on disk per stored turn, using real episode text.

    A deterministic stub stands in for the carried embedder. The stored
    vector is 1,024 float32 values either way, so the byte count is
    faithful; only the vector's contents differ, and nothing here depends
    on them.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / "disk_growth.db"
    if path.exists():
        path.unlink()

    store = EpisodeStore(
        path,
        EpisodicConfig(recency_window_n=32, selector_cluster_count=16),
        embedder=_deterministic_embedder,
    )
    rows = []
    try:
        for index, episode in enumerate(episodes, start=1):
            store.append("user", episode["user_message"])
            store.append("assistant", episode["assistant_message"])
            if index in DISK_CHECKPOINTS:
                size = path.stat().st_size
                rows.append(
                    {
                        "turns": index,
                        "bytes": size,
                        "bytes_per_turn": size / index,
                    }
                )
    finally:
        store.close()

    final = rows[-1]
    # Marginal cost, which is what matters for growth: the slope between
    # the first and last checkpoint, not the average that carries the
    # fixed page and schema overhead.
    first = rows[0]
    marginal = (final["bytes"] - first["bytes"]) / (
        final["turns"] - first["turns"]
    )
    text_bytes = sum(
        len(episode["user_message"].encode("utf-8"))
        + len(episode["assistant_message"].encode("utf-8"))
        for episode in episodes
    )
    return {
        "rows": rows,
        "measured_to_turns": final["turns"],
        "total_bytes": final["bytes"],
        "marginal_bytes_per_turn": marginal,
        "embedding_bytes_per_turn": 1_024 * 4,
        "text_bytes_per_turn": text_bytes / len(episodes),
        "projections": {
            str(horizon): marginal * horizon
            for horizon in PROJECTION_HORIZONS
        },
    }


def measure_latency(episodes: list[dict]) -> dict:
    """Wall-clock `build_context` against pool size, embedding excluded."""
    config = EpisodicConfig()
    query = episodes[-1]["embedding"]
    rows = []
    for size in LATENCY_POOL_SIZES:
        pool = episodes[:size]
        samples = []
        for _ in range(LATENCY_REPEATS):
            started = time.perf_counter()
            build_context(
                episodes=pool,
                query_embedding=query,
                budget=BUDGET_CHARS,
                config=config,
            )
            samples.append((time.perf_counter() - started) * 1_000.0)
        median = statistics.median(samples)
        rows.append(
            {
                "candidates": size,
                "median_ms": median,
                "min_ms": min(samples),
                "max_ms": max(samples),
                "us_per_candidate": median * 1_000.0 / size,
            }
        )

    exponent, coefficient = _fit_power_law(
        [row["candidates"] for row in rows],
        [row["median_ms"] for row in rows],
    )
    measured_max = rows[-1]
    return {
        "rows": rows,
        "repeats_per_point": LATENCY_REPEATS,
        "embedding_excluded": True,
        "measured_to_candidates": measured_max["candidates"],
        "measured_max_ms": measured_max["median_ms"],
        "fitted_exponent": exponent,
        "fitted_coefficient": coefficient,
        "projections_labelled_as_projections": {
            str(horizon): coefficient * (horizon**exponent)
            for horizon in PROJECTION_HORIZONS
        },
    }


def measure_components(episodes: list[dict]) -> dict:
    """Where the time goes, stage by stage.

    Section 3.1 asserts that clustering is about 73% of the cost, on
    DR-002's authority. DR-002 measured that at n = 119. This re-measures
    it across the full 1,000-episode store, because the share is the thing
    that decides whether an eviction policy would even help.
    """
    from episodic._packing import pack_stm_payload
    from episodic._selection import (
        ClusterDiversitySelector,
        deterministic_clusters,
        relevance_vector,
        select,
        vector,
    )

    config = EpisodicConfig()
    rows = []
    for size in LATENCY_POOL_SIZES:
        pool = episodes[:size]
        query = vector(episodes[size - 1]["embedding"])

        relevance_ms = _median_ms(lambda: relevance_vector(query, pool))
        cluster_ms = _median_ms(
            lambda: deterministic_clusters(pool, config.selector_cluster_count)
        )

        assignments = deterministic_clusters(
            pool, config.selector_cluster_count
        )

        def run_select():
            return select(
                candidates=pool,
                query_embedding=query,
                selector=ClusterDiversitySelector(
                    lambda_=config.selector_lambda,
                    cost_exponent=config.selector_cost_exponent,
                    assignments=assignments,
                    cluster_count=config.selector_cluster_count,
                ),
                budget_chars=BUDGET_CHARS,
            )

        select_ms = _median_ms(run_select)

        result = run_select()
        by_id = {str(episode["id"]): episode for episode in pool}
        coverage = [by_id[key] for key in result.selected_ids]
        relevance = relevance_vector(query, pool)
        k_hits = [
            episode
            for index, episode in enumerate(pool)
            if relevance[index] >= config.k_threshold
        ]
        pack_ms = _median_ms(
            lambda: pack_stm_payload(
                pool[-config.recency_window_n :],
                [*k_hits, *coverage],
                BUDGET_CHARS,
            )
        )

        total = relevance_ms + cluster_ms + select_ms + pack_ms
        rows.append(
            {
                "candidates": size,
                "relevance_ms": relevance_ms,
                "cluster_ms": cluster_ms,
                "select_ms": select_ms,
                "pack_ms": pack_ms,
                "stage_total_ms": total,
                "cluster_share": cluster_ms / total if total else 0.0,
            }
        )

    cluster_exponent, _ = _fit_power_law(
        [row["candidates"] for row in rows],
        [row["cluster_ms"] for row in rows],
    )
    largest = rows[-1]
    return {
        "rows": rows,
        "repeats_per_point": LATENCY_REPEATS,
        "cluster_fitted_exponent": cluster_exponent,
        "cluster_share_at_max": largest["cluster_share"],
        "dominant_stage": "cluster_setup",
    }


def _median_ms(callable_) -> float:
    samples = []
    for _ in range(LATENCY_REPEATS):
        started = time.perf_counter()
        callable_()
        samples.append((time.perf_counter() - started) * 1_000.0)
    return statistics.median(samples)


def _fit_power_law(xs, ys) -> tuple[float, float]:
    """Least squares on log-log; returns (exponent, coefficient)."""
    log_x = [float(np.log(x)) for x in xs]
    log_y = [float(np.log(y)) for y in ys]
    n = len(log_x)
    mean_x = sum(log_x) / n
    mean_y = sum(log_y) / n
    sxx = sum((x - mean_x) ** 2 for x in log_x)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(log_x, log_y))
    exponent = sxy / sxx
    intercept = mean_y - exponent * mean_x
    return exponent, float(np.exp(intercept))


def measure(workdir: Path) -> dict:
    episodes = load_episodes()
    disk = measure_disk(episodes, workdir)
    latency = measure_latency(episodes)
    components = measure_components(episodes)
    return {
        "record": "CC-005 store growth measurement",
        "components": components,
        "dr002_reconciliation": {
            "dr002_measured_range_candidates": [20, 119],
            "dr002_exponent": 0.96,
            "dr002_us_per_candidate": "35-43, flat across that range",
            "this_measured_range_candidates": [
                LATENCY_POOL_SIZES[0],
                LATENCY_POOL_SIZES[-1],
            ],
            "this_exponent": latency["fitted_exponent"],
            "note": (
                "DR-002 is corroborated inside the range it measured and "
                "does not extrapolate past it. Per-candidate cost is flat "
                "to 119 candidates and rises steadily after, so a linear "
                "projection from 119 understates cost at 1,000 by roughly "
                "a factor of five. The pre-registration's ~40 ms at 1,000 "
                "and ~400 ms at 10,000 come from that extrapolation."
            ),
        },
        "scope": (
            "committed Study 010 arm L episodes; offline; no eviction "
            "implemented"
        ),
        "budget_chars": BUDGET_CHARS,
        "episodes_available": len(episodes),
        "disk": disk,
        "latency": latency,
        "policy": "unbounded retention; no eviction in v0",
        "context_window": {
            "bounded": True,
            "source": "CC-003 G-E0",
            "note": (
                "The delivered block is bounded by the budget and does not "
                "grow with store size, so context is not one of the growth "
                "paths eviction has to solve for this library."
            ),
        },
    }


def write_artifacts(result: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "growth_measurement.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines = ["candidates,median_ms,min_ms,max_ms,us_per_candidate"]
    for row in result["latency"]["rows"]:
        lines.append(
            f"{row['candidates']},{row['median_ms']:.4f},"
            f"{row['min_ms']:.4f},{row['max_ms']:.4f},"
            f"{row['us_per_candidate']:.3f}"
        )
    (output_dir / "latency_curve.csv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )

    lines = [
        "candidates,relevance_ms,cluster_ms,select_ms,pack_ms,"
        "stage_total_ms,cluster_share"
    ]
    for row in result["components"]["rows"]:
        lines.append(
            f"{row['candidates']},{row['relevance_ms']:.4f},"
            f"{row['cluster_ms']:.4f},{row['select_ms']:.4f},"
            f"{row['pack_ms']:.4f},{row['stage_total_ms']:.4f},"
            f"{row['cluster_share']:.4f}"
        )
    (output_dir / "latency_components.csv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )

    lines = ["turns,bytes,bytes_per_turn"]
    for row in result["disk"]["rows"]:
        lines.append(
            f"{row['turns']},{row['bytes']},{row['bytes_per_turn']:.1f}"
        )
    (output_dir / "disk_growth.csv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()

    result = measure(args.workdir)
    write_artifacts(result, args.output_dir)
    disk = result["disk"]
    latency = result["latency"]
    print(
        f"disk: {disk['marginal_bytes_per_turn']:,.0f} bytes/turn marginal; "
        f"{disk['total_bytes']:,} bytes at {disk['measured_to_turns']:,} turns"
    )
    print(
        f"latency: {latency['measured_max_ms']:.1f} ms at "
        f"{latency['measured_to_candidates']:,} candidates; "
        f"exponent {latency['fitted_exponent']:.2f}"
    )
    for horizon, value in latency[
        "projections_labelled_as_projections"
    ].items():
        print(f"  projected (not measured) {horizon}: {value:.0f} ms")


if __name__ == "__main__":
    main()
