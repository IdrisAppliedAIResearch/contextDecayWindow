from __future__ import annotations

from fractions import Fraction

from .classifier import classify_query
from .config import CORPORA


QUERY_CLASSES = ("lookup", "chained", "enumeration")


def analyze_tier3(evaluation_rows: list[dict], tier2_summary: dict) -> dict:
    pooled = tier2_summary["pooled_class"]
    winners = {
        query_class: _winner(
            [
                row
                for row in pooled
                if row["query_class"] == query_class
            ]
        )
        for query_class in QUERY_CLASSES
    }
    primary_rows = [
        row
        for row in evaluation_rows
        if row["corpus_id"] in {"c121_l", "c1000_l"}
    ]
    selected_methods = {
        query_class: row["method_id"]
        for query_class, row in winners.items()
    }
    oracle_rows = [
        row
        for row in primary_rows
        if row["method_id"] == selected_methods[row["query_class"]]
    ]
    oracle_recall = _exact_query_recall(oracle_rows)

    overall_winner = _winner(tier2_summary["overall_primary"])
    single_rows = [
        row
        for row in primary_rows
        if row["method_id"] == overall_winner["method_id"]
    ]
    single_recall = _exact_query_recall(single_rows)
    oracle_gain = (
        (oracle_recall - single_recall) / single_recall
        if single_recall
        else None
    )

    classifier = _classifier_analysis(primary_rows)
    return {
        "T3.1_per_class_winners": {
            query_class: {
                "method_id": row["method_id"],
                "fact_recall_at_budget": row["fact_recall_at_budget"],
                "fact_recall_exact": row["fact_recall_exact"],
                "precision_proxy": row["precision_proxy"],
                "latency_ms": row["latency_ms"],
            }
            for query_class, row in winners.items()
        },
        "T3.2_oracle_router": {
            "selected_method_by_class": selected_methods,
            "oracle_macro_query_recall": float(oracle_recall),
            "oracle_macro_query_recall_exact": str(oracle_recall),
            "single_best_method": overall_winner["method_id"],
            "single_best_macro_query_recall": float(single_recall),
            "single_best_macro_query_recall_exact": str(single_recall),
            "relative_gain": (
                float(oracle_gain) if oracle_gain is not None else None
            ),
            "relative_gain_exact": (
                str(oracle_gain) if oracle_gain is not None else None
            ),
            "gain_at_least_10_percent": (
                oracle_gain is not None and oracle_gain >= Fraction(1, 10)
            ),
            "interpretation": (
                "routing_worth_confirmatory_work"
                if oracle_gain is not None
                and oracle_gain >= Fraction(1, 10)
                else "do_not_build_routing"
            ),
        },
        "T3.3_classifier": classifier,
    }


def _winner(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Cannot choose a winner from no rows")
    return sorted(
        rows,
        key=lambda row: (
            -Fraction(
                row.get(
                    "fact_recall_exact",
                    str(row["fact_recall_at_budget"]),
                )
            ),
            -float(row["precision_proxy"]),
            float(row["latency_ms"]),
            str(row["method_id"]),
        ),
    )[0]


def _exact_query_recall(rows: list[dict]) -> Fraction:
    return sum(
        (
            Fraction(
                int(row["matched_fact_count"]),
                int(row["required_fact_count"]),
            )
            for row in rows
        ),
        Fraction(),
    ) / len(rows)


def _classifier_analysis(primary_rows: list[dict]) -> dict:
    unique: dict[tuple[str, str], dict] = {}
    for row in primary_rows:
        if row["method_id"] != "M2":
            continue
        unique[(row["corpus_id"], row["query_id"])] = row

    confusion = {
        actual: {predicted: 0 for predicted in QUERY_CLASSES}
        for actual in QUERY_CLASSES
    }
    predictions = []
    for (corpus_id, query_id), row in sorted(unique.items()):
        predicted = classify_query(
            row["query_text"],
            CORPORA[corpus_id].domain_labels,
        )
        actual = row["query_class"]
        confusion[actual][predicted] += 1
        predictions.append(
            {
                "corpus_id": corpus_id,
                "query_id": query_id,
                "actual": actual,
                "predicted": predicted,
                "correct": predicted == actual,
            }
        )
    correct = sum(row["correct"] for row in predictions)
    return {
        "accuracy": correct / len(predictions) if predictions else 0.0,
        "correct": correct,
        "total": len(predictions),
        "confusion_matrix_actual_by_predicted": confusion,
        "predictions": predictions,
        "features": "query text only under the registered deterministic rules",
    }
