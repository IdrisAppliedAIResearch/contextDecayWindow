"""Outcome join and grouped prediction for the NF-004 item-anatomy audit."""

from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.nf004_anatomy_features import FEATURES, FEATURE_FAMILIES, sha256_file

LAMBDAS = (0.01, 0.1, 1.0, 10.0, 100.0)


class AnatomyAnalysisError(RuntimeError):
    pass


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def join_outcomes(feature_path: Path, expected_sha256: str, outcome_path: Path) -> list[dict[str, Any]]:
    if sha256_file(feature_path) != expected_sha256:
        raise AnatomyAnalysisError("Evidence-blind feature seal differs")
    features = _read_csv(feature_path)
    outcomes = json.loads(outcome_path.read_text(encoding="utf-8"))["rows"]
    labels = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in outcomes}
    if len(labels) != len(outcomes):
        raise AnatomyAnalysisError("Duplicate NF-004 outcome key")
    joined = []
    for feature in features:
        key = (feature["comparison_key"], int(feature["duplicate_ordinal"]))
        if key not in labels:
            raise AnatomyAnalysisError("Feature key absent from NF-004 outcomes")
        label = labels[key]
        if feature["sample_id"] != label["sample_id"] or int(feature["source_index"]) != int(label["source_index"]):
            raise AnatomyAnalysisError("Stable item metadata differs at label join")
        pair = bool(label["arms"]["P_PAIR_RANK"]["all_evidence"])
        session = bool(label["arms"]["S_SESSION_RANK"]["all_evidence"])
        outcome_class = "PAIR_GAIN" if pair and not session else "SESSION_RESCUE" if session and not pair else "BOTH_PASS" if pair else "BOTH_FAIL"
        joined.append({**feature, "primary_eligible": bool(label["primary_eligible"]), "outcome_class": outcome_class})
    if len(joined) != 1_104:
        raise AnatomyAnalysisError("Joined population differs")
    return joined


def auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    positives = [float(score) for score, label in zip(scores, labels, strict=True) if label]
    negatives = [float(score) for score, label in zip(scores, labels, strict=True) if not label]
    if not positives or not negatives:
        raise AnatomyAnalysisError("AUC requires both labels")
    wins = sum(p > n for p in positives for n in negatives)
    ties = sum(p == n for p in positives for n in negatives)
    return (wins + 0.5 * ties) / (len(positives) * len(negatives))


def average_precision(scores: Sequence[float], labels: Sequence[int]) -> float:
    order = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    positives = sum(labels)
    hits = 0
    total = 0.0
    for rank, index in enumerate(order, 1):
        if labels[index]:
            hits += 1
            total += hits / rank
    return total / positives


def _prepare(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    medians = np.median(train, axis=0)
    train = np.where(np.isfinite(train), train, medians)
    test = np.where(np.isfinite(test), test, medians)
    means = np.mean(train, axis=0)
    scales = np.std(train, axis=0)
    scales[scales == 0] = 1.0
    return (train - means) / scales, (test - means) / scales


def _fit_logistic(matrix: np.ndarray, labels: np.ndarray, penalty: float) -> np.ndarray:
    design = np.column_stack([np.ones(len(matrix)), matrix])
    weights = np.zeros(design.shape[1], dtype=np.float64)
    regularizer = np.eye(design.shape[1]) * penalty
    regularizer[0, 0] = 0.0
    for _ in range(30):
        linear = np.clip(design @ weights, -30, 30)
        probability = 1.0 / (1.0 + np.exp(-linear))
        variance = np.maximum(probability * (1.0 - probability), 1e-6)
        gradient = design.T @ (probability - labels) + regularizer @ weights
        hessian = (design.T * variance) @ design + regularizer
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        weights -= step
        if float(np.max(np.abs(step))) < 1e-8:
            break
    return weights


def _predict(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray, penalty: float) -> np.ndarray:
    train_scaled, test_scaled = _prepare(train_x, test_x)
    weights = _fit_logistic(train_scaled, train_y, penalty)
    linear = np.column_stack([np.ones(len(test_scaled)), test_scaled]) @ weights
    return 1.0 / (1.0 + np.exp(-np.clip(linear, -30, 30)))


def _choose_lambda(matrix: np.ndarray, labels: np.ndarray, groups: np.ndarray) -> float:
    scores = []
    for penalty in LAMBDAS:
        predicted, observed = [], []
        for group in sorted(set(groups)):
            test = groups == group
            train = ~test
            if len(set(labels[test])) < 2 or len(set(labels[train])) < 2:
                continue
            predicted.extend(_predict(matrix[train], labels[train], matrix[test], penalty))
            observed.extend(labels[test])
        value = auc(predicted, observed) if len(set(observed)) == 2 else -math.inf
        scores.append((value, penalty))
    return max(scores, key=lambda item: (item[0], item[1]))[1]


def grouped_oof(matrix: np.ndarray, labels: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    predictions = np.zeros(len(labels), dtype=np.float64)
    selected: dict[str, float] = {}
    for group in sorted(set(groups)):
        test = groups == group
        train = ~test
        penalty = _choose_lambda(matrix[train], labels[train], groups[train])
        predictions[test] = _predict(matrix[train], labels[train], matrix[test], penalty)
        selected[str(group)] = penalty
    return predictions, selected


def _quantiles(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {"p25": float(np.percentile(array, 25)), "p50": float(np.percentile(array, 50)), "p75": float(np.percentile(array, 75))}


def _feature_anatomy(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    discordant = [row for row in rows if row["outcome_class"] in {"PAIR_GAIN", "SESSION_RESCUE"}]
    output = []
    for name in FEATURES:
        gains = [float(row[name]) for row in discordant if row["outcome_class"] == "PAIR_GAIN"]
        losses = [float(row[name]) for row in discordant if row["outcome_class"] == "SESSION_RESCUE"]
        pooled = auc(gains + losses, [1] * len(gains) + [0] * len(losses))
        by_conversation = []
        for sample_id in sorted({str(row["sample_id"]) for row in discordant}):
            selected = [row for row in discordant if row["sample_id"] == sample_id]
            labels = [int(row["outcome_class"] == "PAIR_GAIN") for row in selected]
            if len(set(labels)) == 2:
                by_conversation.append({"sample_id": sample_id, "auc": auc([float(row[name]) for row in selected], labels), "n": len(selected)})
        pooled_direction = pooled if pooled >= 0.5 else 1.0 - pooled
        scale = float(np.std([float(row[name]) for row in discordant]))
        standardized_median_difference = (float(np.median(gains)) - float(np.median(losses))) / scale if scale else 0.0
        output.append({
            "feature": name, "pair_gain": _quantiles(gains), "session_rescue": _quantiles(losses),
            "class_quantiles": {
                outcome_class: _quantiles([
                    float(row[name]) for row in rows if row["outcome_class"] == outcome_class
                ])
                for outcome_class in ("PAIR_GAIN", "SESSION_RESCUE", "BOTH_PASS", "BOTH_FAIL")
            },
            "pooled_auc_pair_direction": pooled, "pooled_auc_best_direction": pooled_direction,
            "standardized_median_difference": standardized_median_difference,
            "conversation_auc_pair_direction": by_conversation,
        })
    return output


def _permutation_chunk(
    matrix: np.ndarray, groups: np.ndarray, shuffled_labels: np.ndarray, threshold: float
) -> int:
    exceedances = 0
    for labels in shuffled_labels:
        predictions, _ = grouped_oof(matrix, labels, groups)
        exceedances += auc(predictions, labels) >= threshold
    return exceedances


def run_analysis(feature_path: Path, preflight_path: Path, outcome_path: Path, output_dir: Path, *, permutations: int = 10_000) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise AnatomyAnalysisError("Passing committed preflight is absent")
    rows = [row for row in join_outcomes(feature_path, preflight["feature_sha256"], outcome_path) if row["primary_eligible"]]
    population = Counter(row["outcome_class"] for row in rows)
    if population != Counter({"BOTH_PASS": 795, "PAIR_GAIN": 140, "BOTH_FAIL": 115, "SESSION_RESCUE": 48}):
        raise AnatomyAnalysisError(f"NF-004 outcome reproduction differs: {population}")
    discordant = [row for row in rows if row["outcome_class"] in {"PAIR_GAIN", "SESSION_RESCUE"}]
    matrix = np.asarray([[float(row[name]) for name in FEATURES] for row in discordant], dtype=np.float64)
    labels = np.asarray([int(row["outcome_class"] == "PAIR_GAIN") for row in discordant], dtype=int)
    groups = np.asarray([row["sample_id"] for row in discordant])
    predictions, lambdas = grouped_oof(matrix, labels, groups)
    pooled_auc = auc(predictions, labels)
    per_conversation = []
    for group in sorted(set(groups)):
        selected = groups == group
        per_conversation.append({"sample_id": str(group), "gains": int(np.sum(labels[selected])), "losses": int(np.sum(1 - labels[selected])), "auc": auc(predictions[selected], labels[selected])})
    baseline = np.zeros(len(labels), dtype=float)
    for group in sorted(set(groups)):
        selected = groups == group
        baseline[selected] = float(np.mean(labels[~selected]))
    rng = np.random.default_rng(5005)
    shuffled_rows = np.repeat(labels[None, :], permutations, axis=0)
    for shuffled in shuffled_rows:
        for group in sorted(set(groups)):
            indices = np.flatnonzero(groups == group)
            shuffled[indices] = rng.permutation(shuffled[indices])
    workers = min(16, os.cpu_count() or 1, max(1, permutations))
    chunks = [chunk for chunk in np.array_split(shuffled_rows, workers * 2) if len(chunk)]
    if workers == 1:
        exceedances = _permutation_chunk(matrix, groups, shuffled_rows, pooled_auc)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            exceedances = sum(executor.map(
                _permutation_chunk,
                [matrix] * len(chunks),
                [groups] * len(chunks),
                chunks,
                [pooled_auc] * len(chunks),
            ))
    ablations = []
    for family, names in FEATURE_FAMILIES.items():
        keep = [index for index, name in enumerate(FEATURES) if name not in names]
        ablated, _ = grouped_oof(matrix[:, keep], labels, groups)
        ablations.append({"removed_family": family, "auc": auc(ablated, labels)})
    stable = pooled_auc >= 0.65 and (1 + exceedances) / (permutations + 1) <= 0.05 and all(row["auc"] >= 0.5 for row in per_conversation)
    anatomy = _feature_anatomy(rows)
    result = {
        "schema": "nf004-item-anatomy-exploration-v1",
        "status": "CROSS_CONVERSATION_SIGNAL" if stable else "NO_STABLE_EVIDENCE_BLIND_PREDICTOR",
        "standing": "post-outcome exploratory reanalysis on spent LoCoMo holdout",
        "population": dict(sorted(population.items())),
        "prediction": {
            "discordant_n": len(discordant), "feature_count": len(FEATURES),
            "oof_auc": pooled_auc, "oof_average_precision": average_precision(predictions, labels),
            "oof_brier": float(np.mean((predictions - labels) ** 2)),
            "baseline_average_precision": average_precision(baseline, labels),
            "baseline_brier": float(np.mean((baseline - labels) ** 2)),
            "per_conversation": per_conversation, "selected_lambda": lambdas,
            "permutations": permutations, "permutation_exceedances": exceedances,
            "permutation_p": (1 + exceedances) / (permutations + 1),
            "family_ablations": ablations,
        },
        "strongest_anatomy": sorted(anatomy, key=lambda row: (-abs(row["standardized_median_difference"]), row["feature"]))[:10],
        "all_feature_anatomy": anatomy,
        "calls": {"embedding": 0, "model": 0, "cache_misses": 0},
        "claim_boundary": "availability anatomy only; no selector, reader, adoption, or fresh-corpus claim",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output_dir / "joined_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return result


__all__ = ["AnatomyAnalysisError", "auc", "average_precision", "grouped_oof", "join_outcomes", "run_analysis"]
