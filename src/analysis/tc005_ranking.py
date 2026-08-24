"""Label-blind TC-005 relevance ranking mechanism.

This module accepts only candidate episodes, question text, and a query vector.
It has no corpus adapter, labelled measurement input, or outcome code.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from retrieval_bakeoff.config import RRF_CONSTANT
from retrieval_bakeoff.methods import BM25Index, tokenize
from retrieval_bakeoff.models import Candidate

ARMS = ("dense", "bm25", "hybrid")


class TC005RankingError(RuntimeError):
    pass


@dataclass(frozen=True)
class Ranking:
    order: tuple[int, ...]
    scores: tuple[float, ...]
    dense_rank: tuple[int, ...]
    bm25_rank: tuple[int, ...]


@dataclass(frozen=True)
class PreparedRankers:
    episodes: tuple[Any, ...]
    candidates: tuple[Candidate, ...]
    dense_matrix: np.ndarray
    bm25: BM25Index


def _unit(value: np.ndarray) -> np.ndarray:
    array = np.asarray(value, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    if array.shape != (1024,) or not math.isfinite(norm) or norm == 0.0:
        raise TC005RankingError("Expected one finite non-zero 1024-vector")
    return array / norm


def candidates_for(episodes: Sequence[Any]) -> tuple[Candidate, ...]:
    candidates: list[Candidate] = []
    for episode in episodes:
        record = episode.record
        candidate = Candidate(
            candidate_id=episode.identity,
            source_episode_id=episode.identity,
            turn_number=int(record["turn_number"]),
            unit_type="episode",
            user_message=str(record["user_message"]),
            assistant_message=str(record["assistant_message"]),
            domain=str(record["ground_truth_domain"]),
            embedding=np.asarray(record["embedding"], dtype=np.float32),
        )
        if tokenize(candidate.searchable_text) != tokenize(episode.pair.text):
            raise TC005RankingError(
                f"Candidate token stream drifted for {episode.identity}"
            )
        candidates.append(candidate)
    return tuple(candidates)


def prepare_rankers(episodes: Sequence[Any]) -> PreparedRankers:
    frozen = tuple(episodes)
    candidates = candidates_for(frozen)
    return PreparedRankers(
        episodes=frozen,
        candidates=candidates,
        dense_matrix=np.stack([_unit(candidate.embedding) for candidate in candidates]),
        bm25=BM25Index(list(candidates)),
    )


def rank_all(
    episodes: Sequence[Any],
    query_text: str,
    query_vector: np.ndarray,
    prepared: PreparedRankers | None = None,
) -> dict[str, Ranking]:
    store = prepared or prepare_rankers(episodes)
    if tuple(episode.identity for episode in episodes) != tuple(
        episode.identity for episode in store.episodes
    ):
        raise TC005RankingError("Prepared ranker store differs from episodes")
    dense_scores = store.dense_matrix @ _unit(query_vector)
    bm25_scores = store.bm25.scores(query_text)

    def ordered(scores: np.ndarray) -> tuple[int, ...]:
        return tuple(
            sorted(
                range(len(episodes)),
                key=lambda index: (
                    -float(scores[index]),
                    episodes[index].pair.session_order,
                    episodes[index].pair.pair_order,
                ),
            )
        )

    dense_order = ordered(dense_scores)
    bm25_order = ordered(bm25_scores)
    dense_rank = inverse_rank(dense_order)
    bm25_rank = inverse_rank(bm25_order)
    fused_scores = np.asarray(
        [
            1.0 / (RRF_CONSTANT + dense_rank[index])
            + 1.0 / (RRF_CONSTANT + bm25_rank[index])
            for index in range(len(episodes))
        ],
        dtype=np.float64,
    )
    return {
        "dense": Ranking(
            dense_order,
            tuple(float(value) for value in dense_scores),
            dense_rank,
            bm25_rank,
        ),
        "bm25": Ranking(
            bm25_order,
            tuple(float(value) for value in bm25_scores),
            dense_rank,
            bm25_rank,
        ),
        "hybrid": Ranking(
            ordered(fused_scores),
            tuple(float(value) for value in fused_scores),
            dense_rank,
            bm25_rank,
        ),
    }


def inverse_rank(order: Sequence[int]) -> tuple[int, ...]:
    result = [0] * len(order)
    for rank, index in enumerate(order, start=1):
        result[index] = rank
    return tuple(result)


def ranking_digest(episodes: Sequence[Any], ranking: Ranking) -> str:
    return hashlib.sha256(
        json.dumps(
            [episodes[index].identity for index in ranking.order],
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ARMS",
    "PreparedRankers",
    "Ranking",
    "TC005RankingError",
    "candidates_for",
    "inverse_rank",
    "prepare_rankers",
    "rank_all",
    "ranking_digest",
]
