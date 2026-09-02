"""Outcome join and fixed analysis for DA-003."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da003_edge_features import DA003Error, FEATURES
from analysis.nf004_anatomy_features import sha256_file
from analysis.nf004_anatomy_analysis import _predict, auc, average_precision
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split


def read_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "p10": None, "p50": None, "p90": None}
    array = np.asarray(values, dtype=float)
    return {"n": len(values), "p10": float(np.percentile(array, 10)),
            "p50": float(np.percentile(array, 50)), "p90": float(np.percentile(array, 90))}


def grouped_model(rows: Sequence[Mapping[str, Any]], endpoint: str) -> dict[str, Any]:
    x = np.asarray([[float(row["features"][name]) for name in FEATURES] for row in rows])
    y = np.asarray([int(row[endpoint]) for row in rows])
    groups = np.asarray([row["sample_id"] for row in rows])
    probabilities = np.zeros(len(rows), dtype=float)
    by_conversation: dict[str, Any] = {}
    for group in sorted(set(groups)):
        test = groups == group
        train = ~test
        probabilities[test] = _predict(x[train], y[train], x[test], 1.0)
        labels = y[test]
        by_conversation[str(group)] = {
            "n": int(test.sum()), "positives": int(labels.sum()),
            "auc": float(auc(probabilities[test], labels)) if len(set(labels)) == 2 else None,
        }
    return {
        "n": len(rows), "positives": int(y.sum()),
        "auc": float(auc(probabilities, y)),
        "average_precision": float(average_precision(probabilities, y)),
        "brier": float(np.mean((probabilities - y) ** 2)),
        "by_conversation": by_conversation,
    }


def run_analysis(dataset_path: Path, blind_path: Path, preflight_path: Path,
                 g6_path: Path, output_dir: Path) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(blind_path) != preflight["edge_sha256"]:
        raise DA003Error("Committed DA-003 blind edge seal is absent or drifted")
    rows = read_rows(blind_path)
    records = adapt_split(dataset_path, HOLDOUT_IDS)
    evidence: dict[tuple[str, int], set[str]] = {}
    for record in records:
        mapping = {dialogue_id: source.candidate.identity for source in record.candidates for dialogue_id in source.dialogue_ids}
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = {
                mapping[item] for item in question.resolved_dialogue_ids
            }
    g6 = json.loads(g6_path.read_text(encoding="utf-8"))["rows"]
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"]) for row in g6}
    joined = []
    direct_by_question: dict[tuple[str, int], bool] = {}
    for row in rows:
        key = (row["comparison_key"], int(row["duplicate_ordinal"]))
        if not primary[key]:
            continue
        gold = evidence[key]
        direct_set, treatment_set = set(row["direct_selected_ids"]), set(row["counterfactual_selected_ids"])
        direct_complete, treatment_complete = gold <= direct_set, gold <= treatment_set
        direct_by_question[key] = direct_complete
        benefit = treatment_complete and not direct_complete
        harm = direct_complete and not treatment_complete
        if benefit and not (gold - direct_set <= {row["neighbor_id"]}):
            raise DA003Error("Benefit lacks admitted-neighbor causal identity")
        if harm and not (gold & direct_set - treatment_set <= set(row["displaced_ids"])):
            raise DA003Error("Harm lacks displaced-evidence causal identity")
        joined.append({**row, "benefit": benefit, "harm": harm,
                       "label": "BENEFIT" if benefit else "HARM" if harm else "NEUTRAL"})
    if len(direct_by_question) != 1_098 or sum(direct_by_question.values()) != 935:
        raise DA003Error("DA-003 direct primary reproduction differs")
    counts = Counter(row["label"] for row in joined)
    if not all(counts[label] for label in ("BENEFIT", "HARM", "NEUTRAL")):
        raise DA003Error("DA-003 endpoint is degenerate")
    summaries = {
        label: {name: distribution([float(row["features"][name]) for row in joined if row["label"] == label])
                for name in FEATURES}
        for label in ("BENEFIT", "HARM", "NEUTRAL")
    }
    univariate = {}
    for endpoint in ("benefit", "harm"):
        labels = np.asarray([int(row[endpoint]) for row in joined])
        feature_rows = {}
        for name in FEATURES:
            values = np.asarray([float(row["features"][name]) for row in joined])
            per_group = {}
            for group in sorted({row["sample_id"] for row in joined}):
                mask = np.asarray([row["sample_id"] == group for row in joined])
                per_group[group] = float(auc(values[mask], labels[mask])) if len(set(labels[mask])) == 2 else None
            feature_rows[name] = {"auc": float(auc(values, labels)), "by_conversation": per_group}
        univariate[endpoint] = feature_rows
    result = {
        "schema": "da003-edge-result-v1", "standing": "post-outcome exploration on spent NF-004 LoCoMo",
        "population": {"questions": len(direct_by_question), "edges": len(joined), "labels": dict(sorted(counts.items()))},
        "feature_summaries": summaries, "univariate": univariate,
        "models": {endpoint: grouped_model(joined, endpoint) for endpoint in ("benefit", "harm")},
        "calls": {"embedding": 0, "model": 0, "cache_misses": 0},
        "claim_boundary": "descriptive new-signal exploration only; no gate, threshold, reader, or adoption",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    slim = [{key: row[key] for key in ("comparison_key", "duplicate_ordinal", "sample_id", "source_index", "seed_id", "neighbor_id", "benefit", "harm", "label")} for row in joined]
    with (output_dir / "edge_labels.jsonl.gz").open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in slim:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return result


__all__ = ["run_analysis"]
