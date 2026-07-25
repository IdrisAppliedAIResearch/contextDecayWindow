"""Sentence-level span segmentation with offsets for Study 006.

Study 005 scored whole turn episodes. A compact planted fact was therefore buried
inside a long turn and outranked by verbose model output that accumulated entities
and numbers simply by being long. Study 006 selects sentence-level spans so a short
dense fact competes on its own merits.

This module builds the span substrate only: it segments, records offsets, counts the
entity and numeric content eligibility depends on, and applies the eligibility filter.
Salience scoring lives in :mod:`src.memory.dream_engine`.

Every span carries character offsets into its source episode's ``text`` so the
extractive guarantee stays checkable at span granularity: ``source[start:end]``
must equal ``span.text`` exactly.
"""

import re
from dataclasses import dataclass

from src.memory.dream_engine import (
    count_named_entities_fallback,
    count_numeric_tokens,
)


USER_PREFIX = "User: "
ASSISTANT_PREFIX = "Assistant: "
ROLE_SEPARATOR = "\n" + ASSISTANT_PREFIX

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

MIN_SPAN_WORDS = 4
MAX_SPAN_WORDS = 60

REJECT_TOO_SHORT = "word_count_below_minimum"
REJECT_TOO_LONG = "word_count_above_maximum"
REJECT_NO_CONTENT = "no_named_entity_or_numeric_token"

SPACY_MODEL = "en_core_web_sm"

_FALLBACK_SEGMENTER = "regex_sentence_fallback"
_FALLBACK_EXTRACTOR = "capitalized_sequence_fallback"

# Words that end in a period without ending a sentence. Only consulted by the
# regex fallback; spaCy handles these natively.
_ABBREVIATIONS = frozenset(
    {
        "dr", "mr", "mrs", "ms", "prof", "st", "jr", "sr", "vs", "etc",
        "inc", "ltd", "co", "corp", "no", "fig", "eq", "approx", "dept",
        "est", "min", "max", "al", "e.g", "i.e", "cf", "ca",
    }
)

# A sentence boundary is terminal punctuation followed by whitespace and then a
# capital letter or digit. Requiring whitespace after the period is what protects
# decimals: the period in "2.3%" is followed by a digit, not a space.
_BOUNDARY = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[\"'(\[]*[A-Z0-9])")
_TRAILING_WORD = re.compile(r"([A-Za-z][A-Za-z.]*)[\"')\]]*\s*$")
_WORD = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ][\w'’-]*")


@dataclass(frozen=True)
class Span:
    """One sentence-level candidate with provenance back to its source episode."""

    text: str
    start: int
    end: int
    episode_id: str
    turn_number: int
    role: str
    word_count: int
    named_entities: int
    numeric_tokens: int
    eligible: bool
    rejection_reason: str | None = None

    @property
    def base(self) -> int:
        """Absolute entity+numeric content, before length normalization."""
        return self.named_entities + 2 * self.numeric_tokens


class _Segmenter:
    """Loads spaCy once and degrades to the documented regex fallback."""

    def __init__(self) -> None:
        self._nlp = None
        self._loaded = False
        self.segmenter = _FALLBACK_SEGMENTER
        self.extractor = _FALLBACK_EXTRACTOR

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            import spacy

            nlp = spacy.load(SPACY_MODEL, exclude=["parser", "senter"])
            nlp.add_pipe("sentencizer")
        except Exception:
            self._nlp = None
            return
        self._nlp = nlp
        version = nlp.meta.get("version", "unknown")
        self.segmenter = f"spacy:{SPACY_MODEL}:{version}:sentencizer"
        self.extractor = f"spacy:{SPACY_MODEL}:{version}:ner"

    @property
    def spacy_available(self) -> bool:
        self._ensure_loaded()
        return self._nlp is not None

    def sentence_bounds(self, text: str) -> list[tuple[int, int]]:
        """Return whitespace-trimmed (start, end) offsets of each sentence."""
        self._ensure_loaded()
        if self._nlp is not None:
            raw = [
                (sent.start_char, sent.end_char)
                for sent in self._nlp(text).sents
            ]
        else:
            raw = _regex_sentence_bounds(text)
        return [
            trimmed
            for trimmed in (_trim(text, start, end) for start, end in raw)
            if trimmed is not None
        ]

    def count_entities(self, text: str) -> int:
        self._ensure_loaded()
        if self._nlp is None:
            return count_named_entities_fallback(text)
        return len(self._nlp(text).ents)

    def count_words(self, text: str) -> int:
        self._ensure_loaded()
        if self._nlp is None:
            return len(_WORD.findall(text))
        return len(
            [
                token
                for token in self._nlp(text)
                if not token.is_punct and not token.is_space
            ]
        )


_SEGMENTER = _Segmenter()


def _trim(text: str, start: int, end: int) -> tuple[int, int] | None:
    """Shrink (start, end) past surrounding whitespace, or drop it if empty."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return (start, end) if end > start else None


def _regex_sentence_bounds(text: str) -> list[tuple[int, int]]:
    """Documented fallback: split on terminal punctuation + whitespace + capital.

    Decimals are protected because a boundary requires whitespace after the
    period. Abbreviations are protected by rejecting boundaries whose preceding
    word is a known abbreviation.
    """
    bounds = []
    cursor = 0
    for match in _BOUNDARY.finditer(text):
        candidate = match.start()
        preceding = text[cursor:candidate]
        trailing = _TRAILING_WORD.search(preceding.rstrip(".!?"))
        if trailing and trailing.group(1).lower().rstrip(".") in _ABBREVIATIONS:
            continue
        bounds.append((cursor, candidate))
        cursor = match.end()
    if cursor < len(text):
        bounds.append((cursor, len(text)))
    return bounds


def role_segments(episode: dict) -> list[tuple[str, int, int]]:
    """Split an episode's stored text into (role, start, end) regions.

    Episodes are stored as ``User: <message>\\nAssistant: <message>`` and carry a
    single ``role`` of ``conversation``, so per-span source attribution has to be
    recovered from the text layout. Offsets are derived from the message columns
    when they reconstruct the stored text exactly, and located by separator search
    otherwise.
    """
    text = episode["text"]
    user_message = episode.get("user_message")
    assistant_message = episode.get("assistant_message")

    if user_message is not None and assistant_message is not None:
        expected = (
            f"{USER_PREFIX}{user_message}"
            f"{ROLE_SEPARATOR}{assistant_message}"
        )
        if text == expected:
            user_start = len(USER_PREFIX)
            user_end = user_start + len(user_message)
            assistant_start = user_end + len(ROLE_SEPARATOR)
            return _non_empty_segments(
                text, user_start, user_end, assistant_start, len(text)
            )

    separator_at = text.find(ROLE_SEPARATOR)
    if separator_at == -1:
        if text.startswith(USER_PREFIX):
            return _non_empty_segments(
                text, len(USER_PREFIX), len(text), len(text), len(text)
            )
        raise ValueError(
            "Cannot attribute span roles: episode text has neither the "
            "'User: ...\\nAssistant: ...' layout nor a 'User: ' prefix"
        )

    user_start = len(USER_PREFIX) if text.startswith(USER_PREFIX) else 0
    return _non_empty_segments(
        text,
        user_start,
        separator_at,
        separator_at + len(ROLE_SEPARATOR),
        len(text),
    )


def _non_empty_segments(
    text: str,
    user_start: int,
    user_end: int,
    assistant_start: int,
    assistant_end: int,
) -> list[tuple[str, int, int]]:
    segments = []
    for role, start, end in (
        (ROLE_USER, user_start, user_end),
        (ROLE_ASSISTANT, assistant_start, assistant_end),
    ):
        trimmed = _trim(text, start, end)
        if trimmed is not None:
            segments.append((role, trimmed[0], trimmed[1]))
    return segments


def evaluate_eligibility(
    word_count: int,
    named_entities: int,
    numeric_tokens: int,
) -> tuple[bool, str | None]:
    """A span is eligible iff 4-60 words AND >=1 entity or numeric token."""
    if word_count < MIN_SPAN_WORDS:
        return False, REJECT_TOO_SHORT
    if word_count > MAX_SPAN_WORDS:
        return False, REJECT_TOO_LONG
    if named_entities == 0 and numeric_tokens == 0:
        return False, REJECT_NO_CONTENT
    return True, None


def segment_episode(episode: dict) -> list[Span]:
    """Segment one episode into sentence-level spans with offsets and counts.

    Returns every span, eligible or not. Ineligible spans carry a rejection reason
    so the exclusion is auditable; they remain untouched in the raw store.
    """
    text = episode["text"]
    spans: list[Span] = []
    for role, segment_start, segment_end in role_segments(episode):
        segment_text = text[segment_start:segment_end]
        for local_start, local_end in _SEGMENTER.sentence_bounds(segment_text):
            start = segment_start + local_start
            end = segment_start + local_end
            span_text = text[start:end]
            word_count = _SEGMENTER.count_words(span_text)
            named_entities = _SEGMENTER.count_entities(span_text)
            numeric_tokens = count_numeric_tokens(span_text)
            eligible, reason = evaluate_eligibility(
                word_count, named_entities, numeric_tokens
            )
            spans.append(
                Span(
                    text=span_text,
                    start=start,
                    end=end,
                    episode_id=episode["id"],
                    turn_number=episode["turn_number"],
                    role=role,
                    word_count=word_count,
                    named_entities=named_entities,
                    numeric_tokens=numeric_tokens,
                    eligible=eligible,
                    rejection_reason=reason,
                )
            )
    return spans


def eligible_spans(episode: dict) -> list[Span]:
    return [span for span in segment_episode(episode) if span.eligible]


def assert_span_offsets_faithful(episode: dict, spans: list[Span]) -> None:
    """Every span must reproduce exactly from its source at its own offsets."""
    text = episode["text"]
    for span in spans:
        if text[span.start:span.end] != span.text:
            raise AssertionError(
                f"Span offsets do not round-trip for episode "
                f"{episode['id']} at [{span.start}:{span.end}]"
            )


def segmenter_name() -> str:
    _SEGMENTER._ensure_loaded()
    return _SEGMENTER.segmenter


def extractor_name() -> str:
    _SEGMENTER._ensure_loaded()
    return _SEGMENTER.extractor


def spacy_available() -> bool:
    return _SEGMENTER.spacy_available
