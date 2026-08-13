"""LoCoMo development-only exploration for ranking granularity.

The six holdout conversations are filtered by locked sample identity before any
question, dialogue, or evidence field is adapted. This module has no study bars
and cannot emit a confirmatory disposition.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from retrieval_bakeoff.embedding import CarriedEmbedder

DATASET_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
DATASET_BYTES = 2_805_274
DEVELOPMENT_IDS = frozenset({"conv-41", "conv-42", "conv-47", "conv-48"})
BUDGET_CHARS = 32_000
SCHEMA = "locomo-nf-development-v1"
_SESSION = re.compile(r"session_(\d+)")


class LocomoDevelopmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class PairCandidate:
    identity: str
    sample_id: str
    session_id: str
    session_order: int
    pair_order: int
    text: str
    chars: int
    dialog_ids: tuple[str, ...]


@dataclass(frozen=True)
class QuestionCase:
    identity: str
    content_sha256: str
    duplicate_ordinal: int
    sample_id: str
    source_index: int
    category: str
    question: str
    evidence_ids: tuple[str, ...]
    resolved_evidence_ids: tuple[str, ...]
    unresolved_evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ConversationCase:
    sample_id: str
    pairs: tuple[PairCandidate, ...]
    questions: tuple[QuestionCase, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _session_keys(conversation: dict[str, Any]) -> list[str]:
    found: list[tuple[int, str]] = []
    for key in conversation:
        match = _SESSION.fullmatch(key)
        if match:
            found.append((int(match.group(1)), key))
    return [key for _, key in sorted(found)]


def adapt_development(dataset_path: Path) -> tuple[ConversationCase, ...]:
    if dataset_path.stat().st_size != DATASET_BYTES:
        raise LocomoDevelopmentError("LoCoMo byte count differs from the corpus lock")
    if sha256_file(dataset_path) != DATASET_SHA256:
        raise LocomoDevelopmentError("LoCoMo SHA-256 differs from the corpus lock")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    selected = [row for row in raw if row.get("sample_id") in DEVELOPMENT_IDS]
    if {row["sample_id"] for row in selected} != DEVELOPMENT_IDS:
        raise LocomoDevelopmentError("Locked development conversations are incomplete")

    conversations: list[ConversationCase] = []
    question_ids: set[str] = set()
    for row in sorted(selected, key=lambda value: value["sample_id"]):
        sample_id = str(row["sample_id"])
        conversation = row["conversation"]
        pairs: list[PairCandidate] = []
        known_dialog_ids: set[str] = set()
        for session_order, session_id in enumerate(_session_keys(conversation)):
            turns = conversation[session_id]
            for turn in turns:
                dialog_id = str(turn["dia_id"])
                if dialog_id in known_dialog_ids:
                    raise LocomoDevelopmentError(
                        f"{sample_id}: duplicate dialogue id {dialog_id}"
                    )
                known_dialog_ids.add(dialog_id)
            for pair_order, start in enumerate(range(0, len(turns), 2)):
                members = turns[start : start + 2]
                dialog_ids = tuple(str(turn["dia_id"]) for turn in members)
                text = "\n".join(
                    f"{turn['speaker']}: {turn['text']}" for turn in members
                )
                pairs.append(
                    PairCandidate(
                        identity=_identity(sample_id, session_id, *dialog_ids, text),
                        sample_id=sample_id,
                        session_id=session_id,
                        session_order=session_order,
                        pair_order=pair_order,
                        text=text,
                        chars=len(text),
                        dialog_ids=dialog_ids,
                    )
                )

        questions: list[QuestionCase] = []
        occurrences: Counter[str] = Counter()
        for source_index, qa in enumerate(row["qa"]):
            question = str(qa["question"])
            canonical_qa = json.dumps(
                qa, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            content_sha256 = _identity(sample_id, canonical_qa)
            duplicate_ordinal = occurrences[content_sha256]
            occurrences[content_sha256] += 1
            identity = _identity(content_sha256, str(duplicate_ordinal))
            if identity in question_ids:
                raise LocomoDevelopmentError("Question comparison key is not unique")
            question_ids.add(identity)
            evidence = tuple(str(value) for value in (qa.get("evidence") or ()))
            resolved = tuple(value for value in evidence if value in known_dialog_ids)
            unresolved = tuple(value for value in evidence if value not in known_dialog_ids)
            questions.append(
                QuestionCase(
                    identity=identity,
                    content_sha256=content_sha256,
                    duplicate_ordinal=duplicate_ordinal,
                    sample_id=sample_id,
                    source_index=source_index,
                    category=str(qa["category"]),
                    question=question,
                    evidence_ids=evidence,
                    resolved_evidence_ids=resolved,
                    unresolved_evidence_ids=unresolved,
                )
            )
        conversations.append(
            ConversationCase(sample_id, tuple(pairs), tuple(questions))
        )
    return tuple(conversations)


def vector_texts(conversations: Sequence[ConversationCase]) -> tuple[str, ...]:
    texts = {pair.text for case in conversations for pair in case.pairs}
    texts.update(question.question for case in conversations for question in case.questions)
    return tuple(sorted(texts, key=lambda text: _identity(text)))


def inventory(conversations: Sequence[ConversationCase]) -> dict[str, Any]:
    pairs = [pair for case in conversations for pair in case.pairs]
    questions = [question for case in conversations for question in case.questions]
    return {
        "schema": SCHEMA,
        "source": {
            "sha256": DATASET_SHA256,
            "bytes": DATASET_BYTES,
            "development_ids": sorted(DEVELOPMENT_IDS),
        },
        "counts": {
            "conversations": len(conversations),
            "pairs": len(pairs),
            "questions": len(questions),
            "unique_vector_texts": len(vector_texts(conversations)),
            "questions_with_resolved_evidence": sum(
                bool(question.resolved_evidence_ids) for question in questions
            ),
            "questions_with_unresolved_evidence": sum(
                bool(question.unresolved_evidence_ids) for question in questions
            ),
            "unresolved_evidence_references": sum(
                len(question.unresolved_evidence_ids) for question in questions
            ),
            "duplicate_qa_records": sum(
                question.duplicate_ordinal > 0 for question in questions
            ),
        },
        "category_counts": dict(
            sorted(Counter(question.category for question in questions).items())
        ),
        "budget": {
            "chars": BUDGET_CHARS,
            "conversation_pair_chars": {
                case.sample_id: sum(pair.chars for pair in case.pairs)
                for case in conversations
            },
        },
        "unresolved_evidence": [
            {
                "question_id": question.identity,
                "sample_id": question.sample_id,
                "source_index": question.source_index,
                "category": question.category,
                "evidence_count": len(question.evidence_ids),
                "resolved_count": len(question.resolved_evidence_ids),
                "unresolved_ids": list(question.unresolved_evidence_ids),
            }
            for question in questions
            if question.unresolved_evidence_ids
        ],
    }


class _SoloDelegate:
    def __init__(self, delegate: CarriedEmbedder) -> None:
        self.delegate = delegate
        self.model_sha256 = delegate.model_sha256
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        return self.delegate(text)


def capture_vectors(
    conversations: Sequence[ConversationCase], model_path: Path, cache_path: Path
) -> dict[str, Any]:
    from episodic import EmbeddingCache

    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    solo = _SoloDelegate(delegate)
    texts = vector_texts(conversations)
    with EmbeddingCache(cache_path, mode="populate", embedder=solo) as cache:
        for text in texts:
            cache(text)
    record = cache.record()
    if solo.calls != len(texts) or record["entries"] != len(texts):
        raise LocomoDevelopmentError("Vector capture cardinality differs from inventory")
    return {
        "schema": "locomo-nf-development-vectors-v1",
        "dataset_sha256": DATASET_SHA256,
        "development_ids": sorted(DEVELOPMENT_IDS),
        "text_order_digest": _identity(*(_identity(text) for text in texts)),
        "cache": record,
        "llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
        "model_sha256": CARRIED_EMBEDDING_SHA256,
    }


def _unit(vector: np.ndarray) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    if norm == 0.0:
        raise LocomoDevelopmentError("Zero-norm embedding")
    return array / norm


def ranking_orders(
    pairs: Sequence[PairCandidate], scores: np.ndarray
) -> tuple[list[int], list[int]]:
    session_scores: dict[str, float] = {}
    for pair, score in zip(pairs, scores, strict=True):
        session_scores[pair.session_id] = max(
            float(score), session_scores.get(pair.session_id, float("-inf"))
        )
    session_order = sorted(
        range(len(pairs)),
        key=lambda index: (
            -session_scores[pairs[index].session_id],
            pairs[index].session_order,
            pairs[index].pair_order,
        ),
    )
    pair_order = sorted(
        range(len(pairs)),
        key=lambda index: (
            -float(scores[index]),
            pairs[index].session_order,
            pairs[index].pair_order,
        ),
    )
    return session_order, pair_order


def pack_indices(
    pairs: Sequence[PairCandidate], order: Iterable[int], budget: int = BUDGET_CHARS
) -> tuple[list[int], int]:
    delivered: list[int] = []
    used = 0
    for index in order:
        cost = pairs[index].chars
        if used + cost > budget:
            continue
        used += cost
        delivered.append(index)
    return delivered, used


def _paired(rows: Sequence[dict[str, Any]], baseline: str, treatment: str) -> dict[str, int]:
    gains = sum(row[treatment] and not row[baseline] for row in rows)
    losses = sum(row[baseline] and not row[treatment] for row in rows)
    return {"gains": gains, "losses": losses, "ties": len(rows) - gains - losses}


def analyse(
    conversations: Sequence[ConversationCase], cache_path: Path, vector_manifest: dict[str, Any]
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
        for case in conversations:
            pair_matrix = np.vstack([_unit(cache(pair.text)) for pair in case.pairs])
            dialog_to_pair = {
                dialog_id: index
                for index, pair in enumerate(case.pairs)
                for dialog_id in pair.dialog_ids
            }
            for question in case.questions:
                query = _unit(cache(question.question))
                scores = pair_matrix @ query
                session_order, pair_order = ranking_orders(case.pairs, scores)
                baseline, baseline_chars = pack_indices(case.pairs, session_order)
                treatment, treatment_chars = pack_indices(case.pairs, pair_order)
                baseline_set = set(baseline)
                treatment_set = set(treatment)
                evidence_pairs = {
                    dialog_to_pair[value] for value in question.resolved_evidence_ids
                }
                evidence_sessions = {
                    case.pairs[index].session_id for index in evidence_pairs
                }
                baseline_any = bool(evidence_pairs & baseline_set)
                treatment_any = bool(evidence_pairs & treatment_set)
                baseline_session_touch = any(
                    case.pairs[index].session_id in evidence_sessions for index in baseline
                )
                treatment_session_touch = any(
                    case.pairs[index].session_id in evidence_sessions for index in treatment
                )
                baseline_ranks = {
                    index: rank for rank, index in enumerate(session_order, 1)
                }
                treatment_ranks = {
                    index: rank for rank, index in enumerate(pair_order, 1)
                }
                rows.append(
                    {
                        "question_id": question.identity,
                        "question_content_sha256": question.content_sha256,
                        "duplicate_ordinal": question.duplicate_ordinal,
                        "sample_id": question.sample_id,
                        "source_index": question.source_index,
                        "category": question.category,
                        "resolved_evidence_count": len(question.resolved_evidence_ids),
                        "unresolved_evidence_count": len(question.unresolved_evidence_ids),
                        "baseline_any_answer_pair": baseline_any,
                        "treatment_any_answer_pair": treatment_any,
                        "baseline_session_touch": baseline_session_touch,
                        "treatment_session_touch": treatment_session_touch,
                        "baseline_all_answer_pairs": evidence_pairs <= baseline_set,
                        "treatment_all_answer_pairs": evidence_pairs <= treatment_set,
                        "all_evidence_evaluable": not question.unresolved_evidence_ids,
                        "baseline_best_evidence_rank": min(
                            (baseline_ranks[index] for index in evidence_pairs), default=None
                        ),
                        "treatment_best_evidence_rank": min(
                            (treatment_ranks[index] for index in evidence_pairs), default=None
                        ),
                        "baseline_delivered_pairs": len(baseline),
                        "treatment_delivered_pairs": len(treatment),
                        "baseline_chars": baseline_chars,
                        "treatment_chars": treatment_chars,
                    }
                )
        reuse_record = cache.record()

    by_category: dict[str, Any] = {}
    for category in sorted({row["category"] for row in rows}):
        group = [row for row in rows if row["category"] == category]
        by_category[category] = {
            "n": len(group),
            "strict_any": _paired(
                group, "baseline_any_answer_pair", "treatment_any_answer_pair"
            ),
        }
    return {
        "schema": SCHEMA,
        "status": "DEVELOPMENT_EXPLORATION_ONLY",
        "inventory": inventory(conversations),
        "arms": {
            "baseline": "pairs inherit max constituent-pair cosine of their session",
            "treatment": "pairs rank by their own cosine",
            "packing": "32000-char skip-on-overflow over identical pair candidates",
            "primary_measure": "at least one pair containing an exact evidence dia_id",
        },
        "strict_any": {
            "baseline_hits": sum(row["baseline_any_answer_pair"] for row in rows),
            "treatment_hits": sum(row["treatment_any_answer_pair"] for row in rows),
            "paired": _paired(
                rows, "baseline_any_answer_pair", "treatment_any_answer_pair"
            ),
        },
        "session_touch": {
            "baseline_hits": sum(row["baseline_session_touch"] for row in rows),
            "treatment_hits": sum(row["treatment_session_touch"] for row in rows),
            "paired": _paired(rows, "baseline_session_touch", "treatment_session_touch"),
            "baseline_false_hits": sum(
                row["baseline_session_touch"] and not row["baseline_any_answer_pair"]
                for row in rows
            ),
            "treatment_false_hits": sum(
                row["treatment_session_touch"] and not row["treatment_any_answer_pair"]
                for row in rows
            ),
        },
        "by_category": by_category,
        "cache": reuse_record,
        "model_calls": 0,
        "embedding_calls": 0,
        "rows": sorted(rows, key=lambda row: row["question_id"]),
    }
