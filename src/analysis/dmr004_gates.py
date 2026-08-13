"""DMR-004 gate evaluation.

Bars come from the locked pre-registration §7 and are repeated here as
constants so a gate run can be reproduced from committed code alone. They are
not parameters. Changing one changes the study, not the analysis.

G_J, G3 and G4 must all pass. Each alone is passed by a degenerate compiler -
always-`OPEN` passes G3, always-`LOOKUP` passes G4, and neither passes G_J,
which is zero for both by construction. `structural_controls` computes exactly
those degenerate arms so the report can show the joint condition doing its job
rather than asserting that it would.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from analysis import dmr004_corpus as corpus
from biological_memory.query_obligations import (
    CompletenessMode,
    PlanClass,
    QueryObligationCompiler,
    design_sha256,
)

BARS = {
    "G_J": {"min_youden_j": 0.50},
    "G3": {"max_false_finite_rate": 0.15},
    "G4": {"min_lookup_recall": 0.60},
    "G5": {"min_well_formed_share": 1.0},
    "G6": {"max_internal_only_markers": 0},
}

#: Classes the pre-registration emits but does not gate, and why.
UNGATED_CLASSES = {
    "CONJUNCT": "1 instance in the 524-query corpus; every detector that finds more separates the corpora",
    "ENUMERATE_N": "10 instances; supports an exact-match report, not a rate bar",
    "HISTORY": "2 adjudicated instances in 120 development queries",
}


def _confusion(truth: Sequence[bool], predicted: Sequence[bool]) -> dict[str, int]:
    tp = sum(1 for t, p in zip(truth, predicted) if t and p)
    fn = sum(1 for t, p in zip(truth, predicted) if t and not p)
    fp = sum(1 for t, p in zip(truth, predicted) if not t and p)
    tn = sum(1 for t, p in zip(truth, predicted) if not t and not p)
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn}


def _rates(counts: dict[str, int]) -> dict[str, float | None]:
    positives = counts["tp"] + counts["fn"]
    negatives = counts["tn"] + counts["fp"]
    sensitivity = counts["tp"] / positives if positives else None
    specificity = counts["tn"] / negatives if negatives else None
    youden = (
        sensitivity + specificity - 1.0
        if sensitivity is not None and specificity is not None
        else None
    )
    return {
        "sensitivity": sensitivity,
        "specificity": specificity,
        "youden_j": youden,
        "balanced_accuracy": (
            (sensitivity + specificity) / 2.0
            if sensitivity is not None and specificity is not None
            else None
        ),
        "false_finite_rate": counts["fp"] / negatives if negatives else None,
        # Reported because the pre-registration says to report them, and
        # explicitly barred from passing anything.
        "accuracy": (counts["tp"] + counts["tn"]) / max(1, sum(counts.values())),
    }


def load_gold(repository_root: Path, split: str) -> list[dict[str, Any]]:
    path = (
        repository_root
        / "experiments/components/biological_memory/dmr_004/artifacts"
        / f"gold_{split}.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))["gold"]["labels"]


def evaluate(repository_root: Path, split: str) -> dict[str, Any]:
    records = {record.query_id: record for record in corpus.read_cache(repository_root)}
    gold = load_gold(repository_root, split)
    compiler = QueryObligationCompiler()

    truth: list[bool] = []
    predicted: list[bool] = []
    plans = []
    for row in gold:
        record = records[row["query_id"]]
        plan = compiler.compile(record.text)
        plans.append((record, row, plan))
        truth.append(bool(row["finite"]))
        predicted.append(plan.completeness_mode is CompletenessMode.FINITE)

    counts = _confusion(truth, predicted)
    rates = _rates(counts)

    # G4: recall on the one gated class.
    lookup_gold = [(record, row, plan) for record, row, plan in plans if row["plan_class"] == "LOOKUP"]
    lookup_hits = sum(1 for _, _, plan in lookup_gold if plan.plan_class is PlanClass.LOOKUP)
    lookup_recall = lookup_hits / len(lookup_gold) if lookup_gold else None

    # G5: span well-formedness, checked against the original string.
    malformed: list[str] = []
    spanned = 0
    for record, _row, plan in plans:
        spans = [(o.source_start, o.source_end) for o in plan.obligations]
        spanned += len(spans)
        for obligation in plan.obligations:
            start, end = obligation.source_start, obligation.source_end
            if not (0 <= start < end <= len(record.text)):
                malformed.append(f"{record.query_id}:bounds")
            elif obligation.source_text != record.text[start:end]:
                malformed.append(f"{record.query_id}:text")
        for earlier, later in zip(spans, spans[1:]):
            if earlier[1] > later[0]:
                malformed.append(f"{record.query_id}:overlap")

    gates = {
        "G_J": {
            "statistic": "youden_j",
            "value": rates["youden_j"],
            "bar": BARS["G_J"]["min_youden_j"],
            "pass": rates["youden_j"] is not None and rates["youden_j"] >= BARS["G_J"]["min_youden_j"],
        },
        "G3": {
            "statistic": "false_finite_rate",
            "value": rates["false_finite_rate"],
            "bar": BARS["G3"]["max_false_finite_rate"],
            "pass": rates["false_finite_rate"] is not None
            and rates["false_finite_rate"] <= BARS["G3"]["max_false_finite_rate"],
        },
        "G4": {
            "statistic": "lookup_recall",
            "value": lookup_recall,
            "bar": BARS["G4"]["min_lookup_recall"],
            "instances": len(lookup_gold),
            "pass": lookup_recall is not None and lookup_recall >= BARS["G4"]["min_lookup_recall"],
        },
        "G5": {
            "statistic": "well_formed_span_share",
            "value": (spanned - len(malformed)) / spanned if spanned else 1.0,
            "bar": BARS["G5"]["min_well_formed_share"],
            "spans": spanned,
            "malformed": malformed[:10],
            "pass": not malformed,
        },
    }
    gates["G6"] = benchmark_independence(repository_root)
    joint = all(gates[name]["pass"] for name in ("G_J", "G3", "G4"))

    return {
        "split": split,
        "design_sha256": design_sha256(),
        "annotated": len(gold),
        "confusion": counts,
        "rates": rates,
        "gates": gates,
        "joint_condition_pass": joint,
        "compiler_class_distribution": dict(
            Counter(plan.plan_class.value for _, _, plan in plans)
        ),
        "gold_class_distribution": dict(Counter(row["plan_class"] for row in gold)),
        "ungated_classes": UNGATED_CLASSES,
        "structural_controls": structural_controls(truth, [row["plan_class"] for row in gold]),
    }


def benchmark_independence(repository_root: Path) -> dict[str, Any]:
    """G6: a marker that only this program's own probes trigger is a corpus detector.

    Part 1 found every conjunction rule with usable support fired on 66.7% of
    internal probes and 0.4% of natural questions. This checks the markers that
    were actually registered, and also records which never fire at all - untested
    vocabulary the report must not claim coverage for.
    """
    import re

    from biological_memory import query_obligations as grammar

    records = corpus.read_cache(repository_root)
    internal = [grammar.canonical_map(r.text)[0] for r in records if r.source == "internal"]
    external = [grammar.canonical_map(r.text)[0] for r in records if r.source == "longmemeval"]

    groups = {
        "HISTORY_MARKERS": grammar.HISTORY_MARKERS,
        "AGGREGATE_MARKERS": grammar.AGGREGATE_MARKERS,
        "SUPERLATIVE_MARKERS": grammar.SUPERLATIVE_MARKERS,
        "LIST_MARKERS": grammar.LIST_MARKERS,
    }
    internal_only: list[str] = []
    unexercised: list[str] = []
    total = 0
    for group, phrases in groups.items():
        for phrase in phrases:
            total += 1
            pattern = re.compile(r"\b" + re.escape(phrase) + r"\b")
            fires_internal = any(pattern.search(text) for text in internal)
            fires_external = any(pattern.search(text) for text in external)
            if fires_internal and not fires_external:
                internal_only.append(f"{group}:{phrase}")
            if not fires_internal and not fires_external:
                unexercised.append(f"{group}:{phrase}")
    return {
        "statistic": "internal_only_markers",
        "value": len(internal_only),
        "bar": BARS["G6"]["max_internal_only_markers"],
        "markers_total": total,
        "internal_only": internal_only,
        "unexercised": unexercised,
        "unexercised_count": len(unexercised),
        "pass": not internal_only,
    }


def structural_controls(truth: Sequence[bool], gold_classes: Sequence[str]) -> dict[str, Any]:
    """The degenerate arms, so the joint condition can be shown working.

    `always_finite` is the compiler that never refuses; `always_open` is the one
    that never commits. Both are useless and each passes one gate on its own.
    """
    out: dict[str, Any] = {}
    for name, predicted in (
        ("always_finite", [True] * len(truth)),
        ("always_open", [False] * len(truth)),
    ):
        counts = _confusion(truth, predicted)
        rates = _rates(counts)
        lookup_total = sum(1 for cls in gold_classes if cls == "LOOKUP")
        lookup_recall = (
            (1.0 if name == "always_finite" else 0.0) if lookup_total else None
        )
        out[name] = {
            "youden_j": rates["youden_j"],
            "false_finite_rate": rates["false_finite_rate"],
            "lookup_recall": lookup_recall,
            "accuracy": rates["accuracy"],
            "passes_G_J": rates["youden_j"] is not None
            and rates["youden_j"] >= BARS["G_J"]["min_youden_j"],
            "passes_G3": rates["false_finite_rate"] is not None
            and rates["false_finite_rate"] <= BARS["G3"]["max_false_finite_rate"],
            "passes_G4": lookup_recall is not None
            and lookup_recall >= BARS["G4"]["min_lookup_recall"],
        }
    return out


def write_report(repository_root: Path, split: str) -> Path:
    record = evaluate(repository_root, split)
    path = (
        repository_root
        / "experiments/components/biological_memory/dmr_004/artifacts"
        / f"gates_{split}.json"
    )
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
