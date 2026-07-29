from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.db.episode import store_episode
from src.db.retrieval import (
    get_all_episodes_with_embeddings,
    log_retrieval_events_batch,
)
from src.db.schema import init_db
from src.memory.context_matched_stm import (
    ContextMatchedStmRetrievalEngine,
)
from src.retrieval_bakeoff.tier6_equivalence import (
    oracle_turn,
    order_fixture,
    reproduce_locked_vectors,
)


def _unit(index: int) -> np.ndarray:
    vector = np.zeros(1_024, dtype=np.float32)
    vector[index] = 1.0
    return vector


def test_corrected_n_order_uses_persisted_logical_generations(
    tmp_path: Path,
) -> None:
    database = tmp_path / "logical.db"
    conn = init_db(str(database))
    ids = [
        store_episode(
            conn,
            f"user {index}",
            f"assistant {index}",
            _unit(index),
            index + 1,
        )
        for index in range(3)
    ]
    log_retrieval_events_batch(
        conn,
        [
            {
                "turn_number": 4,
                "episode_id": ids[0],
                "similarity_score": 0.0,
                "decay_score": 0.0,
                "retrieval_type": "N",
            },
            {
                "turn_number": 9,
                "episode_id": ids[1],
                "similarity_score": 0.0,
                "decay_score": 0.0,
                "retrieval_type": "N",
            },
        ],
    )
    conn.execute(
        "UPDATE episodes SET last_retrieved_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), ids[0]),
    )
    conn.commit()
    conn.close()

    reopened = init_db(str(database))
    engine = ContextMatchedStmRetrievalEngine(
        reopened,
        n_cap=12,
        k_threshold=0.48,
        payload_budget=20_000,
        embedding_provider=lambda _: _unit(0),
    )
    rows = engine._deserialize(
        get_all_episodes_with_embeddings(reopened)
    )
    ordered, _ = engine._n_retrieve_widened(rows)
    reopened.close()

    assert ordered == [ids[2], ids[0], ids[1]]


def test_minimal_order_fixture_matches_registered_semantics() -> None:
    fixture = order_fixture()
    assert fixture["status"] == "PASS"
    assert fixture["production_order"] == [
        "unretrieved",
        "oldest-retrieved",
        "newest-retrieved",
    ]


def test_oracle_updates_only_admitted_episode_generations() -> None:
    episodes = [
        {
            "id": f"episode-{index}",
            "turn_number": index + 1,
            "topic_id": None,
            "topic_label": "",
            "user_message": "u" + ("x" * 200 * index),
            "assistant_message": "a" + ("y" * 200 * index),
            "embedding": _unit(index),
        }
        for index in range(3)
    ]
    last_generation = {
        "episode-0": 1,
        "episode-1": 2,
    }
    result = oracle_turn(
        eligible=episodes,
        query_vector=_unit(2),
        last_generation=last_generation,
        turn=10,
        n_cap=12,
        k_threshold=0.48,
        payload_budget=1_000,
    )
    assert result["n_candidate_ids"] == [
        "episode-2",
        "episode-0",
        "episode-1",
    ]
    assert set(result["last_generation"].values()) <= {1, 2, 10}
    assert result["payload_chars"] <= 1_000


def test_locked_vector_reproduction_requires_every_exact_vector() -> None:
    traces = [
        {
            "turn_number": turn,
            "production": {
                "payload_chars": 1_000 + turn,
                "delivered_n_ids": ["n"],
                "delivered_k_only_ids": [],
            },
        }
        for turn in range(1, 112)
    ]
    vector = [1_000 + turn for turn in range(92, 112)]
    settings = {
        "arm_l_target_vector": vector,
        "match_gate_median_absolute_percentage_error": 0.05,
        "selected": {
            "delivered_vector": vector,
            "delivered_n_counts": [1] * 20,
            "delivered_k_only_counts": [0] * 20,
            "absolute_errors": [0] * 20,
            "median_absolute_percentage_error": 0.0,
        },
    }
    result = reproduce_locked_vectors(
        traces=traces,
        settings=settings,
    )
    assert result["status"] == "PASS"

    settings["selected"]["delivered_vector"][-1] += 1
    result = reproduce_locked_vectors(
        traces=traces,
        settings=settings,
    )
    assert result["status"] == "FAIL"
    assert result["checks"]["delivered_vector"] is False
