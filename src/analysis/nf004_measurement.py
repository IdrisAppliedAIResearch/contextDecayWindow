"""Corpus adaptation and evidence measurement for registered NF-004."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from analysis.nf004_mechanism import Candidate, Delivery, retrieve, source_order
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from retrieval_bakeoff.embedding import CarriedEmbedder

DATASET_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
DATASET_BYTES = 2_805_274
DEVELOPMENT_IDS = frozenset({"conv-41", "conv-42", "conv-47", "conv-48"})
HOLDOUT_IDS = frozenset(
    {"conv-26", "conv-30", "conv-43", "conv-44", "conv-49", "conv-50"}
)
BUDGET = 16_000
SECONDARY_BUDGET = 32_000
_SESSION = re.compile(r"session_(\d+)")


class NF004MeasurementError(RuntimeError):
    pass


@dataclass(frozen=True)
class CandidateSource:
    candidate: Candidate
    dialogue_ids: tuple[str, ...]


@dataclass(frozen=True)
class QuestionRecord:
    comparison_key: str
    duplicate_ordinal: int
    sample_id: str
    source_index: int
    category: str
    text: str
    resolved_dialogue_ids: tuple[str, ...]
    unresolved_dialogue_ids: tuple[str, ...]


@dataclass(frozen=True)
class ConversationRecord:
    sample_id: str
    candidates: tuple[CandidateSource, ...]
    questions: tuple[QuestionRecord, ...]


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


def _identity(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _session_keys(conversation: dict[str, Any]) -> list[str]:
    found: list[tuple[int, str]] = []
    for key in conversation:
        match = _SESSION.fullmatch(key)
        if match:
            found.append((int(match.group(1)), key))
    return [key for _, key in sorted(found)]


def adapt_split(
    dataset_path: Path, split_ids: frozenset[str]
) -> tuple[ConversationRecord, ...]:
    if dataset_path.stat().st_size != DATASET_BYTES:
        raise NF004MeasurementError("LoCoMo byte count differs from the lock")
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise NF004MeasurementError("LoCoMo SHA-256 differs from the lock")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    selected = [row for row in raw if row.get("sample_id") in split_ids]
    if {row["sample_id"] for row in selected} != split_ids:
        raise NF004MeasurementError("Locked split conversations are incomplete")

    records: list[ConversationRecord] = []
    comparison_keys: set[str] = set()
    for row in sorted(selected, key=lambda value: value["sample_id"]):
        sample_id = str(row["sample_id"])
        conversation = row["conversation"]
        candidates: list[CandidateSource] = []
        known_dialogue_ids: set[str] = set()
        for session_order, session_id in enumerate(_session_keys(conversation)):
            turns = conversation[session_id]
            for turn in turns:
                dialogue_id = str(turn["dia_id"])
                if dialogue_id in known_dialogue_ids:
                    raise NF004MeasurementError(
                        f"{sample_id}: duplicate dialogue id {dialogue_id}"
                    )
                known_dialogue_ids.add(dialogue_id)
            for pair_order, start in enumerate(range(0, len(turns), 2)):
                members = turns[start : start + 2]
                dialogue_ids = tuple(str(turn["dia_id"]) for turn in members)
                text = "\n".join(
                    f"{turn['speaker']}: {turn['text']}" for turn in members
                )
                candidate = Candidate(
                    identity=_identity(
                        sample_id, session_id, *dialogue_ids, text
                    ),
                    session_identity=session_id,
                    session_order=session_order,
                    pair_order=pair_order,
                    text=text,
                    chars=len(text),
                )
                candidates.append(CandidateSource(candidate, dialogue_ids))

        occurrences: Counter[str] = Counter()
        questions: list[QuestionRecord] = []
        for source_index, qa in enumerate(row["qa"]):
            canonical_qa = json.dumps(
                qa, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            comparison_key = _identity(sample_id, canonical_qa)
            duplicate_ordinal = occurrences[comparison_key]
            occurrences[comparison_key] += 1
            if duplicate_ordinal == 0:
                if comparison_key in comparison_keys:
                    raise NF004MeasurementError(
                        "Canonical comparison key is not unique"
                    )
                comparison_keys.add(comparison_key)
            dialogue_ids = tuple(str(value) for value in (qa.get("evidence") or ()))
            questions.append(
                QuestionRecord(
                    comparison_key=comparison_key,
                    duplicate_ordinal=duplicate_ordinal,
                    sample_id=sample_id,
                    source_index=source_index,
                    category=str(qa["category"]),
                    text=str(qa["question"]),
                    resolved_dialogue_ids=tuple(
                        value for value in dialogue_ids if value in known_dialogue_ids
                    ),
                    unresolved_dialogue_ids=tuple(
                        value for value in dialogue_ids if value not in known_dialogue_ids
                    ),
                )
            )
        records.append(
            ConversationRecord(sample_id, tuple(candidates), tuple(questions))
        )
    return tuple(records)


def vector_texts(records: Sequence[ConversationRecord]) -> tuple[str, ...]:
    texts = {
        source.candidate.text for record in records for source in record.candidates
    }
    texts.update(question.text for record in records for question in record.questions)
    return tuple(sorted(texts, key=_identity))


class _SoloDelegate:
    def __init__(self, delegate: CarriedEmbedder) -> None:
        self.delegate = delegate
        self.model_sha256 = delegate.model_sha256
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        return self.delegate(text)


def capture_vectors(
    records: Sequence[ConversationRecord], model_path: Path, cache_path: Path
) -> dict[str, Any]:
    from episodic import EmbeddingCache

    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    solo = _SoloDelegate(delegate)
    texts = vector_texts(records)
    with EmbeddingCache(cache_path, mode="populate", embedder=solo) as cache:
        for text in texts:
            cache(text)
    record = cache.record()
    if solo.calls != len(texts) or record["entries"] != len(texts):
        raise NF004MeasurementError("Vector capture cardinality differs")
    return {
        "schema": "nf004-holdout-vectors-v1",
        "dataset_sha256": DATASET_SHA256,
        "holdout_ids": sorted(HOLDOUT_IDS),
        "text_order_digest": _identity(*(_identity(text) for text in texts)),
        "expected_unique_texts": len(texts),
        "cache": record,
        "llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
        "model_sha256": CARRIED_EMBEDDING_SHA256,
        "embedding_calls": solo.calls,
        "model_generation_calls": 0,
    }


def _delivery_metrics(
    delivery: Delivery,
    evidence_candidates: set[str],
) -> dict[str, Any]:
    selected = set(delivery.selected)
    ranks = {
        identity: rank for rank, identity in enumerate(delivery.order, start=1)
    }
    return {
        "any_evidence": bool(evidence_candidates & selected),
        "all_evidence": evidence_candidates <= selected,
        "delivered_candidates": len(delivery.selected),
        "packed_chars": delivery.packed_chars,
        "best_evidence_rank": min(
            (ranks[identity] for identity in evidence_candidates), default=None
        ),
    }


def run_measurement(
    records: Sequence[ConversationRecord],
    cache_path: Path,
    vector_manifest: dict[str, Any],
    *,
    include_secondary: bool,
) -> dict[str, Any]:
    from episodic import EmbeddingCache

    cache_record = vector_manifest["cache"]
    rows: list[dict[str, Any]] = []
    with EmbeddingCache(
        cache_path,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for record in records:
            candidates = tuple(source.candidate for source in record.candidates)
            candidate_matrix = np.vstack(
                [
                    np.asarray(cache(candidate.text), dtype=np.float32)
                    for candidate in candidates
                ]
            )
            dialogue_to_candidate = {
                dialogue_id: source.candidate.identity
                for source in record.candidates
                for dialogue_id in source.dialogue_ids
            }
            frozen: list[tuple[QuestionRecord, dict[str, Delivery]]] = []
            for question in record.questions:
                query_vector = cache(question.text)
                deliveries = retrieve(
                    candidates, candidate_matrix, query_vector, BUDGET
                )
                if include_secondary:
                    secondary = retrieve(
                        candidates,
                        candidate_matrix,
                        query_vector,
                        SECONDARY_BUDGET,
                    )
                    deliveries = {
                        **deliveries,
                        "SOURCE_ORDER": source_order(candidates, BUDGET),
                        "S_SESSION_RANK_32K": secondary["S_SESSION_RANK"],
                        "P_PAIR_RANK_32K": secondary["P_PAIR_RANK"],
                    }
                frozen.append((question, deliveries))

            for question, deliveries in frozen:
                evidence_candidates = {
                    dialogue_to_candidate[value]
                    for value in question.resolved_dialogue_ids
                }
                row: dict[str, Any] = {
                    "comparison_key": question.comparison_key,
                    "duplicate_ordinal": question.duplicate_ordinal,
                    "sample_id": question.sample_id,
                    "source_index": question.source_index,
                    "category": question.category,
                    "resolved_evidence_count": len(
                        question.resolved_dialogue_ids
                    ),
                    "unresolved_evidence_count": len(
                        question.unresolved_dialogue_ids
                    ),
                    "primary_eligible": (
                        question.duplicate_ordinal == 0
                        and not question.unresolved_dialogue_ids
                    ),
                    "arms": {
                        arm: _delivery_metrics(delivery, evidence_candidates)
                        for arm, delivery in deliveries.items()
                    },
                }
                rows.append(row)
        cache_reuse = cache.record()
    return {
        "rows": sorted(
            rows, key=lambda row: (row["comparison_key"], row["duplicate_ordinal"])
        ),
        "cache": cache_reuse,
        "embedding_calls": 0,
        "model_generation_calls": 0,
    }


def paired_counts(
    rows: Sequence[dict[str, Any]], arm_key: str = "all_evidence"
) -> dict[str, Any]:
    gains = sum(
        row["arms"]["P_PAIR_RANK"][arm_key]
        and not row["arms"]["S_SESSION_RANK"][arm_key]
        for row in rows
    )
    losses = sum(
        row["arms"]["S_SESSION_RANK"][arm_key]
        and not row["arms"]["P_PAIR_RANK"][arm_key]
        for row in rows
    )
    discordant = gains + losses
    p_one_sided = (
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
        "discordant_n": discordant,
        "gain_loss_ratio": gains / losses if losses else None,
        "p_one_sided": p_one_sided,
    }


def distribution(values: Iterable[int]) -> dict[str, int]:
    ordered = sorted(values)
    if not ordered:
        raise NF004MeasurementError("Cannot summarize an empty distribution")

    def nearest(percentile: float) -> int:
        return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]

    return {
        "min": ordered[0],
        "p10": nearest(0.10),
        "p50": nearest(0.50),
        "p90": nearest(0.90),
        "max": ordered[-1],
    }
