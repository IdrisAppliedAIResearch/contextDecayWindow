"""Sealed evidence join and grouped analysis for DA-004."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import DA004Error, FEATURES
from analysis.nf004_anatomy_analysis import _predict, average_precision
from analysis.nf004_anatomy_features import sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split


def read_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def fast_auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    values = np.asarray(scores, dtype=float)
    target = np.asarray(labels, dtype=int)
    positives, negatives = int(target.sum()), int(len(target) - target.sum())
    if not positives or not negatives:
        raise DA004Error("AUC requires both labels")
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + end + 1) / 2.0
        start = end
    rank_sum = float(ranks[target == 1].sum())
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def distribution(values: Sequence[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=float)
    return {"n": len(values), "p10": float(np.percentile(array, 10)),
            "p50": float(np.percentile(array, 50)), "p90": float(np.percentile(array, 90))}


def grouped_model(rows: Sequence[Mapping[str, Any]], endpoint: str) -> dict[str, Any]:
    matrix = np.asarray([[float(row["features"][name]) for name in FEATURES] for row in rows])
    labels = np.asarray([int(row[endpoint]) for row in rows])
    groups = np.asarray([row["sample_id"] for row in rows])
    predictions = np.zeros(len(rows), dtype=float)
    by_group = {}
    for group in sorted(set(groups)):
        test = groups == group
        train = ~test
        predictions[test] = _predict(matrix[train], labels[train], matrix[test], 1.0)
        held = labels[test]
        by_group[str(group)] = {"n": int(test.sum()), "positives": int(held.sum()),
                                "auc": fast_auc(predictions[test], held) if len(set(held)) == 2 else None}
    auc_value = fast_auc(predictions, labels)
    evaluable = [row["auc"] for row in by_group.values() if row["auc"] is not None]
    return {"n": len(rows), "positives": int(labels.sum()), "auc": auc_value,
            "average_precision": average_precision(predictions, labels),
            "brier": float(np.mean((predictions - labels) ** 2)), "by_conversation": by_group,
            "signal_status": "NEW_SIGNAL_PRESENT" if auc_value >= .65 and all(value >= .5 for value in evaluable)
            else "NO_STABLE_PACK_SIGNAL"}


def run_analysis(dataset_path: Path, blind_path: Path, preflight_path: Path,
                 g6_path: Path, output_dir: Path) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(blind_path) != preflight["perturbation_sha256"]:
        raise DA004Error("Committed DA-004 blind seal is absent or drifted")
    blind = read_rows(blind_path)
    evidence = {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        mapping = {dialogue_id: source.candidate.identity for source in record.candidates for dialogue_id in source.dialogue_ids}
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = {
                mapping[item] for item in question.resolved_dialogue_ids
            }
    g6 = json.loads(g6_path.read_text(encoding="utf-8"))["rows"]
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"]) for row in g6}
    rows, direct_questions = [], {}
    carrier_counts = Counter()
    for row in blind:
        key = (row["comparison_key"], int(row["duplicate_ordinal"]))
        if not primary[key]:
            continue
        gold = evidence[key]
        direct, treatment = set(row["direct_selected_ids"]), set(row["counterfactual_selected_ids"])
        added, displaced = set(row["added_ids"]), set(row["displaced_ids"])
        direct_complete, treatment_complete = gold <= direct, gold <= treatment
        direct_questions[key] = direct_complete
        benefit, harm = treatment_complete and not direct_complete, direct_complete and not treatment_complete
        label = "BENEFIT" if benefit else "HARM" if harm else "NEUTRAL"
        if benefit:
            missing = gold - direct
            if not missing or not missing <= added:
                raise DA004Error("Benefit lacks added-set causal accounting")
            carrier = "NEIGHBOR" if missing <= {row["neighbor_id"]} else "DOWNSTREAM"
            carrier_counts[carrier] += 1
        else:
            carrier = None
        if harm and (not (gold & direct - treatment) or not (gold & direct - treatment) <= displaced):
            raise DA004Error("Harm lacks displaced-set causal accounting")
        rows.append({**row, "benefit": benefit, "harm": harm, "label": label, "benefit_carrier": carrier})
    counts = Counter(row["label"] for row in rows)
    expected = Counter({"BENEFIT": 57, "HARM": 40, "NEUTRAL": 25_844})
    if len(direct_questions) != 1_098 or sum(direct_questions.values()) != 935 or counts != expected:
        raise DA004Error(f"DA-004 reproduction differs: {counts}")
    if carrier_counts != Counter({"NEIGHBOR": 48, "DOWNSTREAM": 9}):
        raise DA004Error("DA-003 carrier split differs")
    summaries = {label: {name: distribution([float(row["features"][name]) for row in rows if row["label"] == label])
                         for name in FEATURES} for label in ("BENEFIT", "HARM", "NEUTRAL")}
    univariate = {}
    for endpoint in ("benefit", "harm"):
        labels = np.asarray([int(row[endpoint]) for row in rows])
        feature_results = {}
        for name in FEATURES:
            values = np.asarray([float(row["features"][name]) for row in rows])
            by_group = {}
            for group in sorted({row["sample_id"] for row in rows}):
                mask = np.asarray([row["sample_id"] == group for row in rows])
                by_group[group] = fast_auc(values[mask], labels[mask]) if len(set(labels[mask])) == 2 else None
            feature_results[name] = {"auc": fast_auc(values, labels), "by_conversation": by_group}
        univariate[endpoint] = feature_results
    models = {endpoint: grouped_model(rows, endpoint) for endpoint in ("benefit", "harm")}
    result = {"schema": "da004-pack-result-v1", "standing": "post-outcome exploration on spent NF-004 LoCoMo",
              "population": {"questions": len(direct_questions), "edges": len(rows), "labels": dict(sorted(counts.items())),
                             "benefit_carriers": dict(sorted(carrier_counts.items()))},
              "feature_summaries": summaries, "univariate": univariate, "models": models,
              "calls": {"embedding": 0, "model": 0, "cache_misses": 0},
              "claim_boundary": "descriptive pack signal only; no gate, threshold, reader, or adoption"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output_dir / "edge_labels.jsonl.gz").open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                slim = {key: row[key] for key in ("comparison_key", "duplicate_ordinal", "sample_id", "source_index",
                                                   "seed_id", "neighbor_id", "benefit", "harm", "label", "benefit_carrier")}
                output.write((json.dumps(slim, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return result


__all__ = ["fast_auc", "run_analysis"]
