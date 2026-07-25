"""Density-normalized, source-aware span selection for Study 006.

Study 005 ranked whole turn episodes by absolute entity+numeric counts. Long
generated answers accumulated score simply by being long, so concise user-planted
facts ranked as low as 28th and only two of eleven were selected. This engine
changes three things and nothing else:

1. **Granularity** - selection operates on sentence-level spans, not whole turns.
2. **Normalization** - salience is entity/numeric content *per word*, not absolute.
3. **Source awareness** - user spans carry 1.5x weight, assistant spans 1.0x.

Everything else is carried from Study 005 unchanged: the x2 numeric weight, the
0.95 cosine dedup threshold, the per-topic cap of 3, the minimum outgoing episode
count, the `present_no_salient_fact` marker path, and above all the extractive
constraint - this pass makes **zero inference-model calls**, asserted
programmatically, so fabrication remains structurally impossible.
"""

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from src.db.episode import get_episode_by_id, get_episodes_by_topic
from src.db.topic import get_topic_by_id
from src.embeddings.provider import cosine_similarity
from src.memory.distilled_ltm_store import (
    assert_span_record_faithful,
    get_undreamed_episodes_by_topic,
    log_dream_event,
    log_span_inventory,
    mark_episodes_dreamed,
    write_distilled_span_record,
    write_no_salient_fact_marker,
)
from src.memory.span_segmenter import (
    ROLE_ASSISTANT,
    ROLE_USER,
    Span,
    extractor_name,
    segment_episode,
    segmenter_name,
)


SOURCE_WEIGHTS = {
    ROLE_USER: 1.5,
    ROLE_ASSISTANT: 1.0,
}


def source_weight(role: str) -> float:
    """User content is ground truth; model output is derivative.

    A tiebreaker-scale weight, not a domination weight - a genuinely dense
    assistant span can still outrank a sparse user span.
    """
    return SOURCE_WEIGHTS.get(role, 1.0)


def calculate_span_salience(span: Span) -> tuple[int, float, float]:
    """Return (base, density, salience) for one span.

        base(s)     = named_entity_count(s) + 2 x numeric_token_count(s)
        density(s)  = base(s) / word_count(s)
        salience(s) = density(s) x source_weight(role)
    """
    base = span.named_entities + 2 * span.numeric_tokens
    density = base / span.word_count if span.word_count else 0.0
    return base, density, density * source_weight(span.role)


@dataclass
class SpanCandidate:
    span: Span
    episode: dict
    base: int
    density: float
    salience: float
    embedding: np.ndarray | None = None
    collapsed_span_keys: list[tuple] = field(default_factory=list)
    collapsed_episode_ids: list[str] = field(default_factory=list)
    source_episode_ids: list[str] = field(default_factory=list)
    source_turns: list[int] = field(default_factory=list)

    @property
    def key(self) -> tuple:
        return (self.span.episode_id, self.span.start, self.span.end)


@dataclass
class SpanDreamSummary:
    turn: int
    topic_id: str
    topic: str
    event_type: str
    segmenter: str
    extractor: str
    episodes_evaluated: int
    spans_evaluated: int
    spans_eligible: int
    survivors: int
    records_written: int
    marker_written: bool
    duplicates_collapsed: int
    inference_calls: int
    candidates: list[SpanCandidate]
    selected: list[SpanCandidate]
    distilled_ids: list[str]


class SpanDreamEngine:
    """Select verbatim sentence spans without invoking the inference model."""

    MINIMUM_OUTGOING_EPISODES = 3
    DEDUP_THRESHOLD = 0.95
    PER_TOPIC_CAP = 3
    SALIENCE_FLOOR = 0.15
    END_OF_SESSION_FLUSH_TURN = 111

    def __init__(
        self,
        conn,
        inference_call_count: Callable[[], int] | None = None,
        embed_fn: Callable[[str], np.ndarray] | None = None,
        salience_floor: float | None = None,
    ):
        self._conn = conn
        self._inference_call_count = inference_call_count or (lambda: 0)
        self._embed_fn = embed_fn
        self.salience_floor = (
            self.SALIENCE_FLOOR if salience_floor is None else salience_floor
        )

    def _embed(self, text: str) -> np.ndarray:
        if self._embed_fn is not None:
            return np.asarray(self._embed_fn(text), dtype=np.float32)
        from src.embeddings.provider import embed

        return np.asarray(embed(text), dtype=np.float32)

    # --- entry points ----------------------------------------------------

    def process_transition(
        self,
        previous_episode_id: str | None,
        current_episode_id: str,
        current_turn: int,
    ) -> SpanDreamSummary | None:
        if previous_episode_id is None:
            return None
        previous = get_episode_by_id(self._conn, previous_episode_id)
        current = get_episode_by_id(self._conn, current_episode_id)
        if previous is None or current is None:
            raise ValueError("Cannot dream an episode missing from the raw store")
        if previous["topic_id"] == current["topic_id"]:
            return None
        return self._process_topic(
            previous["topic_id"],
            current_turn,
            event_type="transition",
        )

    def process_flush(
        self,
        active_episode_id: str,
        current_turn: int,
        expected_flush_turn: int = END_OF_SESSION_FLUSH_TURN,
    ) -> SpanDreamSummary | None:
        if current_turn != expected_flush_turn:
            raise ValueError(
                f"End-of-session dream flush must run at turn "
                f"{expected_flush_turn}, got {current_turn}"
            )
        active = get_episode_by_id(self._conn, active_episode_id)
        if active is None:
            raise ValueError("Cannot flush an episode missing from the raw store")
        return self._process_topic(
            active["topic_id"],
            current_turn,
            event_type="end_of_session_flush",
        )

    # --- core ------------------------------------------------------------

    def build_candidates(
        self,
        episodes: list[dict],
    ) -> tuple[list[SpanCandidate], list[Span], int]:
        """Segment and score. Returns (eligible candidates, all spans, count)."""
        all_spans: list[Span] = []
        candidates: list[SpanCandidate] = []
        for episode in episodes:
            spans = segment_episode(episode)
            all_spans.extend(spans)
            for span in spans:
                if not span.eligible:
                    continue
                base, density, salience = calculate_span_salience(span)
                candidates.append(
                    SpanCandidate(
                        span=span,
                        episode=episode,
                        base=base,
                        density=density,
                        salience=salience,
                        source_episode_ids=[span.episode_id],
                        source_turns=[span.turn_number],
                    )
                )
        return candidates, all_spans, len(all_spans)

    def _process_topic(
        self,
        topic_id: str,
        current_turn: int,
        event_type: str,
    ) -> SpanDreamSummary | None:
        topic = get_topic_by_id(self._conn, topic_id)
        if topic is None:
            raise ValueError("Canonical dream topic is missing")
        if (
            len(get_episodes_by_topic(self._conn, topic_id))
            < self.MINIMUM_OUTGOING_EPISODES
        ):
            return None

        snapshot = get_undreamed_episodes_by_topic(self._conn, topic_id)
        calls_before = self._inference_call_count()

        candidates, all_spans, spans_evaluated = self.build_candidates(snapshot)
        for candidate in candidates:
            candidate.embedding = self._embed(candidate.span.text)
        survivors = self.deduplicate(candidates)
        selected = self.select(survivors)

        distilled_ids: list[str] = []
        marker_written = False
        selected_keys = {candidate.key for candidate in selected}
        collapsed_into = {
            key: survivor.key
            for survivor in survivors
            for key in survivor.collapsed_span_keys
        }

        with self._conn:
            for candidate in selected:
                distilled_id = write_distilled_span_record(
                    self._conn,
                    span_text=candidate.span.text,
                    source_episode=candidate.episode,
                    topic_id=topic_id,
                    topic_label=topic["label"],
                    role=candidate.span.role,
                    span_start=candidate.span.start,
                    span_end=candidate.span.end,
                    word_count=candidate.span.word_count,
                    named_entities=candidate.span.named_entities,
                    numeric_tokens=candidate.span.numeric_tokens,
                    base=candidate.base,
                    density=candidate.density,
                    salience_score=candidate.salience,
                    segmenter=segmenter_name(),
                    embedding=candidate.embedding,
                    source_episode_ids=candidate.source_episode_ids,
                    source_turns=candidate.source_turns,
                    collapsed_episode_ids=candidate.collapsed_episode_ids,
                    dream_event=current_turn,
                    event_type=event_type,
                )
                assert_span_record_faithful(self._conn, distilled_id)
                distilled_ids.append(distilled_id)

            if snapshot and not selected:
                marker_episode, marker_base = self._marker_source(
                    snapshot, survivors, all_spans
                )
                distilled_ids.append(
                    write_no_salient_fact_marker(
                        self._conn,
                        source_episode=marker_episode,
                        topic_id=topic_id,
                        topic_label=topic["label"],
                        salience=marker_base,
                        dream_event=current_turn,
                        event_type=event_type,
                    )
                )
                marker_written = True

            log_span_inventory(
                self._conn,
                dream_event=current_turn,
                topic_id=topic_id,
                topic_label=topic["label"],
                rows=self._inventory_rows(
                    all_spans, selected_keys, collapsed_into
                ),
            )
            mark_episodes_dreamed(
                self._conn,
                [episode["id"] for episode in snapshot],
            )

            inference_calls = self._inference_call_count() - calls_before
            if inference_calls:
                raise AssertionError(
                    "Extractive dream pass invoked the inference model"
                )
            log_dream_event(
                self._conn,
                turn=current_turn,
                topic_id=topic_id,
                topic_label=topic["label"],
                event_type=event_type,
                extractor=extractor_name(),
                episodes_evaluated=len(snapshot),
                survivors=len(survivors),
                records_written=len(selected),
                marker_written=marker_written,
                duplicates_collapsed=len(candidates) - len(survivors),
                inference_calls=inference_calls,
                segmenter=segmenter_name(),
                spans_evaluated=spans_evaluated,
                spans_eligible=len(candidates),
                salience_floor=self.salience_floor,
            )

        return SpanDreamSummary(
            turn=current_turn,
            topic_id=topic_id,
            topic=topic["label"],
            event_type=event_type,
            segmenter=segmenter_name(),
            extractor=extractor_name(),
            episodes_evaluated=len(snapshot),
            spans_evaluated=spans_evaluated,
            spans_eligible=len(candidates),
            survivors=len(survivors),
            records_written=len(selected),
            marker_written=marker_written,
            duplicates_collapsed=len(candidates) - len(survivors),
            inference_calls=0,
            candidates=candidates,
            selected=selected,
            distilled_ids=distilled_ids,
        )

    def _marker_source(
        self,
        snapshot: list[dict],
        survivors: list[SpanCandidate],
        all_spans: list[Span],
    ) -> tuple[dict, int]:
        """Pick the episode a `present_no_salient_fact` marker should reference.

        Every processed topic must yield either records or a marker - that
        guarantee is carried from Study 005 and is what keeps a silently empty
        topic from being indistinguishable from an absent one. The marker points
        at the highest-salience span available, preferring surviving candidates,
        then any segmented span even if it failed eligibility, and finally the
        first episode when the topic produced no spans at all.
        """
        if survivors:
            best = min(survivors, key=self._rank_key)
            return best.episode, best.base
        episodes_by_id = {episode["id"]: episode for episode in snapshot}
        if all_spans:
            best_span = max(
                all_spans,
                key=lambda span: (
                    calculate_span_salience(span)[2],
                    -span.turn_number,
                    -span.start,
                ),
            )
            episode = episodes_by_id.get(best_span.episode_id, snapshot[0])
            return episode, calculate_span_salience(best_span)[0]
        return snapshot[0], 0

    def _inventory_rows(
        self,
        all_spans: list[Span],
        selected_keys: set,
        collapsed_into: dict,
    ) -> list[dict]:
        rows = []
        for span in all_spans:
            base, density, salience = calculate_span_salience(span)
            key = (span.episode_id, span.start, span.end)
            survivor = collapsed_into.get(key)
            rows.append(
                {
                    "episode_id": span.episode_id,
                    "turn_number": span.turn_number,
                    "role": span.role,
                    "span_start": span.start,
                    "span_end": span.end,
                    "text": span.text,
                    "word_count": span.word_count,
                    "named_entities": span.named_entities,
                    "numeric_tokens": span.numeric_tokens,
                    "base": base,
                    "density": density,
                    "salience_score": salience,
                    "eligible": span.eligible,
                    "rejection_reason": span.rejection_reason,
                    "selected": key in selected_keys,
                    "collapsed_into": (
                        f"{survivor[0]}:{survivor[1]}:{survivor[2]}"
                        if survivor
                        else None
                    ),
                }
            )
        return rows

    def deduplicate(
        self,
        candidates: list[SpanCandidate],
    ) -> list[SpanCandidate]:
        """Collapse pairwise cosine >= 0.95, keeping the higher-salience member."""
        if not candidates:
            return []
        parents = list(range(len(candidates)))

        def find(index: int) -> int:
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parents[right_root] = left_root

        for left in range(len(candidates)):
            for right in range(left + 1, len(candidates)):
                if (
                    cosine_similarity(
                        candidates[left].embedding,
                        candidates[right].embedding,
                    )
                    >= self.DEDUP_THRESHOLD
                ):
                    union(left, right)

        components: dict[int, list[SpanCandidate]] = {}
        for index, candidate in enumerate(candidates):
            components.setdefault(find(index), []).append(candidate)

        survivors = []
        for members in components.values():
            ordered = sorted(members, key=self._rank_key)
            survivor = ordered[0]
            collapsed = ordered[1:]
            survivor.collapsed_span_keys = [item.key for item in collapsed]
            survivor.collapsed_episode_ids = [
                item.span.episode_id for item in collapsed
            ]
            survivor.source_episode_ids = [
                survivor.span.episode_id,
                *survivor.collapsed_episode_ids,
            ]
            survivor.source_turns = [
                survivor.span.turn_number,
                *(item.span.turn_number for item in collapsed),
            ]
            survivors.append(survivor)
        return sorted(survivors, key=self._rank_key)

    def select(self, survivors: list[SpanCandidate]) -> list[SpanCandidate]:
        """Rank by salience, cap at C, then apply the coverage floor.

        Per the pre-registration: if the topic's top span clears F the selected
        records are written; if *no* span clears F the caller writes a single
        marker instead. A sub-floor span is never promoted to satisfy coverage.
        """
        if not survivors:
            return []
        ranked = sorted(survivors, key=self._rank_key)
        if ranked[0].salience < self.salience_floor:
            return []
        return ranked[: self.PER_TOPIC_CAP]

    @staticmethod
    def _rank_key(candidate: SpanCandidate) -> tuple:
        """Deterministic ordering: salience desc, then earliest, then offsets."""
        return (
            -candidate.salience,
            candidate.span.turn_number,
            str(candidate.span.episode_id),
            candidate.span.start,
            candidate.span.end,
        )
