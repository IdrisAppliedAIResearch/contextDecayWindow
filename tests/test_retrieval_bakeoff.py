from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.retrieval_bakeoff.classifier import classify_query
from src.retrieval_bakeoff.config import CORPORA
from src.retrieval_bakeoff.embedding_cache import EmbeddingCache
from src.retrieval_bakeoff.evaluation import (
    HoldoutEvaluator,
    advancement_decisions,
    validate_locked_artifacts,
)
from src.retrieval_bakeoff.leakage import assert_planted_violations
from src.retrieval_bakeoff.methods import build_method
from src.retrieval_bakeoff.models import (
    Candidate,
    Query,
    RankedCandidate,
    RetrievalResult,
)
from src.retrieval_bakeoff.presence import (
    evaluate_q11_reachability,
    load_q11_atomic_facts,
)
from src.retrieval_bakeoff.serialization import (
    pack_ranked_candidates,
    render_candidate_element,
    render_retrieval_block,
)


def _vector(index: int) -> np.ndarray:
    vector = np.zeros(1_024, dtype=np.float32)
    vector[index] = 1.0
    return vector


def _episode(
    candidate_id: str,
    *,
    turn: int = 1,
    topic: str = "topic_a",
    user: str = "user text",
    assistant: str = "assistant text",
    embedding: np.ndarray | None = None,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        source_episode_id=f"source_{candidate_id}",
        turn_number=turn,
        unit_type="episode",
        user_message=user,
        assistant_message=assistant,
        topic_id=topic,
        topic_label=topic,
        domain="domain",
        embedding=embedding if embedding is not None else _vector(0),
    )


def test_registered_query_classifier_rules() -> None:
    domains = CORPORA["c121_l"].domain_labels
    assert (
        classify_query("Across the four subject threads, list each item.", domains)
        == "enumeration"
    )
    assert classify_query("Pair these two findings.", domains) == "chained"
    assert classify_query("Which bearing was used?", domains) == "lookup"


def test_bm25_ranks_rare_exact_phrase_first() -> None:
    candidates = [
        _episode("a", user="common bridge words"),
        _episode("b", user="rare photophores mantle margin"),
    ]
    method = build_method("M3", candidates)
    ranked = method.rank(
        Query("q", "photophores mantle margin"),
        method.encode(
            Query("q", "photophores mantle margin"),
            CORPORA["c121_l"],
            lambda _: _vector(0),
        ),
    )
    assert ranked[0].candidate.candidate_id == "b"
    assert ranked[0].score > ranked[1].score


def test_m1_collapses_sources_and_applies_one_per_topic_floor() -> None:
    candidates = [
        _episode("a1", topic="a", embedding=_vector(0)),
        _episode("a2", topic="a", embedding=_vector(1)),
        _episode("b1", topic="b", embedding=_vector(2)),
    ]
    method = build_method("M1", candidates)
    ranked = method.rank(
        Query("q", "query"),
        type("Encoded", (), {"vectors": [_vector(0)]})(),
    )
    ordered = method.ordered_for_packing(ranked)
    assert [(item.candidate.candidate_id, phase) for item, phase in ordered] == [
        ("a1", "floor"),
        ("b1", "floor"),
        ("a2", "fill"),
    ]


def test_exact_serializer_skips_oversized_then_accepts_smaller() -> None:
    large = RankedCandidate(
        _episode("large", user="x" * 2_000),
        score=1.0,
    )
    small = RankedCandidate(_episode("small"), score=0.5)
    budget = len(render_retrieval_block("M2", [small]))
    packed = pack_ranked_candidates(
        "M2",
        [(large, "fill"), (small, "fill")],
        budget,
    )
    assert [item.candidate.candidate_id for item in packed.selected] == ["small"]
    assert len(packed.rendered_block) == budget
    assert packed.skipped_oversized == 1


def test_span_serializer_omits_episode_only_domain_attribute() -> None:
    span = Candidate(
        candidate_id="span",
        source_episode_id="source",
        turn_number=4,
        unit_type="span",
        span_text="verbatim span",
        role="user",
        span_start=6,
        span_end=19,
        topic_id="topic",
        topic_label="Topic",
        domain="hidden",
        embedding=_vector(0),
    )
    rendered = render_candidate_element(RankedCandidate(span, 0.25))
    assert 'source_episode_id="source"' in rendered
    assert 'domain="' not in rendered


def test_embedding_cache_batches_unique_missing_texts(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    class Embedder:
        def __call__(self, _: str) -> np.ndarray:
            raise AssertionError("Batch path should be used")

        def embed_many(self, texts: list[str]) -> list[np.ndarray]:
            calls.append(texts)
            return [_vector(index) for index, _ in enumerate(texts)]

    with EmbeddingCache(tmp_path / "cache.sqlite", "f" * 64) as cache:
        first = cache.get_or_embed_many(["a", "b", "a"], Embedder())
        second = cache.get_or_embed_many(["b", "a"], Embedder())
    assert calls == [["a", "b"]]
    assert np.array_equal(first[0], first[2])
    assert np.array_equal(first[0], second[1])


def test_measurement_evaluator_requires_source_provenance() -> None:
    candidate = _episode(
        "service-life",
        turn=12,
        user="The bridge uses a 100-year service life.",
    )
    ranked = RankedCandidate(candidate, score=0.9)
    block = render_retrieval_block("M2", [ranked])
    result = RetrievalResult(
        corpus_id="c121_l",
        method_id="M2",
        query=Query(
            "h121_l01",
            "What operating lifetime was specified?",
        ),
        budget=32_000,
        ranked_count=1,
        selected=[ranked],
        rendered_block=block,
    )
    row = HoldoutEvaluator("c121_l").evaluate(result)
    assert row["fact_recall_at_budget"] == 1.0
    assert row["domain_coverage"] == 1.0
    assert row["evaluation_status"] == "PASS"

    wrong_turn = ranked.candidate.__class__(
        **{
            **ranked.candidate.__dict__,
            "turn_number": 11,
        }
    )
    wrong_ranked = RankedCandidate(wrong_turn, score=0.9)
    result.selected = [wrong_ranked]
    result.rendered_block = render_retrieval_block("M2", [wrong_ranked])
    row = HoldoutEvaluator("c121_l").evaluate(result)
    assert row["fact_recall_at_budget"] == 0.0
    assert row["evaluation_status"] == "FAIL_PROVENANCE"


def test_locked_hashes_and_planted_leakage_gate(tmp_path: Path) -> None:
    assert validate_locked_artifacts()
    assert assert_planted_violations(tmp_path)["status"] == "PASS"


def test_q11_atomic_matrix_and_provenance_matching() -> None:
    facts = load_q11_atomic_facts()
    assert len(facts) == 17
    assert {fact.domain for fact in facts} == {
        "Civil engineering",
        "Renaissance art",
        "Monetary policy",
        "Marine biology",
    }
    candidate = _episode(
        "halcyon",
        turn=3,
        user="Halcyon Crossing has a main span of 847 meters.",
    )
    ranked = RankedCandidate(candidate, score=1.0)
    result = RetrievalResult(
        corpus_id="c121_l",
        method_id="M2",
        query=Query("development_q11_turn_120", "Across all four subjects"),
        budget=32_000,
        ranked_count=1,
        selected=[ranked],
        rendered_block=render_retrieval_block("M2", [ranked]),
    )
    row = evaluate_q11_reachability(result)
    assert row["matched_fact_count"] == 2
    assert row["domain_count"] == 1


def test_advancement_uses_exact_fraction_comparisons() -> None:
    rows = []
    for method_id in ("M1", "M2", "M3", "M4", "M5_span", "M6"):
        for query_class in ("lookup", "chained", "enumeration"):
            exact = "23/96" if query_class == "enumeration" else "1/2"
            rows.append(
                {
                    "method_id": method_id,
                    "query_class": query_class,
                    "fact_recall_exact": exact,
                }
            )
    decisions = {
        row["method_id"]: row for row in advancement_decisions(rows)
    }
    assert decisions["M6"]["winning_classes"] == []
    assert decisions["M6"]["regressing_classes"] == []
    assert decisions["M6"]["advances"] is False


def test_negative_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        pack_ranked_candidates("M2", [], -1)
