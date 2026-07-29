from __future__ import annotations

import math
import sqlite3
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from .config import DEFAULT_BUDGET, EMBEDDING_DIMENSION, CorpusSpec
from .embedding import normalize_embedding
from .methods import BuiltMethod, EncodedQuery, build_method
from .models import Candidate, Query, RetrievalResult
from .serialization import PackResult, pack_ranked_candidates


ARM_SPECS: dict[str, tuple[bool, bool]] = {
    "P_recency": (False, False),
    "P_recency_topic": (True, False),
    "P_recency_rules": (False, True),
    "P_recency_topic_rules": (True, True),
}
REGISTERED_DOMAINS: dict[str, tuple[str, ...]] = {
    "c121_l": (
        "civil_engineering",
        "renaissance_art",
        "monetary_policy",
        "marine_biology",
    ),
    "c1000_l": (
        "structural",
        "epidemiology",
        "archives",
        "battery",
        "monetary",
        "astronomy",
        "ecology",
        "cryptography",
        "geophysics",
        "linguistics",
        "robotics",
        "conservation",
    ),
}
MINIMUM_BUDGET_FILL = 0.95
MINIMUM_BEST_COSINE = 0.50


@dataclass
class OrthogonalAxes:
    report: dict
    topic_centroids: dict[str, np.ndarray]
    resolving_rule_candidate_ids: tuple[str, ...]


@dataclass
class ProgressiveOutcome:
    result: RetrievalResult
    arm_id: str
    searched_tiers: list[str]
    stop_reason: str
    selected_topic_id: str | None
    searched_candidate_count: int
    best_searched_cosine: float | None
    tier_timings: list[dict]


@dataclass
class _Execution:
    packed: PackResult
    searched_tiers: list[str]
    stop_reason: str
    selected_topic_id: str | None
    searched_candidate_count: int
    best_searched_cosine: float | None
    tier_timings: list[dict]
    rank_ms: float
    pack_ms: float
    rank_pack_ms: float


class ProgressiveIndex:
    def __init__(
        self,
        spec: CorpusSpec,
        candidates: list[Candidate],
    ) -> None:
        self.spec = spec
        self.candidates = sorted(
            candidates,
            key=lambda item: (item.turn_number, item.candidate_id),
        )
        expected_turns = list(
            range(spec.eligible_turn_min, spec.eligible_turn_max + 1)
        )
        if [item.turn_number for item in self.candidates] != expected_turns:
            raise AssertionError(
                f"{spec.corpus_id} progressive nodes do not cover eligible turns"
            )
        self.matrix = np.vstack(
            [
                normalize_embedding(np.asarray(candidate.embedding))
                for candidate in self.candidates
            ]
        ).astype(np.float32, copy=False)
        self._candidate_index = {
            candidate.candidate_id: index
            for index, candidate in enumerate(self.candidates)
        }
        if len(self._candidate_index) != len(self.candidates):
            raise AssertionError("Progressive candidates need unique IDs")

        axis_start = time.perf_counter()
        self.axes = inspect_orthogonal_axes(spec, self.candidates)
        self.axis_validation_ms = (
            time.perf_counter() - axis_start
        ) * 1000.0
        self._build_start = time.perf_counter()
        hot_count = math.floor(len(self.candidates) * 0.10)
        warm_count = math.floor(len(self.candidates) * 0.30)
        cold_stop = len(self.candidates) - hot_count - warm_count
        warm_stop = len(self.candidates) - hot_count
        self.tier_counts = {
            "hot": hot_count,
            "warm": warm_count,
            "cold": cold_stop,
        }
        self._base_methods = {
            "hot": build_method("M3", self.candidates[warm_stop:]),
            "warm": build_method(
                "M3",
                self.candidates[cold_stop:warm_stop],
            ),
            "cold": build_method("M3", self.candidates[:cold_stop]),
        }
        self._topic_methods = {}
        if self.axes.report["topic_axis"]["valid"]:
            self._topic_methods = {
                topic_id: build_method(
                    "M3",
                    [
                        candidate
                        for candidate in self.candidates
                        if candidate.topic_id == topic_id
                    ],
                )
                for topic_id in sorted(self.axes.topic_centroids)
            }
        rules = set(self.axes.resolving_rule_candidate_ids)
        self._rules_method = build_method(
            "M3",
            [
                candidate
                for candidate in self.candidates
                if candidate.candidate_id in rules
            ],
        )
        self.total_index_build_ms = (
            time.perf_counter() - self._build_start
        ) * 1000.0

    def arm_statuses(self) -> dict[str, dict]:
        topic_valid = bool(self.axes.report["topic_axis"]["valid"])
        rules_valid = bool(self.axes.report["pinned_rule_axis"]["valid"])
        result = {}
        for arm_id, (needs_topic, needs_rules) in ARM_SPECS.items():
            missing = []
            if needs_topic and not topic_valid:
                missing.append("topic_axis")
            if needs_rules and not rules_valid:
                missing.append("pinned_rule_axis")
            result[arm_id] = {
                "status": "EVALUABLE" if not missing else "NOT_EVALUABLE",
                "invalid_required_axes": missing,
            }
        return result

    def retrieve(
        self,
        arm_id: str,
        query: Query,
        embedder,
        *,
        budget: int = DEFAULT_BUDGET,
        repetitions: int = 9,
    ) -> ProgressiveOutcome:
        if arm_id not in ARM_SPECS:
            raise ValueError(f"Unknown progressive arm: {arm_id}")
        status = self.arm_statuses()[arm_id]
        if status["status"] != "EVALUABLE":
            raise ValueError(f"{arm_id} is {status['status']}: {status}")
        if budget != DEFAULT_BUDGET:
            raise ValueError("Progressive search uses the registered 32k budget")
        if repetitions < 1:
            raise ValueError("repetitions must be positive")

        encode_start = time.perf_counter()
        query_vector = normalize_embedding(embedder(query.text))
        query_encode_ms = (time.perf_counter() - encode_start) * 1000.0
        warm = self._execute(arm_id, query, query_vector, budget)

        executions = [
            self._execute(arm_id, query, query_vector, budget)
            for _ in range(repetitions)
        ]
        for execution in executions:
            if execution.packed.rendered_block != warm.packed.rendered_block:
                raise AssertionError("Progressive retrieval changed across runs")
            if execution.searched_tiers != warm.searched_tiers:
                raise AssertionError("Progressive tier path changed across runs")
            if execution.stop_reason != warm.stop_reason:
                raise AssertionError("Progressive stop reason changed across runs")
            if execution.selected_topic_id != warm.selected_topic_id:
                raise AssertionError("Progressive topic changed across runs")

        final = executions[-1]
        rank_times = [execution.rank_ms for execution in executions]
        pack_times = [execution.pack_ms for execution in executions]
        combined_times = [
            execution.rank_pack_ms for execution in executions
        ]
        tier_timings = []
        for tier_index, tier_name in enumerate(final.searched_tiers):
            tier_rows = [
                execution.tier_timings[tier_index]
                for execution in executions
            ]
            tier_timings.append(
                {
                    **{
                        key: final.tier_timings[tier_index][key]
                        for key in (
                            "tier",
                            "fresh_candidate_count",
                            "cumulative_candidate_count",
                            "cumulative_characters",
                            "budget_fill",
                            "best_searched_cosine",
                        )
                    },
                    "rank_ms": statistics.median(
                        row["rank_ms"] for row in tier_rows
                    ),
                    "pack_ms": statistics.median(
                        row["pack_ms"] for row in tier_rows
                    ),
                    "incremental_ms": statistics.median(
                        row["incremental_ms"] for row in tier_rows
                    ),
                }
            )

        result = RetrievalResult(
            corpus_id=self.spec.corpus_id,
            method_id=arm_id,
            query=query,
            budget=budget,
            ranked_count=final.searched_candidate_count,
            selected=final.packed.selected,
            rendered_block=final.packed.rendered_block,
            phases=final.packed.phases,
            skipped_oversized=final.packed.skipped_oversized,
            duplicate_drops=final.packed.duplicate_drops,
            query_encode_ms=query_encode_ms,
            rank_ms=statistics.median(rank_times),
            pack_ms=statistics.median(pack_times),
            rank_pack_ms=statistics.median(combined_times),
            index_build_ms=self._arm_index_build_ms(arm_id),
            benchmark_repetitions=repetitions,
        )
        return ProgressiveOutcome(
            result=result,
            arm_id=arm_id,
            searched_tiers=final.searched_tiers,
            stop_reason=final.stop_reason,
            selected_topic_id=final.selected_topic_id,
            searched_candidate_count=final.searched_candidate_count,
            best_searched_cosine=final.best_searched_cosine,
            tier_timings=tier_timings,
        )

    def _execute(
        self,
        arm_id: str,
        query: Query,
        query_vector: np.ndarray,
        budget: int,
    ) -> _Execution:
        needs_topic, needs_rules = ARM_SPECS[arm_id]
        selected_topic_id = None
        initial_tiers = ["hot"]
        if needs_rules:
            initial_tiers.append("rules")
        if needs_topic:
            initial_tiers.append("topic")
        sequence = [*initial_tiers, "warm", "cold"]

        seen: set[str] = set()
        accumulated = []
        searched_tiers = []
        tier_timings = []
        best_cosine: float | None = None
        total_rank_ms = 0.0
        total_pack_ms = 0.0
        execution_start = time.perf_counter()
        final_pack: PackResult | None = None
        stop_reason = "exhausted_cold"

        for tier_name in sequence:
            tier_start = time.perf_counter()
            rank_start = tier_start
            if tier_name == "topic":
                selected_topic_id = self._select_topic(query_vector)
            method = self._method_for_tier(tier_name, selected_topic_id)
            ranked = method.rank(query, EncodedQuery())
            fresh = [
                item
                for item in ranked
                if item.candidate.rendered_identity not in seen
            ]
            if fresh:
                indices = np.asarray(
                    [
                        self._candidate_index[item.candidate.candidate_id]
                        for item in fresh
                    ],
                    dtype=np.int32,
                )
                tier_best = float(
                    np.max(self.matrix[indices] @ query_vector)
                )
                best_cosine = (
                    tier_best
                    if best_cosine is None
                    else max(best_cosine, tier_best)
                )
            rank_ms = (time.perf_counter() - rank_start) * 1000.0
            for item in fresh:
                seen.add(item.candidate.rendered_identity)
                accumulated.append((item, tier_name))

            pack_start = time.perf_counter()
            final_pack = pack_ranked_candidates(
                arm_id,
                accumulated,
                budget,
            )
            pack_ms = (time.perf_counter() - pack_start) * 1000.0
            incremental_ms = (time.perf_counter() - tier_start) * 1000.0
            total_rank_ms += rank_ms
            total_pack_ms += pack_ms
            searched_tiers.append(tier_name)
            tier_timings.append(
                {
                    "tier": tier_name,
                    "fresh_candidate_count": len(fresh),
                    "cumulative_candidate_count": len(accumulated),
                    "cumulative_characters": len(final_pack.rendered_block),
                    "budget_fill": len(final_pack.rendered_block) / budget,
                    "best_searched_cosine": best_cosine,
                    "rank_ms": rank_ms,
                    "pack_ms": pack_ms,
                    "incremental_ms": incremental_ms,
                }
            )

            initial_complete = tier_name == initial_tiers[-1]
            warm_complete = tier_name == "warm"
            if (initial_complete or warm_complete) and _should_stop(
                final_pack,
                budget,
                best_cosine,
            ):
                stop_reason = f"threshold_after_{tier_name}"
                break

        if final_pack is None:
            raise AssertionError("Progressive search executed no tiers")
        return _Execution(
            packed=final_pack,
            searched_tiers=searched_tiers,
            stop_reason=stop_reason,
            selected_topic_id=selected_topic_id,
            searched_candidate_count=len(accumulated),
            best_searched_cosine=best_cosine,
            tier_timings=tier_timings,
            rank_ms=total_rank_ms,
            pack_ms=total_pack_ms,
            rank_pack_ms=(time.perf_counter() - execution_start) * 1000.0,
        )

    def _method_for_tier(
        self,
        tier_name: str,
        selected_topic_id: str | None,
    ) -> BuiltMethod:
        if tier_name in self._base_methods:
            return self._base_methods[tier_name]
        if tier_name == "rules":
            return self._rules_method
        if tier_name == "topic" and selected_topic_id is not None:
            return self._topic_methods[selected_topic_id]
        raise AssertionError(f"Unresolvable progressive tier: {tier_name}")

    def _select_topic(self, query_vector: np.ndarray) -> str:
        topic_ids = sorted(self.axes.topic_centroids)
        matrix = np.vstack(
            [self.axes.topic_centroids[topic_id] for topic_id in topic_ids]
        )
        scores = matrix @ query_vector
        order = np.lexsort((np.asarray(topic_ids), -scores))
        return topic_ids[int(order[0])]

    def _arm_index_build_ms(self, arm_id: str) -> float:
        needs_topic, needs_rules = ARM_SPECS[arm_id]
        elapsed = sum(
            method.index_build_ms for method in self._base_methods.values()
        )
        if needs_topic:
            elapsed += sum(
                method.index_build_ms
                for method in self._topic_methods.values()
            )
        if needs_rules:
            elapsed += self._rules_method.index_build_ms
        return elapsed


def inspect_orthogonal_axes(
    spec: CorpusSpec,
    candidates: list[Candidate],
) -> OrthogonalAxes:
    if spec.corpus_id not in REGISTERED_DOMAINS:
        raise ValueError(f"No registered domain set for {spec.corpus_id}")
    registered_domains = REGISTERED_DOMAINS[spec.corpus_id]
    domain_topics: dict[str, Counter[str]] = {
        domain: Counter() for domain in registered_domains
    }
    domain_totals: Counter[str] = Counter()
    topic_domains: dict[str, Counter[str]] = defaultdict(Counter)
    excluded_domains: Counter[str] = Counter()
    for candidate in candidates:
        if candidate.domain not in domain_topics:
            excluded_domains[candidate.domain or "<empty>"] += 1
            continue
        domain_totals[candidate.domain] += 1
        if candidate.topic_id:
            domain_topics[candidate.domain][candidate.topic_id] += 1
            topic_domains[candidate.topic_id][candidate.domain] += 1

    dominant_topics = {}
    domain_rows = []
    purity_values = []
    for domain in registered_domains:
        counts = domain_topics[domain]
        total = domain_totals[domain]
        if not total or not counts:
            domain_rows.append(
                {
                    "domain": domain,
                    "episode_count": 0,
                    "dominant_topic_id": None,
                    "dominant_count": 0,
                    "purity": 0.0,
                    "purity_exact": "0",
                }
            )
            continue
        topic_id, dominant_count = sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0]
        purity = Fraction(dominant_count, total)
        purity_values.append(purity)
        dominant_topics[domain] = topic_id
        domain_rows.append(
            {
                "domain": domain,
                "episode_count": total,
                "dominant_topic_id": topic_id,
                "dominant_count": dominant_count,
                "purity": float(purity),
                "purity_exact": str(purity),
            }
        )
    macro_purity = (
        sum(purity_values, Fraction()) / len(registered_domains)
    )
    distinct_dominants = len(set(dominant_topics.values()))
    domain_complete = len(dominant_topics) == len(registered_domains)

    reverse_values = []
    reverse_rows = []
    for topic_id, counts in sorted(topic_domains.items()):
        total = sum(counts.values())
        domain, dominant_count = sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0]
        purity = Fraction(dominant_count, total)
        reverse_values.append(purity)
        reverse_rows.append(
            {
                "topic_id": topic_id,
                "episode_count": total,
                "dominant_domain": domain,
                "purity": float(purity),
                "purity_exact": str(purity),
            }
        )
    reverse_macro = (
        sum(reverse_values, Fraction()) / len(reverse_values)
        if reverse_values
        else Fraction()
    )

    topic_centroids, rule_rows = _load_axes_from_database(spec)
    candidate_topics = {
        candidate.topic_id for candidate in candidates if candidate.topic_id
    }
    missing_centroids = sorted(candidate_topics - topic_centroids.keys())
    topic_centroids = {
        topic_id: centroid
        for topic_id, centroid in topic_centroids.items()
        if topic_id in candidate_topics
    }
    topic_valid = bool(
        domain_complete
        and macro_purity >= Fraction(4, 5)
        and distinct_dominants == len(registered_domains)
        and not missing_centroids
    )
    topic_reasons = []
    if not domain_complete:
        topic_reasons.append("missing_domain_topic")
    if macro_purity < Fraction(4, 5):
        topic_reasons.append("macro_domain_to_topic_purity_below_0_80")
    if distinct_dominants != len(registered_domains):
        topic_reasons.append("dominant_topics_not_distinct")
    if missing_centroids:
        topic_reasons.append("missing_topic_centroid")

    candidates_by_id = {
        candidate.candidate_id: candidate for candidate in candidates
    }
    resolving_rules = []
    rule_audit = []
    for rule in rule_rows:
        candidate = candidates_by_id.get(rule["episode_id"])
        eligible = candidate is not None
        verbatim = bool(
            candidate is not None
            and rule["rule_summary"] in candidate.user_message
        )
        if eligible and verbatim:
            resolving_rules.append(candidate.candidate_id)
        rule_audit.append(
            {
                "rule_id": rule["id"],
                "episode_id": rule["episode_id"],
                "turn_number": rule["turn_number"],
                "eligible_source_episode": eligible,
                "verbatim_source_resolution": verbatim,
            }
        )
    resolving_rule_ids = tuple(sorted(set(resolving_rules)))
    rule_valid = bool(resolving_rule_ids)

    report = {
        "corpus_id": spec.corpus_id,
        "registered_domains": list(registered_domains),
        "excluded_domain_counts": dict(sorted(excluded_domains.items())),
        "topic_axis": {
            "valid": topic_valid,
            "status": "VALID" if topic_valid else "NOT_EVALUABLE",
            "invalid_reasons": topic_reasons,
            "domain_rows": domain_rows,
            "macro_domain_to_topic_purity": float(macro_purity),
            "macro_domain_to_topic_purity_exact": str(macro_purity),
            "distinct_dominant_topic_count": distinct_dominants,
            "required_distinct_dominant_topic_count": len(
                registered_domains
            ),
            "topic_to_domain_rows": reverse_rows,
            "macro_topic_to_domain_purity": float(reverse_macro),
            "macro_topic_to_domain_purity_exact": str(reverse_macro),
            "missing_centroid_topic_ids": missing_centroids,
        },
        "pinned_rule_axis": {
            "valid": rule_valid,
            "status": "VALID" if rule_valid else "NOT_EVALUABLE",
            "persisted_rule_count": len(rule_rows),
            "resolving_rule_count": len(resolving_rule_ids),
            "resolving_source_candidate_ids": list(resolving_rule_ids),
            "rule_audit": rule_audit,
        },
    }
    return OrthogonalAxes(
        report=report,
        topic_centroids=topic_centroids,
        resolving_rule_candidate_ids=resolving_rule_ids,
    )


def _load_axes_from_database(
    spec: CorpusSpec,
) -> tuple[dict[str, np.ndarray], list[dict]]:
    connection = sqlite3.connect(
        f"file:{spec.database_path.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        topic_rows = connection.execute(
            "SELECT id, centroid FROM topics ORDER BY id"
        ).fetchall()
        rule_rows = connection.execute(
            """
            SELECT id, episode_id, rule_summary, turn_number
            FROM rule_store
            ORDER BY turn_number, id
            """
        ).fetchall()
    finally:
        connection.close()
    centroids = {}
    for row in topic_rows:
        vector = np.frombuffer(row["centroid"], dtype=np.float32).copy()
        if vector.shape != (EMBEDDING_DIMENSION,):
            raise ValueError(f"Invalid topic centroid shape: {vector.shape}")
        centroids[str(row["id"])] = normalize_embedding(vector)
    return (
        centroids,
        [
            {
                "id": str(row["id"]),
                "episode_id": str(row["episode_id"]),
                "rule_summary": str(row["rule_summary"]),
                "turn_number": int(row["turn_number"]),
            }
            for row in rule_rows
        ],
    )


def _should_stop(
    packed: PackResult,
    budget: int,
    best_cosine: float | None,
) -> bool:
    return bool(
        len(packed.rendered_block) >= MINIMUM_BUDGET_FILL * budget
        and best_cosine is not None
        and best_cosine >= MINIMUM_BEST_COSINE
    )
