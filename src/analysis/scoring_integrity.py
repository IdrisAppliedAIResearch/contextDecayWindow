from __future__ import annotations

import re
from dataclasses import dataclass


class ScoringIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class Completeness:
    scoreable_text: str
    no_answer: bool
    unclosed_reasoning: bool
    truncated: bool


def inspect_completeness(response: str, *, generation_cap_hit: bool = False) -> Completeness:
    opens = len(re.findall(r"<think(?:\s[^>]*)?>", response, flags=re.I))
    closes = len(re.findall(r"</think>", response, flags=re.I))
    unclosed = opens > closes
    scoreable = re.sub(
        r"<think(?:\s[^>]*)?>.*?</think>", "", response, flags=re.I | re.S
    )
    if unclosed:
        opening = re.search(r"<think(?:\s[^>]*)?>", scoreable, flags=re.I)
        if opening:
            scoreable = scoreable[:opening.start()]
    scoreable = scoreable.strip()
    return Completeness(
        scoreable_text=scoreable,
        no_answer=not scoreable,
        unclosed_reasoning=unclosed,
        truncated=generation_cap_hit or unclosed,
    )


def validate_score(
    *,
    score: float,
    response: str,
    rationale: str,
    generation_cap_hit: bool = False,
) -> Completeness:
    if not rationale.strip():
        raise ScoringIntegrityError("A written rationale is required")
    completeness = inspect_completeness(
        response, generation_cap_hit=generation_cap_hit
    )
    if score > 0 and completeness.no_answer:
        raise ScoringIntegrityError("NO_ANSWER items must score 0")
    if score > 0 and completeness.truncated:
        raise ScoringIntegrityError("Truncated items cannot receive a score above 0")
    return completeness

