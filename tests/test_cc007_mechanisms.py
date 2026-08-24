from __future__ import annotations

import hashlib

import numpy as np
import pytest

from episodic._aspect import aspect_spread, extract_facets, facet_idf
from episodic._config import EpisodicConfig
from episodic._errors import EpisodicError
from episodic._packing import EMPTY_PAYLOAD_CHARS
from episodic._ranking import normalize_scores, rank_cc80, tokenize
from episodic._retrieval import retrieve_long_term


def _vector(index: int) -> np.ndarray:
    value = np.zeros(1024, dtype=np.float32)
    value[index % 1024] = 1.0
    return value


def _episode(index: int, user: str, assistant: str = "answer") -> dict:
    return {
        "id": hashlib.sha256(f"episode-{index}".encode()).hexdigest(),
        "turn_number": index + 1,
        "user_message": user,
        "assistant_message": assistant,
        "embedding": _vector(index),
    }


def test_cc80_tokenizer_and_minmax_contract() -> None:
    assert tokenize("Alpha_beta O'Brien re-entry 42") == ["alpha", "beta", "o'brien", "re-entry", "42"]
    assert np.allclose(normalize_scores((2.0, 4.0, 6.0)), (0.0, 0.5, 1.0))
    assert np.array_equal(normalize_scores((4.0, 4.0)), np.zeros(2))
    assert normalize_scores(()).size == 0


def test_cc80_ranks_by_frozen_convex_score() -> None:
    episodes = [
        _episode(0, "alpha rare"),
        _episode(1, "beta beta"),
        _episode(2, "gamma"),
    ]
    query = (_vector(0) + _vector(1)).astype(np.float32)
    ranking = rank_cc80(
        episodes,
        "beta",
        query,
        dense_weight=0.8,
        bm25_k1=1.2,
        bm25_b=0.75,
    )
    assert sorted(ranking.order) == [0, 1, 2]
    assert ranking.order[0] == 1
    assert all(0.0 <= score <= 1.0 for score in ranking.scores)


def test_retrieval_excludes_recent_and_continues_filling() -> None:
    episodes = [_episode(index, f"topic {index}", "x" * 80) for index in range(6)]
    result = retrieve_long_term(
        episodes=episodes,
        query_text="topic 5",
        query_embedding=_vector(5),
        budget=2_000,
        config=EpisodicConfig(),
        excluded_ids=[episodes[5]["id"], episodes[4]["id"]],
    )
    assert not ({episodes[5]["id"], episodes[4]["id"]} & set(result.selected_ids))
    assert result.selected_ids
    assert len(result.payload) <= 2_000


def test_empty_singleton_constant_and_zero_budget_are_total() -> None:
    config = EpisodicConfig()
    empty = retrieve_long_term(
        episodes=[], query_text="", query_embedding=_vector(0), budget=0, config=config
    )
    assert empty.selected_ids == ()
    singleton = retrieve_long_term(
        episodes=[_episode(0, "")],
        query_text="",
        query_embedding=_vector(0),
        budget=0,
        config=config,
    )
    assert singleton.selected_ids == ()
    assert singleton.payload == ""


def test_unknown_exclusion_and_duplicate_ids_fail_loudly() -> None:
    config = EpisodicConfig()
    episode = _episode(0, "alpha")
    with pytest.raises(EpisodicError):
        retrieve_long_term(
            episodes=[episode],
            query_text="alpha",
            query_embedding=_vector(0),
            budget=1_000,
            config=config,
            excluded_ids=["missing"],
        )
    with pytest.raises(EpisodicError):
        retrieve_long_term(
            episodes=[episode, dict(episode)],
            query_text="alpha",
            query_embedding=_vector(0),
            budget=1_000,
            config=config,
        )


def test_registered_parameters_cannot_silently_drift() -> None:
    assert EpisodicConfig().aspect_enabled is False
    assert EpisodicConfig().retrieval_budget_chars == 32_000
    with pytest.raises(EpisodicError):
        EpisodicConfig(semantic_dense_weight=0.7)
    with pytest.raises(EpisodicError):
        EpisodicConfig(aspect_share=0.4)


def test_aspect_state_is_monotone_and_reaches_a_stop() -> None:
    spacy = pytest.importorskip("spacy")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        pytest.skip("registered ASPECT parser model is not installed")
    episodes = [
        _episode(0, "Alice paid $20 on Monday."),
        _episode(1, "Bob painted a mural in June."),
        _episode(2, "Carol bought three books."),
    ]
    facets = tuple(extract_facets(nlp(f"{item['user_message']}\n{item['assistant_message']}")) for item in episodes)
    idf, _ = facet_idf(facets)
    trace = aspect_spread(
        episodes,
        facets,
        idf,
        (1.0, 0.7, 0.4),
        (0, 1, 2),
        (0,),
        10_000,
    )
    assert len(set(trace.order)) == len(trace.order)
    assert all(left <= right for left, right in zip(trace.covered_counts, trace.covered_counts[1:]))
    assert trace.stopping_reason in {"no_complete_candidate_fits", "no_positive_marginal"}


def test_aspect_no_fit_state_is_reachable() -> None:
    episode = _episode(0, "Alice paid $20.")
    trace = aspect_spread(
        [episode],
        [frozenset({"entity:PERSON:alice"})],
        {"entity:PERSON:alice": 1.0},
        (1.0,),
        (0,),
        (0,),
        EMPTY_PAYLOAD_CHARS,
    )
    assert trace.order == ()
    assert trace.stopping_reason == "no_complete_candidate_fits"
