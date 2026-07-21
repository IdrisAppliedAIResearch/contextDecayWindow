import asyncio
import threading

import numpy as np

from src.db.episode import store_episode, update_episode_topic
from src.db.schema import init_db
from src.db.topic import store_topic
from src.memory.arbitration import arbitrate_candidates
from src.memory.ltm_store import promote_episode
from src.memory.retrieval_engine import RetrievalEngine


def _candidate(episode_id: str, similarity: float, source: str) -> dict:
    candidate = {
        "id": episode_id,
        "turn_number": 1,
        "topic_label": "topic",
        "user_message": episode_id,
        "assistant_message": "answer",
        "similarity": similarity,
    }
    if source == "ltm":
        candidate.update({
            "promoted_at_turn": 31,
            "trigger_type": "weighted_threshold",
        })
    return candidate


def test_arbitration_deduplicates_before_ranking_and_marks_both():
    result = arbitrate_candidates(
        [_candidate("shared", 0.8, "stm")],
        [_candidate("shared", 0.8, "ltm")],
        k_stm=1,
    )

    assert result.duplicates_removed == 1
    assert result.final_set_size == 1
    assert result.episodes[0]["id"] == "shared"
    assert result.episodes[0]["provenance"] == "both"
    assert result.episodes[0]["promoted_at_turn"] == 31


def test_equal_similarity_has_deterministic_non_tier_tie_break():
    result = arbitrate_candidates(
        [_candidate("z-stm", 0.75, "stm")],
        [_candidate("a-ltm", 0.75, "ltm")],
        k_stm=1,
    )

    assert [item["id"] for item in result.episodes] == ["a-ltm", "z-stm"]


def test_arbitration_caps_at_k_stm_plus_m():
    stm = [_candidate(f"stm-{index}", 0.9 - index / 100, "stm") for index in range(2)]
    ltm = [_candidate(f"ltm-{index}", 0.8 - index / 100, "ltm") for index in range(8)]

    result = arbitrate_candidates(stm, ltm, k_stm=2, ltm_top_m=5)

    assert result.final_set_size == 7
    assert len(result.episodes) == 7


def test_empty_stm_degenerate_case_equals_direct_ltm_ranking():
    ltm = [
        _candidate("low", 0.2, "ltm"),
        _candidate("high", 0.9, "ltm"),
        _candidate("middle", 0.5, "ltm"),
    ]

    result = arbitrate_candidates([], ltm, k_stm=0, ltm_top_m=5)

    assert [item["id"] for item in result.episodes] == [
        item["id"] for item in sorted(
            ltm, key=lambda item: (-item["similarity"], item["id"])
        )
    ]


def test_both_empty_returns_empty_set():
    result = arbitrate_candidates([], [], k_stm=0, ltm_top_m=5)
    assert result.episodes == []
    assert result.final_set_size == 0


def test_tier_queries_overlap_in_time(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    engine = RetrievalEngine(
        conn,
        embedding_provider=lambda _: np.zeros(1024, dtype=np.float32),
    )
    rendezvous = threading.Barrier(2, timeout=2)

    def stm_query(_query_embedding):
        rendezvous.wait()
        return ([], [], {}, [], {})

    def ltm_query(_query_embedding):
        rendezvous.wait()
        return []

    engine._query_stm_tier = stm_query
    engine._query_ltm_tier = ltm_query

    stm_result, ltm_result = asyncio.run(
        engine._retrieve_tiers_parallel(np.zeros(1024, dtype=np.float32))
    )

    assert stm_result == ([], [], {}, [], {})
    assert ltm_result == []


def _store_promoted_episode(conn, episode_id_seed: int, embedding: np.ndarray):
    topic_id = store_topic(
        conn,
        f"topic_{episode_id_seed}",
        embedding,
        "2026-01-01T00:00:00+00:00",
    )
    episode_id = store_episode(
        conn,
        f"promoted user {episode_id_seed}",
        f"promoted assistant {episode_id_seed}",
        embedding,
        episode_id_seed + 1,
    )
    update_episode_topic(conn, episode_id, topic_id)
    promote_episode(
        conn,
        episode_id,
        31,
        f"topic_{episode_id_seed}",
        "weighted_threshold",
        None,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        "fixture",
        embedding,
    )
    return episode_id


def test_ltm_query_is_top_five_ranked_and_read_only(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    query = np.zeros(1024, dtype=np.float32)
    query[0] = 1.0
    for index in range(6):
        embedding = np.zeros(1024, dtype=np.float32)
        embedding[0] = 1.0 - index * 0.1
        embedding[index + 1] = index * 0.1
        _store_promoted_episode(conn, index, embedding)
    before = conn.execute("SELECT COUNT(*) FROM ltm_episodes").fetchone()[0]
    engine = RetrievalEngine(conn, embedding_provider=lambda _: query)

    candidates = engine._query_ltm_tier(query)

    after = conn.execute("SELECT COUNT(*) FROM ltm_episodes").fetchone()[0]
    assert len(candidates) == 5
    assert [item["similarity"] for item in candidates] == sorted(
        [item["similarity"] for item in candidates], reverse=True
    )
    assert after == before == 6


def test_real_retrieval_places_both_provenance_once_in_ltm_block(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    query = np.zeros(1024, dtype=np.float32)
    query[0] = 1.0
    promoted_id = _store_promoted_episode(conn, 0, query)
    conn.execute(
        "UPDATE episodes SET last_retrieved_at = ? WHERE id = ?",
        ("2020-01-01T00:00:00+00:00", promoted_id),
    )

    distractor = np.zeros(1024, dtype=np.float32)
    distractor[1] = 1.0
    distractor_topic = store_topic(
        conn,
        "distractors",
        distractor,
        "2026-01-01T00:00:00+00:00",
    )
    for turn in range(2, 12):
        episode_id = store_episode(
            conn, f"distractor {turn}", "answer", distractor, turn
        )
        update_episode_topic(conn, episode_id, distractor_topic)
    conn.commit()
    engine = RetrievalEngine(conn, embedding_provider=lambda _: query)

    result = engine.retrieve("matching query", 12)

    assert result.arbitration.duplicates_removed == 1
    assert result.arbitration.episodes[0]["provenance"] == "both"
    assert result.retrieved_stm_episodes == []
    assert len(result.retrieved_ltm_episodes) == 1
    assert result.constructed_prompt.count("promoted user 0") == 1
    assert "<retrieved_ltm>" in result.constructed_prompt
    assert 'promoted_at_turn="31"' in result.constructed_prompt
    assert result.total_episodes_in_context == 11
