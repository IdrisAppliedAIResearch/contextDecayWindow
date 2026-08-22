"""TC-001B Preflight Part 1: characterize the dual arm before any bar is locked.

TC-001 compared the shipped four-tier stack against a flat cosine ranking and
found the flat arm ahead by 435 questions on complete evidence delivery. Its
section 3 attributed 61% of the tiered arm's delivered characters to the recency
window, and section 5 recorded that the window is close to worthless on this
corpus **by construction**: LoCoMo asks about a conversation that has already
finished, so "the last 32 turns" is an arbitrary slice of it.

This study removes that tier and asks whether what remains earns its place:

    A_FLAT         rank every candidate by cosine, pack greedily to budget.
    A_TIERED       ``build_context`` as shipped - recency, K, coverage.
    A_DUAL         ``build_context`` with ``recency_window_n=0``. Relevance and
                   coverage only. No new mechanism code: one config field.
    A_DUAL_RANKED  A_DUAL with the K tier offered in cosine order rather than
                   store order, isolating TC-001 section 4's finding.

A_DUAL_RANKED cannot go through ``build_context``, because the ordering it
changes is a line inside that function and ``episodic/src/episodic/_context.py``
is SHA-256 pinned inside TC-001's committed run header. ``compose_context``
therefore restates the composition locally, and ``assert_composition_matches``
holds it to the shipped function on every question at every budget: with
``k_order="store"`` the two must agree byte for byte. A restatement that is
proven equal to the original is measurable; one that is merely believed equal
is not.

**What this module does not compute.** No artifact it writes carries an arm's
absolute availability or any cross-arm contrast. The null band below is measured
here, and a band chosen after seeing the contrast would not be a band. Within-arm
paired counts under sham budget perturbations are the only availability-derived
numbers recorded, exactly as TC-001's Part 1 did.

Zero model calls. The cache is opened in ``reuse`` mode with its file and content
digests asserted, so a miss raises rather than embedding.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    ConversationCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
    BUDGETS,
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    SHAM_FRACTIONS,
    VECTOR_MANIFEST,
    Episode,
    _delivered_ids,
    _evidence_index,
    _repo_relative,
    _score,
    _sham_row,
    build_episodes,
    flat_context,
    flat_order,
    tiered_context,
)
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256, EpisodicConfig
from episodic._context import _candidate_pool, _recency_window, build_context
from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._selection import (
    ClusterDiversitySelector,
    deterministic_clusters,
    relevance_vector,
    select,
    vector,
)

SCHEMA = "tc001b-preflight-part1-v1"

ARTIFACT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts" / "tc001b"
)

#: The shipped configuration, and the same thing with the recency tier removed.
SHIPPED_CONFIG = EpisodicConfig()
DUAL_CONFIG = EpisodicConfig(recency_window_n=0)

#: Arms whose null band this Preflight measures. ``flat`` and ``tiered`` are
#: not re-measured; TC-001's Part 1 measured them on this corpus at these
#: budgets and the pre-registration carries that number forward explicitly.
BAND_ARMS = ("dual", "dual_ranked")

K_ORDERS = ("store", "relevance")


class TC001BExplorationError(RuntimeError):
    """Raised when a Preflight invariant does not hold."""


# --------------------------------------------------------------------------
# The composition, restated so one line of it can be varied
# --------------------------------------------------------------------------


def compose_context(
    records: Sequence[dict],
    query_embedding,
    budget: int,
    config: EpisodicConfig,
    *,
    k_order: str,
) -> tuple[str, tuple[str, ...], dict[str, Any]]:
    """``build_context``'s composition with the K tier's order exposed.

    Every stage is the shipped one, called in the shipped order. The only
    thing this function adds is ``k_order``: ``"store"`` reproduces
    ``build_context`` exactly, and ``"relevance"`` offers the same K
    candidates to the same packer sorted by cosine descending, with the
    library's own ``(-relevance, turn_number, id)`` tie-break.
    """
    if k_order not in K_ORDERS:
        raise TC001BExplorationError(f"Unregistered k_order: {k_order}")

    query = vector(query_embedding)
    recent = _recency_window(records, config.recency_window_n)
    recent_ids = {str(episode["id"]) for episode in recent}

    relevance_by_id: dict[str, float] = {}
    if records:
        relevance = relevance_vector(query, records)
        relevance_by_id = {
            str(episode["id"]): float(relevance[index])
            for index, episode in enumerate(records)
        }

    k_hits = [
        episode
        for episode in records
        if relevance_by_id[str(episode["id"])] >= config.k_threshold
    ]
    if k_order == "relevance":
        k_hits = sorted(
            k_hits,
            key=lambda episode: (
                -relevance_by_id[str(episode["id"])],
                int(episode["turn_number"]),
                str(episode["id"]),
            ),
        )
    k_ids = {str(episode["id"]) for episode in k_hits}

    pool = _candidate_pool(records, relevance_by_id, config)
    coverage: list[dict] = []
    if pool and budget >= EMPTY_PAYLOAD_CHARS:
        result = select(
            candidates=pool,
            query_embedding=query,
            selector=ClusterDiversitySelector(
                lambda_=config.selector_lambda,
                cost_exponent=config.selector_cost_exponent,
                assignments=deterministic_clusters(
                    pool, config.selector_cluster_count
                ),
                cluster_count=config.selector_cluster_count,
            ),
            budget_chars=budget,
        )
        by_id = {str(episode["id"]): episode for episode in pool}
        coverage = [by_id[identifier] for identifier in result.selected_ids]

    packed = pack_stm_payload(recent, [*k_hits, *coverage], budget)
    delivered = set(packed.selected_ids)
    counts = {
        "recency": len(delivered & recent_ids),
        "k": len((delivered & k_ids) - recent_ids),
        "coverage": len(delivered - recent_ids - k_ids),
        "k_offered": len(k_hits),
        "coverage_offered": len(coverage),
        "pool_size": len(pool),
        "chars_delivered": len(packed.payload),
        "k_order": k_order,
    }
    return packed.payload, _delivered_ids(packed.payload, records), counts


# --------------------------------------------------------------------------
# The arms
# --------------------------------------------------------------------------


def dual_context(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[str, tuple[str, ...], Any]:
    """A_DUAL: the shipped function, recency window set to zero."""
    return tiered_context(episodes, query, budget, DUAL_CONFIG)


def dual_ranked_context(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[str, tuple[str, ...], dict[str, Any]]:
    """A_DUAL_RANKED: A_DUAL with the K tier offered best-first."""
    records = [episode.record for episode in episodes]
    return compose_context(
        records, query, budget, DUAL_CONFIG, k_order="relevance"
    )


def assert_composition_matches(
    episodes: Sequence[Episode],
    query: np.ndarray,
    budget: int,
    config: EpisodicConfig,
) -> None:
    """``compose_context(k_order="store")`` is ``build_context``, not a rewrite."""
    records = [episode.record for episode in episodes]
    shipped, shipped_report = build_context(
        episodes=records,
        query_embedding=query,
        budget=budget,
        config=config,
    )
    local, _ids, counts = compose_context(
        records, query, budget, config, k_order="store"
    )
    if local != shipped:
        raise TC001BExplorationError(
            "compose_context diverged from build_context at budget "
            f"{budget}, N={config.recency_window_n}"
        )
    tiers = (
        (shipped_report.stm_count, counts["recency"]),
        (shipped_report.k_count, counts["k"]),
        (shipped_report.coverage_count, counts["coverage"]),
    )
    if any(left != right for left, right in tiers):
        raise TC001BExplorationError(
            "compose_context reported a different tier split than ContextReport"
        )


# --------------------------------------------------------------------------
# Part 1
# --------------------------------------------------------------------------


def explore(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    conversations = adapt_development(DATASET_PATH)

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
        raise TC001BExplorationError(
            f"Read-only cache reported {reuse['misses']} misses"
        )

    by_conversation = {
        case.sample_id: build_episodes(case, vectors) for case in conversations
    }

    result = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PART1_ONLY",
        "note": (
            "Within-arm characterization only. No arm's absolute availability "
            "and no cross-arm contrast appears in this artifact."
        ),
        "inputs": _inputs(manifest, reuse),
        "identity": _identity_checks(conversations, by_conversation, vectors),
        "behaviour": _behaviour(conversations, by_conversation, vectors),
        "null_band": _sham_band(conversations, by_conversation, vectors),
        "cost": _cost(conversations, by_conversation, vectors),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    path = output_dir / "tc001b_preflight_part1.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _inputs(manifest: dict, reuse: dict) -> dict[str, Any]:
    return {
        "dataset_sha256": manifest["dataset_sha256"],
        "cache_file_sha256": manifest["cache"]["file_sha256"],
        "cache_content_sha256": manifest["cache"]["content_sha256"],
        "embedder_sha256": CARRIED_EMBEDDER_SHA256,
        "development_ids": manifest["development_ids"],
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
        "shipped_config": json.loads(SHIPPED_CONFIG.to_json()),
        "dual_config": json.loads(DUAL_CONFIG.to_json()),
        "sources": {
            _repo_relative(path): sha256_file(path)
            for path in (
                Path(__file__).resolve(),
                REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_context.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_packing.py",
                REPO_ROOT / "episodic" / "src" / "episodic" / "_selection.py",
            )
        },
    }


def _identity_checks(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """The gate that makes A_DUAL_RANKED admissible evidence.

    Every question, both budgets, both configurations: the local
    composition with the shipped K order must equal ``build_context``
    byte for byte and tier count for tier count. 871 questions x 2
    budgets x 2 configurations is 3,484 comparisons, and one failure
    is a stop.
    """
    checked = 0
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            query = vectors[question.question]
            for budget in BUDGETS:
                for config in (SHIPPED_CONFIG, DUAL_CONFIG):
                    assert_composition_matches(episodes, query, budget, config)
                    checked += 1

    # The named behaviour of the recency tier at N=0, asserted rather than
    # assumed: `_recency_window` returns nothing, so A_DUAL can deliver no
    # episode that A_TIERED would have counted as recency.
    sample = by_conversation[conversations[0].sample_id]
    empty_window = _recency_window([episode.record for episode in sample], 0)

    return {
        "status": "PASS",
        "composition_comparisons": checked,
        "budgets": list(BUDGETS),
        "configs": ["shipped_n32", "dual_n0"],
        "recency_window_at_n0": len(empty_window),
        "claim": (
            "compose_context(k_order='store') is build_context. The only "
            "difference A_DUAL_RANKED introduces is the order in which the "
            "K tier offers its candidates to the packer."
        ),
    }


def _behaviour(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """What each arm does, as distributions, with the contrast withheld.

    TC-001's Preflight verified *which* candidates each tier holds and
    never asked *in what order each tier offers them*; its report records
    that gap as the reason the K tier's store-order delivery went
    unnoticed until after the verdict. This function asks the ordering
    question directly, before the bars are locked.
    """
    rows: dict[str, dict[str, list]] = {
        name: {
            "delivered": [],
            "chars": [],
            "recency": [],
            "k": [],
            "coverage": [],
        }
        for name in ("tiered", "dual", "dual_ranked", "flat")
    }
    ordering = {
        "questions": 0,
        "k_tier_evaluable": 0,
        "dual_k_in_store_order": 0,
        "dual_k_in_relevance_order": 0,
        "dual_ranked_k_in_relevance_order": 0,
        "dual_and_dual_ranked_identical_delivery": 0,
    }
    degenerate = {
        "dual_delivered_zero_episodes": 0,
        "dual_delivered_zero_k": 0,
        "dual_delivered_zero_coverage": 0,
        "dual_k_leaves_no_room_for_coverage": 0,
    }

    budget = BUDGETS[0]
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        by_identity = {episode.identity: episode for episode in episodes}
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            query = vectors[question.question]
            ordering["questions"] += 1

            _payload, tiered_ids, tiered_report = tiered_context(
                episodes, query, budget, SHIPPED_CONFIG
            )
            _payload, dual_ids, dual_report = dual_context(episodes, query, budget)
            ranked_payload, ranked_ids, ranked_counts = dual_ranked_context(
                episodes, query, budget
            )
            flat_payload, flat_ids = flat_context(episodes, query, budget)

            _collect_report(rows["tiered"], tiered_ids, tiered_report)
            _collect_report(rows["dual"], dual_ids, dual_report)
            _collect_counts(rows["dual_ranked"], ranked_ids, ranked_counts)
            rows["flat"]["delivered"].append(len(flat_ids))
            rows["flat"]["chars"].append(len(flat_payload))

            if set(dual_ids) == set(ranked_ids):
                ordering["dual_and_dual_ranked_identical_delivery"] += 1

            ranks = {
                episodes[index].identity: rank
                for rank, index in enumerate(flat_order(episodes, query), start=1)
            }
            dual_k = dual_report.k_count
            ranked_k = ranked_counts["k"]
            if dual_k >= 3 and ranked_k >= 3:
                ordering["k_tier_evaluable"] += 1
                if _is_store_ordered(dual_ids[:dual_k], by_identity):
                    ordering["dual_k_in_store_order"] += 1
                if _is_relevance_ordered(dual_ids[:dual_k], ranks):
                    ordering["dual_k_in_relevance_order"] += 1
                if _is_relevance_ordered(ranked_ids[:ranked_k], ranks):
                    ordering["dual_ranked_k_in_relevance_order"] += 1

            if not dual_ids:
                degenerate["dual_delivered_zero_episodes"] += 1
            if dual_report.k_count == 0:
                degenerate["dual_delivered_zero_k"] += 1
            if dual_report.coverage_count == 0:
                degenerate["dual_delivered_zero_coverage"] += 1
            if dual_report.k_count and dual_report.coverage_count == 0:
                degenerate["dual_k_leaves_no_room_for_coverage"] += 1

    return {
        "budget_chars": budget,
        "distributions": {
            name: {
                key: _distribution(values)
                for key, values in series.items()
                if values
            }
            for name, series in rows.items()
        },
        "ordering": ordering,
        "degenerate_states": degenerate,
    }


def _collect_report(
    series: dict[str, list], delivered: Sequence[str], report
) -> None:
    series["delivered"].append(len(delivered))
    series["chars"].append(report.chars_delivered)
    series["recency"].append(report.stm_count)
    series["k"].append(report.k_count)
    series["coverage"].append(report.coverage_count)


def _collect_counts(
    series: dict[str, list], delivered: Sequence[str], counts: dict[str, Any]
) -> None:
    series["delivered"].append(len(delivered))
    series["chars"].append(counts["chars_delivered"])
    series["recency"].append(counts["recency"])
    series["k"].append(counts["k"])
    series["coverage"].append(counts["coverage"])


def _is_store_ordered(
    identifiers: Sequence[str], by_identity: dict[str, Episode]
) -> bool:
    turns = [
        int(by_identity[identifier].record["turn_number"])
        for identifier in identifiers
    ]
    return turns == sorted(turns)


def _is_relevance_ordered(
    identifiers: Sequence[str], ranks: dict[str, int]
) -> bool:
    values = [ranks[identifier] for identifier in identifiers]
    return values == sorted(values)


def _sham_band(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """The null band for the two new arms, measured rather than chosen.

    TC-001's method exactly: compare each arm **against itself** at a
    budget nudged by half and one percent, and record only the paired
    gains and losses. One correction is made here. TC-001 measured its
    band on the any-evidence endpoint and applied it to the complete
    endpoint; this measures both, and the registration takes the larger.
    """
    endpoints = ("any", "complete")
    baseline: dict[str, dict[str, dict[str, bool]]] = {
        arm: {endpoint: {} for endpoint in endpoints} for arm in BAND_ARMS
    }
    wanted: dict[str, frozenset[str]] = {}
    budget = BUDGETS[0]

    for case in conversations:
        episodes = by_conversation[case.sample_id]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            query = vectors[question.question]
            target = evidence[question.identity]
            wanted[question.identity] = target
            for arm, delivered in _both_dual_arms(episodes, query, budget):
                hits = set(delivered)
                baseline[arm]["any"][question.identity] = bool(target & hits)
                baseline[arm]["complete"][question.identity] = target <= hits

    per_arm: dict[str, dict[str, list]] = {
        arm: {endpoint: [] for endpoint in endpoints} for arm in BAND_ARMS
    }
    for fraction in SHAM_FRACTIONS:
        nudged = int(round(budget * (1.0 + fraction)))
        counts = {
            arm: {endpoint: [0, 0] for endpoint in endpoints} for arm in BAND_ARMS
        }
        for case in conversations:
            episodes = by_conversation[case.sample_id]
            for question in case.questions:
                if question.duplicate_ordinal or not question.resolved_evidence_ids:
                    continue
                query = vectors[question.question]
                target = wanted[question.identity]
                for arm, delivered in _both_dual_arms(episodes, query, nudged):
                    hits = set(delivered)
                    _score(
                        counts[arm]["any"],
                        baseline[arm]["any"][question.identity],
                        bool(target & hits),
                    )
                    _score(
                        counts[arm]["complete"],
                        baseline[arm]["complete"][question.identity],
                        target <= hits,
                    )
        for arm in BAND_ARMS:
            for endpoint in endpoints:
                gains, losses = counts[arm][endpoint]
                per_arm[arm][endpoint].append(
                    _sham_row(fraction, budget, nudged, gains, losses)
                )

    nets = [
        abs(row["net"])
        for arm in BAND_ARMS
        for endpoint in endpoints
        for row in per_arm[arm][endpoint]
    ]
    return {
        "evaluable_questions": len(wanted),
        "budget_chars": budget,
        "arms": list(BAND_ARMS),
        "endpoints": list(endpoints),
        "perturbations": per_arm,
        "max_abs_net": max(nets),
        "tc001_max_abs_net": 4,
        "band_definition": (
            "The largest absolute gains-minus-losses any sham budget "
            "perturbation produced within a single arm, at this budget, on "
            "either endpoint. TC-001's measured value for the flat and "
            "tiered arms is carried alongside; the registration takes the "
            "maximum over all four arms."
        ),
    }


def _both_dual_arms(
    episodes: Sequence[Episode], query: np.ndarray, budget: int
) -> tuple[tuple[str, Sequence[str]], ...]:
    _payload, dual_ids, _report = dual_context(episodes, query, budget)
    _payload, ranked_ids, _counts = dual_ranked_context(episodes, query, budget)
    return (("dual", dual_ids), ("dual_ranked", ranked_ids))


def _cost(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Per-question wall clock for the new arms at this corpus's pool size."""
    rows = []
    budget = BUDGETS[0]
    for case in conversations:
        episodes = by_conversation[case.sample_id]
        questions = [q for q in case.questions if not q.duplicate_ordinal][:40]
        timings: dict[str, list[float]] = {"dual": [], "dual_ranked": []}
        for question in questions:
            query = vectors[question.question]
            started = time.perf_counter()
            dual_context(episodes, query, budget)
            timings["dual"].append((time.perf_counter() - started) * 1_000.0)
            started = time.perf_counter()
            dual_ranked_context(episodes, query, budget)
            timings["dual_ranked"].append((time.perf_counter() - started) * 1_000.0)
        rows.append(
            {
                "sample_id": case.sample_id,
                "pool_size": len(episodes),
                "questions_timed": len(questions),
                **{
                    f"{arm}_ms": _float_distribution(values)
                    for arm, values in timings.items()
                },
            }
        )
    return {"by_conversation": rows, "budget_chars": budget}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _distribution(values: Iterable[int]) -> dict[str, Any]:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        return {"n": 0}
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p25": ordered[len(ordered) // 4],
        "p50": int(statistics.median(ordered)),
        "p75": ordered[(3 * len(ordered)) // 4],
        "max": ordered[-1],
        "mean": round(statistics.fmean(ordered), 3),
        "zero": sum(1 for value in ordered if value == 0),
    }


def _float_distribution(values: Iterable[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"n": 0}
    return {
        "n": len(ordered),
        "min": round(ordered[0], 4),
        "p50": round(statistics.median(ordered), 4),
        "p95": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 4),
        "max": round(ordered[-1], 4),
        "mean": round(statistics.fmean(ordered), 4),
    }


__all__ = [
    "ARTIFACT_ROOT",
    "BAND_ARMS",
    "DUAL_CONFIG",
    "SCHEMA",
    "SHIPPED_CONFIG",
    "TC001BExplorationError",
    "assert_composition_matches",
    "compose_context",
    "dual_context",
    "dual_ranked_context",
    "explore",
]
