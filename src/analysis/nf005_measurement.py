"""Corpus adaptation, vector capture, and evidence measurement for NF-005."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from analysis.nf002_streams import DATASET_SHA256, episode_text
from analysis.nf005_mechanism import (
    Candidate,
    Delivery,
    inherited_score_order,
    own_score_order,
    pack,
    retrieve,
    source_order,
)
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from retrieval_bakeoff.embedding import CarriedEmbedder

BUDGET = 32_000
SENTINEL_TEXT = "episodic call-shape sentinel: one text per call"
SENTINEL_VECTOR_SHA256 = (
    "baecf77627380f36f75a69c4454b064d886133f04255c5e5b4d3f24f00e7c4b8"
)
OLD_CACHE = Path(
    "experiments/external/longmemeval/runs/ec002_k_first/"
    "ec002_exact_solo_embeddings.db"
)


class NF005MeasurementError(RuntimeError):
    pass


@dataclass(frozen=True)
class EpisodeSource:
    candidate: Candidate
    turn_identities: tuple[str, str]


@dataclass(frozen=True)
class TurnSource:
    candidate: Candidate
    is_target: bool


@dataclass(frozen=True)
class QuestionRecord:
    question_id: str
    question_type: str
    question: str
    episodes: tuple[EpisodeSource, ...]
    turns: tuple[TurnSource, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, indent=1, sort_keys=True) + "\n"
    ).encode("utf-8")


def canonical_digest(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def identity(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def rendered_turn(turn: dict[str, Any]) -> str:
    role = str(turn.get("role", "")).strip().capitalize()
    return f"{role}: {turn.get('content', '')}"


def adapt_population(
    dataset_path: Path, population_ids: frozenset[str]
) -> tuple[QuestionRecord, ...]:
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise NF005MeasurementError("LongMemEval source differs from its corpus lock")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    selected = [row for row in raw if row.get("question_id") in population_ids]
    if {str(row["question_id"]) for row in selected} != population_ids:
        raise NF005MeasurementError("Locked population is incomplete")

    records: list[QuestionRecord] = []
    for item in selected:
        question_id = str(item["question_id"])
        episodes: list[EpisodeSource] = []
        turns: list[TurnSource] = []
        episode_index = 0
        for session_order, (session_id, session) in enumerate(
            zip(item["haystack_session_ids"], item["haystack_sessions"], strict=True)
        ):
            accepted_in_session = 0
            for start in range(0, len(session) - 1, 2):
                first, second = session[start : start + 2]
                if first.get("role") != "user" or second.get("role") != "assistant":
                    continue
                episode_rendering = episode_text(
                    str(first.get("content", "")), str(second.get("content", ""))
                )
                episode_identity = identity(
                    question_id,
                    str(session_id),
                    str(accepted_in_session),
                    "episode",
                    episode_rendering,
                )
                episode_candidate = Candidate(
                    identity=episode_identity,
                    parent_index=episode_index,
                    session_order=session_order,
                    episode_order=accepted_in_session,
                    turn_offset=-1,
                    text=episode_rendering,
                    chars=len(episode_rendering),
                )
                turn_identities: list[str] = []
                for turn_offset, turn in enumerate((first, second)):
                    text = rendered_turn(turn)
                    turn_identity = identity(
                        question_id,
                        str(session_id),
                        str(accepted_in_session),
                        str(turn_offset),
                        str(turn["role"]),
                        text,
                    )
                    turn_identities.append(turn_identity)
                    turns.append(
                        TurnSource(
                            candidate=Candidate(
                                identity=turn_identity,
                                parent_index=episode_index,
                                session_order=session_order,
                                episode_order=accepted_in_session,
                                turn_offset=turn_offset,
                                text=text,
                                chars=len(text),
                            ),
                            is_target=bool(turn.get("has_answer")),
                        )
                    )
                episodes.append(
                    EpisodeSource(episode_candidate, tuple(turn_identities))  # type: ignore[arg-type]
                )
                accepted_in_session += 1
                episode_index += 1
        if not any(turn.is_target for turn in turns):
            raise NF005MeasurementError(f"{question_id}: no exact target turn")
        records.append(
            QuestionRecord(
                question_id=question_id,
                question_type=str(item.get("question_type", "unknown")),
                question=str(item["question"]),
                episodes=tuple(episodes),
                turns=tuple(turns),
            )
        )
    return tuple(records)


def vector_texts(records: Sequence[QuestionRecord]) -> tuple[str, ...]:
    texts = {turn.candidate.text for record in records for turn in record.turns}
    return tuple(sorted(texts, key=identity))


class LegacyCache:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.connection = sqlite3.connect(
            f"file:{self.path.as_posix()}?mode=ro", uri=True
        )
        self.hits = 0

    def close(self) -> None:
        self.connection.close()

    def vector(self, text: str) -> np.ndarray:
        row = self.connection.execute(
            "select embedding from cache where text=?", (text,)
        ).fetchone()
        if row is None:
            raise NF005MeasurementError(f"Legacy cache miss for {len(text)} chars")
        self.hits += 1
        return np.frombuffer(row[0], dtype=np.float32).copy()


class SoloDelegate:
    def __init__(self, delegate: CarriedEmbedder) -> None:
        self.delegate = delegate
        self.model_sha256 = delegate.model_sha256
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        return self.delegate(text)


def capture_vectors(
    records: Sequence[QuestionRecord],
    model_path: Path,
    cache_path: Path,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    from episodic import EmbeddingCache

    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    solo = SoloDelegate(delegate)
    sentinel = np.asarray(solo(SENTINEL_TEXT), dtype=np.float32)
    observed_sentinel = hashlib.sha256(sentinel.tobytes()).hexdigest()
    if observed_sentinel != SENTINEL_VECTOR_SHA256:
        raise NF005MeasurementError(
            f"Call-shape sentinel differs: {observed_sentinel}"
        )

    texts = vector_texts(records)
    with EmbeddingCache(cache_path, mode="populate", embedder=solo) as cache:
        for index, text in enumerate(texts, start=1):
            cache(text)
            if progress is not None and (index % 1024 == 0 or index == len(texts)):
                progress(index, len(texts))
    cache_record = cache.record()
    if solo.calls != len(texts) + 1 or cache_record["entries"] != len(texts):
        raise NF005MeasurementError("Vector capture cardinality differs")
    return {
        "schema": "nf005-source-turn-vectors-v1",
        "dataset_sha256": DATASET_SHA256,
        "population_items": len(records),
        "text_order_digest": canonical_digest([identity(text) for text in texts]),
        "expected_unique_texts": len(texts),
        "sentinel_text": SENTINEL_TEXT,
        "sentinel_vector_sha256": observed_sentinel,
        "cache": cache_record,
        "llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
        "model_sha256": CARRIED_EMBEDDING_SHA256,
        "embedding_calls": solo.calls,
        "model_generation_calls": 0,
    }


def distribution(values: Iterable[int | float]) -> dict[str, int | float]:
    ordered = sorted(values)
    if not ordered:
        raise NF005MeasurementError("Cannot summarize an empty distribution")

    def nearest(percentile: float) -> int | float:
        return ordered[math.ceil(percentile * len(ordered)) - 1]

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p50": nearest(0.50),
        "p90": nearest(0.90),
        "max": ordered[-1],
    }


def delivery_metrics(
    delivery: Delivery,
    target_turns: set[str],
    episode_turns: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    selected = set(delivery.selected)
    delivered_turns = set(selected)
    for identity_value in selected & episode_turns.keys():
        delivered_turns.update(episode_turns[identity_value])
    ranks = {
        identity_value: rank
        for rank, identity_value in enumerate(delivery.order, start=1)
    }
    target_ranks: list[int] = []
    for target in target_turns:
        if target in ranks:
            target_ranks.append(ranks[target])
            continue
        for episode_identity, members in episode_turns.items():
            if target in members:
                target_ranks.append(ranks[episode_identity])
                break
    return {
        "any_target": bool(target_turns & delivered_turns),
        "all_targets": target_turns <= delivered_turns,
        "delivered_candidates": len(delivery.selected),
        "packed_chars": delivery.packed_chars,
        "best_target_rank": min(target_ranks),
        "best_target_rank_fraction": min(target_ranks) / len(delivery.order),
        "selected_digest": canonical_digest(list(delivery.selected)),
        "order_digest": canonical_digest(list(delivery.order)),
    }


def run_control(
    repository_root: Path,
    records: Sequence[QuestionRecord],
) -> dict[str, Any]:
    old = LegacyCache(repository_root / OLD_CACHE)
    rows: list[dict[str, Any]] = []
    episode_any: dict[str, bool] = {}
    try:
        for record in records:
            episodes = tuple(source.candidate for source in record.episodes)
            turns = tuple(source.candidate for source in record.turns)
            query_vector = old.vector(record.question)
            episode_vectors = np.vstack(
                [old.vector(candidate.text) for candidate in episodes]
            )
            episode_delivery = pack(
                episodes,
                own_score_order(episodes, episode_vectors, query_vector),
                BUDGET,
            )
            turn_delivery = pack(
                turns,
                inherited_score_order(turns, episode_vectors, query_vector),
                BUDGET,
            )
            targets = {
                turn.candidate.identity for turn in record.turns if turn.is_target
            }
            episode_turns = {
                episode.candidate.identity: episode.turn_identities
                for episode in record.episodes
            }
            episode_metrics = delivery_metrics(
                episode_delivery, targets, episode_turns
            )
            turn_metrics = delivery_metrics(turn_delivery, targets, episode_turns)
            rows.append(
                {
                    "question_id": record.question_id,
                    "any_evidence": turn_metrics["any_target"],
                    "all_evidence": turn_metrics["all_targets"],
                    "packed_chars": turn_metrics["packed_chars"],
                    "delivered_turns": turn_metrics["delivered_candidates"],
                    "total_chars": sum(candidate.chars for candidate in turns),
                }
            )
            episode_any[record.question_id] = episode_metrics["any_target"]
    finally:
        old.close()
    gains = sum(
        not episode_any[row["question_id"]]
        and row["any_evidence"]
        for row in rows
    )
    losses = sum(
        episode_any[row["question_id"]]
        and not row["any_evidence"]
        for row in rows
    )
    return {
        "items": len(rows),
        "episode_rank_episode_pack_any": sum(
            episode_any[row["question_id"]] for row in rows
        ),
        "episode_rank_turn_pack_any": sum(
            row["any_evidence"] for row in rows
        ),
        "episode_rank_turn_pack_all": sum(
            row["all_evidence"] for row in rows
        ),
        "packing_gains": gains,
        "packing_losses": losses,
        "row_digest": hashlib.sha256(
            json.dumps(
                rows,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "old_cache_hits": old.hits,
    }
def run_measurement(
    repository_root: Path,
    records: Sequence[QuestionRecord],
    turn_cache_path: Path,
    vector_manifest: dict[str, Any],
    *,
    include_targets: bool,
) -> dict[str, Any]:
    from episodic import EmbeddingCache

    old = LegacyCache(repository_root / OLD_CACHE)
    cache_record = vector_manifest["cache"]
    rows: list[dict[str, Any]] = []
    try:
        with EmbeddingCache(
            turn_cache_path,
            mode="reuse",
            expected_file_sha256=cache_record["file_sha256"],
            expected_content_sha256=cache_record["content_sha256"],
            expected_model_sha256=CARRIED_EMBEDDING_SHA256,
        ) as turns_cache:
            for record in records:
                episodes = tuple(source.candidate for source in record.episodes)
                turns = tuple(source.candidate for source in record.turns)
                query_vector = old.vector(record.question)
                episode_vectors = np.vstack(
                    [old.vector(candidate.text) for candidate in episodes]
                )
                turn_vectors = np.vstack(
                    [
                        np.asarray(turns_cache(candidate.text), dtype=np.float32)
                        for candidate in turns
                    ]
                )
                deliveries = retrieve(
                    episodes,
                    turns,
                    episode_vectors,
                    turn_vectors,
                    query_vector,
                    BUDGET,
                )
                deliveries["SOURCE_ORDER_TURN_PACK"] = source_order(turns, BUDGET)
                row: dict[str, Any] = {
                    "question_id": record.question_id,
                    "selection": {
                        arm: {
                            "selected_digest": canonical_digest(list(delivery.selected)),
                            "order_digest": canonical_digest(list(delivery.order)),
                            "packed_chars": delivery.packed_chars,
                            "delivered_candidates": len(delivery.selected),
                        }
                        for arm, delivery in deliveries.items()
                    },
                }
                if include_targets:
                    target_turns = {
                        turn.candidate.identity for turn in record.turns if turn.is_target
                    }
                    episode_turns = {
                        episode.candidate.identity: episode.turn_identities
                        for episode in record.episodes
                    }
                    row["question_type"] = record.question_type
                    row["target_turns"] = len(target_turns)
                    row["arms"] = {
                        arm: delivery_metrics(
                            delivery, target_turns, episode_turns
                        )
                        for arm, delivery in deliveries.items()
                    }
                rows.append(row)
            turn_hits = turns_cache.hits
            turn_misses = turns_cache.misses
    finally:
        old.close()
    return {
        "schema": "nf005-measurement-v1",
        "items": len(rows),
        "budget": BUDGET,
        "include_targets": include_targets,
        "rows": rows,
        "old_cache_hits": old.hits,
        "turn_cache_hits": turn_hits,
        "turn_cache_misses": turn_misses,
        "embedding_calls": 0,
        "model_generation_calls": 0,
    }


def paired_counts(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    gains = losses = 0
    for row in rows:
        baseline = row["arms"]["E_EPISODE_RANK_TURN_PACK"]["any_target"]
        treatment = row["arms"]["T_TURN_RANK_TURN_PACK"]["any_target"]
        gains += not baseline and treatment
        losses += baseline and not treatment
    discordant = gains + losses
    p_value = (
        sum(math.comb(discordant, k) for k in range(gains, discordant + 1))
        / (2**discordant)
        if discordant
        else 1.0
    )
    return {
        "gains": gains,
        "losses": losses,
        "ties": len(rows) - discordant,
        "net": gains - losses,
        "discordant": discordant,
        "gain_loss_ratio": None if losses == 0 else gains / losses,
        "one_sided_exact_p": p_value,
    }
