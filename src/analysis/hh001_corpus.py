"""Corpus adaptation for the HH-001 development run.

NF-004 never needed gold answers: its endpoint was whether evidence text was
delivered, which is answerable from the evidence lists alone. HH-001's endpoint
is whether a reader answered correctly, so this module adds the answer side of
the corpus and the seeded subsample.

`analysis.nf004_measurement` and `analysis.nf004_mechanism` are carried
subsystems and are imported read-only. Nothing here modifies them.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from analysis.nf004_measurement import (
    BUDGET,
    DATASET_BYTES,
    DATASET_SHA256,
    DEVELOPMENT_IDS,
    HOLDOUT_IDS,
    ConversationRecord,
    QuestionRecord,
    adapt_split,
    sha256_file,
)

_SESSION = re.compile(r"session_(\d+)")

#: Category 5 is LoCoMo's adversarial class. Those records carry
#: ``adversarial_answer`` instead of ``answer``: the correct behaviour is a
#: refusal, not a string. They are excluded from the primary population and
#: reported as their own stratum. See ``HH_001_DEVELOPMENT_PLAN.md`` §3.1.
ADVERSARIAL_CATEGORY = 5


class HH001CorpusError(RuntimeError):
    pass


@dataclass(frozen=True)
class Item:
    """One scored question."""

    comparison_key: str
    sample_id: str
    source_index: int
    category: int
    question: str
    gold_answer: str
    answerable: bool
    evidence_dialogue_ids: tuple[str, ...]
    #: False when the source evidence list names a dialogue id the conversation
    #: does not contain. Six holdout records are malformed this way, which is
    #: how NF-004's 1,104 canonical records become its 1,098 primary ones.
    #: The judged endpoint does not need evidence, so these stay in the primary
    #: population here; only the availability secondary excludes them.
    evidence_complete: bool = True
    #: Where the answer lives in the conversation, as a fraction of its turns:
    #: 0.0 is the opening turn, 1.0 the final one. This is the long-horizon
    #: axis — an item whose evidence sits at 0.1 of a 680-turn conversation is
    #: the case a memory layer exists to handle, and accuracy against this is
    #: a different question from accuracy overall.
    evidence_depth: float | None = None
    conversation_turns: int = 0

    @property
    def stratum(self) -> str:
        return f"{self.sample_id}/{self.category}"

    @property
    def availability_scorable(self) -> bool:
        """Whether this item can join to NF-004's per-item availability rows."""
        return self.evidence_complete and bool(self.evidence_dialogue_ids)


@dataclass(frozen=True)
class Conversation:
    """One LoCoMo conversation, with the text every arm reads from."""

    sample_id: str
    record: ConversationRecord
    full_text: str
    turn_count: int

    @property
    def chars(self) -> int:
        return len(self.full_text)


def _digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _session_keys(conversation: dict[str, Any]) -> list[str]:
    found = [
        (int(match.group(1)), key)
        for key in conversation
        if (match := _SESSION.fullmatch(key))
    ]
    return [key for _, key in sorted(found)]


def _turn_positions(conversation: dict[str, Any]) -> dict[str, int]:
    """Global turn index for every dialogue id, in source order."""
    positions: dict[str, int] = {}
    index = 0
    for session_id in _session_keys(conversation):
        for turn in conversation[session_id]:
            positions[str(turn["dia_id"])] = index
            index += 1
    return positions


def _render_conversation(conversation: dict[str, Any]) -> tuple[str, int]:
    """Render a whole conversation exactly as the pair candidates render turns.

    The per-turn form is ``speaker: text``, matching
    ``nf004_measurement.adapt_split``. Keeping the two identical means the
    A1 ceiling and the A2 candidates differ only in *which* turns are present,
    never in how a turn is written.
    """
    lines: list[str] = []
    turns = 0
    for session_id in _session_keys(conversation):
        for turn in conversation[session_id]:
            lines.append(f"{turn['speaker']}: {turn['text']}")
            turns += 1
    return "\n".join(lines), turns


def verify_dataset(dataset_path: Path) -> str:
    """Re-check the corpus lock before anything reads it."""
    if not dataset_path.is_file():
        raise HH001CorpusError(f"LoCoMo dataset not found at {dataset_path}")
    if dataset_path.stat().st_size != DATASET_BYTES:
        raise HH001CorpusError("LoCoMo byte count differs from the corpus lock")
    digest = sha256_file(dataset_path)
    if digest != DATASET_SHA256:
        raise HH001CorpusError("LoCoMo SHA-256 differs from the corpus lock")
    return digest


def _gold_answer(qa: dict[str, Any]) -> tuple[str, bool]:
    """Return ``(gold, answerable)``.

    Six holdout answers are integers and two records carry both an ``answer``
    and an ``adversarial_answer``. An ``answer`` present wins: the record is
    answerable and that string is the gold.
    """
    if "answer" in qa:
        return str(qa["answer"]), True
    if "adversarial_answer" in qa:
        return str(qa["adversarial_answer"]), False
    raise HH001CorpusError("QA record carries neither answer nor adversarial_answer")


def load_corpus(
    dataset_path: Path, split_ids: frozenset[str] = HOLDOUT_IDS
) -> tuple[tuple[Conversation, ...], tuple[Item, ...]]:
    """Adapt one locked split into conversations and scored items."""
    verify_dataset(dataset_path)
    records = adapt_split(dataset_path, split_ids)
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    by_sample = {str(row["sample_id"]): row for row in raw}

    conversations: list[Conversation] = []
    items: list[Item] = []
    for record in records:
        row = by_sample[record.sample_id]
        full_text, turn_count = _render_conversation(row["conversation"])
        positions = _turn_positions(row["conversation"])
        conversations.append(
            Conversation(
                sample_id=record.sample_id,
                record=record,
                full_text=full_text,
                turn_count=turn_count,
            )
        )
        qa_rows = row["qa"]
        for question in record.questions:
            if question.duplicate_ordinal != 0:
                # NF-004's canonical de-duplication: only the first occurrence
                # of an identical QA record is a comparison key.
                continue
            qa = qa_rows[question.source_index]
            gold, answerable = _gold_answer(qa)
            # Earliest evidence turn: the oldest thing the reader must still
            # have. A later turn is easier for any recency-shaped layer.
            depth = None
            if question.resolved_dialogue_ids and turn_count > 1:
                earliest = min(
                    positions[d]
                    for d in question.resolved_dialogue_ids
                    if d in positions
                )
                depth = round(earliest / (turn_count - 1), 4)
            items.append(
                Item(
                    comparison_key=question.comparison_key,
                    sample_id=question.sample_id,
                    source_index=question.source_index,
                    category=int(question.category),
                    question=question.text,
                    gold_answer=gold,
                    answerable=answerable,
                    evidence_dialogue_ids=question.resolved_dialogue_ids,
                    evidence_complete=not question.unresolved_dialogue_ids,
                    evidence_depth=depth,
                    conversation_turns=turn_count,
                )
            )

    conversations.sort(key=lambda value: value.sample_id)
    items.sort(key=lambda value: (value.sample_id, value.source_index))
    return tuple(conversations), tuple(items)


def primary_population(items: Sequence[Item]) -> tuple[Item, ...]:
    """Answerable items only.

    ``AGENTS.md`` §7 forbids scoring an answerless item above zero. An
    adversarial record's correct behaviour is a refusal, which neither the
    containment endpoint nor a correctness rubric measures, so those records
    are reported as their own stratum rather than folded into the primary.
    """
    return tuple(item for item in items if item.answerable)


def adversarial_population(items: Sequence[Item]) -> tuple[Item, ...]:
    return tuple(item for item in items if not item.answerable)


def select_subsample(
    items: Sequence[Item], size: int, seed: str = "5005"
) -> tuple[Item, ...]:
    """Seeded stratified selection, proportional by conversation and category.

    Selection is a pure function of ``(seed, comparison_key)``, so it is stable
    across processes and cannot drift with dict ordering or file layout. Every
    exclusion is mechanical; no item is ever dropped by inspection.
    """
    if size < 0:
        raise HH001CorpusError("Subsample size must be non-negative")
    pool = list(items)
    if size >= len(pool):
        return tuple(sorted(pool, key=lambda item: item.comparison_key))

    strata: dict[str, list[Item]] = {}
    for item in pool:
        strata.setdefault(item.stratum, []).append(item)

    def rank(item: Item) -> str:
        return _digest(seed, "hh001-subsample-v1", item.comparison_key)

    for members in strata.values():
        members.sort(key=rank)

    # Largest-remainder allocation, so the sample's stratum shape matches the
    # population's rather than favouring whichever stratum is iterated first.
    total = len(pool)
    exact = {name: len(members) * size / total for name, members in strata.items()}
    floors = {name: int(value) for name, value in exact.items()}
    remaining = size - sum(floors.values())
    order = sorted(
        strata,
        key=lambda name: (-(exact[name] - floors[name]), name),
    )
    for name in order[:remaining]:
        floors[name] += 1

    chosen: list[Item] = []
    for name, members in strata.items():
        chosen.extend(members[: floors[name]])
    if len(chosen) != size:
        raise HH001CorpusError(
            f"Stratified allocation produced {len(chosen)} items, expected {size}"
        )
    return tuple(sorted(chosen, key=lambda item: item.comparison_key))


def subsample_manifest(
    items: Sequence[Item], size: int, seed: str = "5005"
) -> dict[str, Any]:
    chosen = select_subsample(items, size, seed)
    strata: dict[str, int] = {}
    for item in chosen:
        strata[item.stratum] = strata.get(item.stratum, 0) + 1
    return {
        "schema": "hh001-subsample-v1",
        "seed": seed,
        "dataset_sha256": DATASET_SHA256,
        "population": len(items),
        "size": len(chosen),
        "strata": dict(sorted(strata.items())),
        "comparison_keys": [item.comparison_key for item in chosen],
        "selection_digest": _digest(*(item.comparison_key for item in chosen)),
    }


__all__ = [
    "ADVERSARIAL_CATEGORY",
    "BUDGET",
    "Conversation",
    "DEVELOPMENT_IDS",
    "HOLDOUT_IDS",
    "HH001CorpusError",
    "Item",
    "adversarial_population",
    "load_corpus",
    "primary_population",
    "select_subsample",
    "subsample_manifest",
    "verify_dataset",
]
