"""Deterministic extractive dreaming for Study 005."""

import re
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from src.db.episode import get_episode_by_id
from src.db.topic import get_topic_by_id
from src.embeddings.provider import cosine_similarity
from src.memory.distilled_ltm_store import (
    assert_record_faithful,
    get_undreamed_episodes_by_topic,
    log_dream_event,
    mark_episodes_dreamed,
    write_distilled_record,
    write_no_salient_fact_marker,
)


_NUMBERED_LIST_MARKER = re.compile(r"(?m)^\s*\d+[.)]\s+")
_NUMERIC_TOKEN = re.compile(
    r"(?<!\d)(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?!\d)"
)
_CAPITALIZED_SEQUENCE = re.compile(
    r"\b(?:(?:Dr|Mr|Mrs|Ms|Prof)\.\s+)?"
    r"[A-ZÀ-ÖØ-Þ][\wÀ-ÖØ-öø-ÿ'’-]*"
    r"(?:\s+(?:(?:of|the|da|de|della|del|van|von)\s+)*"
    r"[A-ZÀ-ÖØ-Þ][\wÀ-ÖØ-öø-ÿ'’-]*)+"
)
_ENTITY_STOPLIST = {
    "assistant response",
    "technical specifications",
    "risk low",
    "risk medium",
    "risk high",
}


@dataclass
class DreamCandidate:
    episode: dict
    salience: int
    named_entities: int
    numeric_tokens: int
    collapsed_episode_ids: list[str] = field(default_factory=list)
    source_episode_ids: list[str] = field(default_factory=list)
    source_turns: list[int] = field(default_factory=list)


@dataclass
class DreamSummary:
    turn: int
    topic_id: str
    topic: str
    event_type: str
    extractor: str
    evaluated: int
    survivors: int
    records_written: int
    marker_written: bool
    duplicates_collapsed: int
    inference_calls: int
    candidates: list[DreamCandidate]
    selected: list[DreamCandidate]
    distilled_ids: list[str]


def count_numeric_tokens(text: str) -> int:
    """Count factual numeric tokens while ignoring numbered-list ordinals."""
    without_list_markers = _NUMBERED_LIST_MARKER.sub("", text)
    return len(_NUMERIC_TOKEN.findall(without_list_markers))


def count_named_entities_fallback(text: str) -> int:
    """Count deterministic capitalized multi-word entity sequences."""
    count = 0
    for match in _CAPITALIZED_SEQUENCE.finditer(text):
        normalized = " ".join(match.group(0).lower().split())
        if normalized in _ENTITY_STOPLIST:
            continue
        count += 1
    return count


def calculate_salience(text: str) -> tuple[int, int, int]:
    named_entities = count_named_entities_fallback(text)
    numeric_tokens = count_numeric_tokens(text)
    return (
        named_entities + 2 * numeric_tokens,
        named_entities,
        numeric_tokens,
    )


class DreamEngine:
    """Select verbatim topic records without invoking the inference model."""

    DEDUP_THRESHOLD = 0.95
    PER_TOPIC_CAP = 3
    SALIENCE_FLOOR = 2
    END_OF_SESSION_FLUSH_TURN = 111
    EXTRACTOR = "capitalized_sequence_fallback"

    def __init__(
        self,
        conn,
        inference_call_count: Callable[[], int] | None = None,
    ):
        self._conn = conn
        self._inference_call_count = inference_call_count or (lambda: 0)

    def process_transition(
        self,
        previous_episode_id: str | None,
        current_episode_id: str,
        current_turn: int,
    ) -> DreamSummary | None:
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
    ) -> DreamSummary:
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

    def _process_topic(
        self,
        topic_id: str,
        current_turn: int,
        event_type: str,
    ) -> DreamSummary:
        topic = get_topic_by_id(self._conn, topic_id)
        if topic is None:
            raise ValueError("Canonical dream topic is missing")
        snapshot = get_undreamed_episodes_by_topic(self._conn, topic_id)
        calls_before = self._inference_call_count()
        candidates = [self._score_episode(episode) for episode in snapshot]
        survivors = self._deduplicate(candidates)
        eligible = [
            candidate
            for candidate in survivors
            if candidate.salience >= self.SALIENCE_FLOOR
        ]
        selected = sorted(
            eligible,
            key=self._candidate_rank_key,
        )[: self.PER_TOPIC_CAP]

        distilled_ids: list[str] = []
        marker_written = False
        with self._conn:
            for candidate in selected:
                distilled_id = write_distilled_record(
                    self._conn,
                    source_episode=candidate.episode,
                    topic_id=topic_id,
                    topic_label=topic["label"],
                    source_episode_ids=candidate.source_episode_ids,
                    source_turns=candidate.source_turns,
                    collapsed_episode_ids=candidate.collapsed_episode_ids,
                    salience=candidate.salience,
                    dream_event=current_turn,
                    event_type=event_type,
                )
                assert_record_faithful(self._conn, distilled_id)
                distilled_ids.append(distilled_id)

            if candidates and not selected:
                best = min(survivors, key=self._candidate_rank_key)
                distilled_ids.append(
                    write_no_salient_fact_marker(
                        self._conn,
                        source_episode=best.episode,
                        topic_id=topic_id,
                        topic_label=topic["label"],
                        salience=best.salience,
                        dream_event=current_turn,
                        event_type=event_type,
                    )
                )
                marker_written = True

            mark_episodes_dreamed(
                self._conn,
                [episode["id"] for episode in snapshot],
            )
            calls_after = self._inference_call_count()
            inference_calls = calls_after - calls_before
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
                extractor=self.EXTRACTOR,
                episodes_evaluated=len(candidates),
                survivors=len(survivors),
                records_written=len(selected),
                marker_written=marker_written,
                duplicates_collapsed=len(candidates) - len(survivors),
                inference_calls=inference_calls,
            )

        return DreamSummary(
            turn=current_turn,
            topic_id=topic_id,
            topic=topic["label"],
            event_type=event_type,
            extractor=self.EXTRACTOR,
            evaluated=len(candidates),
            survivors=len(survivors),
            records_written=len(selected),
            marker_written=marker_written,
            duplicates_collapsed=len(candidates) - len(survivors),
            inference_calls=0,
            candidates=candidates,
            selected=selected,
            distilled_ids=distilled_ids,
        )

    @staticmethod
    def _score_episode(episode: dict) -> DreamCandidate:
        salience, named_entities, numeric_tokens = calculate_salience(
            episode["text"]
        )
        return DreamCandidate(
            episode=episode,
            salience=salience,
            named_entities=named_entities,
            numeric_tokens=numeric_tokens,
            source_episode_ids=[episode["id"]],
            source_turns=[episode["turn_number"]],
        )

    def _deduplicate(
        self,
        candidates: list[DreamCandidate],
    ) -> list[DreamCandidate]:
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

        embeddings = [
            np.frombuffer(
                candidate.episode["embedding"],
                dtype=np.float32,
            )
            for candidate in candidates
        ]
        for left in range(len(candidates)):
            for right in range(left + 1, len(candidates)):
                if (
                    cosine_similarity(embeddings[left], embeddings[right])
                    >= self.DEDUP_THRESHOLD
                ):
                    union(left, right)

        components: dict[int, list[DreamCandidate]] = {}
        for index, candidate in enumerate(candidates):
            components.setdefault(find(index), []).append(candidate)

        survivors = []
        for members in components.values():
            ordered = sorted(members, key=self._candidate_rank_key)
            survivor = ordered[0]
            collapsed = ordered[1:]
            survivor.collapsed_episode_ids = [
                item.episode["id"] for item in collapsed
            ]
            survivor.source_episode_ids = [
                survivor.episode["id"],
                *survivor.collapsed_episode_ids,
            ]
            survivor.source_turns = [
                survivor.episode["turn_number"],
                *(item.episode["turn_number"] for item in collapsed),
            ]
            survivors.append(survivor)
        return sorted(survivors, key=self._candidate_rank_key)

    @staticmethod
    def _candidate_rank_key(candidate: DreamCandidate) -> tuple:
        return (
            -candidate.salience,
            candidate.episode["turn_number"],
            str(candidate.episode["id"]),
        )
