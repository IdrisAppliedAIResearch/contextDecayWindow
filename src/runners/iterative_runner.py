import sqlite3
import numpy as np

from src.db.episode import store_episode
from src.db.rule_store import store_rule
from src.memory.retrieval_engine import RetrievalEngine
from src.memory.topic_manager import TopicManager
from src.memory.context_builder import estimate_tokens
from src.memory.retrieval_budget import rendered_cost
from src.inference.provider import InferenceResult
from src.observability.turn_record import TurnRecord, AssignmentResult
from src.runners.base_runner import BaseRunner


class IterativeRunner(BaseRunner):

    condition = "iterative"

    def __init__(
        self,
        conn: sqlite3.Connection,
        embedding_provider,
        topic_manager: TopicManager,
        retrieval_engine: RetrievalEngine,
        observer=None,
    ):
        self._conn = conn
        self._embedding_provider = embedding_provider
        self._topic_manager = topic_manager
        self._retrieval_engine = retrieval_engine
        self._observer = observer

    def build_context(self, user_message: str, turn_number: int) -> tuple[str, TurnRecord]:
        retrieval_result = self._retrieval_engine.retrieve(user_message, turn_number)

        constructed_prompt = retrieval_result.constructed_prompt

        k_episodes = []
        n_episodes = []

        k_set = set(retrieval_result.k_episode_ids)
        n_set = set(retrieval_result.n_episode_ids)

        for ep in retrieval_result.recent_episodes:
            ep_id = ep["id"]
            sim_score = retrieval_result.k_scores.get(ep_id, 0.0)
            decay_score = retrieval_result.n_scores.get(ep_id, 0.0)
            n_episodes.append({
                "id": ep_id,
                "turn_number": ep["turn_number"],
                "user_message": ep["user_message"],
                "assistant_message": ep["assistant_message"],
                "sim_score": sim_score,
                "decay_score": decay_score,
                "topic_label": ep.get("topic_label", ep.get("topic_id", "")),
                "retrieval_type": "KN" if (ep_id in k_set and ep_id in n_set) else ("K" if ep_id in k_set else "N"),
            })

        for ep in retrieval_result.retrieved_stm_episodes:
            k_episodes.append({
                "id": ep["id"],
                "turn_number": ep["turn_number"],
                "user_message": ep["user_message"],
                "assistant_message": ep["assistant_message"],
                "sim_score": ep["similarity"],
                "decay_score": retrieval_result.n_scores.get(ep["id"], 0.0),
                "topic_label": ep.get("topic_label", ep.get("topic_id", "")),
                "retrieval_type": "K",
            })

        ltm_context_episodes = [{
            "id": ep["id"],
            "distilled_id": ep.get("distilled_id"),
            "turn_number": ep["turn_number"],
            "topic_label": ep.get("topic_label", ep.get("topic_id", "")),
            "similarity": ep["similarity"],
            "provenance": ep["provenance"],
            "promoted_at_turn": ep.get("promoted_at_turn"),
            "trigger_type": ep.get("trigger_type"),
            "triggered_filter": ep.get("triggered_filter"),
            "dream_event": ep.get("dream_event"),
            "event_type": ep.get("event_type"),
            "source_episode_ids": ep.get("source_episode_ids", []),
            "source_turns": ep.get("source_turns", []),
            "salience": ep.get("salience"),
        } for ep in retrieval_result.retrieved_ltm_episodes]
        arbitration = retrieval_result.arbitration

        k_token_estimate = 0
        n_token_estimate = 0
        for ep in k_episodes:
            k_token_estimate += estimate_tokens(f"User: {ep['user_message']}\nAssistant: {ep['assistant_message']}")
        for ep in n_episodes:
            n_token_estimate += estimate_tokens(f"User: {ep['user_message']}\nAssistant: {ep['assistant_message']}")

        record = TurnRecord(
            turn_number=turn_number,
            condition=self.condition,
            user_message=user_message,
            k_count=retrieval_result.k_count,
            n_count=retrieval_result.n_count,
            k_only_count=len(k_episodes),
            n_total_in_store=retrieval_result.n_total_in_store,
            total_in_context=retrieval_result.total_episodes_in_context,
            k_episodes=k_episodes,
            n_episodes=n_episodes,
            ltm_context_episodes=ltm_context_episodes,
            arbitration_stm_candidates=arbitration.stm_candidates,
            arbitration_ltm_candidates=arbitration.ltm_candidates,
            arbitration_duplicates_removed=arbitration.duplicates_removed,
            arbitration_final_set_size=arbitration.final_set_size,
            arbitration_ltm_in_final_set=arbitration.ltm_episodes_in_final_set,
            arbitration_provenance_list=[{
                "episode_id": episode["id"],
                "provenance": episode["provenance"],
            } for episode in arbitration.episodes],
            **self._budget_fields(arbitration),
            estimated_tokens=retrieval_result.estimated_tokens,
            k_token_estimate=k_token_estimate,
            n_token_estimate=n_token_estimate,
            topic_count=self._topic_manager.topic_count,
            episode_count=retrieval_result.total_episodes_in_context,
            rule_store_count=len(retrieval_result.rule_episodes),
            rule_token_estimate=retrieval_result.rule_token_estimate,
            constructed_prompt=constructed_prompt,
        )

        return (constructed_prompt, record)

    @staticmethod
    def _budget_fields(arbitration) -> dict:
        """Study 007 retrieval-budget accounting, empty under the count policy."""
        selection = arbitration.budget
        if selection is None:
            return {}
        return {
            "budget_active": True,
            "budget_b_ltm": selection.budget,
            "budget_k_min": selection.k_min,
            "budget_topics_present": list(selection.topics_present),
            "budget_floor_per_topic": dict(selection.floor_per_topic),
            "budget_fill_selected": selection.fill_selected,
            "budget_containment_drops": arbitration.containment_drops,
            "budget_refills": arbitration.refills,
            "budget_chars_used": selection.chars_used,
            "budget_records_used": len(selection.selected),
            "budget_utilization": selection.utilization,
            "budget_chars_per_topic": dict(selection.chars_per_topic),
            "budget_collapsed_to_episode": selection.collapsed_to_episode,
            "budget_selection": [
                {
                    "episode_id": str(candidate["id"]),
                    "distilled_id": candidate.get("distilled_id"),
                    "topic": str(
                        candidate.get("topic_id")
                        or candidate.get("topic_label")
                        or ""
                    ),
                    "similarity": round(float(candidate["similarity"]), 6),
                    "chars": rendered_cost(candidate),
                    "phase": selection.phases[str(candidate["id"])],
                }
                for candidate in selection.selected
            ],
        }

    def on_turn_complete(
        self,
        user_message: str,
        assistant_message: str,
        turn_number: int,
        embedding: np.ndarray = None,
        inference_result: InferenceResult = None,
        topic_embedding: np.ndarray = None,
        ground_truth_domain: str | None = None,
    ) -> AssignmentResult:
        if embedding is None:
            pair_text = f"User: {user_message}\nAssistant: {assistant_message}"
            embedding = self._embedding_provider.embed(pair_text)

        episode_id = store_episode(
            self._conn,
            user_message,
            assistant_message,
            embedding,
            turn_number,
            ground_truth_domain,
        )

        if inference_result and inference_result.contains_rule and inference_result.rule_summary:
            store_rule(
                self._conn,
                episode_id,
                inference_result.rule_summary,
                turn_number,
            )

        assignment = self._topic_manager.assign(
            episode_id, topic_embedding if topic_embedding is not None else embedding
        )

        return assignment

    @property
    def history_token_estimate(self) -> int:
        return 0
