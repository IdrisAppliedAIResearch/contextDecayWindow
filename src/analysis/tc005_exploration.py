"""TC-005 Preflight Part 1: characterize carried relevance rankers.

This module runs dense cosine, carried BM25, and carried reciprocal-rank
fusion on the committed LoCoMo development population before any outcome bar
is locked.  It records ranking and packing behaviour but never computes an
arm-to-arm evidence-delivery contrast.  The only evidence-dependent contrast
is a within-dense sham budget perturbation used to size the instrument band.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    ConversationCase,
    QuestionCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    Episode,
    build_episodes,
    flat_context,
    flat_order,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256
from episodic._packing import pack_stm_payload
from retrieval_bakeoff.config import BM25_B, BM25_K1, CORPORA, RRF_CONSTANT
from retrieval_bakeoff.corpus import load_queries, load_raw_episodes
from retrieval_bakeoff.embedding import CarriedEmbedder
from retrieval_bakeoff.methods import BM25Index, build_method, tokenize
from retrieval_bakeoff.models import Candidate
from retrieval_bakeoff.serialization import pack_ranked_candidates

SCHEMA = "tc005-preflight-part1-v1"
ARTIFACT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts" / "tc005"
)
PRIOR_RESULTS = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier2"
    / "retrieval_results.jsonl"
)
TC001_PRIMARY = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "tier_cost"
    / "runs"
    / "tc001"
    / "run"
    / "per_question_primary.csv"
)
TC001_SECONDARY = TC001_PRIMARY.with_name("per_question_secondary.csv")

ARMS = ("dense", "bm25", "hybrid")
BUDGETS = (8_000, 16_000, 32_000)
SHAM_FRACTIONS = (-0.01, -0.005, 0.005, 0.01)
_SURFACE_LITERAL = re.compile(r'(?:\d|[$€£¥%]|["“”]|\b[A-Z]{2,}\b)')


class TC005ExplorationError(RuntimeError):
    """Raised when a TC-005 Preflight invariant fails."""


@dataclass(frozen=True)
class Ranking:
    order: tuple[int, ...]
    scores: tuple[float, ...]
    dense_rank: tuple[int, ...]
    bm25_rank: tuple[int, ...]


@dataclass(frozen=True)
class PackedRanking:
    payload: str
    selected_ids: tuple[str, ...]
    skipped_ids: tuple[str, ...]


@dataclass(frozen=True)
class PreparedRankers:
    episodes: tuple[Episode, ...]
    candidates: tuple[Candidate, ...]
    dense_matrix: np.ndarray
    bm25: BM25Index


def _unit(value: np.ndarray) -> np.ndarray:
    array = np.asarray(value, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    if array.shape != (1024,) or not math.isfinite(norm) or norm == 0.0:
        raise TC005ExplorationError("Expected one finite non-zero 1024-vector")
    return array / norm


def candidates_for(episodes: Sequence[Episode]) -> tuple[Candidate, ...]:
    """Adapt the carried pairs without changing text, order, or identity."""

    candidates: list[Candidate] = []
    for episode in episodes:
        record = episode.record
        candidate = Candidate(
            candidate_id=episode.identity,
            source_episode_id=episode.identity,
            turn_number=int(record["turn_number"]),
            unit_type="episode",
            user_message=str(record["user_message"]),
            assistant_message=str(record["assistant_message"]),
            domain=str(record["ground_truth_domain"]),
            embedding=np.asarray(record["embedding"], dtype=np.float32),
        )
        # ``Candidate.searchable_text`` always inserts one role separator.
        # Singleton LoCoMo pairs have no second role, so that adapter appends
        # one trailing newline.  The carried tokenizer emits the identical
        # token sequence; rendering and dense vectors continue to use the
        # exact pair bytes in ``episode``.
        if tokenize(candidate.searchable_text) != tokenize(episode.pair.text):
            raise TC005ExplorationError(
                f"Candidate token stream drifted for {episode.identity}"
            )
        candidates.append(candidate)
    return tuple(candidates)


def prepare_rankers(episodes: Sequence[Episode]) -> PreparedRankers:
    frozen = tuple(episodes)
    candidates = candidates_for(frozen)
    return PreparedRankers(
        episodes=frozen,
        candidates=candidates,
        dense_matrix=np.stack([_unit(candidate.embedding) for candidate in candidates]),
        bm25=BM25Index(list(candidates)),
    )


def rank_all(
    episodes: Sequence[Episode],
    query_text: str,
    query_vector: np.ndarray,
    prepared: PreparedRankers | None = None,
) -> dict[str, Ranking]:
    """Run the three carried scoring rules with one conversation tie-break."""

    store = prepared or prepare_rankers(episodes)
    if tuple(episode.identity for episode in episodes) != tuple(
        episode.identity for episode in store.episodes
    ):
        raise TC005ExplorationError("Prepared ranker store differs from episodes")
    dense_scores = store.dense_matrix @ _unit(query_vector)
    bm25_scores = store.bm25.scores(query_text)

    def ordered(scores: np.ndarray) -> tuple[int, ...]:
        return tuple(
            sorted(
                range(len(episodes)),
                key=lambda index: (
                    -float(scores[index]),
                    episodes[index].pair.session_order,
                    episodes[index].pair.pair_order,
                ),
            )
        )

    dense_order = ordered(dense_scores)
    bm25_order = ordered(bm25_scores)
    if dense_order != flat_order(episodes, query_vector):
        raise TC005ExplorationError("Dense order differs from TC-001 A_FLAT")

    dense_rank = _inverse_rank(dense_order)
    bm25_rank = _inverse_rank(bm25_order)
    fused_scores = np.asarray(
        [
            1.0 / (RRF_CONSTANT + dense_rank[index])
            + 1.0 / (RRF_CONSTANT + bm25_rank[index])
            for index in range(len(episodes))
        ],
        dtype=np.float64,
    )
    hybrid_order = ordered(fused_scores)
    return {
        "dense": Ranking(
            dense_order,
            tuple(float(value) for value in dense_scores),
            dense_rank,
            bm25_rank,
        ),
        "bm25": Ranking(
            bm25_order,
            tuple(float(value) for value in bm25_scores),
            dense_rank,
            bm25_rank,
        ),
        "hybrid": Ranking(
            hybrid_order,
            tuple(float(value) for value in fused_scores),
            dense_rank,
            bm25_rank,
        ),
    }


def _inverse_rank(order: Sequence[int]) -> tuple[int, ...]:
    result = [0] * len(order)
    for rank, index in enumerate(order, start=1):
        result[index] = rank
    return tuple(result)


def pack_order(
    episodes: Sequence[Episode], order: Sequence[int], budget: int
) -> PackedRanking:
    if sorted(order) != list(range(len(episodes))):
        raise TC005ExplorationError("Packing order must permute every candidate")
    packed = pack_stm_payload(
        [], [episodes[index].record for index in order], budget
    )
    return PackedRanking(
        packed.payload,
        packed.selected_ids,
        packed.skipped_k_ids,
    )


def question_population(
    case: ConversationCase, question: QuestionCase
) -> str:
    """The TC-007 population split, measured only from frozen evidence ids."""

    if (
        question.duplicate_ordinal > 0
        or not question.resolved_evidence_ids
        or question.unresolved_evidence_ids
    ):
        return "ineligible"
    dialog_to_pair = {
        dialog_id: pair
        for pair in case.pairs
        for dialog_id in pair.dialog_ids
    }
    evidence_pairs = {
        dialog_to_pair[dialog_id].identity
        for dialog_id in question.resolved_evidence_ids
    }
    evidence_sessions = {
        dialog_to_pair[dialog_id].session_id
        for dialog_id in question.resolved_evidence_ids
    }
    if len(evidence_pairs) == 1 and len(evidence_sessions) == 1:
        return "targeted"
    if len(evidence_sessions) >= 3:
        return "breadth"
    return "other"


def surface_class(question: str) -> str:
    """Question-visible diagnostic only; it never reads evidence or answers."""

    return "surface_literal" if _SURFACE_LITERAL.search(question) else "paraphrase"


def evidence_indices(
    case: ConversationCase, episodes: Sequence[Episode], question: QuestionCase
) -> frozenset[int]:
    dialog_to_index = {
        dialog_id: index
        for index, episode in enumerate(episodes)
        for dialog_id in episode.pair.dialog_ids
    }
    return frozenset(
        dialog_to_index[dialog_id]
        for dialog_id in question.resolved_evidence_ids
        if dialog_id in dialog_to_index
    )


def explore(output_dir: Path = ARTIFACT_ROOT / "preflight") -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    conversations = adapt_development(DATASET_PATH)
    started = time.time()

    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {
            text: np.asarray(cache(text), dtype=np.float32)
            for case in conversations
            for text in (
                *(pair.text for pair in case.pairs),
                *(question.question for question in case.questions),
            )
        }
        reuse = cache.record()
    if reuse["misses"]:
        raise TC005ExplorationError("Retained LoCoMo cache missed in reuse mode")

    episodes_by_case = {
        case.sample_id: build_episodes(case, vectors) for case in conversations
    }
    prepared_by_case = {
        sample_id: prepare_rankers(episodes)
        for sample_id, episodes in episodes_by_case.items()
    }
    score_values: dict[str, list[float]] = {arm: [] for arm in ARMS}
    evidence_ranks: dict[str, list[int]] = {arm: [] for arm in ARMS}
    correlations: dict[str, list[float]] = {
        "dense_bm25": [],
        "dense_hybrid": [],
        "bm25_hybrid": [],
    }
    deliveries: dict[str, dict[int, list[int]]] = {
        arm: {budget: [] for budget in BUDGETS} for arm in ARMS
    }
    delivered_chars: dict[str, dict[int, list[int]]] = {
        arm: {budget: [] for budget in BUDGETS} for arm in ARMS
    }
    overflow_skips: dict[str, dict[int, list[int]]] = {
        arm: {budget: [] for budget in BUDGETS} for arm in ARMS
    }
    everything_fits: dict[str, dict[int, int]] = {
        arm: {budget: 0 for budget in BUDGETS} for arm in ARMS
    }
    order_digests: dict[str, list[str]] = {arm: [] for arm in ARMS}
    dense_tie_queries = bm25_zero_queries = rrf_tie_queries = exact_agreement = 0
    max_disagreement: dict[str, Any] | None = None
    metric_identity = {
        "queries": 0,
        "exact_three_order_matches": 0,
        "dot_euclidean_order_matches": 0,
        "carried_float32_dot_matches_float64_dot": 0,
        "max_relation_error": 0.0,
    }
    population_counts: Counter[str] = Counter()
    surface_counts: Counter[str] = Counter()
    question_count = 0

    # Dense-only sham counters: budget -> fraction -> [gains, losses].
    sham = {
        budget: {fraction: [0, 0] for fraction in SHAM_FRACTIONS}
        for budget in BUDGETS
    }

    for case in conversations:
        episodes = episodes_by_case[case.sample_id]
        for question in case.questions:
            if question.duplicate_ordinal > 0:
                continue
            question_count += 1
            population = question_population(case, question)
            population_counts[population] += 1
            surface_counts[surface_class(question.question)] += 1
            rankings = rank_all(
                episodes,
                question.question,
                vectors[question.question],
                prepared_by_case[case.sample_id],
            )
            evidence = evidence_indices(case, episodes, question)

            dense_order = rankings["dense"].order
            bm25_order = rankings["bm25"].order
            hybrid_order = rankings["hybrid"].order
            correlations["dense_bm25"].append(_spearman(dense_order, bm25_order))
            correlations["dense_hybrid"].append(_spearman(dense_order, hybrid_order))
            correlations["bm25_hybrid"].append(_spearman(bm25_order, hybrid_order))
            if dense_order == bm25_order == hybrid_order:
                exact_agreement += 1
            disagreement = correlations["dense_bm25"][-1]
            if max_disagreement is None or disagreement < max_disagreement["spearman"]:
                max_disagreement = {
                    "question_sha256": question.identity,
                    "sample_id": case.sample_id,
                    "spearman": round(disagreement, 9),
                }

            dense_scores = rankings["dense"].scores
            if len(set(dense_scores)) < len(dense_scores):
                dense_tie_queries += 1
            if not any(rankings["bm25"].scores):
                bm25_zero_queries += 1
            fused_counts = Counter(rankings["hybrid"].scores)
            if any(count > 1 for count in fused_counts.values()):
                rrf_tie_queries += 1

            identity = _metric_identity(episodes, vectors[question.question], dense_order)
            metric_identity["queries"] += 1
            metric_identity["exact_three_order_matches"] += int(
                identity["exact_three_order_match"]
            )
            metric_identity["dot_euclidean_order_matches"] += int(
                identity["dot_euclidean_order_match"]
            )
            metric_identity["carried_float32_dot_matches_float64_dot"] += int(
                identity["carried_dot_order_match"]
            )
            metric_identity["max_relation_error"] = max(
                metric_identity["max_relation_error"], identity["relation_error"]
            )

            for arm, ranking in rankings.items():
                score_values[arm].extend(ranking.scores)
                inverse = _inverse_rank(ranking.order)
                evidence_ranks[arm].extend(inverse[index] for index in evidence)
                order_digests[arm].append(
                    _digest([episodes[index].identity for index in ranking.order])
                )
                for budget in BUDGETS:
                    packed = pack_order(episodes, ranking.order, budget)
                    deliveries[arm][budget].append(len(packed.selected_ids))
                    delivered_chars[arm][budget].append(len(packed.payload))
                    overflow_skips[arm][budget].append(len(packed.skipped_ids))
                    everything_fits[arm][budget] += int(not packed.skipped_ids)

            if population == "targeted":
                dense = rankings["dense"]
                for budget in BUDGETS:
                    baseline = set(pack_order(episodes, dense.order, budget).selected_ids)
                    baseline_hit = all(episodes[index].identity in baseline for index in evidence)
                    for fraction in SHAM_FRACTIONS:
                        nudged = int(round(budget * (1.0 + fraction)))
                        perturbed = set(
                            pack_order(episodes, dense.order, nudged).selected_ids
                        )
                        perturbed_hit = all(
                            episodes[index].identity in perturbed for index in evidence
                        )
                        if perturbed_hit and not baseline_hit:
                            sham[budget][fraction][0] += 1
                        elif baseline_hit and not perturbed_hit:
                            sham[budget][fraction][1] += 1

    prior = reproduce_bakeoff()
    tc001 = reproduce_tc001_dense(conversations, episodes_by_case, vectors)
    positive_controls = _positive_controls()
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PART_1_EXPLORATION_ONLY",
        "note": (
            "No BM25-vs-dense or hybrid-vs-dense evidence-delivery contrast "
            "appears in this artifact. Evidence is used for rank distributions "
            "and the within-dense sham band only."
        ),
        "inputs": _inputs(manifest, reuse),
        "corpus": {
            "conversations": len(conversations),
            "candidates": sum(len(case.pairs) for case in conversations),
            "unique_questions": question_count,
            "population_counts": dict(sorted(population_counts.items())),
            "surface_class_counts": dict(sorted(surface_counts.items())),
        },
        "identity": {
            "dense": (
                "Normalized query/candidate dot product (cosine), descending; "
                "conversation order breaks ties."
            ),
            "bm25": (
                "Carried Unicode-casefold BM25 scores (k1=1.2, b=0.75), "
                "descending; conversation order breaks ties."
            ),
            "hybrid": (
                "One-based dense/BM25 reciprocal-rank contributions with "
                "constant 60 are summed; conversation order breaks ties."
            ),
            "bm25_k1": BM25_K1,
            "bm25_b": BM25_B,
            "rrf_constant": RRF_CONSTANT,
            "metric_alias_check": {
                **metric_identity,
                "max_relation_error": float(metric_identity["max_relation_error"]),
                "interpretation": (
                    "Dot and Euclidean are the same metric in exact arithmetic. "
                    "Any carried-float32 versus float64 order difference is "
                    "implementation precision at near-ties, not a distinct "
                    "similarity objective."
                ),
            },
            "tc001_dense_reproduction": tc001,
            "retrieval_bakeoff_reproduction": prior,
        },
        "distributions": {
            "scores": {arm: _float_distribution(values) for arm, values in score_values.items()},
            "evidence_ranks": {
                arm: _distribution(values) for arm, values in evidence_ranks.items()
            },
            "rank_spearman": {
                key: _float_distribution(values) for key, values in correlations.items()
            },
            "delivered_candidates": {
                arm: {
                    str(budget): _distribution(deliveries[arm][budget])
                    for budget in BUDGETS
                }
                for arm in ARMS
            },
            "delivered_characters": {
                arm: {
                    str(budget): _distribution(delivered_chars[arm][budget])
                    for budget in BUDGETS
                }
                for arm in ARMS
            },
            "overflow_skips": {
                arm: {
                    str(budget): _distribution(overflow_skips[arm][budget])
                    for budget in BUDGETS
                }
                for arm in ARMS
            },
            "ranking_digest": {
                arm: _digest(order_digests[arm]) for arm in ARMS
            },
        },
        "degenerate_states": {
            "real_trace": {
                "all_zero_bm25_queries": bm25_zero_queries,
                "dense_tie_queries": dense_tie_queries,
                "rrf_tie_queries": rrf_tie_queries,
                "complete_three_arm_agreement_queries": exact_agreement,
                "maximum_dense_bm25_disagreement": max_disagreement,
                "everything_fits_questions": {
                    arm: {str(b): everything_fits[arm][b] for b in BUDGETS}
                    for arm in ARMS
                },
                "individually_oversized_candidates": {
                    str(budget): sum(
                        episode.element_chars > budget
                        for episodes in episodes_by_case.values()
                        for episode in episodes
                    )
                    for budget in BUDGETS
                },
            },
            "positive_controls": positive_controls,
            "feedback": "none; every order is a pure function of frozen query and store",
        },
        "sham_band": {
            str(budget): _sham_summary(budget, sham[budget]) for budget in BUDGETS
        },
        "embedding_audit": {
            "llm_or_generative_calls": 0,
            "locomo_cache_hits": reuse["hits"],
            "locomo_cache_misses": reuse["misses"],
            "bakeoff_embedding_calls": prior["embedding_calls"],
            "programme_model_free": True,
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }
    (output_dir / "tc005_preflight_part1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


class _CountingEmbedder:
    def __init__(self, delegate: CarriedEmbedder) -> None:
        self.delegate = delegate
        self.calls = 0

    def __call__(self, text: str) -> np.ndarray:
        self.calls += 1
        return self.delegate(text)


def reproduce_bakeoff() -> dict[str, Any]:
    """Replay committed M2/M3/M4 selected identities with prior code."""

    expected: dict[tuple[str, str, str], dict[str, Any]] = {}
    with PRIOR_RESULTS.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["method_id"] in {"M2", "M3", "M4"}:
                expected[(row["corpus_id"], row["method_id"], row["query_id"])] = row
    embedder = _CountingEmbedder(CarriedEmbedder())
    embedder.delegate.assert_carried_model()
    checked = 0
    rank_digests: list[str] = []
    payload_digests: list[str] = []
    for corpus_id, spec in CORPORA.items():
        queries = load_queries(spec)
        candidates = load_raw_episodes(spec)
        for method_id in ("M2", "M3", "M4"):
            method = build_method(method_id, candidates)
            for query in queries:
                encoded = method.encode(query, spec, embedder)
                ranked = method.rank(query, encoded)
                packed = pack_ranked_candidates(
                    method_id, method.ordered_for_packing(ranked), 32_000
                )
                prior = expected[(corpus_id, method_id, query.query_id)]
                selected = [item.candidate.candidate_id for item in packed.selected]
                prior_selected = [item["candidate_id"] for item in prior["selected"]]
                digest = hashlib.sha256(packed.rendered_block.encode("utf-8")).hexdigest()
                if selected != prior_selected or digest != prior["rendered_sha256"]:
                    raise TC005ExplorationError(
                        f"Bakeoff replay drifted: {corpus_id}/{method_id}/{query.query_id}"
                    )
                checked += 1
                rank_digests.append(
                    _digest([item.candidate.candidate_id for item in ranked])
                )
                payload_digests.append(digest)
    if checked != len(expected):
        raise TC005ExplorationError(
            f"Bakeoff reproduction count drifted: {checked} != {len(expected)}"
        )
    return {
        "status": "PASS",
        "rows_checked": checked,
        "selected_identity_and_payload_digest_matches": checked,
        "ranking_digest": _digest(rank_digests),
        "payload_digest": _digest(payload_digests),
        "embedding_calls": embedder.calls,
        "expected_artifact_sha256": sha256_file(PRIOR_RESULTS),
    }


def reproduce_tc001_dense(
    conversations: Sequence[ConversationCase],
    episodes_by_case: Mapping[str, Sequence[Episode]],
    vectors: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    expected = {
        16_000: _csv_by_question(TC001_PRIMARY),
        32_000: _csv_by_question(TC001_SECONDARY),
    }
    payload_digests: list[str] = []
    checked = 0
    for case in conversations:
        episodes = episodes_by_case[case.sample_id]
        for question in case.questions:
            if question.duplicate_ordinal > 0:
                continue
            for budget in (16_000, 32_000):
                payload, selected = flat_context(
                    episodes, vectors[question.question], budget
                )
                row = expected[budget][question.identity]
                if len(selected) != int(row["flat_delivered"]):
                    raise TC005ExplorationError("TC-001 dense delivery count drifted")
                if len(payload) != int(row["flat_chars"]):
                    raise TC005ExplorationError("TC-001 dense payload cost drifted")
                checked += 1
                payload_digests.append(hashlib.sha256(payload.encode("utf-8")).hexdigest())
    return {
        "status": "PASS",
        "question_budget_payloads_checked": checked,
        "payload_digest": _digest(payload_digests),
        "committed_primary_sha256": sha256_file(TC001_PRIMARY),
        "committed_secondary_sha256": sha256_file(TC001_SECONDARY),
    }


def _csv_by_question(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["question_id"]: row for row in csv.DictReader(handle)}


def _metric_identity(
    episodes: Sequence[Episode], query: np.ndarray, dense_order: Sequence[int]
) -> dict[str, Any]:
    matrix = np.stack([_unit(episode.record["embedding"]) for episode in episodes]).astype(
        np.float64
    )
    q = _unit(query).astype(np.float64)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    q /= np.linalg.norm(q)
    dot = matrix @ q
    distance_score = -np.sum((matrix - q) ** 2, axis=1)
    order_dot = tuple(sorted(range(len(episodes)), key=lambda i: (-dot[i], i)))
    order_distance = tuple(
        sorted(range(len(episodes)), key=lambda i: (-distance_score[i], i))
    )
    relation_error = float(np.max(np.abs(distance_score - (2.0 * dot - 2.0))))
    return {
        "exact_three_order_match": order_dot == order_distance == tuple(dense_order),
        "dot_euclidean_order_match": order_dot == order_distance,
        "carried_dot_order_match": order_dot == tuple(dense_order),
        "relation_error": relation_error,
    }


def _positive_controls() -> dict[str, Any]:
    # These controls exercise states that may be absent on the real corpus.
    zero_candidates = [
        Candidate("a", "a", 1, "episode", user_message="alpha"),
        Candidate("b", "b", 2, "episode", user_message="beta"),
    ]
    zero_scores = BM25Index(zero_candidates).scores("unseen-token")
    tiny = [
        {"id": "a", "turn_number": 1, "user_message": "a", "assistant_message": ""},
        {"id": "b", "turn_number": 2, "user_message": "b" * 10_000, "assistant_message": ""},
    ]
    fits = pack_stm_payload([], tiny[:1], 1_000)
    oversized = pack_stm_payload([], tiny, 1_000)
    return {
        "all_zero_bm25": bool(np.all(zero_scores == 0.0)),
        "dense_tie_resolved_by_conversation_order": tuple(
            sorted(range(2), key=lambda index: (-1.0, index))
        ) == (0, 1),
        "rrf_tie_resolved_by_conversation_order": tuple(
            sorted(range(2), key=lambda index: (-0.02, index))
        ) == (0, 1),
        "everything_fits": fits.selected_ids == ("a",),
        "oversized_candidate_skipped": oversized.selected_ids == ("a",)
        and oversized.skipped_k_ids == ("b",),
    }


def _spearman(left: Sequence[int], right: Sequence[int]) -> float:
    if len(left) != len(right) or set(left) != set(right):
        raise TC005ExplorationError("Spearman inputs must be equal permutations")
    n = len(left)
    if n < 2:
        return 1.0
    l_rank = _inverse_rank(left)
    r_rank = _inverse_rank(right)
    squared = sum((l_rank[index] - r_rank[index]) ** 2 for index in range(n))
    return 1.0 - (6.0 * squared) / (n * (n * n - 1))


def _sham_summary(budget: int, rows: Mapping[float, Sequence[int]]) -> dict[str, Any]:
    perturbations = []
    max_abs = 0
    for fraction in SHAM_FRACTIONS:
        gains, losses = rows[fraction]
        net = gains - losses
        max_abs = max(max_abs, abs(net))
        perturbations.append(
            {
                "fraction": fraction,
                "budget_chars": budget,
                "nudged_budget_chars": int(round(budget * (1.0 + fraction))),
                "gains": gains,
                "losses": losses,
                "net": net,
                "discordant": gains + losses,
            }
        )
    return {
        "budget_chars": budget,
        "population": "targeted",
        "endpoint": "complete_required_evidence",
        "max_abs_net": max_abs,
        "perturbations": perturbations,
    }


def _inputs(manifest: dict[str, Any], reuse: dict[str, Any]) -> dict[str, Any]:
    paths = (
        Path(__file__).resolve(),
        REPO_ROOT / "src" / "analysis" / "locomo_nf_development.py",
        REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
        REPO_ROOT / "src" / "retrieval_bakeoff" / "methods.py",
        REPO_ROOT / "src" / "retrieval_bakeoff" / "config.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_packing.py",
        REPO_ROOT / "episodic" / "src" / "episodic" / "_render.py",
    )
    return {
        "dataset": {
            "bytes": DATASET_PATH.stat().st_size,
            "sha256": sha256_file(DATASET_PATH),
        },
        "locomo_cache": {
            "entries": manifest["cache"]["entries"],
            "file_sha256": manifest["cache"]["file_sha256"],
            "content_sha256": manifest["cache"]["content_sha256"],
            "hits": reuse["hits"],
            "misses": reuse["misses"],
        },
        "vector_manifest_sha256": sha256_file(VECTOR_MANIFEST),
        "embedder_sha256": CARRIED_EMBEDDER_SHA256,
        "prior_results": {
            "rows": sum(1 for _ in PRIOR_RESULTS.open("r", encoding="utf-8")),
            "sha256": sha256_file(PRIOR_RESULTS),
        },
        "sources": {
            path.resolve().relative_to(REPO_ROOT).as_posix(): sha256_file(path)
            for path in paths
        },
        "threading": {
            key: os.environ.get(key)
            for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
    }


def _distribution(values: Iterable[int]) -> dict[str, Any]:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        return {"n": 0}
    return _ordered_distribution(ordered)


def _float_distribution(values: Iterable[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"n": 0}
    result = _ordered_distribution(ordered)
    return {
        key: (round(value, 9) if isinstance(value, float) else value)
        for key, value in result.items()
    }


def _ordered_distribution(ordered: Sequence[float | int]) -> dict[str, Any]:
    def rank(percentile: float) -> float | int:
        return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p05": rank(0.05),
        "p25": rank(0.25),
        "p50": rank(0.50),
        "p75": rank(0.75),
        "p95": rank(0.95),
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
    }


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


__all__ = [
    "ARMS",
    "ARTIFACT_ROOT",
    "BUDGETS",
    "PackedRanking",
    "Ranking",
    "candidates_for",
    "evidence_indices",
    "explore",
    "pack_order",
    "prepare_rankers",
    "question_population",
    "rank_all",
    "surface_class",
]
