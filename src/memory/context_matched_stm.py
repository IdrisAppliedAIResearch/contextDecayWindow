from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

import numpy as np

from src.db.retrieval import (
    get_all_episodes_with_embeddings,
    get_last_retrieval_generations,
    update_retrieval_metadata,
)
from src.db.rule_store import get_all_rules
from src.embeddings.provider import cosine_similarity
from src.memory.stm_context_builder import (
    build_stm_context,
    render_episode_block,
    render_rules_block,
)
from src.memory.stm_retrieval_engine import (
    StmRetrievalEngine,
    StmRetrievalResult,
)


@dataclass(frozen=True)
class PackedStmPayload:
    recent_episodes: tuple[dict, ...]
    stm_episodes: tuple[dict, ...]
    payload: str
    skipped_n_ids: tuple[str, ...] = ()
    skipped_k_ids: tuple[str, ...] = ()
    duplicate_ids: tuple[str, ...] = ()

    @property
    def serialized_chars(self) -> int:
        return len(self.payload)

    @property
    def selected_ids(self) -> tuple[str, ...]:
        return tuple(
            str(episode["id"])
            for episode in (*self.recent_episodes, *self.stm_episodes)
        )


@dataclass
class ContextMatchedStmResult(StmRetrievalResult):
    payload_budget: int = 0
    retrieval_payload_chars: int = 0
    retrieval_payload_sha256: str = ""
    n_candidate_count: int = 0
    k_candidate_count: int = 0
    n_candidate_ids: list[str] = field(default_factory=list)
    k_candidate_ids: list[str] = field(default_factory=list)
    delivered_k_only_ids: list[str] = field(default_factory=list)
    n_k_duplicate_ids: list[str] = field(default_factory=list)
    n_candidate_last_generations: dict[str, int | None] = field(
        default_factory=dict
    )
    skipped_n_ids: list[str] = field(default_factory=list)
    skipped_k_ids: list[str] = field(default_factory=list)


def render_stm_payload(
    recent_episodes: Iterable[dict],
    stm_episodes: Iterable[dict],
) -> str:
    return "\n\n".join(
        (
            render_episode_block(
                "recent_context",
                list(recent_episodes),
                "recent",
            ),
            render_episode_block(
                "retrieved_stm",
                list(stm_episodes),
                "stm",
            ),
        )
    )


def extract_arm_l_payload(prompt: str) -> str:
    return "\n\n".join(
        _extract_block(prompt, name)
        for name in ("recent_context", "retrieved_stm", "retrieved_ltm")
    )


def extract_stm_payload(prompt: str) -> str:
    return "\n\n".join(
        _extract_block(prompt, name)
        for name in ("recent_context", "retrieved_stm")
    )


def pack_stm_payload(
    n_candidates: Iterable[dict],
    k_candidates: Iterable[dict],
    budget: int,
) -> PackedStmPayload:
    if budget < len(render_stm_payload([], [])):
        raise ValueError("Payload budget cannot fit the two empty STM blocks")

    recent: list[dict] = []
    stm: list[dict] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    skipped_n: list[str] = []
    skipped_k: list[str] = []

    def consider(candidate: dict, *, tier: str) -> None:
        candidate_id = str(candidate["id"])
        if candidate_id in seen:
            duplicates.append(candidate_id)
            return
        target = recent if tier == "n" else stm
        target.append(candidate)
        payload = render_stm_payload(recent, stm)
        if len(payload) <= budget:
            seen.add(candidate_id)
            return
        target.pop()
        if tier == "n":
            skipped_n.append(candidate_id)
        else:
            skipped_k.append(candidate_id)

    for candidate in n_candidates:
        consider(candidate, tier="n")
    for candidate in k_candidates:
        consider(candidate, tier="k")

    payload = render_stm_payload(recent, stm)
    if len(payload) > budget:
        raise AssertionError("STM payload exceeded its character budget")
    return PackedStmPayload(
        recent_episodes=tuple(recent),
        stm_episodes=tuple(stm),
        payload=payload,
        skipped_n_ids=tuple(skipped_n),
        skipped_k_ids=tuple(skipped_k),
        duplicate_ids=tuple(duplicates),
    )


class ContextMatchedStmRetrievalEngine(StmRetrievalEngine):
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        n_cap: int,
        k_threshold: float,
        payload_budget: int,
        embedding_provider=None,
        system_prompt: str | None = None,
    ) -> None:
        super().__init__(
            conn,
            embedding_provider=embedding_provider,
            system_prompt=system_prompt,
        )
        if n_cap <= 10:
            raise ValueError("Context matching requires N above the carried cap")
        if not 0.0 <= k_threshold < 0.50:
            raise ValueError(
                "Context matching requires K below the carried threshold"
            )
        if payload_budget < 1:
            raise ValueError("Payload budget must be positive")
        self.n_cap = n_cap
        self.k_threshold = k_threshold
        self.payload_budget = payload_budget
        self.last_result: ContextMatchedStmResult | None = None

    def retrieve(
        self,
        user_message: str,
        turn_number: int,
    ) -> ContextMatchedStmResult:
        rule_episodes = self._fetch_rule_episodes(get_all_rules(self.conn))
        query_embedding = self._embedding_provider(user_message)
        rows = get_all_episodes_with_embeddings(self.conn)
        episodes = self._deserialize(rows)
        k_candidate_ids, all_k_scores = self._k_retrieve_widened(
            query_embedding,
            episodes,
        )
        n_candidate_ids, all_n_scores = self._n_retrieve_widened(episodes)

        by_id = {
            str(episode["id"]): self._clean_episode(episode)
            for episode in episodes
        }
        n_candidates = [
            by_id[episode_id]
            for episode_id in n_candidate_ids
            if episode_id in by_id
        ]
        n_candidate_set = set(n_candidate_ids)
        k_candidates = [
            {
                **by_id[episode_id],
                "similarity": all_k_scores[episode_id],
                "provenance": "stm",
            }
            for episode_id in k_candidate_ids
            if episode_id in by_id and episode_id not in n_candidate_set
        ]
        packed = pack_stm_payload(
            n_candidates,
            k_candidates,
            self.payload_budget,
        )

        delivered_n_ids = [
            str(episode["id"]) for episode in packed.recent_episodes
        ]
        delivered_ids = set(packed.selected_ids)
        delivered_k_ids = [
            episode_id
            for episode_id in k_candidate_ids
            if episode_id in delivered_ids
        ]
        delivered_k_only_ids = [
            str(episode["id"]) for episode in packed.stm_episodes
        ]
        k_scores = {
            episode_id: all_k_scores[episode_id]
            for episode_id in delivered_k_ids
        }
        n_scores = {
            episode_id: all_n_scores[episode_id]
            for episode_id in delivered_n_ids
        }

        if packed.selected_ids:
            update_retrieval_metadata(
                self.conn,
                list(packed.selected_ids),
                datetime.now(timezone.utc).isoformat(),
            )
        self._log_retrieval_events(
            turn_number,
            episodes,
            delivered_k_ids,
            k_scores,
            delivered_n_ids,
            n_scores,
        )

        prompt = build_stm_context(
            system_prompt=self._system_prompt,
            current_user_message=user_message,
            rule_episodes=rule_episodes,
            recent_episodes=list(packed.recent_episodes),
            stm_episodes=list(packed.stm_episodes),
        )
        if extract_stm_payload(prompt) != packed.payload:
            raise AssertionError("Packed payload differs from live prompt")
        rule_text = render_rules_block(rule_episodes)
        result = ContextMatchedStmResult(
            k_episode_ids=delivered_k_ids,
            k_scores=k_scores,
            n_episode_ids=delivered_n_ids,
            n_scores=n_scores,
            constructed_prompt=prompt,
            estimated_tokens=len(prompt) // 4,
            n_total_in_store=len(episodes),
            rule_episodes=rule_episodes,
            rule_token_estimate=(len(rule_text) // 4 if rule_episodes else 0),
            recent_episodes=list(packed.recent_episodes),
            retrieved_stm_episodes=list(packed.stm_episodes),
            payload_budget=self.payload_budget,
            retrieval_payload_chars=packed.serialized_chars,
            retrieval_payload_sha256=hashlib.sha256(
                packed.payload.encode("utf-8")
            ).hexdigest(),
            n_candidate_count=len(n_candidate_ids),
            k_candidate_count=len(k_candidate_ids),
            n_candidate_ids=list(n_candidate_ids),
            k_candidate_ids=list(k_candidate_ids),
            delivered_k_only_ids=delivered_k_only_ids,
            n_k_duplicate_ids=[
                episode_id
                for episode_id in k_candidate_ids
                if episode_id in n_candidate_set
            ],
            n_candidate_last_generations={
                episode_id: self._last_generations.get(episode_id)
                for episode_id in n_candidate_ids
            },
            skipped_n_ids=list(packed.skipped_n_ids),
            skipped_k_ids=list(packed.skipped_k_ids),
        )
        self.last_result = result
        return result

    def _k_retrieve_widened(
        self,
        query_embedding: np.ndarray,
        episodes: list[dict],
    ) -> tuple[list[str], dict[str, float]]:
        episode_ids = []
        scores = {}
        for episode in episodes:
            episode_embedding = episode.get("embedding")
            if episode_embedding is None:
                continue
            similarity = cosine_similarity(query_embedding, episode_embedding)
            if similarity >= self.k_threshold:
                episode_id = str(episode["id"])
                episode_ids.append(episode_id)
                scores[episode_id] = similarity
        return episode_ids, scores

    def _n_retrieve_widened(
        self,
        episodes: list[dict],
    ) -> tuple[list[str], dict[str, float]]:
        self._last_generations = get_last_retrieval_generations(self.conn)
        scores = {
            str(episode["id"]): logical_n_score(
                self._last_generations.get(str(episode["id"]))
            )
            for episode in episodes
        }
        ranked = sorted(
            episodes,
            key=lambda episode: logical_n_key(
                episode,
                self._last_generations,
            ),
        )
        episode_ids = [str(episode["id"]) for episode in ranked]
        return episode_ids[: self.n_cap], scores


def logical_n_key(
    episode: dict,
    last_generations: dict[str, int],
) -> tuple[bool, int, int, str]:
    episode_id = str(episode["id"])
    generation = last_generations.get(episode_id)
    return (
        generation is not None,
        generation if generation is not None else -1,
        int(episode["turn_number"]),
        episode_id,
    )


def logical_n_score(generation: int | None) -> float:
    if generation is None:
        return 1.0
    return 1.0 / (generation + 2.0)


def context_match_accounting(result: ContextMatchedStmResult) -> dict:
    return {
        "payload_budget": result.payload_budget,
        "retrieval_payload_chars": result.retrieval_payload_chars,
        "retrieval_payload_sha256": result.retrieval_payload_sha256,
        "n_candidate_count": result.n_candidate_count,
        "k_candidate_count": result.k_candidate_count,
        "n_candidate_ids": result.n_candidate_ids,
        "k_candidate_ids": result.k_candidate_ids,
        "delivered_n_ids": result.n_episode_ids,
        "delivered_k_only_ids": result.delivered_k_only_ids,
        "n_k_duplicate_ids": result.n_k_duplicate_ids,
        "n_candidate_last_generations": (
            result.n_candidate_last_generations
        ),
        "n_delivered_count": len(result.n_episode_ids),
        "k_delivered_count": len(result.k_episode_ids),
        "k_only_delivered_count": len(result.retrieved_stm_episodes),
        "skipped_n_ids": result.skipped_n_ids,
        "skipped_k_ids": result.skipped_k_ids,
        "selected_ids": [
            str(episode["id"])
            for episode in (
                *result.recent_episodes,
                *result.retrieved_stm_episodes,
            )
        ],
    }


def _extract_block(prompt: str, name: str) -> str:
    opening = f"<{name}>"
    empty = f"<{name}/>"
    if empty in prompt:
        if opening in prompt:
            raise ValueError(f"Prompt has duplicate {name} blocks")
        return empty
    start = prompt.find(opening)
    closing = f"</{name}>"
    end = prompt.find(closing, start + len(opening))
    if start < 0 or end < 0:
        raise ValueError(f"Prompt has no complete {name} block")
    if prompt.find(opening, start + len(opening)) >= 0:
        raise ValueError(f"Prompt has duplicate {name} blocks")
    return prompt[start : end + len(closing)]
