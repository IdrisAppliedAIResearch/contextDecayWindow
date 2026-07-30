from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np

from src.embeddings.provider import cosine_similarity
from src.memory.context_matched_stm import render_stm_payload
from src.retrieval_bakeoff.config import EMBEDDING_DIMENSION


FORBIDDEN_MECHANISM_PATH_PARTS = (
    "q_facts_key",
    "rubric",
    "atomic_items",
    "targeted_items",
)


@dataclass(frozen=True)
class Segment:
    index: int
    text: str


@dataclass(frozen=True)
class SegmentHit:
    segment_index: int
    segment_text: str
    local_rank: int
    candidate_id: str
    source_turn: int
    domain: str
    cosine: float
    outcome: str


@dataclass(frozen=True)
class SegmentedRetrievalResult:
    query: str
    segment_width: int
    boundary_offset: int
    per_segment_budget: int
    budget_chars: int
    segments: tuple[Segment, ...]
    hits: tuple[SegmentHit, ...]
    selected_ids: tuple[str, ...]
    selected_source_turns: tuple[int, ...]
    selected_domains: tuple[str, ...]
    serialized_chars: int
    payload_sha256: str
    payload: str


def assert_mechanism_path_allowed(path: str | Path) -> None:
    normalized = str(path).replace("\\", "/").lower()
    if any(part in normalized for part in FORBIDDEN_MECHANISM_PATH_PARTS):
        raise ValueError(f"Mechanism path crosses the measurement boundary: {path}")


def query_units(query: str) -> tuple[str, ...]:
    units = tuple(query.split())
    if not units:
        raise ValueError("Query must contain at least one non-whitespace unit")
    return units


def segment_query(
    query: str,
    *,
    segment_width: int,
    boundary_offset: int,
) -> tuple[Segment, ...]:
    if segment_width < 1:
        raise ValueError("segment_width must be positive")
    if not 0 <= boundary_offset < segment_width:
        raise ValueError("boundary_offset must be in [0, segment_width)")

    units = query_units(query)
    chunks: list[tuple[str, ...]] = []
    cursor = 0
    if boundary_offset:
        prefix_end = min(boundary_offset, len(units))
        chunks.append(units[:prefix_end])
        cursor = prefix_end
    while cursor < len(units):
        chunks.append(units[cursor : cursor + segment_width])
        cursor += segment_width

    return tuple(
        Segment(index=index, text=" ".join(chunk))
        for index, chunk in enumerate(chunks)
        if chunk
    )


def exhaustive_configurations(query: str) -> tuple[tuple[int, int, int], ...]:
    length = len(query_units(query))
    return tuple(
        (width, offset, per_segment_budget)
        for width in range(1, length + 1)
        for offset in range(width)
        for per_segment_budget in (1, 2)
    )


def retrieve_segmented(
    *,
    query: str,
    candidates: Sequence[dict],
    segment_width: int,
    boundary_offset: int,
    per_segment_budget: int,
    budget_chars: int,
    embed: Callable[[str], np.ndarray],
) -> SegmentedRetrievalResult:
    if per_segment_budget not in {1, 2}:
        raise ValueError("per_segment_budget must be 1 or 2")
    if not candidates:
        raise ValueError("At least one eligible candidate is required")

    segments = segment_query(
        query,
        segment_width=segment_width,
        boundary_offset=boundary_offset,
    )
    ranked = [
        _rank_segment(segment, candidates, embed(segment.text))[
            :per_segment_budget
        ]
        for segment in segments
    ]

    selected: list[dict] = []
    seen: set[str] = set()
    hits: list[SegmentHit] = []
    for local_rank in range(per_segment_budget):
        for segment, segment_hits in zip(segments, ranked, strict=True):
            if local_rank >= len(segment_hits):
                continue
            candidate, score = segment_hits[local_rank]
            candidate_id = str(candidate["id"])
            if candidate_id in seen:
                outcome = "duplicate"
            else:
                proposed = [*selected, candidate]
                payload = render_stm_payload([], proposed)
                if len(payload) <= budget_chars:
                    selected.append(candidate)
                    seen.add(candidate_id)
                    outcome = "selected"
                else:
                    outcome = "budget_skip"
            hits.append(
                SegmentHit(
                    segment_index=segment.index,
                    segment_text=segment.text,
                    local_rank=local_rank + 1,
                    candidate_id=candidate_id,
                    source_turn=int(candidate["turn_number"]),
                    domain=str(candidate.get("ground_truth_domain") or ""),
                    cosine=score,
                    outcome=outcome,
                )
            )

    payload = render_stm_payload([], selected)
    if len(payload) > budget_chars:
        raise AssertionError("Segmented retrieval exceeded its character budget")
    return SegmentedRetrievalResult(
        query=query,
        segment_width=segment_width,
        boundary_offset=boundary_offset,
        per_segment_budget=per_segment_budget,
        budget_chars=budget_chars,
        segments=segments,
        hits=tuple(hits),
        selected_ids=tuple(str(candidate["id"]) for candidate in selected),
        selected_source_turns=tuple(
            int(candidate["turn_number"]) for candidate in selected
        ),
        selected_domains=tuple(
            str(candidate.get("ground_truth_domain") or "")
            for candidate in selected
        ),
        serialized_chars=len(payload),
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        payload=payload,
    )


def eligible_candidates(
    candidates: Iterable[dict],
    *,
    probe_turn: int,
) -> tuple[dict, ...]:
    eligible = tuple(
        candidate
        for candidate in candidates
        if int(candidate["turn_number"]) < probe_turn
    )
    if any(int(candidate["turn_number"]) >= probe_turn for candidate in eligible):
        raise AssertionError("Temporal eligibility filter leaked a future episode")
    return eligible


def result_record(
    result: SegmentedRetrievalResult,
    *,
    configuration_id: str,
    probe_turn: int,
) -> dict:
    return {
        "configuration_id": configuration_id,
        "probe_turn": probe_turn,
        "query": result.query,
        "segment_width": result.segment_width,
        "boundary_offset": result.boundary_offset,
        "per_segment_budget": result.per_segment_budget,
        "budget_chars": result.budget_chars,
        "segments": [
            {"index": segment.index, "text": segment.text}
            for segment in result.segments
        ],
        "hits": [
            {
                "segment_index": hit.segment_index,
                "segment_text": hit.segment_text,
                "local_rank": hit.local_rank,
                "candidate_id": hit.candidate_id,
                "source_turn": hit.source_turn,
                "domain": hit.domain,
                "cosine": hit.cosine,
                "outcome": hit.outcome,
            }
            for hit in result.hits
        ],
        "selected_ids": list(result.selected_ids),
        "selected_source_turns": list(result.selected_source_turns),
        "selected_domains": list(result.selected_domains),
        "serialized_chars": result.serialized_chars,
        "payload_sha256": result.payload_sha256,
    }


def configuration_id(
    segment_width: int,
    boundary_offset: int,
    per_segment_budget: int,
) -> str:
    return (
        f"s{segment_width:02d}_o{boundary_offset:02d}_"
        f"b{per_segment_budget}"
    )


def _rank_segment(
    segment: Segment,
    candidates: Sequence[dict],
    query_embedding: np.ndarray,
) -> list[tuple[dict, float]]:
    query_vector = _vector(query_embedding)
    scored = [
        (
            candidate,
            cosine_similarity(
                query_vector,
                _vector(candidate["embedding"]),
            ),
        )
        for candidate in candidates
    ]
    return sorted(
        scored,
        key=lambda item: (
            -item[1],
            int(item[0]["turn_number"]),
            str(item[0]["id"]),
        ),
    )


def _vector(value: object) -> np.ndarray:
    if isinstance(value, (bytes, bytearray, memoryview)):
        array = np.frombuffer(value, dtype=np.float32).copy()
    else:
        array = np.asarray(value, dtype=np.float32)
    return array.reshape(EMBEDDING_DIMENSION)
