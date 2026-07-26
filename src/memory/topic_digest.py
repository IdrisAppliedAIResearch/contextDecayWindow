"""Study 009 topic digest: extractive, density-ranked, and budget exact."""

from dataclasses import dataclass, field
from html import escape

import numpy as np

from src.db.retrieval import get_all_episodes_with_embeddings
from src.embeddings.provider import cosine_similarity, embed
from src.memory.span_segmenter import Span, segment_episode
from src.memory.span_dream_engine import calculate_span_salience
from src.memory.stm_context_builder import (
    render_current_turn,
    render_episode_block,
    render_rules_block,
)


DEDUP_THRESHOLD = 0.95
DEFAULT_D = 2
DEFAULT_BUDGET = 2500


@dataclass(frozen=True)
class DigestSpan:
    topic_id: str
    topic_label: str
    source_episode_id: str
    source_turn: int
    role: str
    span_start: int
    span_end: int
    text: str
    density: float


@dataclass
class DigestFrame:
    spans: list[DigestSpan] = field(default_factory=list)
    budget: int = DEFAULT_BUDGET
    built_at_turn: int = 0


@dataclass
class DigestRender:
    text: str
    chars: int
    span_count: int
    topics: list[str]
    containment_drops: list[dict]
    spans: list[dict]


class TopicDigest:
    def __init__(
        self,
        conn,
        embedding_provider=None,
        spans_per_topic: int = DEFAULT_D,
        budget: int = DEFAULT_BUDGET,
    ):
        if spans_per_topic < 1:
            raise ValueError("Digest d must be at least one")
        if budget < len("<topic_digest></topic_digest>"):
            raise ValueError("Digest budget is too small for its frame")
        self._conn = conn
        self._embedding_provider = embedding_provider or embed
        self.spans_per_topic = spans_per_topic
        self.budget = budget
        self.frame = DigestFrame(budget=budget)

    def rebuild(
        self, turn_number: int, through_turn: int | None = None
    ) -> DigestFrame:
        candidates: dict[str, list[DigestSpan]] = {}
        for row in get_all_episodes_with_embeddings(self._conn):
            if through_turn is not None and int(row["turn_number"]) > through_turn:
                continue
            topic_id = str(row.get("topic_id") or "")
            if not topic_id:
                continue
            episode = dict(row)
            episode["text"] = (
                f"User: {episode['user_message']}\n"
                f"Assistant: {episode['assistant_message']}"
            )
            for span in segment_episode(episode):
                if not span.eligible:
                    continue
                _, density, _ = calculate_span_salience(span)
                digest_span = DigestSpan(
                    topic_id=topic_id,
                    topic_label=str(row.get("topic_label") or topic_id),
                    source_episode_id=str(row["id"]),
                    source_turn=int(row["turn_number"]),
                    role=span.role,
                    span_start=span.start,
                    span_end=span.end,
                    text=span.text,
                    density=float(density),
                )
                candidates.setdefault(topic_id, []).append(digest_span)

        selected_by_topic = {}
        for topic_id, topic_candidates in candidates.items():
            survivors: list[tuple[DigestSpan, np.ndarray]] = []
            for span in sorted(topic_candidates, key=self._rank_key):
                vector = self._embedding_provider(span.text)
                if any(
                    cosine_similarity(vector, survivor_vector)
                    >= DEDUP_THRESHOLD
                    for _, survivor_vector in survivors
                ):
                    continue
                survivors.append((span, vector))
                if len(survivors) == self.spans_per_topic:
                    break
            selected_by_topic[topic_id] = [
                span for span, _ in survivors
            ]
        selected = self._fit_budget(selected_by_topic)
        self.frame = DigestFrame(
            spans=selected,
            budget=self.budget,
            built_at_turn=turn_number,
        )
        return self.frame

    def render(self, stm_episode_ids: set[str] | None = None) -> DigestRender:
        contained = set(stm_episode_ids or set())
        kept = []
        drops = []
        for span in self.frame.spans:
            if span.source_episode_id in contained:
                drops.append(self._span_dict(span))
            else:
                kept.append(span)
        text = render_topic_digest(kept)
        if len(text) > self.budget:
            raise AssertionError(
                f"Serialized digest cost {len(text)} exceeds {self.budget}"
            )
        return DigestRender(
            text=text,
            chars=len(text),
            span_count=len(kept),
            topics=sorted({span.topic_label for span in kept}),
            containment_drops=drops,
            spans=[self._span_dict(span) for span in kept],
        )

    def _fit_budget(
        self, selected_by_topic: dict[str, list[DigestSpan]]
    ) -> list[DigestSpan]:
        working = {
            topic_id: list(spans)
            for topic_id, spans in selected_by_topic.items()
            if spans
        }
        while len(render_topic_digest(self._flatten(working))) > self.budget:
            reducible = [
                topic_id
                for topic_id, spans in working.items()
                if len(spans) > 1
            ]
            if not reducible:
                break
            largest = max(len(working[topic_id]) for topic_id in reducible)
            for topic_id in sorted(reducible):
                if len(working[topic_id]) != largest:
                    continue
                working[topic_id].pop()
                if len(render_topic_digest(self._flatten(working))) <= self.budget:
                    return self._flatten(working)

        spans = self._flatten(working)
        if len(render_topic_digest(spans)) <= self.budget:
            return spans
        return self._truncate_floor(spans)

    def _truncate_floor(self, spans: list[DigestSpan]) -> list[DigestSpan]:
        if not spans:
            return []
        overhead = len(render_topic_digest([
            DigestSpan(**{**self._span_dict(span), "text": ""})
            for span in spans
        ]))
        available = self.budget - overhead
        if available < 3 * len(spans):
            raise ValueError(
                "Digest budget cannot preserve one ellipsis-marked span per topic"
            )
        allocations = [available // len(spans)] * len(spans)
        for index in range(available % len(spans)):
            allocations[index] += 1
        truncated = [
            DigestSpan(
                **{
                    **self._span_dict(span),
                    "text": _truncate_at_word(span.text, allocations[index]),
                }
            )
            for index, span in enumerate(spans)
        ]
        while len(render_topic_digest(truncated)) > self.budget:
            index = max(range(len(allocations)), key=allocations.__getitem__)
            allocations[index] -= 1
            span = spans[index]
            truncated[index] = DigestSpan(
                **{
                    **self._span_dict(span),
                    "text": _truncate_at_word(span.text, allocations[index]),
                }
            )
        return truncated

    def _deduplicate(
        self, candidates: list[tuple[DigestSpan, np.ndarray]]
    ) -> list[tuple[DigestSpan, np.ndarray]]:
        survivors = []
        for candidate in sorted(
            candidates, key=lambda item: self._rank_key(item[0])
        ):
            if any(
                cosine_similarity(candidate[1], survivor[1])
                >= DEDUP_THRESHOLD
                for survivor in survivors
            ):
                continue
            survivors.append(candidate)
        return survivors

    @staticmethod
    def _rank_key(span: DigestSpan) -> tuple:
        return (
            -span.density,
            span.source_turn,
            span.source_episode_id,
            span.span_start,
            span.span_end,
        )

    @staticmethod
    def _flatten(
        selected_by_topic: dict[str, list[DigestSpan]]
    ) -> list[DigestSpan]:
        return [
            span
            for topic_id in sorted(selected_by_topic)
            for span in selected_by_topic[topic_id]
        ]

    @staticmethod
    def _span_dict(span: DigestSpan) -> dict:
        return {
            "topic_id": span.topic_id,
            "topic_label": span.topic_label,
            "source_episode_id": span.source_episode_id,
            "source_turn": span.source_turn,
            "role": span.role,
            "span_start": span.span_start,
            "span_end": span.span_end,
            "text": span.text,
            "density": span.density,
        }


class DigestContextRenderer:
    def __init__(self, digest: TopicDigest):
        self.digest = digest
        self.last_render = DigestRender("", 0, 0, [], [], [])

    def __call__(
        self,
        system_prompt: str,
        current_user_message: str,
        rule_episodes: list | None = None,
        recent_episodes: list | None = None,
        stm_episodes: list | None = None,
    ) -> str:
        recent = list(recent_episodes or [])
        stm = list(stm_episodes or [])
        self.last_render = self.digest.render({
            str(episode["id"]) for episode in (*recent, *stm)
        })
        blocks = [
            render_rules_block(list(rule_episodes or [])),
            self.last_render.text,
            render_episode_block("recent_context", recent, "recent"),
            render_episode_block("retrieved_stm", stm, "stm"),
            render_current_turn(current_user_message),
        ]
        return "\n\n".join([system_prompt, *blocks])


def render_topic_digest(spans: list[DigestSpan]) -> str:
    if not spans:
        return "<topic_digest/>"
    by_topic: dict[tuple[str, str], list[DigestSpan]] = {}
    for span in spans:
        by_topic.setdefault(
            (span.topic_id, span.topic_label), []
        ).append(span)
    lines = ["<topic_digest>"]
    for (topic_id, topic_label), topic_spans in sorted(
        by_topic.items(), key=lambda item: item[0]
    ):
        lines.append(
            f'  <topic id="{_attribute(topic_id)}" '
            f'name="{_attribute(topic_label)}">'
        )
        for span in topic_spans:
            lines.append(
                f'    <span source_episode_id="{_attribute(span.source_episode_id)}" '
                f'source_turn="{span.source_turn}" role="{_attribute(span.role)}" '
                f'span_start="{span.span_start}" span_end="{span.span_end}" '
                f'density="{span.density:.6f}">{_text(span.text)}</span>'
            )
        lines.append("  </topic>")
    lines.append("</topic_digest>")
    return "\n".join(lines)


def _truncate_at_word(text: str, limit: int) -> str:
    marker = "..."
    if len(text) <= limit:
        return text
    if limit <= len(marker):
        return marker[:limit]
    prefix = text[: limit - len(marker)].rstrip()
    boundary = prefix.rfind(" ")
    if boundary > 0:
        prefix = prefix[:boundary].rstrip()
    return f"{prefix}{marker}"


def _attribute(value) -> str:
    return escape(str(value), quote=True)


def _text(value) -> str:
    return escape(str(value), quote=False)
