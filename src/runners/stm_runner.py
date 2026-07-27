"""Runtime adapter for the structurally minimal Study 009 STM composition."""

import sqlite3

import numpy as np

from src.db.episode import store_episode
from src.db.rule_store import store_rule
from src.inference.provider import InferenceResult
from src.memory.stm_retrieval_engine import StmRetrievalEngine
from src.memory.topic_manager import TopicManager
from src.observability.turn_record import AssignmentResult, TurnRecord
from src.runners.base_runner import BaseRunner


class StmRunner(BaseRunner):
    condition = "iterative"

    def __init__(
        self,
        conn: sqlite3.Connection,
        embedding_provider,
        topic_manager: TopicManager,
        retrieval_engine: StmRetrievalEngine,
    ):
        self._conn = conn
        self._embedding_provider = embedding_provider
        self._topic_manager = topic_manager
        self._retrieval_engine = retrieval_engine

    def build_context(
        self, user_message: str, turn_number: int
    ) -> tuple[str, TurnRecord]:
        result = self._retrieval_engine.retrieve(user_message, turn_number)
        k_set = set(result.k_episode_ids)
        n_set = set(result.n_episode_ids)

        n_episodes = []
        for episode in result.recent_episodes:
            episode_id = episode["id"]
            n_episodes.append({
                "id": episode_id,
                "turn_number": episode["turn_number"],
                "user_message": episode["user_message"],
                "assistant_message": episode["assistant_message"],
                "sim_score": result.k_scores.get(episode_id, 0.0),
                "decay_score": result.n_scores.get(episode_id, 0.0),
                "topic_label": episode.get(
                    "topic_label", episode.get("topic_id", "")
                ),
                "retrieval_type": (
                    "KN" if episode_id in k_set and episode_id in n_set else "N"
                ),
            })

        k_episodes = [{
            "id": episode["id"],
            "turn_number": episode["turn_number"],
            "user_message": episode["user_message"],
            "assistant_message": episode["assistant_message"],
            "sim_score": episode["similarity"],
            "decay_score": result.n_scores.get(episode["id"], 0.0),
            "topic_label": episode.get(
                "topic_label", episode.get("topic_id", "")
            ),
            "retrieval_type": "K",
        } for episode in result.retrieved_stm_episodes]

        k_chars = sum(
            len(
                f"User: {episode['user_message']}\n"
                f"Assistant: {episode['assistant_message']}"
            )
            for episode in k_episodes
        )
        n_chars = sum(
            len(
                f"User: {episode['user_message']}\n"
                f"Assistant: {episode['assistant_message']}"
            )
            for episode in n_episodes
        )
        total = result.total_episodes_in_context
        record = TurnRecord(
            turn_number=turn_number,
            condition=self.condition,
            user_message=user_message,
            k_count=result.k_count,
            n_count=result.n_count,
            k_only_count=len(k_episodes),
            n_total_in_store=result.n_total_in_store,
            total_in_context=total,
            k_episodes=k_episodes,
            n_episodes=n_episodes,
            arbitration_stm_candidates=len(k_episodes),
            arbitration_final_set_size=len(k_episodes),
            arbitration_provenance_list=[
                {"episode_id": episode["id"], "provenance": "stm"}
                for episode in k_episodes
            ],
            estimated_tokens=result.estimated_tokens,
            k_token_estimate=k_chars // 4,
            n_token_estimate=n_chars // 4,
            topic_count=self._topic_manager.topic_count,
            episode_count=result.n_total_in_store,
            rule_store_count=len(result.rule_episodes),
            rule_token_estimate=result.rule_token_estimate,
            constructed_prompt=result.constructed_prompt,
        )
        return result.constructed_prompt, record

    def on_turn_complete(
        self,
        user_message: str,
        assistant_message: str,
        turn_number: int,
        embedding: np.ndarray | None = None,
        inference_result: InferenceResult | None = None,
        topic_embedding: np.ndarray | None = None,
        ground_truth_domain: str | None = None,
    ) -> AssignmentResult:
        if embedding is None:
            embedding = self._embedding_provider(
                f"User: {user_message}\nAssistant: {assistant_message}"
            )
        episode_id = store_episode(
            self._conn,
            user_message,
            assistant_message,
            embedding,
            turn_number,
            ground_truth_domain,
        )
        if (
            inference_result
            and inference_result.contains_rule
            and inference_result.rule_summary
        ):
            store_rule(
                self._conn,
                episode_id,
                inference_result.rule_summary,
                turn_number,
            )
        assignment = self._topic_manager.assign(
            episode_id,
            topic_embedding if topic_embedding is not None else embedding,
        )
        return assignment

    @property
    def history_token_estimate(self) -> int:
        return 0
