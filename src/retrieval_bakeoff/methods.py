from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .classifier import classify_query
from .config import BM25_B, BM25_K1, RRF_CONSTANT, CorpusSpec
from .embedding import normalize_embedding
from .models import Candidate, Query, RankedCandidate


METHOD_IDS = ("M1", "M2", "M3", "M4", "M5_span", "M6")
_DENSE_METHODS = {"M1", "M2", "M4", "M5_span", "M6"}
_TOKEN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN.finditer(text)]


class BM25Index:
    def __init__(self, candidates: list[Candidate]) -> None:
        self.candidates = candidates
        self.term_frequencies = [
            Counter(tokenize(candidate.searchable_text))
            for candidate in candidates
        ]
        self.document_lengths = np.asarray(
            [sum(frequencies.values()) for frequencies in self.term_frequencies],
            dtype=np.float64,
        )
        self.average_length = (
            float(np.mean(self.document_lengths))
            if len(self.document_lengths)
            else 0.0
        )
        document_frequency: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            document_frequency.update(frequencies.keys())
        total = len(candidates)
        self.idf = {
            term: math.log(1.0 + (total - count + 0.5) / (count + 0.5))
            for term, count in document_frequency.items()
        }

    def scores(self, query: str) -> np.ndarray:
        scores = np.zeros(len(self.candidates), dtype=np.float64)
        if not self.candidates or not self.average_length:
            return scores
        query_terms = Counter(tokenize(query))
        for index, frequencies in enumerate(self.term_frequencies):
            length_ratio = self.document_lengths[index] / self.average_length
            normalization = BM25_K1 * (1.0 - BM25_B + BM25_B * length_ratio)
            score = 0.0
            for term, query_frequency in query_terms.items():
                term_frequency = frequencies.get(term, 0)
                if not term_frequency:
                    continue
                numerator = term_frequency * (BM25_K1 + 1.0)
                score += (
                    query_frequency
                    * self.idf.get(term, 0.0)
                    * numerator
                    / (term_frequency + normalization)
                )
            scores[index] = score
        return scores


@dataclass
class EncodedQuery:
    texts: list[str] = field(default_factory=list)
    vectors: list[np.ndarray] = field(default_factory=list)
    query_class: str = ""


@dataclass
class BuiltMethod:
    method_id: str
    candidates: list[Candidate]
    dense_matrix: np.ndarray | None = None
    bm25: BM25Index | None = None
    index_build_ms: float = 0.0

    def encode(
        self,
        query: Query,
        spec: CorpusSpec,
        embedder,
    ) -> EncodedQuery:
        query_class = classify_query(query.text, spec.domain_labels)
        if self.method_id not in _DENSE_METHODS:
            return EncodedQuery(query_class=query_class)
        texts = [query.text]
        if self.method_id == "M6" and query_class == "enumeration":
            texts.extend(
                f"{domain}: {query.text}" for domain in spec.domain_labels
            )
        vectors = [normalize_embedding(embedder(text)) for text in texts]
        return EncodedQuery(
            texts=texts,
            vectors=vectors,
            query_class=query_class,
        )

    def rank(
        self,
        query: Query,
        encoded: EncodedQuery,
    ) -> list[RankedCandidate]:
        if self.method_id in {"M1", "M2", "M5_span"}:
            return self._dense_rank(encoded.vectors[0])
        if self.method_id == "M3":
            if self.bm25 is None:
                raise AssertionError("M3 was built without a BM25 index")
            return _rank_scores(
                self.candidates,
                self.bm25.scores(query.text),
                component="bm25",
            )
        if self.method_id == "M4":
            if self.bm25 is None:
                raise AssertionError("M4 was built without a BM25 index")
            dense = self._dense_rank(encoded.vectors[0])
            sparse = _rank_scores(
                self.candidates,
                self.bm25.scores(query.text),
                component="bm25",
            )
            return reciprocal_rank_fusion(
                [dense, sparse],
                component_names=["dense", "bm25"],
            )
        if self.method_id == "M6":
            rankings = [self._dense_rank(vector) for vector in encoded.vectors]
            if len(rankings) == 1:
                return rankings[0]
            return reciprocal_rank_fusion(
                rankings,
                component_names=[
                    "original",
                    *[f"domain_{index}" for index in range(1, len(rankings))],
                ],
            )
        raise ValueError(f"Unsupported method: {self.method_id}")

    def ordered_for_packing(
        self,
        ranked: list[RankedCandidate],
    ) -> list[tuple[RankedCandidate, str]]:
        if self.method_id != "M1":
            return [(candidate, "fill") for candidate in ranked]

        collapsed: list[RankedCandidate] = []
        seen_sources: set[str] = set()
        for candidate in ranked:
            source_id = candidate.candidate.source_episode_id
            if source_id in seen_sources:
                continue
            seen_sources.add(source_id)
            collapsed.append(candidate)

        by_topic: dict[str, list[RankedCandidate]] = {}
        for candidate in collapsed:
            topic = (
                candidate.candidate.topic_id
                or candidate.candidate.topic_label
                or ""
            )
            by_topic.setdefault(topic, []).append(candidate)

        ordered: list[tuple[RankedCandidate, str]] = []
        selected_sources: set[str] = set()
        for bucket in by_topic.values():
            if not bucket:
                continue
            candidate = bucket[0]
            ordered.append((candidate, "floor"))
            selected_sources.add(candidate.candidate.source_episode_id)
        ordered.extend(
            (candidate, "fill")
            for candidate in collapsed
            if candidate.candidate.source_episode_id not in selected_sources
        )
        return ordered

    def _dense_rank(self, query_vector: np.ndarray) -> list[RankedCandidate]:
        if self.dense_matrix is None:
            raise AssertionError(f"{self.method_id} was built without dense vectors")
        scores = self.dense_matrix @ normalize_embedding(query_vector)
        return _rank_scores(self.candidates, scores, component="dense")


def build_method(
    method_id: str,
    candidates: list[Candidate],
) -> BuiltMethod:
    if method_id not in METHOD_IDS:
        raise ValueError(f"Unsupported method: {method_id}")
    start = time.perf_counter()
    dense_matrix = None
    bm25 = None
    if method_id in _DENSE_METHODS:
        missing = [
            candidate.candidate_id
            for candidate in candidates
            if candidate.embedding is None
        ]
        if missing:
            raise ValueError(
                f"{method_id} candidates lack embeddings: {missing[:5]}"
            )
        dense_matrix = np.vstack(
            [
                normalize_embedding(np.asarray(candidate.embedding))
                for candidate in candidates
            ]
        ).astype(np.float32, copy=False)
    if method_id in {"M3", "M4"}:
        bm25 = BM25Index(candidates)
    return BuiltMethod(
        method_id=method_id,
        candidates=candidates,
        dense_matrix=dense_matrix,
        bm25=bm25,
        index_build_ms=(time.perf_counter() - start) * 1000.0,
    )


def reciprocal_rank_fusion(
    rankings: list[list[RankedCandidate]],
    *,
    component_names: list[str],
) -> list[RankedCandidate]:
    if len(rankings) != len(component_names):
        raise ValueError("Every ranking needs one component name")
    candidates: dict[str, Candidate] = {}
    totals: dict[str, float] = {}
    components: dict[str, dict[str, float]] = {}
    for component, ranking in zip(component_names, rankings, strict=True):
        for rank, item in enumerate(ranking, start=1):
            candidate_id = item.candidate.candidate_id
            contribution = 1.0 / (RRF_CONSTANT + rank)
            candidates[candidate_id] = item.candidate
            totals[candidate_id] = totals.get(candidate_id, 0.0) + contribution
            components.setdefault(candidate_id, {})[component] = contribution
    fused = [
        RankedCandidate(
            candidate=candidates[candidate_id],
            score=score,
            component_scores=components[candidate_id],
        )
        for candidate_id, score in totals.items()
    ]
    fused.sort(key=lambda item: (-item.score, item.candidate.candidate_id))
    return fused


def _rank_scores(
    candidates: list[Candidate],
    scores: np.ndarray,
    *,
    component: str,
) -> list[RankedCandidate]:
    if len(candidates) != len(scores):
        raise ValueError("Candidate and score counts differ")
    ranked = [
        RankedCandidate(
            candidate=candidate,
            score=float(score),
            component_scores={component: float(score)},
        )
        for candidate, score in zip(candidates, scores, strict=True)
    ]
    ranked.sort(key=lambda item: (-item.score, item.candidate.candidate_id))
    return ranked
