from dataclasses import dataclass

import numpy as np

from src.db.episode import store_episode, update_episode_topic
from src.db.schema import init_db
from src.db.topic import store_topic
from src.memory.promotion_engine import PromotionEngine


@dataclass
class FakeResult:
    assistant_message: str


class FakeInferenceClient:
    def complete(self, prompt, suppress_rule_detection=False):
        assert suppress_rule_detection is True
        return FakeResult("0.8")


def _store_topic_and_episode(conn, label, embedding, turn):
    topic_id = store_topic(conn, label, embedding, "2026-01-01T00:00:00+00:00")
    episode_id = store_episode(conn, f"user {turn}", f"assistant {turn}", embedding, turn)
    update_episode_topic(conn, episode_id, topic_id)
    return topic_id, episode_id


def test_promotes_outgoing_topic_at_genuine_transition(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    first_embedding = np.zeros(1024, dtype=np.float32)
    first_embedding[0] = 1.0
    second_embedding = np.zeros(1024, dtype=np.float32)
    second_embedding[1] = 1.0
    first_topic, first_episode = _store_topic_and_episode(conn, "topic_1", first_embedding, 1)
    _, second_episode = _store_topic_and_episode(conn, "topic_2", second_embedding, 2)
    conn.execute("UPDATE episodes SET retrieval_count = 5 WHERE id = ?", (first_episode,))
    conn.commit()

    summary = PromotionEngine(conn, FakeInferenceClient()).process_transition(
        first_episode, second_episode, 2
    )

    assert summary is not None
    assert summary.topic == "topic_1"
    assert summary.evaluated == 1
    assert summary.promoted == 1
    assert conn.execute("SELECT COUNT(*) FROM ltm_episodes").fetchone()[0] == 1
    assert conn.execute("SELECT topic FROM ltm_promotion_log").fetchone()[0] == "topic_1"


def test_canonical_same_topic_does_not_trigger_promotion(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    embedding = np.zeros(1024, dtype=np.float32)
    embedding[0] = 1.0
    topic_id, first_episode = _store_topic_and_episode(conn, "topic_1", embedding, 1)
    second_episode = store_episode(conn, "user 2", "assistant 2", embedding, 2)
    update_episode_topic(conn, second_episode, topic_id)

    summary = PromotionEngine(conn, FakeInferenceClient()).process_transition(
        first_episode, second_episode, 2
    )

    assert summary is None
    assert conn.execute("SELECT COUNT(*) FROM ltm_promotion_log").fetchone()[0] == 0
