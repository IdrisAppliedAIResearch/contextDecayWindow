from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path

import numpy as np

from src.memory.distilled_ltm_store import get_distilled_retrieval_rows
from src.memory.span_segmenter import segment_episode

from .config import EMBEDDING_DIMENSION, CorpusSpec
from .models import Candidate, Query


def _read_only_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def _vector(blob: bytes | memoryview | None) -> np.ndarray | None:
    if blob is None:
        return None
    vector = np.frombuffer(blob, dtype=np.float32).copy()
    if vector.shape != (EMBEDDING_DIMENSION,):
        raise ValueError(
            f"Expected embedding shape {(EMBEDDING_DIMENSION,)}, got {vector.shape}"
        )
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


def load_queries(spec: CorpusSpec) -> list[Query]:
    payload = json.loads(spec.query_manifest.read_text(encoding="utf-8"))
    if payload["eligible_turn_min"] != spec.eligible_turn_min:
        raise AssertionError("Query manifest minimum turn does not match corpus")
    if payload["eligible_turn_max"] != spec.eligible_turn_max:
        raise AssertionError("Query manifest maximum turn does not match corpus")
    queries = [
        Query(query_id=str(row["query_id"]), text=str(row["text"]))
        for row in payload["queries"]
    ]
    if len(queries) != 24 or len({query.query_id for query in queries}) != 24:
        raise AssertionError("A locked corpus query manifest must contain 24 unique IDs")
    return queries


def load_raw_episodes(spec: CorpusSpec) -> list[Candidate]:
    connection = _read_only_connection(spec.database_path)
    try:
        rows = connection.execute(
            """
            SELECT
                episodes.id,
                episodes.turn_number,
                episodes.user_message,
                episodes.assistant_message,
                episodes.embedding,
                episodes.topic_id,
                COALESCE(topics.label, episodes.topic_id, '') AS topic_label,
                COALESCE(episodes.ground_truth_domain, '') AS ground_truth_domain
            FROM episodes
            LEFT JOIN topics ON topics.id = episodes.topic_id
            WHERE episodes.turn_number BETWEEN ? AND ?
            ORDER BY episodes.turn_number ASC, episodes.id ASC
            """,
            (spec.eligible_turn_min, spec.eligible_turn_max),
        ).fetchall()
    finally:
        connection.close()

    candidates = [
        Candidate(
            candidate_id=str(row["id"]),
            source_episode_id=str(row["id"]),
            turn_number=int(row["turn_number"]),
            unit_type="episode",
            user_message=str(row["user_message"] or ""),
            assistant_message=str(row["assistant_message"] or ""),
            topic_id=str(row["topic_id"] or ""),
            topic_label=str(row["topic_label"] or ""),
            domain=str(row["ground_truth_domain"] or ""),
            embedding=_vector(row["embedding"]),
        )
        for row in rows
    ]
    _assert_temporal_bounds(candidates, spec)
    return candidates


def load_distilled_ltm(spec: CorpusSpec) -> list[Candidate]:
    if not spec.has_distilled_ltm:
        raise ValueError(f"{spec.corpus_id} has no distilled LTM baseline")
    connection = _read_only_connection(spec.database_path)
    try:
        rows = get_distilled_retrieval_rows(connection)
    finally:
        connection.close()

    candidates = []
    for row in rows:
        turn = int(row["turn_number"])
        if not spec.eligible_turn_min <= turn <= spec.eligible_turn_max:
            continue
        candidates.append(
            Candidate(
                candidate_id=str(row["distilled_id"]),
                source_episode_id=str(row["id"]),
                turn_number=turn,
                unit_type="episode",
                user_message=str(row.get("user_message") or ""),
                assistant_message=str(row.get("assistant_message") or ""),
                topic_id=str(row.get("topic_id") or ""),
                topic_label=str(row.get("topic_label") or ""),
                domain=str(row.get("ground_truth_domain") or ""),
                embedding=_vector(row.get("embedding")),
                distilled_id=str(row["distilled_id"]),
            )
        )
    _assert_temporal_bounds(candidates, spec)
    return candidates


def build_raw_spans(
    episodes: list[Candidate],
    embedder: Callable[[str], np.ndarray],
    cache: "EmbeddingCacheProtocol | None" = None,
) -> list[Candidate]:
    inventory: list[tuple[Candidate, object]] = []
    for episode in episodes:
        source = {
            "id": episode.source_episode_id,
            "turn_number": episode.turn_number,
            "user_message": episode.user_message,
            "assistant_message": episode.assistant_message,
            "text": (
                f"User: {episode.user_message}\n"
                f"Assistant: {episode.assistant_message}"
            ),
        }
        for span in segment_episode(source):
            if not span.text.strip():
                continue
            inventory.append((episode, span))

    texts = [span.text for _, span in inventory]
    embeddings = (
        cache.get_or_embed_many(texts, embedder)
        if cache is not None
        else _embed_many(texts, embedder)
    )

    spans: list[Candidate] = []
    for (episode, span), embedding in zip(
        inventory,
        embeddings,
        strict=True,
    ):
        candidate_id = (
            f"span:{episode.source_episode_id}:{span.role}:"
            f"{span.start}:{span.end}"
        )
        spans.append(
            Candidate(
                candidate_id=candidate_id,
                source_episode_id=episode.source_episode_id,
                turn_number=episode.turn_number,
                unit_type="span",
                span_text=span.text,
                role=span.role,
                span_start=span.start,
                span_end=span.end,
                topic_id=episode.topic_id,
                topic_label=episode.topic_label,
                domain=episode.domain,
                embedding=_normalized(embedding),
            )
        )
    return spans


def _normalized(vector: np.ndarray) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32).reshape(EMBEDDING_DIMENSION)
    norm = float(np.linalg.norm(array))
    return array / norm if norm else array


def _embed_many(
    texts: list[str],
    embedder: Callable[[str], np.ndarray],
) -> list[np.ndarray]:
    batch = getattr(embedder, "embed_many", None)
    if callable(batch):
        return list(batch(texts))
    return [embedder(text) for text in texts]


def _assert_temporal_bounds(
    candidates: list[Candidate],
    spec: CorpusSpec,
) -> None:
    violations = [
        candidate.turn_number
        for candidate in candidates
        if not spec.eligible_turn_min
        <= candidate.turn_number
        <= spec.eligible_turn_max
    ]
    if violations:
        raise AssertionError(
            f"{spec.corpus_id} loaded out-of-range turns: {sorted(set(violations))}"
        )


class EmbeddingCacheProtocol:
    def get_or_embed(
        self,
        text: str,
        embedder: Callable[[str], np.ndarray],
    ) -> np.ndarray:
        raise NotImplementedError

    def get_or_embed_many(
        self,
        texts: list[str],
        embedder: Callable[[str], np.ndarray],
    ) -> list[np.ndarray]:
        raise NotImplementedError
