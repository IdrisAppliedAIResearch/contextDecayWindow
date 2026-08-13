"""DMR-004: a deterministic query-obligation compiler.

Registered design: `experiments/components/biological_memory/dmr_004/
DMR_004_PRE_REGISTRATION.md`, SHA-256
`fd99a9175a5d8048038d5e4d5b70e6a9091c90f71731026dbfdd68dd9eefcfda`, with
Amendment 001.

The compiler answers one question about a user's query: is the evidence this
request needs mechanically bounded, or can that not be determined from the text?
It answers conservatively. Saying "I cannot tell" is always available and is
the right answer more often than not - Part 1 measured 58% of real queries as
requests whose extent the words do not fix.

What it does not do is as important as what it does. It never reads the memory
store, an embedding, a candidate, an answer, a rubric, a domain label, or a
model. It has no state, no clock, no randomness, and no I/O. Given the same
string it returns the same plan in any process, on any machine, forever, and
the test suite proves that in a second interpreter rather than asserting it.

Public surface:

    QueryObligationCompiler().compile(query) -> QueryPlan
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

__all__ = [
    "CompletenessMode",
    "ObligationKind",
    "PlanClass",
    "QueryObligation",
    "QueryObligationCompiler",
    "QueryObligationError",
    "QueryPlan",
    "SupportMode",
    "canonical_map",
    "design_sha256",
]

GRAMMAR_VERSION = "dmr-query-grammar-v1"
QUERY_ID_PREFIX = "dmr-query-plan-v1"
OBLIGATION_ID_PREFIX = "dmr-obligation-v1"

#: The longest query the compiler accepts. PF7 asks for a bounded parse depth
#: and output cardinality at the intended maximum length; both are bounded here
#: by refusing anything longer rather than by hoping none arrives.
MAX_QUERY_CHARACTERS = 4096

#: The largest cardinality a query may state. Part 1 observed a maximum of 6.
MAX_REQUESTED_COUNT = 100


class QueryObligationError(ValueError):
    """Raised for input the compiler refuses rather than guesses at."""


class PlanClass(str, Enum):
    LOOKUP = "LOOKUP"
    CONJUNCT = "CONJUNCT"
    ENUMERATE_N = "ENUMERATE_N"
    HISTORY = "HISTORY"
    OPEN = "OPEN"


class CompletenessMode(str, Enum):
    FINITE = "FINITE"
    NOVELTY_ONLY = "NOVELTY_ONLY"
    UNREPRESENTABLE = "UNREPRESENTABLE"


class ObligationKind(str, Enum):
    LOOKUP = "LOOKUP"
    LIST_MEMBER = "LIST_MEMBER"
    HISTORY_LINEAGE = "HISTORY_LINEAGE"


class SupportMode(str, Enum):
    ONE_EVIDENCE = "ONE_EVIDENCE"
    N_DISTINCT = "N_DISTINCT"
    LINEAGE = "LINEAGE"
    #: Declared by the registration's §2 schema. No plan emits it: an OPEN plan
    #: carries no obligation at all, so there is nothing to mark. Reported as
    #: unexercised rather than quietly dropped.
    NEVER_COMPLETE = "NEVER_COMPLETE"


# --------------------------------------------------------------- frozen grammar

INTERROGATIVE = (
    "what", "who", "whom", "whose", "where", "when", "which", "why", "how",
    "did", "do", "does", "is", "are", "was", "were", "can", "could", "will",
    "would", "have", "has", "had",
)

HISTORY_MARKERS = (
    "previous", "prior", "former", "formerly", "used to", "initially",
    "originally", "back then",
)

AGGREGATE_MARKERS = (
    "how many", "how much", "how long", "how often", "how far", "total",
    "in total", "combined", "altogether", "average", "mean", "median",
    "difference", "differ", "compared to", "more than", "less than",
    "fewer than", "sum of", "count of",
)

#: `first` and `last` are registered members of this set. They are common words
#: and demoting on them costs sensitivity on queries like "the music event last
#: Saturday", but the registration lists them and the implementation follows it.
SUPERLATIVE_MARKERS = (
    "most recent", "latest", "earliest", "highest", "lowest", "best", "worst",
    "the most", "largest", "smallest", "first", "last",
)

LIST_MARKERS = (
    "list", "enumerate", "name all", "name every", "order of", "in the order",
    "what are the", "which",
)

#: "our previous conversation about X" points at where to look, not at what
#: changed. Part 1 found 41 of these in 500 natural queries and found that a
#: history rule without this exclusion becomes a detector for one benchmark
#: label, firing on 49 of 56 single-session-assistant items.
DISCOURSE_POINTER = re.compile(
    r"\b(?:our|the|my|a)\s+(?:previous|earlier|last|prior)\s+"
    r"(?:conversation|chat|discussion|session|talk|exchange|game)\b"
)

CHANGE_FRAME = re.compile(r"\bhow\s+(?:did|has|have)\b.*?\b(?:chang|updat|evolv)")

SPELLED_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}

#: A cardinality is an integer bound to a plural noun. A price, a date, a model
#: number, a distance, a duration and an ordinal all fail that test, which is
#: what separates "the three trips" from "the iPhone 13 Pro". Part 1 found 27 of
#: 28 integer matches were not cardinalities.
CARDINALITY = re.compile(
    r"\b(?:the\s+)?(?P<n>\d+|" + "|".join(SPELLED_NUMBERS) + r")\s+"
    r"(?:other\s+|remaining\s+|distinct\s+|different\s+|separate\s+)?"
    r"(?P<noun>[a-z]+(?:s|ies|es))\b"
)

#: An ordinal selects one member of a list; it is never a cardinality.
ORDINAL = re.compile(r"\b\d+(?:st|nd|rd|th)\b")

CLAUSE_INITIAL = re.compile(
    r"(?:^|[.?;!]\s+|\n)\s*(?P<frame>" + "|".join(INTERROGATIVE) + r")\b"
)

BULLET = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+")

_WORD_BOUNDED = {}


def _marker(phrase: str) -> re.Pattern[str]:
    pattern = _WORD_BOUNDED.get(phrase)
    if pattern is None:
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b")
        _WORD_BOUNDED[phrase] = pattern
    return pattern


def _any_marker(view: str, phrases: Sequence[str]) -> str | None:
    for phrase in phrases:
        if _marker(phrase).search(view):
            return phrase
    return None


def design_sha256() -> str:
    """A hash over every constant the grammar's behavior depends on.

    Change a marker, a precedence, or the maximum length and this moves, which
    is what lets a later study prove it ran the same grammar rather than
    asserting it.
    """
    parts = [
        GRAMMAR_VERSION,
        unicodedata.unidata_version,
        "|".join(INTERROGATIVE),
        "|".join(HISTORY_MARKERS),
        "|".join(AGGREGATE_MARKERS),
        "|".join(SUPERLATIVE_MARKERS),
        "|".join(LIST_MARKERS),
        DISCOURSE_POINTER.pattern,
        CHANGE_FRAME.pattern,
        CARDINALITY.pattern,
        ORDINAL.pattern,
        CLAUSE_INITIAL.pattern,
        BULLET.pattern,
        str(MAX_QUERY_CHARACTERS),
        str(MAX_REQUESTED_COUNT),
        "HISTORY>ENUMERATE_N>CONJUNCT>DEMOTE>LOOKUP>OPEN",
    ]
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


# --------------------------------------------------------------- canonical view

def canonical_map(text: str) -> tuple[str, tuple[int, ...]]:
    """NFKC, case fold, whitespace collapse, strip - with offsets carried back.

    NFKC expands ligatures and case folding expands 'ß', so the canonical view
    and the original can differ in length and index arithmetic between them is
    unsound. The second return value gives, for each canonical character, the
    index in the original string it came from, so every reported offset points
    into what the user actually typed.

    Matching the raw string instead is not a shortcut. Part 1 measured it: a
    two-word marker stops matching the moment a user types two spaces, and
    42.2% of plans flip - toward claiming completeness, the unsafe direction.
    """
    pieces: list[str] = []
    origins: list[int] = []
    for index, character in enumerate(text):
        for produced in unicodedata.normalize("NFKC", character).casefold():
            pieces.append(produced)
            origins.append(index)

    collapsed: list[str] = []
    collapsed_origins: list[int] = []
    in_space = False
    for character, origin in zip(pieces, origins):
        if character.isspace():
            if in_space:
                continue
            in_space = True
            collapsed.append(" ")
            collapsed_origins.append(origin)
            continue
        in_space = False
        collapsed.append(character)
        collapsed_origins.append(origin)

    start, end = 0, len(collapsed)
    while start < end and collapsed[start] == " ":
        start += 1
    while end > start and collapsed[end - 1] == " ":
        end -= 1
    return "".join(collapsed[start:end]), tuple(collapsed_origins[start:end])


# --------------------------------------------------------------- output types

@dataclass(frozen=True)
class QueryObligation:
    obligation_id: str
    kind: ObligationKind
    source_start: int
    source_end: int
    source_text: str
    requested_count: int | None
    support_mode: SupportMode

    def as_row(self) -> dict[str, object]:
        return {
            "obligation_id": self.obligation_id,
            "kind": self.kind.value,
            "source_start": self.source_start,
            "source_end": self.source_end,
            "source_text": self.source_text,
            "requested_count": self.requested_count,
            "support_mode": self.support_mode.value,
        }


@dataclass(frozen=True)
class QueryPlan:
    query_hash: str
    normalized_hash: str
    plan_class: PlanClass
    obligations: tuple[QueryObligation, ...]
    completeness_mode: CompletenessMode
    ambiguity_codes: tuple[str, ...] = field(default_factory=tuple)
    design_sha256: str = ""

    @property
    def claims_completeness(self) -> bool:
        """Whether a controller may treat this plan's obligations as closable.

        `NOVELTY_ONLY` does not claim it. A value may have had any number of
        prior values and the query text does not bound them, so a lineage
        obligation is not a finite one.
        """
        return self.completeness_mode is CompletenessMode.FINITE

    def as_row(self) -> dict[str, object]:
        return {
            "query_hash": self.query_hash,
            "normalized_hash": self.normalized_hash,
            "plan_class": self.plan_class.value,
            "completeness_mode": self.completeness_mode.value,
            "ambiguity_codes": list(self.ambiguity_codes),
            "design_sha256": self.design_sha256,
            "obligations": [obligation.as_row() for obligation in self.obligations],
        }

    def digest(self) -> str:
        """A byte-stable identity for the whole plan, for the determinism gate."""
        parts = [
            self.query_hash,
            self.normalized_hash,
            self.plan_class.value,
            self.completeness_mode.value,
            ",".join(self.ambiguity_codes),
            self.design_sha256,
        ]
        for obligation in self.obligations:
            parts.append(
                "\x1f".join(
                    [
                        obligation.obligation_id,
                        obligation.kind.value,
                        str(obligation.source_start),
                        str(obligation.source_end),
                        str(obligation.requested_count),
                        obligation.support_mode.value,
                    ]
                )
            )
        return hashlib.sha256("\x1e".join(parts).encode("utf-8")).hexdigest()


# --------------------------------------------------------------- the compiler

class QueryObligationCompiler:
    """A pure precedence parser over query text.

    Stateless by construction: an instance holds nothing, so two instances and
    two processes cannot disagree.
    """

    __slots__ = ()

    def compile(self, query: str) -> QueryPlan:
        if not isinstance(query, str):
            raise QueryObligationError("query must be a string")
        if len(query) > MAX_QUERY_CHARACTERS:
            raise QueryObligationError(
                f"query of {len(query)} characters exceeds the {MAX_QUERY_CHARACTERS} limit"
            )

        view, origins = canonical_map(query)
        query_hash = hashlib.sha256(
            (QUERY_ID_PREFIX + "\0" + query).encode("utf-8")
        ).hexdigest()
        normalized_hash = hashlib.sha256(view.encode("utf-8")).hexdigest()
        design = design_sha256()
        codes: list[str] = []

        if not view:
            # Step 6's registered code is still emitted; EMPTY_QUERY only adds
            # detail the registration does not name.
            return self._plan(
                query_hash, normalized_hash, PlanClass.OPEN, (),
                CompletenessMode.UNREPRESENTABLE,
                ("EMPTY_QUERY", "NO_INTERROGATIVE_FRAME"), design,
            )

        pointer = DISCOURSE_POINTER.search(view) is not None
        if pointer:
            codes.append("DISCOURSE_POINTER_NOT_HISTORY")

        # 1. HISTORY
        if not pointer and (
            _any_marker(view, HISTORY_MARKERS) is not None or CHANGE_FRAME.search(view)
        ):
            span = self._target_span(query, view, origins)
            obligation = self._obligation(
                query, query_hash, ObligationKind.HISTORY_LINEAGE, span, None, SupportMode.LINEAGE
            )
            return self._plan(
                query_hash, normalized_hash, PlanClass.HISTORY, (obligation,),
                CompletenessMode.NOVELTY_ONLY, tuple(codes), design,
            )

        # 2. ENUMERATE_N
        count = self._cardinality(view, codes)
        if count is not None and _any_marker(view, LIST_MARKERS) is not None:
            span = self._target_span(query, view, origins)
            # Amendment 001: one obligation carrying N, not N obligations. The
            # queries that trigger this rule hold one list request and no N
            # distinct spans, so N obligations would be N identical spans and
            # the non-overlap gate could never pass.
            obligation = self._obligation(
                query, query_hash, ObligationKind.LIST_MEMBER, span, count, SupportMode.N_DISTINCT
            )
            return self._plan(
                query_hash, normalized_hash, PlanClass.ENUMERATE_N, (obligation,),
                CompletenessMode.FINITE, tuple(codes), design,
            )

        # 3. CONJUNCT
        clauses = self._clause_spans(query, view, origins)
        if len(clauses) >= 2:
            # The registration gives a CONJUNCT plan the support mode
            # N_DISTINCT, not ONE_EVIDENCE per clause: the plan is closed by N
            # distinct items even though each clause contributes one.
            obligations = tuple(
                self._obligation(
                    query, query_hash, ObligationKind.LOOKUP, span, None, SupportMode.N_DISTINCT
                )
                for span in clauses
            )
            return self._plan(
                query_hash, normalized_hash, PlanClass.CONJUNCT, obligations,
                CompletenessMode.FINITE, tuple(codes), design,
            )

        # 4. Demotion to open
        aggregate = _any_marker(view, AGGREGATE_MARKERS)
        if aggregate is not None:
            codes.append("AGGREGATE_FRAME")
            return self._plan(
                query_hash, normalized_hash, PlanClass.OPEN, (),
                CompletenessMode.UNREPRESENTABLE, tuple(codes), design,
            )
        superlative = _any_marker(view, SUPERLATIVE_MARKERS)
        if superlative is not None and count is None:
            codes.append("SUPERLATIVE_OVER_UNNUMBERED_SET")
            return self._plan(
                query_hash, normalized_hash, PlanClass.OPEN, (),
                CompletenessMode.UNREPRESENTABLE, tuple(codes), design,
            )

        # 5. LOOKUP
        span = self._target_span(query, view, origins)
        if span is not None:
            obligation = self._obligation(
                query, query_hash, ObligationKind.LOOKUP, span, None, SupportMode.ONE_EVIDENCE
            )
            return self._plan(
                query_hash, normalized_hash, PlanClass.LOOKUP, (obligation,),
                CompletenessMode.FINITE, tuple(codes), design,
            )

        # 6. OPEN
        codes.append("NO_INTERROGATIVE_FRAME")
        return self._plan(
            query_hash, normalized_hash, PlanClass.OPEN, (),
            CompletenessMode.UNREPRESENTABLE, tuple(codes), design,
        )

    # -------------------------------------------------------------- internals

    @staticmethod
    def _plan(
        query_hash: str,
        normalized_hash: str,
        plan_class: PlanClass,
        obligations: tuple[QueryObligation, ...],
        completeness: CompletenessMode,
        codes: tuple[str, ...],
        design: str,
    ) -> QueryPlan:
        return QueryPlan(
            query_hash=query_hash,
            normalized_hash=normalized_hash,
            plan_class=plan_class,
            obligations=obligations,
            completeness_mode=completeness,
            ambiguity_codes=codes,
            design_sha256=design,
        )

    @staticmethod
    def _obligation(
        query: str,
        query_hash: str,
        kind: ObligationKind,
        span: tuple[int, int] | None,
        count: int | None,
        support: SupportMode,
    ) -> QueryObligation:
        if span is None:
            span = (0, len(query))
        start, end = span
        payload = (
            OBLIGATION_ID_PREFIX + "\0" + query_hash + "\0"
            + str(start) + "\0" + str(end) + "\0" + kind.value
        )
        return QueryObligation(
            obligation_id=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            kind=kind,
            source_start=start,
            source_end=end,
            source_text=query[start:end],
            requested_count=count,
            support_mode=support,
        )

    @staticmethod
    def _cardinality(view: str, codes: list[str]) -> int | None:
        """An integer bound to a plural noun, and not an ordinal."""
        for match in CARDINALITY.finditer(view):
            token = match.group("n")
            if ORDINAL.match(token):
                continue
            value = int(token) if token.isdigit() else SPELLED_NUMBERS.get(token)
            if value is None or value <= 0 or value > MAX_REQUESTED_COUNT:
                codes.append("CARDINALITY_OUT_OF_RANGE")
                continue
            # An ordinal immediately before the integer ("the 7th job") means
            # the query selects a member, not a count of them.
            prefix = view[max(0, match.start() - 12): match.start()]
            if ORDINAL.search(prefix):
                continue
            return value
        if ORDINAL.search(view):
            codes.append("NUMERAL_NOT_CARDINALITY")
        return None

    @staticmethod
    def _canonical_to_original(
        query: str, origins: Sequence[int], start: int, end: int
    ) -> tuple[int, int] | None:
        if start >= end or start < 0 or end > len(origins):
            return None
        first = origins[start]
        last = origins[end - 1]
        if first > last:
            return None
        return (first, min(len(query), last + 1))

    @classmethod
    def _target_span(
        cls, query: str, view: str, origins: Sequence[int]
    ) -> tuple[int, int] | None:
        """The complement of the first clause-initial interrogative frame."""
        match = CLAUSE_INITIAL.search(view)
        if match is None:
            return None
        start = match.end()
        tail = re.search(r"[?.!]\s*$", view[start:])
        end = start + (tail.start() if tail else len(view) - start)
        while start < end and view[start] == " ":
            start += 1
        if start >= end:
            return None
        return cls._canonical_to_original(query, origins, start, end)

    @classmethod
    def _clause_spans(
        cls, query: str, view: str, origins: Sequence[int]
    ) -> tuple[tuple[int, int], ...]:
        """Non-overlapping spans, one per top-level clause.

        Clause boundaries are the starts of clause-initial interrogative
        frames, plus top-level semicolons and bullets. Each span runs to the
        next boundary, so siblings cannot overlap by construction - which is
        what G5 requires and what the enumerate rule could not deliver.
        """
        boundaries = sorted(
            {match.start("frame") for match in CLAUSE_INITIAL.finditer(view)}
            | {match.start() + 1 for match in re.finditer(r";", view)}
            | {match.start() for match in BULLET.finditer(view)}
        )
        if len(boundaries) < 2:
            return ()

        spans: list[tuple[int, int]] = []
        for index, begin in enumerate(boundaries):
            stop = boundaries[index + 1] if index + 1 < len(boundaries) else len(view)
            text = view[begin:stop]
            trimmed = text.rstrip(" ;?.!")
            if not trimmed.strip():
                continue
            mapped = cls._canonical_to_original(
                query, origins, begin, begin + len(trimmed)
            )
            if mapped is None:
                continue
            if spans and mapped[0] < spans[-1][1]:
                # Never emit an overlapping sibling; drop the later one instead
                # of reporting a span the gate would have to fail.
                continue
            spans.append(mapped)
        return tuple(spans)
