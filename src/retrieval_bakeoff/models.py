from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

import numpy as np


UnitType = Literal["episode", "span"]


@dataclass(frozen=True)
class Query:
    query_id: str
    text: str


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    source_episode_id: str
    turn_number: int
    unit_type: UnitType
    user_message: str = ""
    assistant_message: str = ""
    span_text: str = ""
    role: str = "conversation"
    span_start: int | None = None
    span_end: int | None = None
    topic_id: str = ""
    topic_label: str = ""
    domain: str = ""
    embedding: np.ndarray | None = field(default=None, compare=False, repr=False)
    distilled_id: str = ""

    @property
    def rendered_identity(self) -> str:
        if self.unit_type == "span":
            return self.candidate_id
        return self.source_episode_id

    @property
    def searchable_text(self) -> str:
        if self.unit_type == "span":
            return self.span_text
        return f"{self.user_message}\n{self.assistant_message}"

    def with_embedding(self, embedding: np.ndarray) -> "Candidate":
        return replace(self, embedding=embedding)


@dataclass(frozen=True)
class RankedCandidate:
    candidate: Candidate
    score: float
    component_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    corpus_id: str
    method_id: str
    query: Query
    budget: int
    ranked_count: int
    selected: list[RankedCandidate]
    rendered_block: str
    phases: dict[str, str] = field(default_factory=dict)
    skipped_oversized: int = 0
    duplicate_drops: int = 0
    query_encode_ms: float = 0.0
    rank_ms: float = 0.0
    pack_ms: float = 0.0
    rank_pack_ms: float = 0.0
    index_build_ms: float = 0.0
    benchmark_repetitions: int = 0

    @property
    def delivered_characters(self) -> int:
        return len(self.rendered_block)

    @property
    def latency_ms(self) -> float:
        return self.query_encode_ms + self.rank_pack_ms
