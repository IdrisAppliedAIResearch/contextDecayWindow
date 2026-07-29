from __future__ import annotations

import hashlib
import json
import sqlite3
import statistics
from pathlib import Path
from typing import Callable

import numpy as np

from src.db.retrieval import get_last_retrieval_generations
from src.db.schema import init_db
from src.embeddings.provider import cosine_similarity
from src.memory.context_matched_stm import (
    ContextMatchedStmRetrievalEngine,
    extract_stm_payload,
    logical_n_key,
    pack_stm_payload,
)
from src.retrieval_bakeoff.config import REPO_ROOT
from src.retrieval_bakeoff.tier6 import _calibration_n_key


MAX_REPLAY_TURN = 111
CALIBRATION_TURNS = tuple(range(92, 112))
AMENDMENT_ANCHOR = "39ba9175"


def run_equivalence_replay(
    *,
    source_database: Path,
    script_path: Path,
    query_vectors: dict[int, np.ndarray],
    settings: dict,
    production_database: Path,
) -> dict:
    episodes, topics = load_source_corpus(
        source_database,
        max_turn=MAX_REPLAY_TURN,
    )
    script_turns = load_script_turns(
        script_path,
        max_turn=MAX_REPLAY_TURN,
    )
    if set(query_vectors) != set(script_turns):
        raise AssertionError("Query vectors do not cover turns 1-111 exactly")

    selected = settings["selected"]
    n_cap = int(selected["n_cap"])
    k_threshold = float(selected["k_threshold"])
    payload_budget = int(settings["payload_budget"])
    oracle_last_generation: dict[str, int] = {}
    vector_holder: list[np.ndarray] = [
        np.zeros(1_024, dtype=np.float32)
    ]

    conn = init_db(str(production_database))
    try:
        seed_topics(conn, topics)
        engine = ContextMatchedStmRetrievalEngine(
            conn,
            n_cap=n_cap,
            k_threshold=k_threshold,
            payload_budget=payload_budget,
            embedding_provider=lambda _: vector_holder[0],
            system_prompt="You are a helpful assistant.",
        )
        traces = []
        all_match = True
        for turn in range(1, MAX_REPLAY_TURN + 1):
            query_vector = np.asarray(
                query_vectors[turn],
                dtype=np.float32,
            )
            eligible = [
                episode
                for episode in episodes
                if int(episode["turn_number"]) < turn
            ]
            oracle = oracle_turn(
                eligible=eligible,
                query_vector=query_vector,
                last_generation=oracle_last_generation,
                turn=turn,
                n_cap=n_cap,
                k_threshold=k_threshold,
                payload_budget=payload_budget,
            )

            vector_holder[0] = query_vector
            production_eligible = eligible_episode_ids(conn)
            production_result = engine.retrieve(
                script_turns[turn],
                turn,
            )
            production_payload = extract_stm_payload(
                production_result.constructed_prompt
            )
            production_last_generation = (
                get_last_retrieval_generations(conn)
            )
            production = {
                "eligible_ids": production_eligible,
                "n_candidate_ids": production_result.n_candidate_ids,
                "k_candidate_ids": production_result.k_candidate_ids,
                "delivered_n_ids": production_result.n_episode_ids,
                "delivered_k_only_ids": (
                    production_result.delivered_k_only_ids
                ),
                "skipped_n_ids": production_result.skipped_n_ids,
                "skipped_k_ids": production_result.skipped_k_ids,
                "duplicate_ids": production_result.n_k_duplicate_ids,
                "payload_sha256": sha256_text(production_payload),
                "payload_chars": len(production_payload),
                "last_generation": production_last_generation,
            }
            checks = {
                field: oracle[field] == production[field]
                for field in (
                    "eligible_ids",
                    "n_candidate_ids",
                    "k_candidate_ids",
                    "delivered_n_ids",
                    "delivered_k_only_ids",
                    "skipped_n_ids",
                    "skipped_k_ids",
                    "duplicate_ids",
                    "payload_sha256",
                    "payload_chars",
                    "last_generation",
                )
            }
            checks["payload_bytes"] = (
                oracle["payload"] == production_payload
            )
            turn_match = all(checks.values())
            all_match = all_match and turn_match
            traces.append(
                {
                    "turn_number": turn,
                    "status": "PASS" if turn_match else "FAIL",
                    "checks": checks,
                    "oracle": {
                        key: value
                        for key, value in oracle.items()
                        if key != "payload"
                    },
                    "production": production,
                }
            )
            insert_source_episode(
                conn,
                next(
                    episode
                    for episode in episodes
                    if int(episode["turn_number"]) == turn
                ),
            )
    finally:
        conn.close()

    settings_reproduction = reproduce_locked_vectors(
        traces=traces,
        settings=settings,
    )
    fixture = order_fixture()
    status = (
        "PASS"
        if all_match
        and settings_reproduction["status"] == "PASS"
        and fixture["status"] == "PASS"
        else "FAIL"
    )
    return {
        "status": status,
        "turn_count": len(traces),
        "all_turns_exact": all_match,
        "selected_settings": {
            "n_cap": n_cap,
            "k_threshold": k_threshold,
            "payload_budget": payload_budget,
        },
        "order_fixture": fixture,
        "settings_reproduction": settings_reproduction,
        "turns": traces,
    }


def oracle_turn(
    *,
    eligible: list[dict],
    query_vector: np.ndarray,
    last_generation: dict[str, int],
    turn: int,
    n_cap: int,
    k_threshold: float,
    payload_budget: int,
) -> dict:
    eligible_ordered = sorted(
        eligible,
        key=lambda episode: (
            int(episode["turn_number"]),
            str(episode["id"]),
        ),
    )
    n_ranked = sorted(
        eligible_ordered,
        key=lambda episode: _calibration_n_key(
            episode,
            last_generation,
        ),
    )[:n_cap]
    similarities = {
        str(episode["id"]): cosine_similarity(
            query_vector,
            episode["embedding"],
        )
        for episode in eligible_ordered
    }
    k_ranked = [
        episode
        for episode in eligible_ordered
        if similarities[str(episode["id"])] >= k_threshold
    ]
    n_ids = {str(episode["id"]) for episode in n_ranked}
    duplicate_ids = [
        str(episode["id"])
        for episode in k_ranked
        if str(episode["id"]) in n_ids
    ]
    k_only = [
        {
            **clean_episode(episode),
            "similarity": similarities[str(episode["id"])],
            "provenance": "stm",
        }
        for episode in k_ranked
        if str(episode["id"]) not in n_ids
    ]
    packed = pack_stm_payload(
        [clean_episode(episode) for episode in n_ranked],
        k_only,
        payload_budget,
    )
    for episode_id in packed.selected_ids:
        last_generation[episode_id] = turn
    return {
        "eligible_ids": [
            str(episode["id"]) for episode in eligible_ordered
        ],
        "n_candidate_ids": [
            str(episode["id"]) for episode in n_ranked
        ],
        "k_candidate_ids": [
            str(episode["id"]) for episode in k_ranked
        ],
        "delivered_n_ids": [
            str(episode["id"]) for episode in packed.recent_episodes
        ],
        "delivered_k_only_ids": [
            str(episode["id"]) for episode in packed.stm_episodes
        ],
        "skipped_n_ids": list(packed.skipped_n_ids),
        "skipped_k_ids": list(packed.skipped_k_ids),
        "duplicate_ids": duplicate_ids,
        "payload": packed.payload,
        "payload_sha256": sha256_text(packed.payload),
        "payload_chars": packed.serialized_chars,
        "last_generation": dict(sorted(last_generation.items())),
    }


def reproduce_locked_vectors(*, traces: list[dict], settings: dict) -> dict:
    selected = settings["selected"]
    by_turn = {
        int(row["turn_number"]): row
        for row in traces
    }
    delivered_vector = [
        by_turn[turn]["production"]["payload_chars"]
        for turn in CALIBRATION_TURNS
    ]
    delivered_n_counts = [
        len(by_turn[turn]["production"]["delivered_n_ids"])
        for turn in CALIBRATION_TURNS
    ]
    delivered_k_only_counts = [
        len(by_turn[turn]["production"]["delivered_k_only_ids"])
        for turn in CALIBRATION_TURNS
    ]
    target_vector = [int(value) for value in settings["arm_l_target_vector"]]
    absolute_errors = [
        abs(delivered - target)
        for delivered, target in zip(
            delivered_vector,
            target_vector,
            strict=True,
        )
    ]
    median_ape = statistics.median(
        error / target
        for error, target in zip(
            absolute_errors,
            target_vector,
            strict=True,
        )
    )
    checks = {
        "delivered_vector": (
            delivered_vector == selected["delivered_vector"]
        ),
        "delivered_n_counts": (
            delivered_n_counts == selected["delivered_n_counts"]
        ),
        "delivered_k_only_counts": (
            delivered_k_only_counts
            == selected["delivered_k_only_counts"]
        ),
        "absolute_errors": absolute_errors == selected["absolute_errors"],
        "median_absolute_percentage_error": (
            abs(
                median_ape
                - float(selected["median_absolute_percentage_error"])
            )
            <= 1e-15
        ),
        "registered_match_gate": (
            median_ape
            <= float(
                settings[
                    "match_gate_median_absolute_percentage_error"
                ]
            )
        ),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "calibration_turns": list(CALIBRATION_TURNS),
        "delivered_vector": delivered_vector,
        "delivered_n_counts": delivered_n_counts,
        "delivered_k_only_counts": delivered_k_only_counts,
        "absolute_errors": absolute_errors,
        "median_absolute_percentage_error": median_ape,
    }


def order_fixture() -> dict:
    episodes = [
        {"id": "oldest-retrieved", "turn_number": 1},
        {"id": "newest-retrieved", "turn_number": 2},
        {"id": "unretrieved", "turn_number": 3},
    ]
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE retrieval_events "
            "(episode_id TEXT NOT NULL, turn_number INTEGER NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO retrieval_events (episode_id, turn_number) "
            "VALUES (?, ?)",
            [
                ("oldest-retrieved", 4),
                ("newest-retrieved", 9),
            ],
        )
        generations = get_last_retrieval_generations(connection)
    finally:
        connection.close()
    oracle = [
        episode["id"]
        for episode in sorted(
            episodes,
            key=lambda episode: _calibration_n_key(
                episode,
                generations,
            ),
        )
    ]
    production = [
        episode["id"]
        for episode in sorted(
            episodes,
            key=lambda episode: logical_n_key(
                episode,
                generations,
            ),
        )
    ]
    expected = [
        "unretrieved",
        "oldest-retrieved",
        "newest-retrieved",
    ]
    return {
        "status": (
            "PASS"
            if oracle == production == expected
            else "FAIL"
        ),
        "expected_order": expected,
        "oracle_order": oracle,
        "production_order": production,
        "database_generations": generations,
    }


def load_source_corpus(
    database: Path,
    *,
    max_turn: int,
) -> tuple[list[dict], list[dict]]:
    connection = sqlite3.connect(
        f"file:{database.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        episodes = [
            dict(row)
            for row in connection.execute(
                """
                SELECT e.id, e.topic_id, t.label AS topic_label,
                       e.user_message, e.assistant_message, e.embedding,
                       e.turn_number, e.ground_truth_domain, e.created_at,
                       e.role, e.text, e.dreamed
                FROM episodes AS e
                LEFT JOIN topics AS t ON t.id = e.topic_id
                WHERE e.turn_number <= ?
                ORDER BY e.turn_number, e.id
                """,
                (max_turn,),
            ).fetchall()
        ]
        topics = [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, label, centroid, episode_count, created_at,
                       last_updated_at
                FROM topics
                ORDER BY id
                """
            ).fetchall()
        ]
    finally:
        connection.close()
    expected_turns = list(range(1, max_turn + 1))
    observed_turns = [int(row["turn_number"]) for row in episodes]
    if observed_turns != expected_turns:
        raise AssertionError("Source database does not have one episode per turn")
    for episode in episodes:
        if episode["embedding"] is None:
            raise AssertionError(
                f"Source episode {episode['id']} has no embedding"
            )
        episode["embedding"] = np.frombuffer(
            episode["embedding"],
            dtype=np.float32,
        )
    return episodes, topics


def load_script_turns(script_path: Path, *, max_turn: int) -> dict[int, str]:
    payload = json.loads(script_path.read_text(encoding="utf-8"))
    turns = {
        int(row["turn"]): str(row["user"])
        for row in payload["turns"]
        if int(row["turn"]) <= max_turn
    }
    if set(turns) != set(range(1, max_turn + 1)):
        raise AssertionError("Script does not cover the replay range exactly")
    return turns


def seed_topics(conn: sqlite3.Connection, topics: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO topics (
            id, label, centroid, episode_count, created_at, last_updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row["label"],
                row["centroid"],
                row["episode_count"],
                row["created_at"],
                row["last_updated_at"],
            )
            for row in topics
        ],
    )
    conn.commit()


def insert_source_episode(conn: sqlite3.Connection, episode: dict) -> None:
    conn.execute(
        """
        INSERT INTO episodes (
            id, topic_id, user_message, assistant_message, embedding,
            turn_number, ground_truth_domain, created_at, last_retrieved_at,
            retrieval_count, role, text, dreamed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, ?, ?, ?)
        """,
        (
            episode["id"],
            episode["topic_id"],
            episode["user_message"],
            episode["assistant_message"],
            np.asarray(
                episode["embedding"],
                dtype=np.float32,
            ).tobytes(),
            int(episode["turn_number"]),
            episode["ground_truth_domain"],
            episode["created_at"],
            episode["role"],
            episode["text"],
            int(episode["dreamed"]),
        ),
    )
    conn.commit()


def eligible_episode_ids(conn: sqlite3.Connection) -> list[str]:
    return [
        str(row[0])
        for row in conn.execute(
            "SELECT id FROM episodes ORDER BY turn_number, id"
        ).fetchall()
    ]


def clean_episode(episode: dict) -> dict:
    return {
        "id": str(episode["id"]),
        "topic_id": episode.get("topic_id"),
        "topic_label": (
            episode.get("topic_label")
            or episode.get("topic_id")
            or ""
        ),
        "user_message": episode["user_message"],
        "assistant_message": episode["assistant_message"],
        "turn_number": int(episode["turn_number"]),
    }


def embed_script_turns(
    *,
    script_turns: dict[int, str],
    embedder: Callable[[str], np.ndarray],
) -> dict[int, np.ndarray]:
    ordered = sorted(script_turns)
    texts = [script_turns[turn] for turn in ordered]
    vectors = (
        embedder.embed_many(texts)
        if hasattr(embedder, "embed_many")
        else [embedder(text) for text in texts]
    )
    return {
        turn: np.asarray(vector, dtype=np.float32)
        for turn, vector in zip(ordered, vectors, strict=True)
    }


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
