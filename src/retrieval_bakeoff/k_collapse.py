from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np

from .config import REPO_ROOT
from .embedding import CarriedEmbedder, normalize_embedding


SCRIPT_PATH = REPO_ROOT / "experiments" / "study_005" / "script.json"
STORES = {
    "study_009_arm_s": (
        REPO_ROOT
        / "experiments/study_009/runs/study_009_full_001/arm_s"
    ),
    "study_002_condition_c": (
        REPO_ROOT / "experiments/study_002/runs/run_001/iterative"
    ),
}


def run_k_collapse_diagnostic(embedder: CarriedEmbedder) -> dict:
    query = _turn_120_query()
    query_vector = normalize_embedding(embedder(query))
    stores: dict[str, dict] = {}
    for store_id, run_directory in STORES.items():
        episodes = _load_episodes(run_directory / "study.db")
        pair_texts = [
            f"User: {row['user_message']}\nAssistant: {row['assistant_message']}"
            for row in episodes
        ]
        user_texts = [row["user_message"] for row in episodes]
        raw_pair_vectors = embedder.embed_many(pair_texts)
        pair_vectors = [
            normalize_embedding(vector) for vector in raw_pair_vectors
        ]
        user_vectors = [
            normalize_embedding(vector)
            for vector in embedder.embed_many(user_texts)
        ]
        distribution = []
        stored_matches = 0
        for episode, raw_pair_vector, pair_vector, user_vector in zip(
            episodes,
            raw_pair_vectors,
            pair_vectors,
            user_vectors,
            strict=True,
        ):
            stored_vector = normalize_embedding(
                np.frombuffer(episode["embedding"], dtype=np.float32)
            )
            raw_recomputed = np.asarray(raw_pair_vector, dtype=np.float32)
            raw_stored = np.frombuffer(episode["embedding"], dtype=np.float32)
            if np.array_equal(raw_stored, raw_recomputed):
                stored_matches += 1
            distribution.append(
                {
                    "turn_number": episode["turn_number"],
                    "episode_id": episode["id"],
                    "stored_similarity": float(stored_vector @ query_vector),
                    "recomputed_pair_similarity": float(
                        pair_vector @ query_vector
                    ),
                    "recomputed_user_similarity": float(
                        user_vector @ query_vector
                    ),
                    "assistant_characters": len(episode["assistant_message"]),
                    "pair_text_sha256": hashlib.sha256(
                        pair_texts[len(distribution)].encode("utf-8")
                    ).hexdigest(),
                }
            )
        _attach_ranks(distribution, "stored_similarity", "stored_rank")
        _attach_ranks(
            distribution,
            "recomputed_pair_similarity",
            "recomputed_pair_rank",
        )
        stores[store_id] = {
            "run_directory": str(run_directory.relative_to(REPO_ROOT)),
            "database_sha256": hashlib.sha256(
                (run_directory / "study.db").read_bytes()
            ).hexdigest(),
            "episode_count": len(episodes),
            "historical_k_count": _historical_k_count(run_directory),
            "stored_vector_exact_match_count": stored_matches,
            "stored_vector_exact_match_fraction": stored_matches / len(episodes),
            "stored": _distribution_summary(
                [row["stored_similarity"] for row in distribution]
            ),
            "recomputed_pair": _distribution_summary(
                [row["recomputed_pair_similarity"] for row in distribution]
            ),
            "recomputed_user": _distribution_summary(
                [row["recomputed_user_similarity"] for row in distribution]
            ),
            "distribution": sorted(
                distribution,
                key=lambda row: row["turn_number"],
            ),
        }

    turnwise_user_delta = _turnwise_delta(
        stores["study_009_arm_s"]["distribution"],
        stores["study_002_condition_c"]["distribution"],
        "recomputed_user_similarity",
    )
    pair_counts = {
        store_id: row["recomputed_pair"]["at_or_above_0_50"]
        for store_id, row in stores.items()
    }
    vectors_match = all(
        row["stored_vector_exact_match_fraction"] == 1.0
        for row in stores.values()
    )
    user_identical = turnwise_user_delta["max_absolute_delta"] <= 1e-7
    if (
        vectors_match
        and user_identical
        and pair_counts["study_009_arm_s"] == 0
        and pair_counts["study_002_condition_c"] > 0
    ):
        mechanism = "assistant_response_dilution_in_pair_embeddings"
        confirmation = (
            "Stored vectors reproduce exactly; user-only similarities are "
            "turnwise identical; adding each arm's assistant response "
            "reproduces the K-count divergence."
        )
    elif not vectors_match:
        mechanism = "stored_embedding_drift_or_corruption"
        confirmation = (
            "Recomputed pair vectors differ from persisted episode vectors."
        )
    else:
        mechanism = "corpus_content_shift_not_isolated"
        confirmation = (
            "The registered comparisons do not isolate one mechanism."
        )

    return {
        "test_id": "T1.3",
        "status": "COMPLETE",
        "query_turn": 120,
        "query": query,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "threshold": 0.50,
        "near_threshold_band": [0.45, 0.50],
        "stores": stores,
        "turnwise_user_similarity_comparison": turnwise_user_delta,
        "most_likely_mechanism": mechanism,
        "confirming_evidence": confirmation,
    }


def _load_episodes(path: Path) -> list[dict]:
    connection = sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding
            FROM episodes
            WHERE turn_number BETWEEN 1 AND 119
            ORDER BY turn_number, id
            """
        ).fetchall()
    finally:
        connection.close()
    episodes = [dict(row) for row in rows]
    if len(episodes) != 119:
        raise AssertionError(f"Expected 119 pre-query episodes in {path}")
    if any(row["embedding"] is None for row in episodes):
        raise AssertionError(f"Missing stored embedding in {path}")
    return episodes


def _turn_120_query() -> str:
    payload = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    row = next(item for item in payload["turns"] if int(item["turn"]) == 120)
    return str(row["user"])


def _historical_k_count(run_directory: Path) -> int:
    path = run_directory / "logs" / "retrieval.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if int(row.get("turn_number", -1)) == 120:
            return int(row["k_count"])
    raise AssertionError(f"No turn-120 retrieval record in {path}")


def _distribution_summary(values: list[float]) -> dict:
    array = np.asarray(values, dtype=np.float64)
    return {
        "minimum": float(np.min(array)),
        "p05": float(np.percentile(array, 5)),
        "p25": float(np.percentile(array, 25)),
        "median": float(np.median(array)),
        "p75": float(np.percentile(array, 75)),
        "p95": float(np.percentile(array, 95)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
        "at_or_above_0_50": int(np.sum(array >= 0.50)),
        "from_0_45_below_0_50": int(
            np.sum((array >= 0.45) & (array < 0.50))
        ),
    }


def _attach_ranks(
    rows: list[dict],
    score_key: str,
    rank_key: str,
) -> None:
    ordered = sorted(
        rows,
        key=lambda row: (-row[score_key], row["episode_id"]),
    )
    for rank, row in enumerate(ordered, start=1):
        row[rank_key] = rank


def _turnwise_delta(
    left: list[dict],
    right: list[dict],
    key: str,
) -> dict:
    left_by_turn = {row["turn_number"]: row[key] for row in left}
    right_by_turn = {row["turn_number"]: row[key] for row in right}
    shared = sorted(left_by_turn.keys() & right_by_turn.keys())
    deltas = [left_by_turn[turn] - right_by_turn[turn] for turn in shared]
    return {
        "shared_turn_count": len(shared),
        "max_absolute_delta": max((abs(value) for value in deltas), default=0.0),
        "mean_absolute_delta": (
            float(np.mean(np.abs(np.asarray(deltas, dtype=np.float64))))
            if deltas
            else 0.0
        ),
    }
