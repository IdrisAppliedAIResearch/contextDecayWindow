import csv
from dataclasses import dataclass

import numpy as np
import pytest

from src.db.episode import store_episode, update_episode_topic
from src.db.schema import init_db
from src.db.topic import merge_topics, reassign_episodes, store_topic
from src.memory.ltm_store import get_ltm_snapshot, promote_episode
from src.memory.promotion_engine import PromotionEngine
from src.memory.topic_manager import TopicManager
from src.observability.file_writer import FileWriter
from src.observability.run_config import RunConfig
from src.observability.turn_record import TurnRecord
from src.study.runner import StudyRunner


@dataclass
class FakeResult:
    assistant_message: str


class ZeroEmotionalInference:
    def complete(self, prompt, suppress_rule_detection=False):
        assert suppress_rule_detection is True
        return FakeResult("0.0")


def _unit_vector(index: int) -> np.ndarray:
    vector = np.zeros(1024, dtype=np.float32)
    vector[index] = 1.0
    return vector


def _topic(conn, label: str, embedding: np.ndarray) -> str:
    return store_topic(
        conn, label, embedding, "2026-01-01T00:00:00+00:00"
    )


def _episode(
    conn,
    topic_id: str,
    embedding: np.ndarray,
    turn: int,
    domain: str,
) -> str:
    episode_id = store_episode(
        conn,
        f"user {turn}",
        f"assistant {turn}",
        embedding,
        turn,
        domain,
    )
    update_episode_topic(conn, episode_id, topic_id)
    return episode_id


def _promote_fixture(conn, episode_id, topic, embedding, turn=31):
    return promote_episode(
        conn,
        episode_id,
        turn,
        topic,
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


def test_ltm_snapshot_pools_different_stored_labels_after_canonical_merge(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    first = _unit_vector(0)
    second = _unit_vector(1)
    topic_a = _topic(conn, "topic_a", first)
    topic_b = _topic(conn, "topic_b", second)
    episode_a = _episode(conn, topic_a, first, 1, "civil_engineering")
    episode_b = _episode(conn, topic_b, second, 31, "renaissance_art")
    _promote_fixture(conn, episode_a, "topic_a", first)
    _promote_fixture(conn, episode_b, "topic_b", second)

    reassign_episodes(conn, topic_b, topic_a)
    expected = np.mean(np.stack([first, second]), axis=0, dtype=np.float32)
    merge_topics(conn, topic_a, topic_b, expected, 2)

    snapshot = get_ltm_snapshot(conn)

    assert snapshot.episode_count == 2
    assert len(snapshot.topic_centroids) == 1
    assert np.allclose(next(iter(snapshot.topic_centroids.values())), expected)


def test_promotion_batch_freezes_topic_centroids_before_mid_batch_writes(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    prior_embedding = _unit_vector(0)
    outgoing_embedding = _unit_vector(1)
    current_embedding = _unit_vector(2)

    prior_topic = _topic(conn, "prior", prior_embedding)
    prior_episode = _episode(
        conn, prior_topic, prior_embedding, 1, "civil_engineering"
    )
    _promote_fixture(conn, prior_episode, "prior", prior_embedding)

    outgoing_topic = _topic(conn, "outgoing", outgoing_embedding)
    outgoing_episodes = [
        _episode(
            conn,
            outgoing_topic,
            outgoing_embedding,
            turn,
            "renaissance_art",
        )
        for turn in (31, 32, 33)
    ]
    conn.execute(
        "UPDATE episodes SET retrieval_count = 5 WHERE topic_id = ?",
        (outgoing_topic,),
    )
    conn.commit()

    current_topic = _topic(conn, "current", current_embedding)
    current_episode = _episode(
        conn, current_topic, current_embedding, 61, "monetary_policy"
    )

    summary = PromotionEngine(
        conn, ZeroEmotionalInference()
    ).process_transition(outgoing_episodes[-1], current_episode, 61)

    assert summary is not None
    assert summary.promoted == 3
    assert [result.association for result in summary.episode_results] == pytest.approx(
        [0.0, 0.0, 0.0]
    )


def test_turn_111_flush_uses_standard_path_and_records_event_type(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    embedding = _unit_vector(3)
    active_topic = _topic(conn, "marine", embedding)
    active_episodes = [
        _episode(conn, active_topic, embedding, turn, "marine_biology")
        for turn in (109, 110, 111)
    ]
    conn.execute(
        "UPDATE episodes SET retrieval_count = 5 WHERE topic_id = ?",
        (active_topic,),
    )
    conn.commit()

    summary = PromotionEngine(conn, ZeroEmotionalInference()).process_flush(
        active_episodes[-1], 111
    )

    assert summary is not None
    assert summary.event_type == "end_of_session_flush"
    assert summary.evaluated == 3
    assert summary.promoted == 3
    log_row = conn.execute(
        "SELECT turn, event_type FROM ltm_promotion_log"
    ).fetchone()
    assert log_row == (111, "end_of_session_flush")


def test_probe_block_cannot_start_until_turn_111_flush_completes():
    with pytest.raises(RuntimeError, match="flush must complete"):
        StudyRunner._assert_flush_completed_before_turn(112, False)

    StudyRunner._assert_flush_completed_before_turn(112, True)


def test_probe_turns_remain_outside_promotion_emission_window():
    assert StudyRunner._promotion_emission_allowed(111)
    assert all(
        not StudyRunner._promotion_emission_allowed(turn)
        for turn in range(112, 122)
    )


def _two_topic_manager(
    conn,
    first_turn: int,
    first_domain: str,
    second_turn: int,
    second_domain: str,
) -> TopicManager:
    manager = TopicManager(conn)
    embedding = _unit_vector(4)
    created_at = "2026-01-01T00:00:00+00:00"
    topic_a = store_topic(conn, "topic_a", embedding, created_at)
    topic_b = store_topic(conn, "topic_b", embedding, created_at)
    _episode(conn, topic_a, embedding, first_turn, first_domain)
    _episode(conn, topic_b, embedding, second_turn, second_domain)
    manager._topics[topic_a] = {
        "label": "topic_a",
        "centroid": embedding.copy(),
        "episode_count": 1,
        "created_at": created_at,
        "last_updated_at": created_at,
    }
    manager._topics[topic_b] = {
        "label": "topic_b",
        "centroid": embedding.copy(),
        "episode_count": 1,
        "created_at": created_at,
        "last_updated_at": created_at,
    }
    manager._episode_count = 2
    return manager


def test_clean_same_domain_merge_has_no_cross_domain_event(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    manager = _two_topic_manager(
        conn, 1, "civil_engineering", 2, "civil_engineering"
    )

    result = manager._run_consolidation_pass(current_turn=10)

    assert result.pairs_merged == 1
    assert not [
        event
        for event in result.purity_events
        if event["event_type"] == "cross_domain_merge"
    ]


def test_mixed_domain_merge_is_logged_and_written_to_purity_csv(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    manager = _two_topic_manager(
        conn, 1, "civil_engineering", 31, "renaissance_art"
    )

    result = manager._run_consolidation_pass(current_turn=31)

    assert result.pairs_merged == 1
    events = [
        event
        for event in result.purity_events
        if event["event_type"] == "cross_domain_merge"
    ]
    assert len(events) == 1
    assert events[0]["turn"] == 31
    assert events[0]["similarity"] == pytest.approx(1.0)

    output_dir = tmp_path / "output"
    writer = FileWriter(RunConfig(
        condition="iterative",
        run_id="synthetic",
        output_dir=str(output_dir),
        study_dir=str(tmp_path),
    ))
    writer.init_run()
    writer.write_turn(TurnRecord(
        turn_number=31,
        condition="iterative",
        user_message="mixed-domain fixture",
        consolidation_occurred=True,
        consolidation_result=result,
    ))

    with open(
        output_dir / "logs" / "consolidation_purity.csv",
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["event_type"] == "cross_domain_merge"
    assert rows[0]["topic_a"] == "topic_a"
    assert rows[0]["topic_b"] == "topic_b"


def test_probe_episode_blocks_bridge_merge_and_logs_rejection(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    manager = _two_topic_manager(
        conn, 1, "civil_engineering", 115, "probe"
    )

    result = manager._run_consolidation_pass(current_turn=115)

    assert result.pairs_merged == 0
    assert result.topics_after == result.topics_before == 2
    events = [
        event
        for event in result.purity_events
        if event["event_type"] == "probe_bridge_blocked"
    ]
    assert len(events) == 1
    assert events[0]["probe_turns"] == [115]
    assert events[0]["similarity"] == pytest.approx(1.0)
