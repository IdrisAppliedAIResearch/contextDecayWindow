from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import spacy

from analysis.tc011_spread import (
    aspect_spread,
    chain_spread,
    extract_facets,
    facet_idf,
    logdet_spread,
)
from analysis.tc011_study import arm_disposition, family_disposition


def _episode(index: int, vector: tuple[float, ...], text: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        identity=f"e{index}",
        record={
            "id": f"e{index}",
            "turn_number": index,
            "user_message": text or f"user {index}",
            "assistant_message": f"assistant {index}",
            "embedding": np.asarray(vector, dtype=np.float32),
        },
    )


def _cell(kind: str) -> dict:
    positive = kind == "positive"
    neutral = kind == "neutral"
    return {
        "combined": {"gains": 3 if positive else 1, "losses": 1 if positive or neutral else 3, "net": 2 if positive else 0 if neutral else -2},
        "targeted": {"gains": 1, "losses": 1 if positive or neutral else 2, "net": 0 if positive or neutral else -1},
        "breadth": {"gains": 2 if positive else 1 if neutral else 0, "losses": 0 if positive else 1 if neutral else 2, "net": 2 if positive else 0 if neutral else -2},
        "breadth_identity": {"net_identities": 2 if positive else 0 if neutral else -2},
        "conversation_nets": {"a": 1 if positive else 0 if neutral else -1, "b": 1 if positive else 0, "c": 0, "d": 0},
    }


def test_registered_dispositions_are_reachable() -> None:
    assert arm_disposition({"16000": _cell("positive"), "32000": _cell("positive")}) == "WORKS"
    assert arm_disposition({"16000": _cell("positive"), "32000": _cell("neutral")}) == "CARRIES_SIGNAL"
    assert arm_disposition({"16000": _cell("negative"), "32000": _cell("negative")}) == "NO_POSITIVE_SIGNAL"
    assert family_disposition({"a": "WORKS"}) == "CANDIDATE_IDENTIFIED"
    assert family_disposition({"a": "CARRIES_SIGNAL"}) == "SIGNAL_ONLY"
    assert family_disposition({"a": "NO_POSITIVE_SIGNAL"}) == "NO_CANDIDATE"


def test_chain_variants_are_distinct_and_do_not_repeat() -> None:
    episodes = [
        _episode(0, (1.0, 0.0)),
        _episode(1, (0.95, 0.312)),
        _episode(2, (0.2, 0.98)),
        _episode(3, (0.94, 0.341)),
    ]
    matrix = np.stack([np.asarray(ep.record["embedding"], dtype=np.float64) for ep in episodes])
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    order = (0, 2, 3, 1)
    anchored = chain_spread(episodes, matrix, np.asarray((0.0, 1.0)), order, (0,), 10_000, anchored=True)
    pure = chain_spread(episodes, matrix, np.asarray((0.0, 1.0)), order, (0,), 10_000, anchored=False)
    assert len(set(anchored.order)) == len(anchored.order)
    assert len(set(pure.order)) == len(pure.order)
    assert anchored.order != pure.order
    assert anchored.stopping_reason == pure.stopping_reason == "no_complete_candidate_fits"


def test_logdet_and_aspect_have_monotone_registered_state() -> None:
    episodes = [
        _episode(0, (1.0, 0.0), "Alice paid $20 on Monday."),
        _episode(1, (0.0, 1.0), "Bob painted a mural in June."),
        _episode(2, (0.7, 0.7), "Carol bought three books."),
    ]
    matrix = np.stack([np.asarray(ep.record["embedding"], dtype=np.float64) for ep in episodes])
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    relevance = np.asarray((1.0, 0.7, 0.4))
    logdet = logdet_spread(episodes, matrix, relevance, (0, 1, 2), (0,), 10_000)
    assert len(set(logdet.order)) == len(logdet.order)
    assert all(left >= right for left, right in zip(logdet.auxiliary, logdet.auxiliary[1:]))

    nlp = spacy.load("en_core_web_sm")
    candidate_facets = tuple(extract_facets(doc) for doc in nlp.pipe([ep.record["user_message"] for ep in episodes]))
    idf, families = facet_idf(candidate_facets)
    aspect = aspect_spread(episodes, candidate_facets, idf, relevance, (0, 1, 2), (0,), 10_000)
    assert len(set(aspect.order)) == len(aspect.order)
    assert all(left <= right for left, right in zip(aspect.auxiliary, aspect.auxiliary[1:]))
    assert {"noun", "event", "entity", "number"} <= set(families)
