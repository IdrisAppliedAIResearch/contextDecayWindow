"""Deployed episodic-chat arms for HH-003."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from analysis.hh002_dataset import Conversation, Question
from episodic import EpisodeStore, EpisodicConfig
from retrieval_bakeoff.embedding import CarriedEmbedder

_TURN = re.compile(r'<episode turn="(\d+)">')


class HH003ArmError(RuntimeError):
    pass


class SharedEmbedder:
    def __init__(self, embedder: CarriedEmbedder) -> None:
        self._embedder = embedder
        self.model_sha256 = embedder.model_sha256
        self._vectors: dict[str, np.ndarray] = {}
        self.hits = 0
        self.misses = 0

    def embed(self, text: str):
        cached = self._vectors.get(text)
        if cached is not None:
            self.hits += 1
            return cached.copy()
        self.misses += 1
        vector = self._embedder(text)
        self._vectors[text] = vector.copy()
        return vector

    def __call__(self, text: str):
        return self.embed(text)


@dataclass
class EpisodicState:
    store: EpisodeStore
    db_path: Path
    sample_id: str
    source_turns: dict[int, tuple[str, ...]]
    dangling_turns: tuple[str, ...]


def stable_item_key(sample_id: str, question: Question) -> str:
    material = "\0".join(
        (sample_id, str(question.source_index), question.question, question.answer)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class EpisodicArm:
    """One public EpisodeStore configuration at the HH-002 memory seam."""

    cacheable_contexts = True

    def __init__(
        self,
        workdir: Path,
        *,
        aspect_enabled: bool,
        embedder: SharedEmbedder,
    ) -> None:
        self.workdir = workdir
        self.aspect_enabled = aspect_enabled
        self.name = "A_EPISODIC_ASPECT" if aspect_enabled else "A_EPISODIC"
        self.config = EpisodicConfig(aspect_enabled=aspect_enabled)
        self.embedder = embedder

    def item_key(self, conversation: Conversation, question: Question) -> str:
        return stable_item_key(conversation.sample_id, question)

    def prepare(self, conversation: Conversation, client: Any) -> EpisodicState:
        del client
        arm_dir = self.workdir / self.name
        arm_dir.mkdir(parents=True, exist_ok=True)
        db_path = arm_dir / f"{conversation.sample_id}.db"
        expected = len(conversation.turns) // 2
        existing = 0
        if db_path.exists():
            with sqlite3.connect(db_path) as conn:
                try:
                    existing = int(conn.execute("SELECT count(*) FROM episodes").fetchone()[0])
                except sqlite3.OperationalError:
                    existing = 0
        if existing not in (0, expected):
            raise HH003ArmError(
                f"{db_path} is partial: {existing}/{expected} episodes; "
                "resume cannot infer the acknowledged append boundary"
            )

        store = EpisodeStore(db_path, config=self.config, embedder=self.embedder)
        source_turns: dict[int, tuple[str, ...]] = {}
        for episode_number, start in enumerate(range(0, expected * 2, 2), start=1):
            members = conversation.turns[start : start + 2]
            source_turns[episode_number] = tuple(turn.dia_id for turn in members)
            if existing == expected:
                continue
            first, second = members
            store.append(
                "user", f"{first.timestamp} | {first.speaker}: {first.text}"
            )
            store.append(
                "assistant", f"{second.timestamp} | {second.speaker}: {second.text}"
            )

        dangling = tuple(turn.dia_id for turn in conversation.turns[expected * 2 :])
        return EpisodicState(
            store, db_path, conversation.sample_id, source_turns, dangling
        )

    def context(
        self, state: EpisodicState, question: Question, client: Any
    ) -> tuple[str, float, dict[str, Any]]:
        del client
        before = state.db_path.stat().st_mtime_ns
        payload, report = state.store.context(question.question)
        after = state.db_path.stat().st_mtime_ns
        if before != after:
            raise HH003ArmError("EpisodeStore.context() mutated the store")

        delivered_turns = tuple(int(value) for value in _TURN.findall(payload))
        if len(delivered_turns) != len(set(delivered_turns)):
            raise HH003ArmError("A source episode was rendered more than once")
        source_ids = tuple(
            dia_id
            for turn in delivered_turns
            for dia_id in state.source_turns[turn]
        )
        detail = asdict(report) | {
            "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            "delivered_episode_turns": delivered_turns,
            "delivered_source_ids": source_ids,
            "stable_item_key": stable_item_key(state.sample_id, question),
            "dangling_source_ids": state.dangling_turns,
            "store_unchanged": True,
        }
        return payload, report.latency_ms / 1000.0, detail

    @staticmethod
    def close_state(state: EpisodicState) -> None:
        state.store.close()


__all__ = ["EpisodicArm", "HH003ArmError", "SharedEmbedder", "stable_item_key"]
