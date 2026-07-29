from __future__ import annotations

import re
from collections import defaultdict
from fractions import Fraction
from statistics import fmean

from .graph import GRAPH_CONFIGS


_METHOD = re.compile(r"^G_(.+)_d([123])$")
_CLASSES = ("lookup", "chained", "enumeration")


def analyze_graph_results(
    rows: list[dict],
    *,
    tier2_corrected_summary: dict,
    baseline_rows: list[dict],
    update_benchmark: dict,
) -> dict:
    corpus_class = _corpus_class_rows(rows)
    pooled = _pooled_rows(corpus_class)
    baseline_old = {
        row["query_class"]: row
        for row in _pooled_rows(_corpus_class_rows(baseline_rows))
    }
    baseline = {
        row["query_class"]: row
        for row in tier2_corrected_summary["pooled_class"]
        if row["method_id"] == "M1"
    }
    slopes = update_benchmark["component_slopes"]
    advancement = []
    for method_id in sorted({row["method_id"] for row in pooled}):
        method_rows = {
            row["query_class"]: row
            for row in pooled
            if row["method_id"] == method_id
        }
        config_id, depth = parse_graph_method_id(method_id)
        values = {
            query_class: Fraction(
                method_rows[query_class]["fact_recall_exact"]
            )
            for query_class in _CLASSES
        }
        baseline_values = {
            query_class: Fraction(
                baseline[query_class]["fact_recall_exact"]
            )
            for query_class in _CLASSES
        }
        wins = [
            query_class
            for query_class in _CLASSES
            if values[query_class] > baseline_values[query_class]
        ]
        regressions = [
            query_class
            for query_class in _CLASSES
            if baseline_values[query_class] > 0
            and values[query_class]
            < Fraction(9, 10) * baseline_values[query_class]
        ]
        component_slopes = {
            component: slopes[component]["log10_slope"]
            for component in GRAPH_CONFIGS[config_id]
        }
        update_pass = all(value <= 1.10 for value in component_slopes.values())
        eligible_core = config_id != "E4"
        advancement.append(
            {
                "method_id": method_id,
                "config_id": config_id,
                "depth": depth,
                "eligible_core": eligible_core,
                "recall_pass": bool(wins and not regressions),
                "update_cost_pass": update_pass,
                "advances": bool(
                    eligible_core and wins and not regressions and update_pass
                ),
                "winning_classes": wins,
                "regressing_classes": regressions,
                "component_update_slopes": component_slopes,
                "candidate_recall_exact": {
                    key: str(value) for key, value in values.items()
                },
                "baseline_recall_exact": {
                    key: str(value) for key, value in baseline_values.items()
                },
            }
        )

    winners_all = _per_class_winners(pooled)
    winners_core = _per_class_winners(
        [
            row
            for row in pooled
            if parse_graph_method_id(row["method_id"])[0] != "E4"
        ]
    )

    depth_curves = []
    by_method: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_method[row["method_id"]].append(row)
    for method_id, group in sorted(by_method.items()):
        config_id, depth = parse_graph_method_id(method_id)
        depth_curves.append(
            {
                "method_id": method_id,
                "config_id": config_id,
                "depth": depth,
                **_aggregate_group(group),
                "query_count": len(group),
            }
        )

    return {
        "corpus_class": corpus_class,
        "pooled_class": pooled,
        "advancement": advancement,
        "gate_passes": any(row["advances"] for row in advancement),
        "advancing_methods": [
            row["method_id"] for row in advancement if row["advances"]
        ],
        "per_class_winners": winners_core,
        "per_class_winners_including_descriptive_e4": winners_all,
        "depth_curves": depth_curves,
        "old_fact_comparison": {
            "flat_m1": baseline_old,
            "graph": [
                {
                    "method_id": row["method_id"],
                    "query_class": row["query_class"],
                    "old_fact_miss_rate": row["old_fact_miss_rate"],
                    "old_fact_miss_rate_exact": (
                        row["old_fact_miss_rate_exact"]
                    ),
                    "flat_m1_old_fact_miss_rate": baseline_old[
                        row["query_class"]
                    ]["old_fact_miss_rate"],
                    "delta_from_flat_m1": (
                        row["old_fact_miss_rate"]
                        - baseline_old[row["query_class"]][
                            "old_fact_miss_rate"
                        ]
                        if row["old_fact_miss_rate"] is not None
                        and baseline_old[row["query_class"]][
                            "old_fact_miss_rate"
                        ]
                        is not None
                        else None
                    ),
                }
                for row in pooled
            ],
        },
    }


def _per_class_winners(rows: list[dict]) -> dict[str, dict]:
    winners = {}
    for query_class in _CLASSES:
        candidates = [
            row for row in rows if row["query_class"] == query_class
        ]
        winners[query_class] = sorted(
            candidates,
            key=lambda row: (
                -Fraction(row["fact_recall_exact"]),
                -float(row["precision_proxy"]),
                float(row["latency_ms"]),
                row["method_id"],
            ),
        )[0]
    return winners


def parse_graph_method_id(method_id: str) -> tuple[str, int]:
    match = _METHOD.match(method_id)
    if match is None:
        raise ValueError(f"Invalid graph method ID: {method_id}")
    config_id, depth = match.groups()
    if config_id not in GRAPH_CONFIGS:
        raise ValueError(f"Unknown graph configuration: {config_id}")
    return config_id, int(depth)


def _corpus_class_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[
            (row["method_id"], row["corpus_id"], row["query_class"])
        ].append(row)
    return [
        {
            "method_id": method_id,
            "corpus_id": corpus_id,
            "query_class": query_class,
            **_aggregate_group(group),
            "query_count": len(group),
        }
        for (method_id, corpus_id, query_class), group in sorted(
            grouped.items()
        )
    ]


def _pooled_rows(corpus_class: list[dict]) -> list[dict]:
    result = []
    methods = sorted({row["method_id"] for row in corpus_class})
    for method_id in methods:
        for query_class in _CLASSES:
            cells = [
                row
                for row in corpus_class
                if row["method_id"] == method_id
                and row["query_class"] == query_class
            ]
            if len(cells) != 2:
                raise AssertionError(
                    f"Expected two corpus cells for {method_id}/{query_class}"
                )
            exact = sum(
                (Fraction(cell["fact_recall_exact"]) for cell in cells),
                Fraction(),
            ) / 2
            old_cells = [
                Fraction(cell["old_fact_miss_rate_exact"])
                for cell in cells
                if cell["old_fact_miss_rate_exact"] is not None
            ]
            old_exact = (
                sum(old_cells, Fraction()) / len(old_cells)
                if old_cells
                else None
            )
            result.append(
                {
                    "method_id": method_id,
                    "query_class": query_class,
                    "fact_recall_at_budget": float(exact),
                    "fact_recall_exact": str(exact),
                    "domain_coverage": fmean(
                        cell["domain_coverage"] for cell in cells
                    ),
                    "precision_proxy": fmean(
                        cell["precision_proxy"] for cell in cells
                    ),
                    "delivered_characters": fmean(
                        cell["delivered_characters"] for cell in cells
                    ),
                    "latency_ms": fmean(
                        cell["latency_ms"] for cell in cells
                    ),
                    "index_build_ms": fmean(
                        cell["index_build_ms"] for cell in cells
                    ),
                    "old_fact_miss_rate": (
                        float(old_exact) if old_exact is not None else None
                    ),
                    "old_fact_miss_rate_exact": (
                        str(old_exact) if old_exact is not None else None
                    ),
                    "corpus_count": len(cells),
                }
            )
    return result


def _aggregate_group(rows: list[dict]) -> dict:
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
            len(row["old_required_fact_ids"]) - len(row["old_matched_fact_ids"]),
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
        "fact_recall_at_budget": float(recall),
        "fact_recall_exact": str(recall),
        "domain_coverage": fmean(float(row["domain_coverage"]) for row in rows),
        "precision_proxy": fmean(float(row["precision_proxy"]) for row in rows),
        "delivered_characters": fmean(
            float(row["delivered_characters"]) for row in rows
        ),
        "latency_ms": fmean(float(row["latency_ms"]) for row in rows),
        "index_build_ms": fmean(float(row["index_build_ms"]) for row in rows),
        "old_fact_miss_rate": (
            float(old_miss) if old_miss is not None else None
        ),
        "old_fact_miss_rate_exact": (
            str(old_miss) if old_miss is not None else None
        ),
    }
