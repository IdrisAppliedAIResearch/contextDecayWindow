from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from episodic._aspect import aspect_spread, extract_facets, facet_idf
from episodic._config import EpisodicConfig
from episodic._context import build_chat_context
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


def test_recency_is_additive_to_the_retrieval_budget_and_deduplicated() -> None:
    episodes = [
        _episode(index, f"topic {index}", "detail " * 40) for index in range(40)
    ]
    block, report = build_chat_context(
        episodes=episodes,
        query_text="topic 39",
        query_embedding=_vector(39),
        budget=500,
        config=EpisodicConfig(),
    )
    assert report.recency_count == 32
    assert report.recent_ids == tuple(item["id"] for item in episodes[-32:])
    assert report.retrieval_chars_delivered <= 500
    assert len(block) > 500
    assert block.count("<episode turn=") == report.episodes_delivered
    assert report.stm_count == report.recency_count
    assert report.coverage_count == report.aspect_count == 0


def test_zero_retrieval_budget_still_returns_all_recent_continuity() -> None:
    episodes = [_episode(index, f"topic {index}") for index in range(35)]
    block, report = build_chat_context(
        episodes=episodes,
        query_text="topic 0",
        query_embedding=_vector(0),
        budget=0,
        config=EpisodicConfig(),
    )
    assert report.recency_count == 32
    assert report.semantic_count == report.aspect_count == 0
    assert report.retrieval_chars_delivered == 0
    assert block.count("<episode turn=") == 32
    assert len(block) > 0


def test_negative_public_retrieval_budget_is_rejected() -> None:
    with pytest.raises(EpisodicError):
        build_chat_context(
            episodes=[_episode(0, "topic")],
            query_text="topic",
            query_embedding=_vector(0),
            budget=-1,
            config=EpisodicConfig(),
        )


def test_stores_shorter_than_recency_window_do_not_repeat_long_term() -> None:
    episodes = [_episode(index, f"topic {index}") for index in range(8)]
    block, report = build_chat_context(
        episodes=episodes,
        query_text="topic 0",
        query_embedding=_vector(0),
        budget=32_000,
        config=EpisodicConfig(),
    )
    assert report.recency_count == report.episodes_delivered == 8
    assert report.semantic_count == report.aspect_count == 0
    assert block.count("<episode turn=") == 8


def test_activation_is_guarded_by_the_committed_passing_parity_artifact() -> None:
    artifact = (
        Path(__file__).resolve().parents[1]
        / "experiments/components/episodic_chat/artifacts/cc007/preflight.json"
    )
    result = json.loads(artifact.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["pf3"]["gate_precedes_activation"] is True
    assert result["pf6"] == {
        "actual_trace_groups": 4355,
        "expected_trace_groups": 4355,
        "first_mismatches": [],
        "mismatches": 0,
    }


def test_opt_in_aspect_runs_the_protected_public_branch() -> None:
    spacy = pytest.importorskip("spacy")
    try:
        spacy.load("en_core_web_sm")
    except OSError:
        pytest.skip("registered ASPECT parser model is not installed")
    episodes = []
    for index in range(40):
        episode = _episode(
            index,
            f"Person {index} visited city {index} on Monday and bought {index + 1} books.",
            "The visit was recorded.",
        )
        vector = np.zeros(1024, dtype=np.float32)
        vector[0] = 1.0
        vector[index + 1] = 0.05 + index / 100.0
        episode["embedding"] = vector
        episodes.append(episode)
    block, report = build_chat_context(
        episodes=episodes,
        query_text="Who visited a city and what did they buy?",
        query_embedding=_vector(0),
        budget=4_000,
        config=EpisodicConfig(recency_window_n=2, aspect_enabled=True),
    )
    assert report.aspect_enabled is True
    assert report.aspect_count > 0
    assert report.semantic_count > 0
    assert report.retrieval_chars_delivered <= 4_000
    assert block.count("<episode turn=") == report.episodes_delivered
