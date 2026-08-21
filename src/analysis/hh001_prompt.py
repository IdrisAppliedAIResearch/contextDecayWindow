"""Prompt rendering for the reader and the judge.

One template, byte-identical across arms; only the memory block differs
(``HH_001_DEVELOPMENT_PLAN.md`` §4). Every rendered prompt is hashed before
inference, so a template that drifted between arms is caught by digest rather
than by reading.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Sequence

READER_TEMPLATE = """\
You are answering a question about a conversation between two people.

{memory_section}Question: {question}

Answer with the fact itself, as briefly as the question allows. Do not explain \
your reasoning. If the material above does not contain the answer, reply \
exactly: I don't know.

Answer:"""

MEMORY_SECTION = """\
Here is what you remember of the conversation:

{block}

"""

EMPTY_MEMORY_SECTION = """\
You have no record of the conversation.

"""

JUDGE_TEMPLATE = """\
You are grading one answer against a reference answer.

Question: {question}
Reference answer: {gold}
Answer to grade: {answer}

The answer is CORRECT if it states the same fact as the reference answer, even \
in different words, a different format, or with extra detail. The answer is \
INCORRECT if it states a different fact, contradicts the reference, refuses, \
says it does not know, or is empty.

Reply with exactly two lines:
VERDICT: CORRECT or INCORRECT
REASON: one sentence

VERDICT:"""


class HH001PromptError(RuntimeError):
    pass


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_reader_prompt(question: str, block: str) -> str:
    """Render the reader prompt.

    The A0 arm gets an explicit "you have no record" section rather than a
    silently missing one, so the template's shape is identical across arms and
    the floor arm is not accidentally given a different task.
    """
    if not question.strip():
        raise HH001PromptError("Question is empty")
    section = (
        MEMORY_SECTION.format(block=block) if block.strip() else EMPTY_MEMORY_SECTION
    )
    return READER_TEMPLATE.format(memory_section=section, question=question)


def render_judge_prompt(question: str, gold: str, answer: str) -> str:
    return JUDGE_TEMPLATE.format(
        question=question,
        gold=gold,
        answer=answer.strip() or "(the model returned nothing)",
    )


def parse_judge_verdict(raw: str) -> tuple[bool, str]:
    """Read a verdict out of the judge's reply.

    An unparseable reply raises rather than defaulting. A default would be a
    silent vote, and a silent vote in a two-arm contrast is a thumb on the
    scale in whichever direction the default happens to point.
    """
    text = (raw or "").strip()
    if not text:
        raise HH001PromptError("Judge returned nothing")
    upper = text.upper()
    reason = ""
    for line in text.splitlines():
        if line.strip().upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()
            break
    head = upper.split("REASON:", 1)[0]
    has_correct = "CORRECT" in head and "INCORRECT" not in head
    has_incorrect = "INCORRECT" in head
    if has_incorrect and not has_correct:
        return False, reason
    if has_correct and not has_incorrect:
        return True, reason
    raise HH001PromptError(f"Judge verdict is not parseable: {text[:200]!r}")


@dataclass(frozen=True)
class TemplateManifest:
    reader_template_sha256: str
    judge_template_sha256: str
    memory_section_sha256: str
    empty_memory_section_sha256: str

    def as_dict(self) -> dict[str, str]:
        return {
            "reader_template_sha256": self.reader_template_sha256,
            "judge_template_sha256": self.judge_template_sha256,
            "memory_section_sha256": self.memory_section_sha256,
            "empty_memory_section_sha256": self.empty_memory_section_sha256,
        }


def template_manifest() -> TemplateManifest:
    return TemplateManifest(
        reader_template_sha256=digest(READER_TEMPLATE),
        judge_template_sha256=digest(JUDGE_TEMPLATE),
        memory_section_sha256=digest(MEMORY_SECTION),
        empty_memory_section_sha256=digest(EMPTY_MEMORY_SECTION),
    )


def blinded_surface(
    answers: Sequence[dict[str, Any]], seed: str = "5005"
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Strip arm identity and shuffle, returning the surface and a sealed map.

    The judge sees question, gold and answer text. It never sees the arm, the
    memory block, or the replicate index. Ordering is a seeded shuffle over the
    whole pooled set, so an arm cannot be inferred from position either.
    """
    surface: list[dict[str, Any]] = []
    mapping: dict[str, dict[str, Any]] = {}
    for row in answers:
        for field in ("comparison_key", "arm", "replicate", "question", "gold", "answer"):
            if field not in row:
                raise HH001PromptError(f"Answer row is missing {field!r}")
        blind_id = hashlib.sha256(
            "\0".join(
                (
                    seed,
                    "hh001-blind-v1",
                    row["comparison_key"],
                    row["arm"],
                    str(row["replicate"]),
                )
            ).encode("utf-8")
        ).hexdigest()
        if blind_id in mapping:
            raise HH001PromptError("Blind id collision")
        surface.append(
            {
                "blind_id": blind_id,
                "question": row["question"],
                "gold": row["gold"],
                "answer": row["answer"],
            }
        )
        mapping[blind_id] = {
            "comparison_key": row["comparison_key"],
            "arm": row["arm"],
            "replicate": row["replicate"],
        }
    surface.sort(key=lambda entry: entry["blind_id"])
    return surface, mapping


__all__ = [
    "EMPTY_MEMORY_SECTION",
    "HH001PromptError",
    "JUDGE_TEMPLATE",
    "MEMORY_SECTION",
    "READER_TEMPLATE",
    "TemplateManifest",
    "blinded_surface",
    "digest",
    "parse_judge_verdict",
    "render_judge_prompt",
    "render_reader_prompt",
    "template_manifest",
]
