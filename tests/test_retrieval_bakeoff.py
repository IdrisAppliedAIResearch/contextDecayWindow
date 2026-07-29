from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from src.retrieval_bakeoff.classifier import classify_query
from src.retrieval_bakeoff.ann import (
    benchmark_ann,
    build_scaled_vector_store,
)
from src.retrieval_bakeoff.config import CORPORA, CorpusSpec
from src.retrieval_bakeoff.embedding_cache import EmbeddingCache
from src.retrieval_bakeoff.evaluation import (
    HoldoutEvaluator,
    advancement_decisions,
    validate_locked_artifacts,
)
from src.retrieval_bakeoff.graph import AssociativeGraphIndex, GraphRetriever
from src.retrieval_bakeoff.graph_analysis import analyze_graph_results
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
from src.retrieval_bakeoff.progressive import (
    ProgressiveIndex,
    inspect_orthogonal_axes,
)
from src.retrieval_bakeoff.serialization import (
    pack_ranked_candidates,
    render_candidate_element,
    render_retrieval_block,
)
from src.retrieval_bakeoff.tier5_analysis import analyze_tier5


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
    domain: str = "domain",
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
        domain=domain,
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
    assert row["oldest_quartile_turn_max"] == 28
    assert row["old_required_fact_ids"]
    assert row["old_fact_miss_rate"] == 0.0

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
    assert row["old_fact_miss_rate"] == 1.0
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


def test_associative_graph_edges_and_traversal(tmp_path: Path) -> None:
    prompt_root = tmp_path / "constructed_prompts"
    prompt_root.mkdir()
    prompts = {
        1: "<recent_context/><retrieved_stm/><retrieved_ltm/>",
        2: (
            '<recent_context><episode turn="1"/></recent_context>'
            "<retrieved_stm/><retrieved_ltm/>"
        ),
        3: (
            "<recent_context/>"
            '<retrieved_stm><episode turn="1"/><episode turn="2"/>'
            "</retrieved_stm><retrieved_ltm/>"
        ),
    }
    for turn, prompt in prompts.items():
        (prompt_root / f"turn_{turn:03d}.txt").write_text(
            prompt,
            encoding="utf-8",
        )
    spec = CorpusSpec(
        corpus_id="tiny",
        database_path=tmp_path / "unused.db",
        eligible_turn_min=1,
        eligible_turn_max=3,
        query_manifest=tmp_path / "unused.json",
        domain_labels=("domain",),
        has_distilled_ltm=False,
        advancement_primary=False,
        run_directory=tmp_path,
    )
    candidates = [
        _episode("a", turn=1, topic="same", embedding=_vector(0)),
        _episode("b", turn=2, topic="same", embedding=_vector(1)),
        _episode("c", turn=3, topic="other", embedding=_vector(2)),
    ]
    graph = AssociativeGraphIndex(spec, candidates)
    assert graph.components["E1"].undirected_edge_count == 2
    assert graph.components["E2"].undirected_edge_count == 1
    assert graph.components["E3"].undirected_edge_count == 0
    assert graph.components["E4"].undirected_edge_count == 1
    assert graph.components["E1"].connected_component_count == 1

    propagated = graph.components["E1"].transition.propagate(
        np.asarray([1.0, 0.0, 0.0])
    )
    assert np.array_equal(propagated, np.asarray([0.0, 1.0, 0.0]))

    result = GraphRetriever(graph, lambda _: _vector(0)).retrieve(
        "E1",
        1,
        Query("tiny_query", "find a"),
        repetitions=2,
    )
    assert result.method_id == "G_E1_d1"
    assert result.selected[0].candidate.candidate_id == "b"
    assert result.delivered_characters <= 32_000
    assert result.benchmark_repetitions == 2


def test_graph_advancement_uses_exact_recall_and_old_fact_baseline() -> None:
    graph_rows = []
    baseline_rows = []
    class_counts = {
        "lookup": (3, 4),
        "chained": (1, 2),
        "enumeration": (1, 2),
    }
    for corpus_id in ("c121_l", "c1000_l"):
        for query_class, (matched, required) in class_counts.items():
            common = {
                "corpus_id": corpus_id,
                "query_class": query_class,
                "required_fact_count": required,
                "domain_coverage": matched / required,
                "precision_proxy": 0.1,
                "delivered_characters": 1_000,
                "latency_ms": 2.0,
                "index_build_ms": 3.0,
                "old_required_fact_ids": ["old"],
            }
            graph_rows.append(
                {
                    **common,
                    "method_id": "G_E1_d1",
                    "matched_fact_count": matched,
                    "old_matched_fact_ids": ["old"],
                }
            )
            baseline_rows.append(
                {
                    **common,
                    "method_id": "M1",
                    "matched_fact_count": 1,
                    "required_fact_count": 2,
                    "old_matched_fact_ids": [],
                }
            )
    tier2 = {
        "pooled_class": [
            {
                "method_id": "M1",
                "query_class": query_class,
                "fact_recall_exact": "1/2",
            }
            for query_class in class_counts
        ]
    }
    benchmark = {
        "component_slopes": {
            component: {"log10_slope": 0.5}
            for component in ("E1", "E2", "E3", "E4")
        }
    }
    analysis = analyze_graph_results(
        graph_rows,
        tier2_corrected_summary=tier2,
        baseline_rows=baseline_rows,
        update_benchmark=benchmark,
    )
    assert analysis["gate_passes"] is True
    assert analysis["advancing_methods"] == ["G_E1_d1"]
    lookup = next(
        row
        for row in analysis["old_fact_comparison"]["graph"]
        if row["query_class"] == "lookup"
    )
    assert lookup["old_fact_miss_rate_exact"] == "0"
    assert lookup["flat_m1_old_fact_miss_rate"] == 1.0
    assert lookup["delta_from_flat_m1"] == -1.0


def test_ann_registered_path_and_synthetic_provenance(tmp_path: Path) -> None:
    candidates = [
        _episode(
            f"ann_{index}",
            turn=index + 1,
            embedding=_vector(index),
        )
        for index in range(120)
    ]
    real = build_scaled_vector_store(candidates, 120)
    assert real.real_count == 120
    assert real.synthetic_count == 0
    result = benchmark_ann(
        real,
        [_vector(index) for index in range(24)],
        tmp_path,
    )
    assert result["scale"] == 120
    assert len(result["exact_query_samples_ns"]) == 25
    assert len(result["hnsw_query_samples_ns"]) == 25
    assert 0.0 <= result["recall_at_10"] <= 1.0

    padded = build_scaled_vector_store(candidates, 1_000)
    provenance = list(padded.provenance_rows())
    assert padded.synthetic_count == 880
    assert len(provenance) == 1_000
    assert sum(row["synthetic"] for row in provenance) == 880
    assert np.allclose(
        np.linalg.norm(padded.vectors, axis=1),
        1.0,
        atol=1e-5,
    )


def test_topic_validation_rejects_collapsed_high_purity_axis(
    tmp_path: Path,
) -> None:
    spec, candidates = _progressive_fixture(tmp_path, collapsed=True)
    axes = inspect_orthogonal_axes(spec, candidates)
    topic = axes.report["topic_axis"]
    assert topic["macro_domain_to_topic_purity_exact"] == "1"
    assert topic["distinct_dominant_topic_count"] == 1
    assert topic["status"] == "NOT_EVALUABLE"
    assert "dominant_topics_not_distinct" in topic["invalid_reasons"]


def test_progressive_search_runs_valid_orthogonal_tiers(
    tmp_path: Path,
) -> None:
    spec, candidates = _progressive_fixture(tmp_path, collapsed=False)
    index = ProgressiveIndex(spec, candidates)
    assert index.axes.report["topic_axis"]["status"] == "VALID"
    assert index.axes.report["pinned_rule_axis"]["status"] == "VALID"
    outcome = index.retrieve(
        "P_recency_topic_rules",
        Query("q", "find topic zero"),
        lambda _: _vector(0),
        repetitions=2,
    )
    assert outcome.searched_tiers == [
        "hot",
        "rules",
        "topic",
        "warm",
        "cold",
    ]
    assert outcome.stop_reason == "exhausted_cold"
    assert outcome.selected_topic_id == "topic_0"
    selected_sources = [
        item.candidate.source_episode_id for item in outcome.result.selected
    ]
    assert len(selected_sources) == len(set(selected_sources))
    assert outcome.result.delivered_characters <= 32_000


def test_tier5_analysis_uses_matched_cells_and_exact_dominance() -> None:
    def row(
        corpus_id: str,
        method_id: str,
        query_id: str,
        *,
        budget: int = 32_000,
        latency: float = 2.0,
    ) -> dict:
        return {
            "corpus_id": corpus_id,
            "method_id": method_id,
            "query_id": query_id,
            "query_class": "lookup",
            "budget": budget,
            "required_fact_count": 1,
            "matched_fact_count": 1,
            "domain_coverage": 1.0,
            "precision_proxy": 0.1,
            "delivered_characters": budget - 1,
            "selected_count": 1,
            "latency_ms": latency,
            "old_required_fact_ids": ["old"],
            "old_matched_fact_ids": ["old"],
        }

    budget_rows = [
        row(corpus, "M3", f"{corpus}_{budget}_{index}", budget=budget)
        for corpus in ("c121_l", "c1000_l")
        for budget in (32_000, 64_000, 160_000, 320_000)
        for index in range(24)
    ]
    progressive_rows = [
        {
            **row(corpus, "P_recency", f"q_{corpus}"),
            "searched_tiers": ["hot"],
            "stop_reason": "threshold_after_hot",
        }
        for corpus in ("c121_l", "c1000_l")
    ]
    graph_rows = [
        row(corpus, method, f"q_{corpus}", latency=1.0)
        for method in ("G_E1_E3_d1", "G_E3_d2", "G_E3_d3")
        for corpus in ("c121_l", "c1000_l")
    ]
    analysis = analyze_tier5(
        budget_rows=budget_rows,
        progressive_rows=progressive_rows,
        graph_rows=graph_rows,
        ann_results=[
            {"recall_at_10": 1.0, "recall_at_50": 1.0}
            for _ in range(4)
        ],
        axis_reports={},
    )
    assert (
        analysis["T5.0_budget_multiples"][
            "fact_recall_collapse_above_2x"
        ]
        is False
    )
    comparison = analysis["T5.4_tiering_comparison"]
    assert comparison["any_depth_matches_or_beats_partition"] is True
    assert all(
        item["query_count"] == 2 for item in comparison["comparisons"]
    )


def _progressive_fixture(
    tmp_path: Path,
    *,
    collapsed: bool,
) -> tuple[CorpusSpec, list[Candidate]]:
    database = tmp_path / "study.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE topics (
            id TEXT PRIMARY KEY,
            centroid BLOB NOT NULL
        );
        CREATE TABLE rule_store (
            id TEXT PRIMARY KEY,
            episode_id TEXT NOT NULL,
            rule_summary TEXT NOT NULL,
            turn_number INTEGER NOT NULL
        );
        """
    )
    domains = (
        "civil_engineering",
        "renaissance_art",
        "monetary_policy",
        "marine_biology",
    )
    topic_ids = ["topic_0"] if collapsed else [
        f"topic_{index}" for index in range(4)
    ]
    for index, topic_id in enumerate(topic_ids):
        connection.execute(
            "INSERT INTO topics (id, centroid) VALUES (?, ?)",
            (topic_id, _vector(index).tobytes()),
        )
    rule = "Always number technical lists."
    connection.execute(
        """
        INSERT INTO rule_store (id, episode_id, rule_summary, turn_number)
        VALUES ('rule_1', 'candidate_0', ?, 1)
        """,
        (rule,),
    )
    connection.commit()
    connection.close()

    candidates = []
    for index in range(12):
        domain_index = index % 4
        topic_id = "topic_0" if collapsed else f"topic_{domain_index}"
        candidates.append(
            _episode(
                f"candidate_{index}",
                turn=index + 1,
                topic=topic_id,
                user=(
                    rule
                    if index == 0
                    else f"source text {index}"
                ),
                embedding=_vector(domain_index),
                domain=domains[domain_index],
            )
        )
    spec = CorpusSpec(
        corpus_id="c121_l",
        database_path=database,
        eligible_turn_min=1,
        eligible_turn_max=12,
        query_manifest=tmp_path / "unused.json",
        domain_labels=("domain",),
        has_distilled_ltm=False,
        advancement_primary=True,
        run_directory=tmp_path,
    )
    return spec, candidates
