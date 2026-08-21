"""The two endpoints, and the guard that fires when they disagree.

Primary is judged-correct, aggregated to a per-item majority across replicates.
The cross-check is deterministic containment of the gold answer, which needs no
model and cannot be flattered by a judge.

``HH_001_DEVELOPMENT_PLAN.md`` §5: if the two disagree in the *sign* of the
A2-versus-A3 contrast, the run reports that and makes no directional claim.
NF-003 is why — its loose measure read 49 gains and 0 losses where the strict
one read 26 gains and 63 losses.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s+")
_INT = re.compile(r"^-?\d+$")
_NUMBER_WITH_SEPARATORS = re.compile(r"(?<=\d),(?=\d{3}\b)")
_ORDINAL = re.compile(r"\b(\d+)(st|nd|rd|th)\b")

_MONTHS = {
    "january": "1", "jan": "1",
    "february": "2", "feb": "2",
    "march": "3", "mar": "3",
    "april": "4", "apr": "4",
    "may": "5",
    "june": "6", "jun": "6",
    "july": "7", "jul": "7",
    "august": "8", "aug": "8",
    "september": "9", "sep": "9", "sept": "9",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12",
}


class HH001EndpointError(RuntimeError):
    pass


def normalize(text: str) -> str:
    """Casefold, NFKC, strip punctuation, collapse whitespace, canonicalize
    numbers and month names.

    The date handling is deliberately shallow. It maps month names to their
    ordinal and drops ordinal suffixes, so ``7th May 2023`` and ``7 may 2023``
    and ``May 7, 2023`` all normalize to the same token sequence in some order.
    It does **not** reorder day and month, because ``05/07`` is genuinely
    ambiguous and guessing would make the endpoint wrong rather than strict.
    """
    if text is None:
        return ""
    folded = unicodedata.normalize("NFKC", str(text)).casefold()
    folded = _NUMBER_WITH_SEPARATORS.sub("", folded)
    folded = _ORDINAL.sub(r"\1", folded)
    folded = _PUNCT.sub(" ", folded)
    tokens = [_MONTHS.get(token, token) for token in _SPACE.split(folded) if token]
    tokens = [
        str(int(token)) if _INT.fullmatch(token) else token for token in tokens
    ]
    return " ".join(tokens)


def contains_gold(answer: str, gold: str) -> bool:
    """Token-sequence containment of the normalized gold inside the answer.

    Token-sequence rather than substring, so ``12`` does not match inside
    ``120``. This is the weaker of the two endpoints by design: it misses
    correct paraphrase. What it cannot do is be talked into a yes.
    """
    gold_tokens = normalize(gold).split()
    if not gold_tokens:
        raise HH001EndpointError("Gold answer normalizes to nothing")
    answer_tokens = normalize(answer).split()
    width = len(gold_tokens)
    if width > len(answer_tokens):
        return False
    for start in range(len(answer_tokens) - width + 1):
        if answer_tokens[start : start + width] == gold_tokens:
            return True
    return False


@dataclass(frozen=True)
class ItemOutcome:
    """One item, one arm, aggregated across replicates."""

    comparison_key: str
    arm: str
    judged_correct: bool
    contained: bool
    judged_votes: tuple[bool, ...]
    contained_votes: tuple[bool, ...]

    @property
    def replicates(self) -> int:
        return len(self.judged_votes)

    @property
    def judged_unanimous(self) -> bool:
        return len(set(self.judged_votes)) <= 1

    @property
    def contained_unanimous(self) -> bool:
        return len(set(self.contained_votes)) <= 1


def majority(votes: Sequence[bool]) -> bool:
    if not votes:
        raise HH001EndpointError("Cannot take a majority of zero replicates")
    if len(votes) % 2 == 0:
        raise HH001EndpointError(
            f"Replicate count must be odd to avoid a tie, got {len(votes)}"
        )
    return sum(1 for vote in votes if vote) * 2 > len(votes)


def aggregate(
    comparison_key: str,
    arm: str,
    judged_votes: Sequence[bool],
    contained_votes: Sequence[bool],
) -> ItemOutcome:
    if len(judged_votes) != len(contained_votes):
        raise HH001EndpointError(
            "Judged and containment replicate counts differ; both endpoints are "
            "computed on every answer"
        )
    return ItemOutcome(
        comparison_key=comparison_key,
        arm=arm,
        judged_correct=majority(judged_votes),
        contained=majority(contained_votes),
        judged_votes=tuple(judged_votes),
        contained_votes=tuple(contained_votes),
    )


def unanimity_rate(outcomes: Sequence[ItemOutcome], endpoint: str = "judged") -> float:
    """This instrument's own noise reading.

    ``HH_001_DEVELOPMENT_PLAN.md`` §8: the carried 3.0-point band was measured
    on a different instrument and does not transfer. This is the replacement,
    measured here, per arm, before any contrast is interpreted.
    """
    if not outcomes:
        raise HH001EndpointError("No outcomes to measure unanimity over")
    if endpoint == "judged":
        agreed = sum(1 for outcome in outcomes if outcome.judged_unanimous)
    elif endpoint == "contained":
        agreed = sum(1 for outcome in outcomes if outcome.contained_unanimous)
    else:
        raise HH001EndpointError(f"Unknown endpoint {endpoint!r}")
    return agreed / len(outcomes)


@dataclass(frozen=True)
class SignCheck:
    """Whether the two endpoints agree on the direction of a contrast."""

    judged_net: int
    contained_net: int
    agree: bool
    reason: str

    @property
    def blocks_directional_claim(self) -> bool:
        return not self.agree


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def sign_check(judged_net: int, contained_net: int) -> SignCheck:
    """Compare the sign of the same contrast under both endpoints.

    A zero net on either endpoint is treated as agreement, not disagreement: a
    tie is not evidence that the two measures point different ways, and
    promoting it to a block would fire the guard on the quietest possible
    result. The disagreement that matters is a genuine reversal.
    """
    judged_sign = _sign(judged_net)
    contained_sign = _sign(contained_net)
    if judged_sign == 0 or contained_sign == 0:
        return SignCheck(
            judged_net=judged_net,
            contained_net=contained_net,
            agree=True,
            reason="one endpoint is exactly tied; a tie is not a reversal",
        )
    if judged_sign == contained_sign:
        return SignCheck(
            judged_net=judged_net,
            contained_net=contained_net,
            agree=True,
            reason="both endpoints point the same way",
        )
    return SignCheck(
        judged_net=judged_net,
        contained_net=contained_net,
        agree=False,
        reason=(
            "judged and containment endpoints reverse; no directional claim is "
            "reported (HH_001_DEVELOPMENT_PLAN.md §5)"
        ),
    )


__all__ = [
    "HH001EndpointError",
    "ItemOutcome",
    "SignCheck",
    "aggregate",
    "contains_gold",
    "majority",
    "normalize",
    "sign_check",
    "unanimity_rate",
]
