"""Study 003 STM-to-LTM promotion at canonical topic transitions."""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.db.episode import get_episode_by_id, get_episodes_by_topic
from src.db.topic import get_topic_by_id
from src.memory.ltm_store import (
    get_ltm_centroid,
    get_ltm_episode_count,
    is_episode_promoted,
    log_promotion_event,
    promote_episode,
)
from src.memory.promotion_filters import (
    calculate_weighted_score,
    evaluate_promotion,
    score_association,
    score_emotional_valence,
    score_novelty,
    score_repetition,
)


@dataclass
class EpisodePromotionResult:
    episode_id: str
    turn_number: int
    topic: str
    novelty: float
    repetition: float
    association: float
    emotional: float
    weighted_score: float
    promoted: bool
    trigger_type: str
    triggered_filter: Optional[str]


@dataclass
class PromotionSummary:
    turn: int
    topic: str
    evaluated: int
    promoted: int
    episode_results: list[EpisodePromotionResult]


class PromotionEngine:
    """Evaluate the outgoing canonical topic after each genuine transition."""

    MINIMUM_OUTGOING_EPISODES = 3

    def __init__(self, conn, inference_client):
        self._conn = conn
        self._inference_client = inference_client

    def process_transition(
        self,
        previous_episode_id: Optional[str],
        current_episode_id: str,
        current_turn: int,
    ) -> Optional[PromotionSummary]:
        if previous_episode_id is None:
            return None

        previous = get_episode_by_id(self._conn, previous_episode_id)
        current = get_episode_by_id(self._conn, current_episode_id)
        if previous is None or current is None:
            raise ValueError("Cannot evaluate promotion for an episode missing from STM")
        if previous["topic_id"] == current["topic_id"]:
            return None

        topic_row = get_topic_by_id(self._conn, previous["topic_id"])
        if topic_row is None:
            raise ValueError("Outgoing canonical topic is missing")
        topic_label = topic_row["label"]
        outgoing_episodes = get_episodes_by_topic(self._conn, previous["topic_id"])
        if len(outgoing_episodes) < self.MINIMUM_OUTGOING_EPISODES:
            return None

        # Snapshot exactly once so all episodes in this batch share the same LTM reference.
        ltm_centroid = get_ltm_centroid(self._conn)
        ltm_is_empty = get_ltm_episode_count(self._conn) == 0
        results = []
        promoted = 0
        for episode in outgoing_episodes:
            if is_episode_promoted(self._conn, episode["id"]):
                continue
            embedding = np.frombuffer(episode["embedding"], dtype=np.float32)
            content = (
                f"User: {episode['user_message']}\n"
                f"Assistant: {episode['assistant_message']}"
            )
            novelty = score_novelty(embedding, ltm_centroid)
            repetition = score_repetition(episode["retrieval_count"])
            association = score_association(embedding, ltm_centroid)
            emotional = score_emotional_valence(content, self._inference_client)
            weighted = calculate_weighted_score(novelty, repetition, association, emotional)
            should_promote, trigger_type, triggered_filter = evaluate_promotion(
                novelty, repetition, association, emotional, ltm_is_empty=ltm_is_empty
            )
            if should_promote:
                promote_episode(
                    self._conn, episode["id"], current_turn, topic_label, trigger_type,
                    triggered_filter, novelty, repetition, association, emotional,
                    weighted, content, embedding,
                )
                promoted += 1
            results.append(EpisodePromotionResult(
                episode_id=episode["id"], turn_number=episode["turn_number"], topic=topic_label,
                novelty=novelty, repetition=repetition, association=association,
                emotional=emotional, weighted_score=weighted, promoted=should_promote,
                trigger_type=trigger_type, triggered_filter=triggered_filter,
            ))

        log_promotion_event(self._conn, current_turn, topic_label, len(results), promoted)
        return PromotionSummary(current_turn, topic_label, len(results), promoted, results)
