"""STM-to-LTM promotion at transitions and the Study 004 final flush."""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.db.episode import get_episode_by_id, get_episodes_by_topic
from src.db.topic import get_topic_by_id
from src.memory.ltm_store import (
    get_ltm_snapshot,
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
    global_association: float
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
    event_type: str = "transition"


class PromotionEngine:
    """Evaluate canonical topics through one shared batch-snapshot path."""

    MINIMUM_OUTGOING_EPISODES = 3
    END_OF_SESSION_FLUSH_TURN = 111

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

        return self._process_topic(
            previous["topic_id"], current_turn, event_type="transition"
        )

    def process_flush(
        self,
        active_episode_id: str,
        current_turn: int,
        expected_flush_turn: int = END_OF_SESSION_FLUSH_TURN,
    ) -> Optional[PromotionSummary]:
        """Evaluate the final active topic before the probe block begins."""
        if current_turn != expected_flush_turn:
            raise ValueError(
                f"End-of-session promotion flush must run at turn "
                f"{expected_flush_turn}, got {current_turn}"
            )
        active = get_episode_by_id(self._conn, active_episode_id)
        if active is None:
            raise ValueError("Cannot flush an episode missing from STM")
        return self._process_topic(
            active["topic_id"], current_turn, event_type="end_of_session_flush"
        )

    def _process_topic(
        self,
        topic_id: str,
        current_turn: int,
        event_type: str,
    ) -> Optional[PromotionSummary]:
        topic_row = get_topic_by_id(self._conn, topic_id)
        if topic_row is None:
            raise ValueError("Canonical promotion topic is missing")
        topic_label = topic_row["label"]
        outgoing_episodes = get_episodes_by_topic(self._conn, topic_id)
        if len(outgoing_episodes) < self.MINIMUM_OUTGOING_EPISODES:
            return None

        # Snapshot exactly once so writes during this batch cannot change either
        # the global Novelty reference or the per-topic Association references.
        ltm_snapshot = get_ltm_snapshot(self._conn)
        ltm_is_empty = ltm_snapshot.episode_count == 0
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
            novelty = score_novelty(embedding, ltm_snapshot.global_centroid)
            repetition = score_repetition(episode["retrieval_count"])
            association = score_association(
                embedding, ltm_snapshot.topic_centroids
            )
            global_association = score_association(
                embedding,
                []
                if ltm_snapshot.global_centroid is None
                else [ltm_snapshot.global_centroid],
            )
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
                global_association=global_association,
                emotional=emotional, weighted_score=weighted, promoted=should_promote,
                trigger_type=trigger_type, triggered_filter=triggered_filter,
            ))

        log_promotion_event(
            self._conn,
            current_turn,
            topic_label,
            len(results),
            promoted,
            event_type=event_type,
        )
        return PromotionSummary(
            current_turn,
            topic_label,
            len(results),
            promoted,
            results,
            event_type,
        )
