from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from statistics import fmean


BUDGETS = (32_000, 64_000, 160_000, 320_000)
GRAPH_COMPARATORS = (
    "G_E1_E3_d1",
    "G_E3_d2",
    "G_E3_d3",
)


def analyze_tier5(
    *,
    budget_rows: list[dict],
    progressive_rows: list[dict],
    graph_rows: list[dict],
    ann_results: list[dict],
    axis_reports: dict[str, dict],
) -> dict:
    budget_analysis = _budget_analysis(budget_rows)
    progressive_analysis = _progressive_analysis(progressive_rows)
    comparison = _tiering_comparison(progressive_rows, graph_rows)
    return {
        "T5.0_budget_multiples": budget_analysis,
        "T5.1_ann": {
            "scales": ann_results,
            "minimum_recall_at_10": min(
                row["recall_at_10"] for row in ann_results
            ),
            "minimum_recall_at_50": min(
                row["recall_at_50"] for row in ann_results
            ),
        },
        "T5.2_progressive_search": progressive_analysis,
        "T5.3_axis_validation": axis_reports,
        "T5.4_tiering_comparison": comparison,
    }


def _budget_analysis(rows: list[dict]) -> dict:
    expected = 2 * len(BUDGETS) * 24
    if len(rows) != expected:
        raise AssertionError(f"Expected {expected} T5.0 rows, got {len(rows)}")
    by_corpus_budget_class = _group_aggregate(
        rows,
        ("corpus_id", "budget", "query_class"),
    )
    by_budget = _group_aggregate(rows, ("budget",))
    by_budget_map = {int(row["budget"]): row for row in by_budget}
    two_x = by_budget_map[64_000]
    higher = [by_budget_map[160_000], by_budget_map[320_000]]
    recall_collapse = [
        row["budget"]
        for row in higher
        if Fraction(row["fact_recall_exact"])
        < Fraction(two_x["fact_recall_exact"])
    ]
    coverage_collapse = [
        row["budget"]
        for row in higher
        if row["domain_coverage"] < two_x["domain_coverage"]
    ]
    return {
        "policy": "M3",
        "status": "advancing",
        "by_corpus_budget_class": by_corpus_budget_class,
        "overall_by_budget": by_budget,
        "fact_recall_collapse_above_2x": bool(recall_collapse),
        "fact_recall_collapsing_budgets": recall_collapse,
        "domain_coverage_collapse_above_2x": bool(coverage_collapse),
        "domain_coverage_collapsing_budgets": coverage_collapse,
    }


def _progressive_analysis(rows: list[dict]) -> dict:
    by_corpus_arm_class = _group_aggregate(
        rows,
        ("corpus_id", "method_id", "query_class"),
    )
    by_arm = _group_aggregate(rows, ("method_id",))
    paths = defaultdict(Counter)
    stops = defaultdict(Counter)
    for row in rows:
        key = (row["corpus_id"], row["method_id"])
        paths[key][" > ".join(row["searched_tiers"])] += 1
        stops[key][row["stop_reason"]] += 1
    return {
        "by_corpus_arm_class": by_corpus_arm_class,
        "overall_by_arm": by_arm,
        "tier_path_counts": [
            {
                "corpus_id": corpus_id,
                "method_id": method_id,
                "paths": dict(sorted(counts.items())),
                "stop_reasons": dict(sorted(stops[(corpus_id, method_id)].items())),
            }
            for (corpus_id, method_id), counts in sorted(paths.items())
        ],
    }


def _tiering_comparison(
    progressive_rows: list[dict],
    graph_rows: list[dict],
) -> dict:
    graph_by_method = defaultdict(list)
    for row in graph_rows:
        if row["method_id"] in GRAPH_COMPARATORS:
            graph_by_method[row["method_id"]].append(row)
    progressive_by_arm = defaultdict(list)
    for row in progressive_rows:
        progressive_by_arm[row["method_id"]].append(row)

    comparisons = []
    for arm_id, partition_rows in sorted(progressive_by_arm.items()):
        corpus_ids = sorted({row["corpus_id"] for row in partition_rows})
        partition_cells = {
            (row["corpus_id"], row["query_id"]) for row in partition_rows
        }
        partition_metrics = _aggregate(partition_rows)
        for graph_method in GRAPH_COMPARATORS:
            matched_graph = [
                row
                for row in graph_by_method[graph_method]
                if row["corpus_id"] in corpus_ids
            ]
            graph_cells = {
                (row["corpus_id"], row["query_id"])
                for row in matched_graph
            }
            if graph_cells != partition_cells:
                raise AssertionError(
                    f"Unmatched T5.4 cells for {arm_id}/{graph_method}"
                )
            graph_metrics = _aggregate(matched_graph)
            graph_dominates = _dominates(graph_metrics, partition_metrics)
            partition_dominates = _dominates(
                partition_metrics,
                graph_metrics,
            )
            if graph_dominates and partition_dominates:
                interpretation = "exact_match"
            elif graph_dominates:
                interpretation = "depth_matches_or_beats_partition"
            elif partition_dominates:
                interpretation = "partition_matches_or_beats_depth"
            else:
                interpretation = "tradeoff"
            comparisons.append(
                {
                    "partition_arm": arm_id,
                    "graph_method": graph_method,
                    "corpus_ids": corpus_ids,
                    "query_count": len(partition_rows),
                    "partition": partition_metrics,
                    "graph": graph_metrics,
                    "graph_matches_or_beats_partition": graph_dominates,
                    "partition_matches_or_beats_graph": partition_dominates,
                    "interpretation": interpretation,
                }
            )
    return {
        "graph_comparators": list(GRAPH_COMPARATORS),
        "comparisons": comparisons,
        "any_depth_matches_or_beats_partition": any(
            row["graph_matches_or_beats_partition"]
            for row in comparisons
        ),
    }


def _dominates(candidate: dict, baseline: dict) -> bool:
    candidate_old = candidate["old_fact_miss_rate_exact"]
    baseline_old = baseline["old_fact_miss_rate_exact"]
    old_ok = (
        candidate_old is None
        and baseline_old is None
        or candidate_old is not None
        and baseline_old is not None
        and Fraction(candidate_old) <= Fraction(baseline_old)
    )
    return bool(
        Fraction(candidate["fact_recall_exact"])
        >= Fraction(baseline["fact_recall_exact"])
        and candidate["latency_ms"] <= baseline["latency_ms"]
        and old_ok
    )


def _group_aggregate(
    rows: list[dict],
    keys: tuple[str, ...],
) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    return [
        {
            **dict(zip(keys, values, strict=True)),
            **_aggregate(group),
        }
        for values, group in sorted(grouped.items())
    ]


def _aggregate(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Cannot aggregate an empty row set")
    recall = sum(
        (
            Fraction(
                int(row["matched_fact_count"]),
                int(row["required_fact_count"]),
            )
            for row in rows
        ),
        Fraction(),
    ) / len(rows)
    old_rows = [
        Fraction(
            len(row["old_required_fact_ids"])
            - len(row["old_matched_fact_ids"]),
            len(row["old_required_fact_ids"]),
        )
        for row in rows
        if row["old_required_fact_ids"]
    ]
    old_miss = (
        sum(old_rows, Fraction()) / len(old_rows)
        if old_rows
        else None
    )
    return {
        "query_count": len(rows),
        "fact_recall_at_budget": float(recall),
        "fact_recall_exact": str(recall),
        "domain_coverage": fmean(
            float(row["domain_coverage"]) for row in rows
        ),
        "precision_proxy": fmean(
            float(row["precision_proxy"]) for row in rows
        ),
        "delivered_characters": fmean(
            float(row["delivered_characters"]) for row in rows
        ),
        "selected_count": fmean(float(row["selected_count"]) for row in rows),
        "latency_ms": fmean(float(row["latency_ms"]) for row in rows),
        "old_fact_miss_rate": (
            float(old_miss) if old_miss is not None else None
        ),
        "old_fact_miss_rate_exact": (
            str(old_miss) if old_miss is not None else None
        ),
    }
