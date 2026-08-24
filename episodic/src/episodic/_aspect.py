"""Frozen TC-011 static ASPECT protected-spread mechanism."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping, Sequence

import numpy as np

from ._errors import EpisodicError
from ._packing import EMPTY_PAYLOAD_CHARS
from ._ranking import searchable_text
from ._selection import additive_weight

OBJECT_DEPENDENCIES = frozenset(
    {"dobj", "obj", "pobj", "attr", "oprd", "dative", "nsubjpass"}
)


@dataclass(frozen=True)
class AspectTrace:
    order: tuple[int, ...]
    marginal: tuple[float, ...]
    covered_counts: tuple[int, ...]
    solo_chars: int
    stopping_reason: str


def _normalized_words(tokens: Any) -> str:
    words = [
        token.lemma_.casefold()
        for token in tokens
        if not token.is_space
        and not token.is_punct
        and (not token.is_stop or token.like_num)
    ]
    return "_".join(words)


def extract_facets(doc: Any) -> frozenset[str]:
    """Extract the exact six registered deterministic facet families."""

    found: set[str] = set()
    for entity in doc.ents:
        value = _normalized_words(entity)
        if value:
            found.add(f"entity:{entity.label_}:{value}")
            if entity.label_ == "DATE":
                found.add(f"date:{value}")
    for token in doc:
        if token.like_num:
            found.add(f"number:{token.lower_}")
        if token.pos_ == "VERB":
            found.add(f"event:{token.lemma_.casefold()}")
        if (
            token.dep_ in OBJECT_DEPENDENCIES
            and token.head.pos_ in {"VERB", "AUX"}
        ):
            value = _normalized_words(token.subtree)
            if value:
                found.add(
                    f"relation:{token.head.lemma_.casefold()}:{token.dep_}:{value}"
                )
    for chunk in doc.noun_chunks:
        value = _normalized_words(chunk)
        if value:
            found.add(f"noun:{value}")
    return frozenset(found)


def facet_idf(
    candidate_facets: Sequence[frozenset[str]],
) -> tuple[dict[str, float], dict[str, int]]:
    count = len(candidate_facets)
    document_frequency = Counter(
        facet for candidate in candidate_facets for facet in sorted(candidate)
    )
    idf = {
        facet: math.log((count + 1) / (frequency + 1)) + 1.0
        for facet, frequency in document_frequency.items()
    }
    families = Counter(
        facet.split(":", 1)[0]
        for candidate in candidate_facets
        for facet in sorted(candidate)
    )
    return idf, dict(families)


@lru_cache(maxsize=None)
def _load_spacy_model(model_name: str):
    try:
        import spacy
    except ImportError as error:  # pragma: no cover - exercised in clean venv
        raise EpisodicError(
            "ASPECT requires the optional parser dependencies; install "
            "episodic-chat[aspect]"
        ) from error
    try:
        return spacy.load(model_name)
    except OSError as error:
        raise EpisodicError(
            f"ASPECT requires parser model {model_name!r}; install "
            "episodic-chat[aspect]"
        ) from error


def prepare_facets(
    episodes: Sequence[dict], model_name: str
) -> tuple[tuple[frozenset[str], ...], dict[str, float], dict[str, int]]:
    nlp = _load_spacy_model(model_name)
    docs = nlp.pipe([searchable_text(episode) for episode in episodes], batch_size=64)
    facets = tuple(extract_facets(doc) for doc in docs)
    idf, families = facet_idf(facets)
    return facets, idf, families


def aspect_spread(
    episodes: Sequence[dict],
    candidate_facets: Sequence[frozenset[str]],
    idf: Mapping[str, float],
    relevance_scores: Sequence[float],
    relevance_order: Sequence[int],
    initial: Sequence[int],
    allowance: int,
    *,
    excluded: Sequence[int] = (),
) -> AspectTrace:
    """Greedy CC80-weighted saturation, byte-equivalent on TC-011 inputs."""

    count = len(episodes)
    if sorted(relevance_order) != list(range(count)):
        raise EpisodicError("CC80 order must permute the store")
    scores = np.asarray(relevance_scores, dtype=np.float64)
    if len(candidate_facets) != count or scores.shape != (count,):
        raise EpisodicError("ASPECT input shape drift")
    if not initial or len(set(initial)) != len(initial):
        raise EpisodicError("ASPECT requires a unique nonempty semantic seed")
    rank = {candidate: position for position, candidate in enumerate(relevance_order)}

    covered: dict[str, float] = {}
    for candidate in initial:
        for facet in sorted(candidate_facets[candidate]):
            covered[facet] = max(
                covered.get(facet, 0.0), scores[candidate] * idf[facet]
            )
    excluded_set = set(initial) | set(excluded)
    chosen: list[int] = []
    marginal: list[float] = []
    covered_counts: list[int] = []
    spent = EMPTY_PAYLOAD_CHARS
    while True:
        fit = [
            index
            for index in range(count)
            if index not in excluded_set
            and spent + additive_weight(episodes[index]) <= allowance
        ]
        if not fit:
            reason = "no_complete_candidate_fits"
            break
        options = []
        for candidate in fit:
            raw = sum(
                max(
                    0.0,
                    scores[candidate] * idf[facet] - covered.get(facet, 0.0),
                )
                for facet in sorted(candidate_facets[candidate])
            )
            ratio = raw / additive_weight(episodes[candidate])
            # This tuple and max operation intentionally match TC-011 exactly.
            options.append((ratio, -rank[candidate], candidate, raw))
        _, _, candidate, raw = max(options)
        if raw <= 1e-12:
            reason = "no_positive_marginal"
            break

        prior = dict(covered)
        chosen.append(candidate)
        excluded_set.add(candidate)
        marginal.append(raw)
        spent += additive_weight(episodes[candidate])
        for facet in sorted(candidate_facets[candidate]):
            covered[facet] = max(
                covered.get(facet, 0.0), scores[candidate] * idf[facet]
            )
        if any(covered[key] + 1e-12 < value for key, value in prior.items()):
            raise EpisodicError("ASPECT coverage decreased")
        covered_counts.append(len(covered))

    return AspectTrace(
        order=tuple(chosen),
        marginal=tuple(marginal),
        covered_counts=tuple(covered_counts),
        solo_chars=spent,
        stopping_reason=reason,
    )


__all__ = [
    "AspectTrace",
    "OBJECT_DEPENDENCIES",
    "aspect_spread",
    "extract_facets",
    "facet_idf",
    "prepare_facets",
]
