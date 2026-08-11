from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Sequence

from src.memory.span_segmenter import assert_span_offsets_faithful, segment_episode
from src.retrieval_bakeoff.models import Candidate, RankedCandidate
from src.retrieval_bakeoff.serialization import PackResult, pack_ranked_candidates


BUDGET_CHARS = 32_000
FORBIDDEN_PATH_MARKERS = (
    "answer_key",
    "q_facts_key",
    "rubric",
    "fact_matrix",
    "evaluation_results",
    "ta001_measurement",
    "span_embeddings",
)


def source_content_sha256(candidate: Candidate) -> str:
    payload = (
        f"{candidate.turn_number}\n"
        f"{candidate.user_message}\n"
        f"{candidate.assistant_message}"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def span_content_sha256(candidate: Candidate) -> str:
    if candidate.unit_type != "span":
        raise ValueError("span_content_sha256 requires a span candidate")
    payload = (
        f"{candidate.source_episode_id}\n{candidate.role}\n"
        f"{candidate.span_start}\n{candidate.span_end}\n{candidate.span_text}"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def assert_mechanism_path_allowed(path: str | Path) -> None:
    normalized = str(path).replace("\\", "/").casefold()
    if any(marker in normalized for marker in FORBIDDEN_PATH_MARKERS):
        raise PermissionError(f"SR-001 mechanism cannot open forbidden path: {path}")


def rank_sources(
    candidates: Sequence[Candidate],
    scores: Sequence[float],
) -> list[RankedCandidate]:
    if len(candidates) != len(scores):
        raise ValueError("Candidate and score counts differ")
    if any(candidate.unit_type != "episode" for candidate in candidates):
        raise ValueError("SR-001 source ranking accepts whole episodes only")
    ranked = [
        RankedCandidate(
            candidate=candidate,
            score=float(score),
            component_scores={"dense": float(score)},
        )
        for candidate, score in zip(candidates, scores, strict=True)
    ]
    ranked.sort(key=lambda row: (-row.score, source_content_sha256(row.candidate)))
    return ranked


def episode_to_spans(episode: Candidate) -> list[Candidate]:
    if episode.unit_type != "episode":
        raise ValueError("Only source episodes can be segmented")
    source_text = f"User: {episode.user_message}\nAssistant: {episode.assistant_message}"
    source = {
        "id": episode.source_episode_id,
        "turn_number": episode.turn_number,
        "user_message": episode.user_message,
        "assistant_message": episode.assistant_message,
        "text": source_text,
    }
    spans = [span for span in segment_episode(source) if span.text.strip()]
    assert_span_offsets_faithful(source, spans)
    role_order = {"user": 0, "assistant": 1}
    spans.sort(key=lambda span: (role_order[span.role], span.start, span.end))
    return [
        Candidate(
            candidate_id=(
                f"span:{episode.source_episode_id}:{span.role}:"
                f"{span.start}:{span.end}"
            ),
            source_episode_id=episode.source_episode_id,
            turn_number=episode.turn_number,
            unit_type="span",
            span_text=span.text,
            role=span.role,
            span_start=span.start,
            span_end=span.end,
            topic_id=episode.topic_id,
            topic_label=episode.topic_label,
        )
        for span in spans
    ]


def source_rank_preserving_spans(
    ranked_sources: Sequence[RankedCandidate],
) -> list[RankedCandidate]:
    output: list[RankedCandidate] = []
    for source in ranked_sources:
        for span in episode_to_spans(source.candidate):
            output.append(
                RankedCandidate(
                    candidate=span,
                    score=source.score,
                    component_scores=dict(source.component_scores),
                )
            )
    return output


def pack_control(
    ranked_sources: Sequence[RankedCandidate],
    *,
    budget: int = BUDGET_CHARS,
) -> PackResult:
    return pack_ranked_candidates(
        "M2", [(row, "fill") for row in ranked_sources], budget
    )


def pack_treatment(
    ranked_sources: Sequence[RankedCandidate],
    *,
    budget: int = BUDGET_CHARS,
) -> PackResult:
    ranked_spans = source_rank_preserving_spans(ranked_sources)
    return pack_ranked_candidates(
        "M2", [(row, "fill") for row in ranked_spans], budget
    )


def source_identity_sequence(
    ranked_sources: Iterable[RankedCandidate],
) -> tuple[str, ...]:
    return tuple(source_content_sha256(row.candidate) for row in ranked_sources)


def packed_source_identities(pack: PackResult) -> tuple[str, ...]:
    return tuple(row.candidate.source_episode_id for row in pack.selected)
