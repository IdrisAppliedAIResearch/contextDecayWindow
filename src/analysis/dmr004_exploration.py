"""DMR-004 Part 1: what shape are the queries actually in?

This module is exploration, not the component. Nothing here is a candidate for
`src/biological_memory/query_obligations.py`; its whole job is to measure the
query population before a grammar is designed against it, so that the bars in
the pre-registration are set against something real.

Two candidate grammars are implemented side by side:

`R1` is the specification's §5.2 shape read literally - history markers,
integer cardinality tied to a list verb, top-level clause separators, one
interrogative frame, everything else open.

`R2` is R1 plus the one thing R1 cannot see: a query whose answer is an
aggregate over an unknown number of stored items ("how many", "total",
"average", "difference", "order of") looks exactly like a single lookup on the
surface, and R1 hands it `ONE_EVIDENCE`. R2 routes those to open instead.

Both are throwaway. The point is the difference between them.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

# ---------------------------------------------------------------- canonical view

_WHITESPACE = re.compile(r"\s+")


def canonical_map(text: str) -> tuple[str, tuple[int, ...]]:
    """NFKC + casefold + whitespace-collapse, carrying an offset map back.

    Both transforms can change a string's length - NFKC on ligatures, casefold
    on 'ß' - so index arithmetic against the original is not safe. The second
    return value gives, for each canonical character, the index in the original
    string it came from, which is what section 5.1's "source offsets always
    point into the original string" actually requires.

    Matching on the raw string instead is not a shortcut but a defect: a
    two-word marker like "how many" stops matching the moment a user types two
    spaces. Part 1 measured that at 42.2% of the corpus.
    """
    pieces: list[str] = []
    origins: list[int] = []
    for index, character in enumerate(text):
        expanded = unicodedata.normalize("NFKC", character).casefold()
        for produced in expanded:
            pieces.append(produced)
            origins.append(index)

    canon: list[str] = []
    canon_origins: list[int] = []
    in_space = False
    for character, origin in zip(pieces, origins):
        if character.isspace():
            if in_space:
                continue
            in_space = True
            canon.append(" ")
            canon_origins.append(origin)
            continue
        in_space = False
        canon.append(character)
        canon_origins.append(origin)

    start = 0
    end = len(canon)
    while start < end and canon[start] == " ":
        start += 1
    while end > start and canon[end - 1] == " ":
        end -= 1
    return "".join(canon[start:end]), tuple(canon_origins[start:end])


def canonical(text: str) -> str:
    return canonical_map(text)[0]


def canonical_is_length_preserving(text: str) -> bool:
    """Whether canonicalization is a character-for-character map on this query."""
    return len(unicodedata.normalize("NFKC", text).casefold()) == len(text)


def to_original_span(text: str, origins: Sequence[int], start: int, end: int) -> tuple[int, int]:
    """Map a canonical [start, end) span back to original character offsets."""
    if start >= end:
        raise ValueError("empty canonical span")
    first = origins[start]
    last = origins[end - 1]
    return (first, last + 1)


# ---------------------------------------------------------------- surface features

INTERROGATIVE = r"(?:what|who|whom|whose|where|when|which|why|how|did|do|does|is|are|was|were|can|could|will|would|have|has|had)"

PATTERNS: dict[str, re.Pattern[str]] = {
    "question_mark": re.compile(r"\?"),
    "multi_question_mark": re.compile(r"\?[^?]*\?"),
    "semicolon": re.compile(r";"),
    "newline": re.compile(r"\n"),
    "bullet": re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+"),
    "coord_and": re.compile(r"\sand\s", re.I),
    "coord_or": re.compile(r"\sor\s", re.I),
    "digit": re.compile(r"\d"),
    "ordinal_digit": re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.I),
    "spelled_number": re.compile(
        r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", re.I
    ),
    "list_verb": re.compile(r"\b(?:list|enumerate|name all|name every)\b", re.I),
    "universal": re.compile(r"\b(?:all|every|each)\b", re.I),
    "history_word": re.compile(r"\b(?:histor\w*|previously|used to|formerly)\b", re.I),
    "change_word": re.compile(r"\b(?:change[ds]?|changing|updated?|revised?|switch(?:ed)?)\b", re.I),
    "prior_word": re.compile(r"\b(?:previous|earlier|before|prior|last)\b", re.I),
    "discourse_pointer": re.compile(
        r"\b(?:our|the|a|my)\s+(?:previous|earlier|last|prior)\s+"
        r"(?:conversation|chat|discussion|session|talk|exchange|game)",
        re.I,
    ),
    "remind_frame": re.compile(r"\b(?:remind me|do you remember|you mentioned|you said)\b", re.I),
    "quote": re.compile(r"['\"‘’“”]"),
    "first_person": re.compile(r"\b(?:i|me|my|mine)\b", re.I),
}

#: Frames whose answer is computed over an unknown number of stored items.
AGGREGATE = re.compile(
    r"\b(?:how many|how much|how long|how often|how far"
    r"|total(?:\s+(?:number|cost|distance|amount|weight|price))?"
    r"|in total|combined|altogether"
    r"|average|mean|median"
    r"|difference|differ|compared to|more than|less than|fewer than"
    r"|order of|from earliest|from first|in the order"
    r"|sum of|count of)\b",
    re.I,
)

#: A cardinality that is bound to a plural noun the query is asking to be given,
#: rather than a measurement, a date, a price, or a product name.
CARDINALITY = re.compile(
    r"\b(?:the\s+)?(?P<n>\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
    r"(?:other\s+|remaining\s+|distinct\s+|different\s+|separate\s+)?"
    r"(?P<noun>[a-z]+(?:s|ies|es))\b",
    re.I,
)

_SPELLED = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}


def spelled_value(token: str) -> int | None:
    token = token.lower()
    if token.isdigit():
        return int(token)
    return _SPELLED.get(token)


def surface_features(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in PATTERNS.items()}


def interrogative_frames(text: str) -> int:
    """Count clause-initial interrogative frames.

    Clause-initial means after a sentence end, a semicolon, or the string start -
    a bare "what" inside "tell me what you know" is not a second frame.
    """
    pattern = re.compile(rf"(?:^|[.?;!]\s+|\n)\s*(?:{INTERROGATIVE})\b", re.I)
    return len(pattern.findall(text))


# ---------------------------------------------------------------- candidate grammars

PLAN_CLASSES = ("LOOKUP", "CONJUNCT", "ENUMERATE_N", "HISTORY", "OPEN")


@dataclass(frozen=True)
class Plan:
    plan_class: str
    requested_count: int | None = None
    codes: tuple[str, ...] = field(default_factory=tuple)
    span: tuple[int, int] | None = None


def _history_r1(text: str) -> bool:
    """Section 5.2's history rule, read literally.

    An explicit history marker plus a target. The discourse-pointer exclusion is
    NOT part of R1 - that exclusion is one of the things Part 1 is here to show
    is necessary.
    """
    if PATTERNS["history_word"].search(text):
        return True
    if re.search(r"\bbefore and after\b", text, re.I):
        return True
    if re.search(rf"\bhow (?:did|has|have)\b.*\b(?:chang|updat|evolv)", text, re.I):
        return True
    if PATTERNS["prior_word"].search(text):
        return True
    return False


def _enumerate_r1(text: str) -> int | None:
    """An explicit positive integer tied to a list request."""
    match = CARDINALITY.search(text)
    if match is None:
        return None
    value = spelled_value(match.group("n"))
    if value is None or value <= 0:
        return None
    return value


def _conjunct_r1(text: str) -> bool:
    if PATTERNS["semicolon"].search(text):
        return True
    if PATTERNS["bullet"].search(text):
        return True
    return interrogative_frames(text) >= 2


def _lookup_span(view: str) -> tuple[int, int] | None:
    """The complement of the first clause-initial interrogative frame.

    A crude span, on purpose: the surrogate table warns that a span covering the
    whole query overlaps every gold span, so Part 1 needs the length distribution
    of a span rule that is trying to be tight.
    """
    match = re.search(rf"(?:^|[.?;!]\s+|\n)\s*({INTERROGATIVE})\b", view, re.I)
    if match is None:
        return None
    start = match.end()
    tail = re.search(r"[?.!]\s*$", view[start:])
    end = start + (tail.start() if tail else len(view) - start)
    while start < end and view[start] in " \t":
        start += 1
    if start >= end:
        return None
    return (start, end)


def _view(text: str, canonicalize: bool) -> tuple[str, tuple[int, ...] | None]:
    if canonicalize:
        return canonical_map(text)
    return text, None


def _span_out(
    text: str, origins: tuple[int, ...] | None, span: tuple[int, int] | None
) -> tuple[int, int] | None:
    if span is None:
        return None
    if origins is None:
        return span
    return to_original_span(text, origins, span[0], span[1])


def compile_r1(text: str, *, canonicalize: bool = True) -> Plan:
    """Specification §5.2 precedence: history, enumerate, conjunct, lookup, open."""
    view, origins = _view(text, canonicalize)
    codes: list[str] = []
    span = _span_out(text, origins, _lookup_span(view))
    if _history_r1(view):
        return Plan("HISTORY", None, tuple(codes), span)
    count = _enumerate_r1(view)
    if count is not None:
        return Plan("ENUMERATE_N", count, tuple(codes), span)
    if _conjunct_r1(view):
        return Plan("CONJUNCT", None, tuple(codes), span)
    if span is None:
        codes.append("NO_INTERROGATIVE_FRAME")
        return Plan("OPEN", None, tuple(codes), None)
    return Plan("LOOKUP", None, tuple(codes), span)


def compile_r2(text: str, *, canonicalize: bool = True) -> Plan:
    """R1 plus the exclusions Part 1 found it needs.

    1. A discourse pointer ("our previous conversation about X") is not a
       history request; it names where to look, not what changed.
    2. An aggregate frame is not a single lookup. Its answer is computed over an
       unknown number of stored items, so no fixed evidence count completes it.
    3. A cardinality is only a cardinality when a list verb or an ordering frame
       asks for the members.
    """
    view, origins = _view(text, canonicalize)
    codes: list[str] = []
    span = _span_out(text, origins, _lookup_span(view))
    aggregate = AGGREGATE.search(view) is not None
    pointer = PATTERNS["discourse_pointer"].search(view) is not None

    history = _history_r1(view) and not pointer
    if pointer:
        codes.append("DISCOURSE_POINTER_NOT_HISTORY")
    if history and not aggregate:
        return Plan("HISTORY", None, tuple(codes), span)

    count = _enumerate_r1(view)
    listy = PATTERNS["list_verb"].search(view) is not None or re.search(
        r"\b(?:order of|in the order|what are the|which)\b", view, re.I
    )
    if count is not None and listy:
        return Plan("ENUMERATE_N", count, tuple(codes), span)
    if count is not None:
        codes.append("NUMERAL_NOT_CARDINALITY")

    if aggregate:
        codes.append("AGGREGATE_FRAME")
        return Plan("OPEN", None, tuple(codes), None)

    if _conjunct_r1(view):
        return Plan("CONJUNCT", None, tuple(codes), span)

    if span is None:
        codes.append("NO_INTERROGATIVE_FRAME")
        return Plan("OPEN", None, tuple(codes), None)
    return Plan("LOOKUP", None, tuple(codes), span)


def compile_r2_raw(text: str) -> Plan:
    """R2 matching the raw string instead of the canonical view.

    Kept only so the Part 1 figure it produced stays reproducible from committed
    code: matching multi-word markers against raw text flips the plan class on
    42.2% of the corpus under nothing worse than doubled spaces.
    """
    return compile_r2(text, canonicalize=False)


GRAMMARS = {"R1": compile_r1, "R2": compile_r2, "R2_RAW": compile_r2_raw}


# ---------------------------------------------------------------- perturbations

def perturb_case(text: str) -> str:
    return text.upper()


def perturb_whitespace(text: str) -> str:
    return "  " + text.replace(" ", "  ") + " "


def perturb_punctuation(text: str) -> str:
    return text.rstrip("?. ") + " ?"


def perturb_quotes(text: str) -> str:
    return text.replace("'", "’").replace('"', "“")


def perturb_decimal(text: str) -> str:
    """Rewrite bare integers as finite decimals: 3 -> 3.0.

    Section 11 says `3.0 items` must not silently become a valid integer
    cardinality unless that is preregistered.
    """
    return re.sub(r"\b(\d+)\b", r"\1.0", text)


def perturb_reorder_conjuncts(text: str) -> str:
    """Swap the two halves of a top-level semicolon, leaving meaning intact."""
    if ";" not in text:
        return text
    head, _, tail = text.partition(";")
    return f"{tail.strip().rstrip('?')}; {head.strip()}?"


PERTURBATIONS = {
    "case": perturb_case,
    "whitespace": perturb_whitespace,
    "punctuation": perturb_punctuation,
    "quotes": perturb_quotes,
    "decimal": perturb_decimal,
    "reorder_conjuncts": perturb_reorder_conjuncts,
}


def perturbation_stability(texts: Sequence[str], grammar_name: str) -> dict[str, dict[str, object]]:
    """How often each perturbation changes the plan class.

    A grammar that is not stable under case or whitespace is not a grammar, it
    is a lookup table for this corpus.
    """
    compile_fn = GRAMMARS[grammar_name]
    out: dict[str, dict[str, object]] = {}
    for name, fn in PERTURBATIONS.items():
        changed: list[tuple[str, str, str]] = []
        applicable = 0
        for text in texts:
            mutated = fn(text)
            if mutated == text:
                continue
            applicable += 1
            before = compile_fn(text)
            after = compile_fn(mutated)
            if before.plan_class != after.plan_class or before.requested_count != after.requested_count:
                changed.append((text, before.plan_class, after.plan_class))
        out[name] = {
            "applicable": applicable,
            "changed": len(changed),
            "rate": (len(changed) / applicable) if applicable else None,
            "examples": changed[:6],
        }
    return out


# ---------------------------------------------------------------- distributions

def class_distribution(texts: Sequence[str], grammar_name: str) -> Counter[str]:
    compile_fn = GRAMMARS[grammar_name]
    return Counter(compile_fn(text).plan_class for text in texts)


def code_distribution(texts: Sequence[str], grammar_name: str) -> Counter[str]:
    compile_fn = GRAMMARS[grammar_name]
    counter: Counter[str] = Counter()
    for text in texts:
        for code in compile_fn(text).codes:
            counter[code] += 1
    return counter


def span_lengths(texts: Sequence[str], grammar_name: str) -> list[float]:
    """Span length as a fraction of query length, for the whole-query surrogate."""
    compile_fn = GRAMMARS[grammar_name]
    out = []
    for text in texts:
        plan = compile_fn(text)
        if plan.span is None:
            continue
        start, end = plan.span
        out.append((end - start) / len(text))
    return out
