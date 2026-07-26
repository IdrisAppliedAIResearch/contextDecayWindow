"""N + K retrieval with no LTM or digest dependency."""

import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from src.db.episode import get_episode_by_id
from src.db.retrieval import (
    get_all_episodes_with_embeddings,
    log_retrieval_events_batch,
    update_retrieval_metadata,
)
from src.db.rule_store import get_all_rules
from src.embeddings.provider import cosine_similarity, embed
from src.memory.stm_context_builder import build_stm_context, render_rules_block


DECAY_RATE = 0.1
K_SIMILARITY_THRESHOLD = 0.50
N_RETRIEVAL_CAP = 10


@dataclass
class StmRetrievalResult:
    k_episode_ids: list = field(default_factory=list)
    k_scores: dict = field(default_factory=dict)
    n_episode_ids: list = field(default_factory=list)
    n_scores: dict = field(default_factory=dict)
    constructed_prompt: str = ""
    estimated_tokens: int = 0
    n_total_in_store: int = 0
    rule_episodes: list = field(default_factory=list)
    rule_token_estimate: int = 0
    recent_episodes: list = field(default_factory=list)
    retrieved_stm_episodes: list = field(default_factory=list)

    @property
    def k_count(self) -> int:
        return len(self.k_episode_ids)

    @property
    def n_count(self) -> int:
        return len(self.n_episode_ids)

    @property
    def total_episodes_in_context(self) -> int:
        return len(self.recent_episodes) + len(self.retrieved_stm_episodes)


class StmRetrievalEngine:
    def __init__(
        self,
        conn: sqlite3.Connection,
        embedding_provider=None,
        system_prompt: str | None = None,
        context_renderer=None,
    ):
        self.conn = conn
        self._embedding_provider = embedding_provider or embed
        self._system_prompt = system_prompt or "You are a helpful assistant."
        self._context_renderer = context_renderer or build_stm_context

    def retrieve(self, user_message: str, turn_number: int) -> StmRetrievalResult:
        rule_episodes = self._fetch_rule_episodes(get_all_rules(self.conn))
        query_embedding = self._embedding_provider(user_message)
        rows = get_all_episodes_with_embeddings(self.conn)
        episodes = self._deserialize(rows)
        k_episode_ids, k_scores = self._k_retrieve(query_embedding, episodes)
        n_episode_ids, n_scores = self._n_retrieve(episodes)

        by_id = {
            episode["id"]: self._clean_episode(episode)
            for episode in episodes
        }
        n_set = set(n_episode_ids)
        recent = [
            by_id[episode_id]
            for episode_id in n_episode_ids
            if episode_id in by_id
        ]
        stm = [
            {
                **by_id[episode_id],
                "similarity": k_scores[episode_id],
                "provenance": "stm",
            }
            for episode_id in k_episode_ids
            if episode_id in by_id and episode_id not in n_set
        ]

        final_ids = list(dict.fromkeys(
            episode["id"] for episode in (*recent, *stm)
        ))
        if final_ids:
            update_retrieval_metadata(
                self.conn,
                final_ids,
                datetime.now(timezone.utc).isoformat(),
            )
        self._log_retrieval_events(
            turn_number,
            episodes,
            k_episode_ids,
            k_scores,
            n_episode_ids,
            n_scores,
        )

        prompt = self._context_renderer(
            system_prompt=self._system_prompt,
            current_user_message=user_message,
            rule_episodes=rule_episodes,
            recent_episodes=recent,
            stm_episodes=stm,
        )
        rule_text = render_rules_block(rule_episodes)
        return StmRetrievalResult(
            k_episode_ids=k_episode_ids,
            k_scores=k_scores,
            n_episode_ids=n_episode_ids,
            n_scores=n_scores,
            constructed_prompt=prompt,
            estimated_tokens=len(prompt) // 4,
            n_total_in_store=len(episodes),
            rule_episodes=rule_episodes,
            rule_token_estimate=(len(rule_text) // 4 if rule_episodes else 0),
            recent_episodes=recent,
            retrieved_stm_episodes=stm,
        )

    @staticmethod
    def _deserialize(rows: list[dict]) -> list[dict]:
        episodes = []
        for row in rows:
            episode = dict(row)
            if episode["embedding"] is not None:
                episode["embedding"] = np.frombuffer(
                    episode["embedding"], dtype=np.float32
                )
            episodes.append(episode)
        return episodes

    @staticmethod
    def _clean_episode(episode: dict) -> dict:
        return {
            "id": episode["id"],
            "topic_id": episode["topic_id"],
            "topic_label": (
                episode.get("topic_label")
                or episode.get("topic_id")
                or ""
            ),
            "user_message": episode["user_message"],
            "assistant_message": episode["assistant_message"],
            "turn_number": episode["turn_number"],
            "created_at": episode["created_at"],
            "last_retrieved_at": episode["last_retrieved_at"],
            "retrieval_count": episode["retrieval_count"],
        }

    @staticmethod
    def _k_retrieve(
        query_embedding: np.ndarray, episodes: list[dict]
    ) -> tuple[list[str], dict[str, float]]:
        episode_ids = []
        scores = {}
        for episode in episodes:
            episode_embedding = episode.get("embedding")
            if episode_embedding is None:
                continue
            similarity = cosine_similarity(query_embedding, episode_embedding)
            if similarity >= K_SIMILARITY_THRESHOLD:
                episode_ids.append(episode["id"])
                scores[episode["id"]] = similarity
        return episode_ids, scores

    @staticmethod
    def _n_retrieve(episodes: list[dict]) -> tuple[list[str], dict[str, float]]:
        scores = {
            episode["id"]: StmRetrievalEngine._compute_decay(
                episode.get("last_retrieved_at")
            )
            for episode in episodes
        }
        episode_ids = sorted(scores, key=lambda episode_id: scores[episode_id], reverse=True)
        return episode_ids[:N_RETRIEVAL_CAP], scores

    @staticmethod
    def _compute_decay(last_retrieved_at) -> float:
        if last_retrieved_at is None:
            return 1.0
        last_dt = datetime.fromisoformat(last_retrieved_at)
        elapsed_hours = (
            datetime.now(timezone.utc) - last_dt
        ).total_seconds() / 3600.0
        return math.exp(-DECAY_RATE * elapsed_hours)

    def _fetch_rule_episodes(self, rule_rows: list) -> list:
        episodes = []
        for row in rule_rows:
            episode = get_episode_by_id(self.conn, row["episode_id"])
            if episode is None:
                continue
            episodes.append({
                "id": episode["id"],
                "rule_id": row["id"],
                "rule_summary": row["rule_summary"],
                "set_at_turn": row["turn_number"],
                "turn_number": episode["turn_number"],
                "user_message": episode["user_message"],
                "assistant_message": episode["assistant_message"],
            })
        return episodes

    def _log_retrieval_events(
        self,
        turn_number: int,
        episodes: list[dict],
        k_episode_ids: list[str],
        k_scores: dict[str, float],
        n_episode_ids: list[str],
        n_scores: dict[str, float],
    ) -> None:
        included = set(k_episode_ids) | set(n_episode_ids)
        if not included:
            return
        k_set = set(k_episode_ids)
        n_set = set(n_episode_ids)
        events = []
        for episode in sorted(
            (item for item in episodes if item["id"] in included),
            key=lambda item: item["turn_number"],
        ):
            episode_id = episode["id"]
            retrieval_type = (
                "KN"
                if episode_id in k_set and episode_id in n_set
                else ("K" if episode_id in k_set else "N")
            )
            events.append({
                "turn_number": turn_number,
                "episode_id": episode_id,
                "similarity_score": k_scores.get(episode_id, 0.0),
                "decay_score": n_scores.get(episode_id, 0.0),
                "retrieval_type": retrieval_type,
            })
        log_retrieval_events_batch(self.conn, events)
