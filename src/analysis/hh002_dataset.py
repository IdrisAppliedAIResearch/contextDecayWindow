"""LoCoMo in the shape the paper-era Mem0 harness reads.

The published table (arXiv:2504.19413 Table 2) was produced by the ``evaluation/``
tree of ``mem0ai/mem0``, retired in June 2026 and read here at commit
``7b3abd06``.  Its RAG and full-context arms read ``dataset/locomo10_rag.json``,
a file distributed through the authors' Google Drive rather than through git.

Rather than fetch an unversioned artifact, this module *derives* that shape from
the corpus this programme already locked by SHA-256, and pins the derivation to
the conventions the harness itself uses:

* ``src/rag.py::clean_chat_history`` renders one turn as
  ``f"{timestamp} | {speaker}: {text}\\n"``, so a turn needs exactly a
  timestamp, a speaker and a text.
* Every arm in that tree - ``src/rag.py``, ``src/memzero/add.py``,
  ``src/zep/add.py`` - reads ``chat['text']`` and nothing else.  LoCoMo's
  ``img_url`` and ``blip_caption`` fields are not read by any of them, so they
  are not rendered here either.
* Sessions carry their date in a sibling ``session_N_date_time`` key, which is
  the per-turn timestamp for every turn in that session.

The result is a file whose *content* is derived from a hashed source and whose
*shape* is fixed by the harness's own reader.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from analysis.nf004_measurement import (
    DATASET_BYTES,
    DATASET_SHA256,
    sha256_file,
)

_SESSION = re.compile(r"session_(\d+)")

#: LoCoMo's adversarial class.  ``evaluation/evals.py:22`` and
#: ``evaluation/metrics/llm_judge.py:86`` both skip it, so no category-5 record
#: contributes to any number in the published table.  Records in this class
#: carry ``adversarial_answer`` and no ``answer``.
ADVERSARIAL_CATEGORY = 5


class HH002DatasetError(RuntimeError):
    pass


@dataclass(frozen=True)
class Turn:
    """One conversational turn, carrying only what the harness renders."""

    timestamp: str
    speaker: str
    text: str
    dia_id: str
    session_id: str
    session_order: int

    def as_harness_turn(self) -> dict[str, str]:
        """The three keys ``clean_chat_history`` reads."""
        return {
            "timestamp": self.timestamp,
            "speaker": self.speaker,
            "text": self.text,
        }


@dataclass(frozen=True)
class Question:
    question: str
    answer: str
    category: int
    evidence: tuple[str, ...]
    source_index: int

    @property
    def scored(self) -> bool:
        """Whether this record reaches the published metric at all."""
        return self.category != ADVERSARIAL_CATEGORY


@dataclass(frozen=True)
class Conversation:
    sample_id: str
    speaker_a: str
    speaker_b: str
    turns: tuple[Turn, ...]
    questions: tuple[Question, ...]

    @property
    def scored_questions(self) -> tuple[Question, ...]:
        return tuple(q for q in self.questions if q.scored)

    def clean_chat_history(self) -> str:
        """Byte-for-byte ``src/rag.py::clean_chat_history``.

        Reproduced rather than imported so the string the reader sees is
        defined in this repository and can be hashed here.  The trailing
        newline after the final turn is theirs and is kept.
        """
        rendered = ""
        for turn in self.turns:
            rendered += f"{turn.timestamp} | {turn.speaker}: {turn.text}\n"
        return rendered


def _session_keys(conversation: dict[str, Any]) -> list[str]:
    """Session keys in numeric order.

    ``conv-41`` has 32 sessions, so lexical ordering would place
    ``session_10`` before ``session_2`` and silently reorder a third of the
    corpus.  Sorting is numeric for that reason.
    """
    found: list[tuple[int, str]] = []
    for key in conversation:
        match = _SESSION.fullmatch(key)
        if match:
            found.append((int(match.group(1)), key))
    return [key for _, key in sorted(found)]


def load_corpus(dataset_path: Path) -> tuple[Conversation, ...]:
    """Read LoCoMo, verifying it against this programme's lock first."""
    if dataset_path.stat().st_size != DATASET_BYTES:
        raise HH002DatasetError(
            f"LoCoMo byte count differs from the lock: "
            f"{dataset_path.stat().st_size} != {DATASET_BYTES}"
        )
    digest = sha256_file(dataset_path)
    if digest != DATASET_SHA256:
        raise HH002DatasetError(
            f"LoCoMo SHA-256 differs from the lock: {digest} != {DATASET_SHA256}"
        )

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    conversations: list[Conversation] = []
    for row in raw:
        sample_id = str(row["sample_id"])
        source = row["conversation"]
        turns: list[Turn] = []
        for session_order, session_id in enumerate(_session_keys(source)):
            date_key = f"{session_id}_date_time"
            if date_key not in source:
                raise HH002DatasetError(f"{sample_id}: {session_id} has no date")
            timestamp = str(source[date_key])
            for turn in source[session_id]:
                turns.append(
                    Turn(
                        timestamp=timestamp,
                        speaker=str(turn["speaker"]),
                        text=str(turn["text"]),
                        dia_id=str(turn["dia_id"]),
                        session_id=session_id,
                        session_order=session_order,
                    )
                )

        questions: list[Question] = []
        for source_index, qa in enumerate(row["qa"]):
            category = int(qa["category"])
            # Category 5 records answer with ``adversarial_answer``; the
            # harness reads ``answer`` and would see "" here.  It never
            # scores them, so the empty string is faithful and inert.
            answer = qa.get("answer", "")
            questions.append(
                Question(
                    question=str(qa["question"]),
                    answer=str(answer),
                    category=category,
                    evidence=tuple(str(e) for e in qa.get("evidence", ())),
                    source_index=source_index,
                )
            )

        conversations.append(
            Conversation(
                sample_id=sample_id,
                speaker_a=str(source["speaker_a"]),
                speaker_b=str(source["speaker_b"]),
                turns=tuple(turns),
                questions=tuple(questions),
            )
        )

    conversations.sort(key=lambda c: c.sample_id)
    return tuple(conversations)


def as_harness_dataset(
    conversations: tuple[Conversation, ...]
) -> dict[str, dict[str, Any]]:
    """The exact JSON object ``RAGManager`` iterates over.

    ``rag.py`` does ``for key, value in data.items()`` then reads
    ``value["conversation"]`` and ``value["question"]``.
    """
    return {
        conversation.sample_id: {
            "conversation": [t.as_harness_turn() for t in conversation.turns],
            "question": [
                {
                    "question": q.question,
                    "answer": q.answer,
                    "category": q.category,
                    "evidence": list(q.evidence),
                }
                for q in conversation.questions
            ],
        }
        for conversation in conversations
    }


def iter_scored_items(
    conversations: tuple[Conversation, ...]
) -> Iterator[tuple[Conversation, Question]]:
    for conversation in conversations:
        for question in conversation.scored_questions:
            yield conversation, question


__all__ = [
    "ADVERSARIAL_CATEGORY",
    "Conversation",
    "HH002DatasetError",
    "Question",
    "Turn",
    "as_harness_dataset",
    "iter_scored_items",
    "load_corpus",
]
