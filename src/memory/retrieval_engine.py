import asyncio
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from src.embeddings.provider import embed, cosine_similarity
from src.db.retrieval import (
    get_all_episodes_with_embeddings,
    update_retrieval_metadata,
    log_retrieval_events_batch,
)
from src.db.rule_store import get_all_rules
from src.db.episode import get_episode_by_id
from src.memory.arbitration import ArbitrationResult, arbitrate_candidates
from src.memory.context_builder import (
    build_pinned_rules_block,
    build_tagged_context,
    estimate_tokens,
)
from src.memory.ltm_store import get_ltm_retrieval_rows


DECAY_RATE = 0.1

# Study 001: K_SIMILARITY_THRESHOLD = 0.70
K_SIMILARITY_THRESHOLD = 0.50
# Reduced from 0.70. Study 001: K fired once in 32 turns.
# 0.70 was too strict for Qwen3-Embedding-0.6B's embedding space.

N_RETRIEVAL_CAP = 10
# Hard floor of the soft cap. Top 10 decay-sorted episodes always included.
# Additional episodes included if they score above K_SIMILARITY_THRESHOLD
# regardless of whether they appear in the top-10 N set.
# Rule episodes are unconditional and do not count against this cap.


@dataclass
class RetrievalResult:
    episodes: list = field(default_factory=list)
    k_episode_ids: list = field(default_factory=list)
    k_scores: dict = field(default_factory=dict)
    n_episode_ids: list = field(default_factory=list)
    n_scores: dict = field(default_factory=dict)
    constructed_prompt: str = ""
    estimated_tokens: int = 0
    k_count: int = 0
    n_count: int = 0
    n_total_in_store: int = 0
    total_episodes_in_context: int = 0
    rule_episodes: list = field(default_factory=list)
    rule_token_estimate: int = 0
    recent_episodes: list = field(default_factory=list)
    retrieved_stm_episodes: list = field(default_factory=list)
    retrieved_ltm_episodes: list = field(default_factory=list)
    arbitration: ArbitrationResult = field(default_factory=ArbitrationResult)


class RetrievalEngine:

    LTM_TOP_M = 5

    def __init__(self, conn, embedding_provider=None, system_prompt=None):
        self.conn = conn
        self._embedding_provider = embedding_provider or embed
        self._system_prompt = system_prompt or "You are a helpful assistant."
        database_row = conn.execute("PRAGMA database_list").fetchone()
        self._database_path = database_row[2] if database_row else ""

    def retrieve(self, user_message: str, turn_number: int) -> RetrievalResult:
        """Synchronous boundary used by the existing study runner."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.retrieve_async(user_message, turn_number))
        raise RuntimeError("Use await retrieve_async() from an active event loop")

    async def retrieve_async(
        self, user_message: str, turn_number: int
    ) -> RetrievalResult:
        rule_rows = get_all_rules(self.conn)
        rule_episodes = self._fetch_rule_episodes(rule_rows)

        query_embedding = self._embedding_provider(user_message)
        stm_result, ltm_candidates = await self._retrieve_tiers_parallel(
            query_embedding
        )
        (
            deserialized_episodes,
            k_episode_ids,
            k_scores,
            n_episode_ids,
            n_scores,
        ) = stm_result

        n_set = set(n_episode_ids)
        by_id = {
            episode["id"]: self._clean_stm_episode(episode)
            for episode in deserialized_episodes
        }
        recent_episodes = [
            by_id[episode_id]
            for episode_id in n_episode_ids
            if episode_id in by_id
        ]
        stm_candidates = [
            {**by_id[episode_id], "similarity": k_scores[episode_id]}
            for episode_id in k_episode_ids
            if episode_id in by_id and episode_id not in n_set
        ]
        arbitration = arbitrate_candidates(
            stm_candidates,
            ltm_candidates,
            k_stm=len(stm_candidates),
            ltm_top_m=self.LTM_TOP_M,
        )
        retrieved_stm_episodes = [
            episode for episode in arbitration.episodes
            if episode["provenance"] == "stm"
        ]
        retrieved_ltm_episodes = [
            episode for episode in arbitration.episodes
            if episode["provenance"] in {"ltm", "both"}
        ]
        # The registered recency-precedence rule applies to N∩K within STM.
        # An LTM survivor must retain its provenance and tagged placement, so
        # remove it from N instead of suppressing it from arbitration.
        arbitration_ids = {
            episode["id"] for episode in arbitration.episodes
        }
        recent_episodes = [
            episode for episode in recent_episodes
            if episode["id"] not in arbitration_ids
        ]
        clean_episodes = [*recent_episodes, *arbitration.episodes]

        final_ids = list(dict.fromkeys(
            episode["id"] for episode in clean_episodes
        ))
        if final_ids:
            update_retrieval_metadata(
                self.conn,
                final_ids,
                datetime.now(timezone.utc).isoformat(),
            )
        self._log_stm_retrieval_events(
            turn_number,
            deserialized_episodes,
            k_episode_ids,
            k_scores,
            n_episode_ids,
            n_scores,
        )

        rule_block_text = build_pinned_rules_block(rule_episodes)
        rule_token_estimate = (
            estimate_tokens(rule_block_text) if rule_episodes else 0
        )
        constructed_prompt = build_tagged_context(
            system_prompt=self._system_prompt,
            current_user_message=user_message,
            rule_episodes=rule_episodes,
            recent_episodes=recent_episodes,
            stm_episodes=retrieved_stm_episodes,
            ltm_episodes=retrieved_ltm_episodes,
        )
        estimated_tokens = estimate_tokens(constructed_prompt)

        return RetrievalResult(
            episodes=clean_episodes,
            k_episode_ids=list(k_episode_ids),
            k_scores=dict(k_scores),
            n_episode_ids=list(n_episode_ids),
            n_scores=dict(n_scores),
            constructed_prompt=constructed_prompt,
            estimated_tokens=estimated_tokens,
            k_count=len(k_episode_ids),
            n_count=len(n_episode_ids),
            n_total_in_store=len(deserialized_episodes),
            total_episodes_in_context=len(clean_episodes),
            rule_episodes=rule_episodes,
            rule_token_estimate=rule_token_estimate,
            recent_episodes=recent_episodes,
            retrieved_stm_episodes=retrieved_stm_episodes,
            retrieved_ltm_episodes=retrieved_ltm_episodes,
            arbitration=arbitration,
        )

    async def _retrieve_tiers_parallel(
        self, query_embedding: np.ndarray
    ) -> tuple[tuple, list[dict]]:
        """Issue STM and LTM reads concurrently and await them jointly."""
        if self._database_path:
            return tuple(await asyncio.gather(
                asyncio.to_thread(self._query_stm_tier, query_embedding),
                asyncio.to_thread(self._query_ltm_tier, query_embedding),
            ))

        # In-memory SQLite databases cannot be reopened in worker threads.
        # Snapshot both stores on the owning thread, then score concurrently.
        stm_rows = get_all_episodes_with_embeddings(self.conn)
        ltm_rows = get_ltm_retrieval_rows(self.conn)
        return tuple(await asyncio.gather(
            asyncio.to_thread(self._score_stm_rows, query_embedding, stm_rows),
            asyncio.to_thread(self._score_ltm_rows, query_embedding, ltm_rows),
        ))

    def _query_stm_tier(self, query_embedding: np.ndarray) -> tuple:
        with sqlite3.connect(self._database_path) as conn:
            rows = get_all_episodes_with_embeddings(conn)
        return self._score_stm_rows(query_embedding, rows)

    def _query_ltm_tier(self, query_embedding: np.ndarray) -> list[dict]:
        with sqlite3.connect(self._database_path) as conn:
            rows = get_ltm_retrieval_rows(conn)
        return self._score_ltm_rows(query_embedding, rows)

    def _score_stm_rows(
        self, query_embedding: np.ndarray, rows: list[dict]
    ) -> tuple:
        deserialized = []
        for episode in rows:
            item = dict(episode)
            if item["embedding"] is not None:
                item["embedding"] = np.frombuffer(
                    item["embedding"], dtype=np.float32
                )
            deserialized.append(item)
        k_episode_ids, k_scores = self._k_retrieve(
            query_embedding, deserialized
        )
        n_episode_ids, n_scores = self._n_retrieve(deserialized)
        return deserialized, k_episode_ids, k_scores, n_episode_ids, n_scores

    def _score_ltm_rows(
        self, query_embedding: np.ndarray, rows: list[dict]
    ) -> list[dict]:
        candidates = []
        for row in rows:
            embedding = np.frombuffer(row["embedding"], dtype=np.float32)
            candidates.append({
                "id": row["id"],
                "turn_number": row["turn_number"],
                "topic_id": row["topic_id"],
                "topic_label": row["topic_label"],
                "user_message": row["user_message"],
                "assistant_message": row["assistant_message"],
                "similarity": cosine_similarity(query_embedding, embedding),
                "promoted_at_turn": row["promoted_at_turn"],
                "trigger_type": row["trigger_type"],
                "triggered_filter": row["triggered_filter"],
            })
        candidates.sort(
            key=lambda item: (-float(item["similarity"]), str(item["id"]))
        )
        return candidates[:self.LTM_TOP_M]

    @staticmethod
    def _clean_stm_episode(episode: dict) -> dict:
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

    def _log_stm_retrieval_events(
        self,
        turn_number: int,
        all_episodes: list[dict],
        k_episode_ids: list[str],
        k_scores: dict,
        n_episode_ids: list[str],
        n_scores: dict,
    ) -> None:
        included_ids = set(k_episode_ids) | set(n_episode_ids)
        if not included_ids:
            return
        k_set = set(k_episode_ids)
        n_set = set(n_episode_ids)
        events = []
        for episode in self._deduplicate_and_sort(all_episodes, included_ids):
            episode_id = episode["id"]
            if episode_id in k_set and episode_id in n_set:
                retrieval_type = "KN"
            elif episode_id in k_set:
                retrieval_type = "K"
            else:
                retrieval_type = "N"
            events.append({
                "turn_number": turn_number,
                "episode_id": episode_id,
                "similarity_score": k_scores.get(episode_id, 0.0),
                "decay_score": n_scores.get(episode_id, 0.0),
                "retrieval_type": retrieval_type,
            })
        log_retrieval_events_batch(self.conn, events)

    def _k_retrieve(
        self, query_embedding: np.ndarray, all_episodes: list
    ) -> tuple:
        k_episode_ids = []
        k_scores = {}
        for ep in all_episodes:
            ep_embedding = ep.get("embedding")
            if ep_embedding is None:
                continue
            sim = cosine_similarity(query_embedding, ep_embedding)
            if sim >= K_SIMILARITY_THRESHOLD:
                k_episode_ids.append(ep["id"])
                k_scores[ep["id"]] = sim
        return k_episode_ids, k_scores

    def _n_retrieve(self, all_episodes: list) -> tuple:
        n_scores = {}
        for ep in all_episodes:
            decay = self._compute_decay(ep.get("last_retrieved_at"))
            n_scores[ep["id"]] = decay
        n_episode_ids = sorted(n_scores.keys(), key=lambda eid: n_scores[eid], reverse=True)
        capped_ids = n_episode_ids[:N_RETRIEVAL_CAP]
        return capped_ids, n_scores

    def _compute_decay(self, last_retrieved_at):
        if last_retrieved_at is None:
            return 1.0
        last_dt = datetime.fromisoformat(last_retrieved_at)
        now_dt = datetime.now(timezone.utc)
        delta = now_dt - last_dt
        hours_since = delta.total_seconds() / 3600.0
        score = math.exp(-DECAY_RATE * hours_since)
        return score

    def _deduplicate_and_sort(self, all_episodes: list, included_ids: set) -> list:
        filtered = [ep for ep in all_episodes if ep["id"] in included_ids]
        filtered.sort(key=lambda ep: ep["turn_number"])
        return filtered

    def _fetch_rule_episodes(self, rule_rows: list) -> list:
        rule_episodes = []
        for rule_row in rule_rows:
            ep = get_episode_by_id(self.conn, rule_row["episode_id"])
            if ep is not None:
                rule_episodes.append({
                    "id": ep["id"],
                    "rule_id": rule_row["id"],
                    "rule_summary": rule_row["rule_summary"],
                    "set_at_turn": rule_row["turn_number"],
                    "turn_number": ep["turn_number"],
                    "user_message": ep["user_message"],
                    "assistant_message": ep["assistant_message"],
                })
        return rule_episodes
