from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np

from .config import REPO_ROOT
from .embedding import CarriedEmbedder, normalize_embedding
from .k_collapse import STORES


def run_corrected_k_diagnostic(embedder: CarriedEmbedder) -> dict:
    store_data = {
        store_id: _load_store(run_directory)
        for store_id, run_directory in STORES.items()
    }
    store_ids = list(store_data)
    if len(store_ids) != 2:
        raise AssertionError("The corrected diagnostic requires exactly two stores")

    computed: dict[str, dict] = {}
    for store_id in store_ids:
        base = store_data[store_id]
        other_id = next(value for value in store_ids if value != store_id)
        other = store_data[other_id]
        query_vector = normalize_embedding(embedder(base["query"]))

        raw_pair_vectors = embedder.embed_many(base["pair_texts"])
        pair_vectors = [normalize_embedding(vector) for vector in raw_pair_vectors]
        user_vectors = [
            normalize_embedding(vector)
            for vector in embedder.embed_many(base["user_messages"])
        ]
        assistant_swap_vectors = [
            normalize_embedding(vector)
            for vector in embedder.embed_many(
                [
                    f"User: {user}\nAssistant: {assistant}"
                    for user, assistant in zip(
                        base["user_messages"],
                        other["assistant_messages"],
                        strict=True,
                    )
                ]
            )
        ]
        script_swap_query = normalize_embedding(embedder(other["query"]))
        script_swap_vectors = [
            normalize_embedding(vector)
            for vector in embedder.embed_many(
                [
                    f"User: {user}\nAssistant: {assistant}"
                    for user, assistant in zip(
                        other["user_messages"],
                        base["assistant_messages"],
                        strict=True,
                    )
                ]
            )
        ]

        rows = []
        exact_vectors = 0
        threshold_crossings = 0
        for index, episode in enumerate(base["episodes"]):
            raw_stored = np.frombuffer(
                episode["embedding"],
                dtype=np.float32,
            )
            stored_vector = normalize_embedding(raw_stored)
            raw_recomputed = np.asarray(
                raw_pair_vectors[index],
                dtype=np.float32,
            )
            if np.array_equal(raw_stored, raw_recomputed):
                exact_vectors += 1
            stored_score = float(stored_vector @ query_vector)
            recomputed_score = float(pair_vectors[index] @ query_vector)
            crossed = (stored_score >= 0.50) != (recomputed_score >= 0.50)
            threshold_crossings += int(crossed)
            rows.append(
                {
                    "turn_number": episode["turn_number"],
                    "episode_id": episode["id"],
                    "stored_similarity": stored_score,
                    "recomputed_pair_similarity": recomputed_score,
                    "recomputed_user_similarity": float(
                        user_vectors[index] @ query_vector
                    ),
                    "assistant_swap_similarity": float(
                        assistant_swap_vectors[index] @ query_vector
                    ),
                    "script_swap_similarity": float(
                        script_swap_vectors[index] @ script_swap_query
                    ),
                    "stored_recomputed_threshold_crossing": crossed,
                    "user_message_matches_other_store": (
                        base["user_messages"][index]
                        == other["user_messages"][index]
                    ),
                    "assistant_characters": len(
                        base["assistant_messages"][index]
                    ),
                    "other_assistant_characters": len(
                        other["assistant_messages"][index]
                    ),
                }
            )

        summaries = {
            "stored": _summary(rows, "stored_similarity"),
            "recomputed_pair": _summary(
                rows,
                "recomputed_pair_similarity",
            ),
            "recomputed_user": _summary(
                rows,
                "recomputed_user_similarity",
            ),
            "assistant_swap": _summary(
                rows,
                "assistant_swap_similarity",
            ),
            "script_swap": _summary(
                rows,
                "script_swap_similarity",
            ),
        }
        historical_k_count = _historical_k_count(base["run_directory"])
        computed[store_id] = {
            "run_directory": str(
                base["run_directory"].relative_to(REPO_ROOT)
            ),
            "query": base["query"],
            "query_sha256": hashlib.sha256(
                base["query"].encode("utf-8")
            ).hexdigest(),
            "query_matches_other_store": base["query"] == other["query"],
            "historical_k_count": historical_k_count,
            "historical_count_reproduced": (
                summaries["stored"]["at_or_above_0_50"]
                == historical_k_count
            ),
            "stored_vector_exact_match_count": exact_vectors,
            "stored_vector_exact_match_fraction": exact_vectors / len(rows),
            "stored_recomputed_threshold_crossings": threshold_crossings,
            "assistant_character_mean": float(
                np.mean(
                    np.asarray(
                        [len(value) for value in base["assistant_messages"]],
                        dtype=np.float64,
                    )
                )
            ),
            "summaries": summaries,
            "distribution": rows,
        }

    first, second = (store_data[store_id] for store_id in store_ids)
    user_difference_count = sum(
        left != right
        for left, right in zip(
            first["user_messages"],
            second["user_messages"],
            strict=True,
        )
    )
    causal_drift = any(
        row["stored_recomputed_threshold_crossings"] > 0
        and row["summaries"]["recomputed_pair"]["at_or_above_0_50"]
        != row["historical_k_count"]
        for row in computed.values()
    )
    historical_reproduced = all(
        row["historical_count_reproduced"] for row in computed.values()
    )
    assistant_changes = any(
        row["summaries"]["assistant_swap"]["at_or_above_0_50"]
        != row["summaries"]["recomputed_pair"]["at_or_above_0_50"]
        for row in computed.values()
    )
    script_changes = any(
        row["summaries"]["script_swap"]["at_or_above_0_50"]
        != row["summaries"]["recomputed_pair"]["at_or_above_0_50"]
        for row in computed.values()
    )
    if historical_reproduced and not causal_drift and assistant_changes:
        attribution = "assistant_response_content_shift"
    elif historical_reproduced and not causal_drift and script_changes:
        attribution = "script_encoding_or_user_text_shift"
    elif causal_drift:
        attribution = "stored_embedding_drift"
    else:
        attribution = "not_isolated"

    return {
        "test_id": "T1.3_CORRECTED_BY_AMENDMENT_002",
        "status": "COMPLETE",
        "threshold": 0.50,
        "near_threshold_band": [0.45, 0.50],
        "store_order": store_ids,
        "user_message_difference_count": user_difference_count,
        "shared_turn_count": len(first["episodes"]),
        "stores": computed,
        "causal_stored_embedding_drift": causal_drift,
        "assistant_swap_changes_k_count": assistant_changes,
        "script_swap_changes_k_count": script_changes,
        "most_likely_mechanism": attribution,
        "confirming_evidence": (
            "Historical counts are reproduced from persisted vectors; "
            "byte-level replay differences cause no 0.50 threshold crossing; "
            "the registered assistant swap changes at least one K count."
            if attribution == "assistant_response_content_shift"
            else "See the fixed counterfactual fields and full distributions."
        ),
    }


def _load_store(run_directory: Path) -> dict:
    database = run_directory / "study.db"
    connection = sqlite3.connect(
        f"file:{database.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        episode_rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding
            FROM episodes
            WHERE turn_number BETWEEN 1 AND 119
            ORDER BY turn_number, id
            """
        ).fetchall()
        query_row = connection.execute(
            "SELECT user_message FROM episodes WHERE turn_number = 120"
        ).fetchone()
    finally:
        connection.close()
    if len(episode_rows) != 119 or query_row is None:
        raise AssertionError(f"Incomplete historical store: {database}")
    episodes = [dict(row) for row in episode_rows]
    return {
        "run_directory": run_directory,
        "episodes": episodes,
        "query": str(query_row["user_message"]),
        "user_messages": [str(row["user_message"]) for row in episodes],
        "assistant_messages": [
            str(row["assistant_message"]) for row in episodes
        ],
        "pair_texts": [
            f"User: {row['user_message']}\nAssistant: {row['assistant_message']}"
            for row in episodes
        ],
    }


def _historical_k_count(run_directory: Path) -> int:
    path = run_directory / "logs" / "retrieval.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if int(row.get("turn_number", -1)) == 120:
            return int(row["k_count"])
    raise AssertionError(f"No turn-120 retrieval row in {path}")


def _summary(rows: list[dict], key: str) -> dict:
    values = np.asarray([row[key] for row in rows], dtype=np.float64)
    return {
        "minimum": float(np.min(values)),
        "p05": float(np.percentile(values, 5)),
        "p25": float(np.percentile(values, 25)),
        "median": float(np.median(values)),
        "p75": float(np.percentile(values, 75)),
        "p95": float(np.percentile(values, 95)),
        "maximum": float(np.max(values)),
        "mean": float(np.mean(values)),
        "at_or_above_0_50": int(np.sum(values >= 0.50)),
        "from_0_45_below_0_50": int(
            np.sum((values >= 0.45) & (values < 0.50))
        ),
    }
