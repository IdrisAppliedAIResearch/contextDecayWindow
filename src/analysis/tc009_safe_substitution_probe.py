"""Evidence-blind feature extraction and descriptive TC-009 substitution probe."""

from __future__ import annotations

import csv
import gzip
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.sal001_statistics import auc_for_labels
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT
from analysis.tc008_study import load_blind_manifest, load_blind_vectors

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
RUN = ROOT / "runs" / "tc009" / "run"
G0 = ROOT / "runs" / "tc009" / "g0"
FROZEN = RUN / "frozen_selections.jsonl.gz"
LABELS = RUN / "per_question.csv"
BLIND = G0 / "label_blind_selection_manifest.json.gz"
OUTPUT = ROOT / "artifacts" / "tc009_safe_substitution_probe"
PREFLIGHT = OUTPUT / "preflight"
RESULT = OUTPUT / "result"
BUDGET = "32000"
FROZEN_SHA256 = "629bdfa1a7547b4bcf2df36c45628397d3f5b0c88c3d9b461dd2f9f48fe80900"
LABELS_SHA256 = "680835bf63571b620e59930cff4aa897a2524cd093bbccdefe3be9b67735a742"

FEATURES = (
    "query_margin_best",
    "query_margin_worst",
    "incoming_novelty_max",
    "incoming_novelty_mean",
    "outgoing_redundancy_max",
    "outgoing_redundancy_mean",
    "neg_incoming_dense_rank_best",
    "neg_incoming_dense_rank_mean",
    "outgoing_dense_rank_worst",
    "outgoing_dense_rank_mean",
    "represented_session_delta",
    "selected_candidate_delta",
    "payload_char_delta",
    "neg_incoming_penalty_max",
    "neg_incoming_penalty_mean",
)
MISSING_FIELDS = ("incoming_missing", "outgoing_missing", "retained_missing")


class ProbeError(RuntimeError):
    pass


def _unit_rows(values: Sequence[np.ndarray]) -> np.ndarray:
    matrix = np.vstack([np.asarray(value, dtype=np.float32) for value in values])
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(norms == 0):
        raise ProbeError("Zero-norm candidate vector")
    return matrix / norms[:, None]


def _summary(values: Sequence[float], mode: str) -> float:
    if not values:
        return 0.0
    if mode == "max":
        return float(max(values))
    if mode == "min":
        return float(min(values))
    if mode == "mean":
        return float(np.mean(values))
    raise ProbeError(f"Unknown summary mode: {mode}")


def feature_row(
    frozen: Mapping[str, Any],
    *,
    pair_by_id: Mapping[str, Any],
    gram: np.ndarray,
    index_by_id: Mapping[str, int],
) -> dict[str, Any]:
    block = frozen["budgets"][BUDGET]
    control = set(block["control"]["selected_ids"])
    dynamic = set(block["dynamic"]["selected_ids"])
    incoming = sorted(dynamic - control)
    outgoing = sorted(control - dynamic)
    retained = sorted(control & dynamic)
    steps = {step["candidate_id"]: step for step in frozen["dynamic_steps"]}
    dense_rank = {identifier: rank for rank, identifier in enumerate(frozen["orders"]["dense"], 1)}

    def similarities(candidates: Sequence[str]) -> list[float]:
        if not candidates or not retained:
            return []
        left = [index_by_id[item] for item in candidates]
        right = [index_by_id[item] for item in retained]
        return [float(value) for value in np.max(gram[np.ix_(left, right)], axis=1)]

    incoming_scores = [float(steps[item]["raw_similarity"]) for item in incoming]
    outgoing_scores = [float(steps[item]["raw_similarity"]) for item in outgoing]
    incoming_similarity = similarities(incoming)
    outgoing_similarity = similarities(outgoing)
    incoming_novelty = [1.0 - value for value in incoming_similarity]
    incoming_ranks = [float(dense_rank[item]) for item in incoming]
    outgoing_ranks = [float(dense_rank[item]) for item in outgoing]
    incoming_penalties = [float(steps[item]["accumulated_penalty"]) for item in incoming]
    sessions = lambda chosen: {str(pair_by_id[item].session_id) for item in chosen}
    row = {
        "blind_key": frozen["blind_key"],
        "sample_id": frozen["sample_id"],
        "source_index": int(frozen["source_index"]),
        "question_text_sha256": frozen["blind_key"],
        "control_payload_sha256": block["control"]["payload_sha256"],
        "dynamic_payload_sha256": block["dynamic"]["payload_sha256"],
        "incoming_count": len(incoming),
        "outgoing_count": len(outgoing),
        "retained_count": len(retained),
        "incoming_missing": int(not incoming),
        "outgoing_missing": int(not outgoing),
        "retained_missing": int(not retained),
        "query_margin_best": _summary(incoming_scores, "max") - _summary(outgoing_scores, "max"),
        "query_margin_worst": _summary(incoming_scores, "min") - _summary(outgoing_scores, "min"),
        "incoming_novelty_max": _summary(incoming_novelty, "max"),
        "incoming_novelty_mean": _summary(incoming_novelty, "mean"),
        "outgoing_redundancy_max": _summary(outgoing_similarity, "max"),
        "outgoing_redundancy_mean": _summary(outgoing_similarity, "mean"),
        "neg_incoming_dense_rank_best": -_summary(incoming_ranks, "min"),
        "neg_incoming_dense_rank_mean": -_summary(incoming_ranks, "mean"),
        "outgoing_dense_rank_worst": _summary(outgoing_ranks, "max"),
        "outgoing_dense_rank_mean": _summary(outgoing_ranks, "mean"),
        "represented_session_delta": len(sessions(dynamic)) - len(sessions(control)),
        "selected_candidate_delta": len(dynamic) - len(control),
        "payload_char_delta": int(block["dynamic"]["payload_chars"]) - int(block["control"]["payload_chars"]),
        "neg_incoming_penalty_max": -_summary(incoming_penalties, "max"),
        "neg_incoming_penalty_mean": -_summary(incoming_penalties, "mean"),
    }
    if not all(math.isfinite(float(row[name])) for name in FEATURES):
        raise ProbeError("Non-finite evidence-blind feature")
    return row


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def extract_features(output: Path, *, forbidden_label_path: Path | None = None) -> dict[str, Any]:
    if forbidden_label_path is not None:
        raise ProbeError("Label input is forbidden during feature extraction")
    if sha256_file(FROZEN) != FROZEN_SHA256:
        raise ProbeError("Accepted frozen selections drifted")
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    case_data = {}
    for case in cases:
        matrix = _unit_rows([vectors[pair.text] for pair in case.pairs])
        case_data[case.sample_id] = (
            {pair.identity: pair for pair in case.pairs},
            matrix @ matrix.T,
            {pair.identity: index for index, pair in enumerate(case.pairs)},
        )
    rows = []
    with gzip.open(FROZEN, "rt", encoding="utf-8") as handle:
        for line in handle:
            frozen = json.loads(line)
            pair_by_id, gram, index_by_id = case_data[frozen["sample_id"]]
            rows.append(feature_row(frozen, pair_by_id=pair_by_id, gram=gram, index_by_id=index_by_id))
    if len(rows) != 871 or len({row["blind_key"] for row in rows}) != 871:
        raise ProbeError("Feature population drifted")
    _write_csv(output, rows)
    return {
        "rows": len(rows),
        "sha256": sha256_file(output),
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
        "embedding_calls": 0,
        "llm_or_generative_calls": 0,
        "evidence_imported": False,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _average_precision(scores: Sequence[float], labels: Sequence[bool]) -> float:
    positives = sum(labels)
    if not positives:
        raise ProbeError("Average precision requires a positive")
    thresholds = sorted(set(float(value) for value in scores), reverse=True)
    previous_recall = 0.0
    ap = 0.0
    for threshold in thresholds:
        chosen = [index for index, value in enumerate(scores) if float(value) >= threshold]
        tp = sum(bool(labels[index]) for index in chosen)
        recall = tp / positives
        precision = tp / len(chosen)
        ap += (recall - previous_recall) * precision
        previous_recall = recall
    return ap


def evaluate_feature(rows: Sequence[Mapping[str, Any]], name: str) -> dict[str, Any]:
    scores = [float(row[name]) for row in rows]
    gains = [str(row["direction"]) == "gain" for row in rows]
    prevalence = sum(gains) / len(gains)
    ap = _average_precision(scores, gains)
    discordant = [row for row in rows if row["direction"] in {"gain", "loss"}]
    discordant_auc = auc_for_labels(
        [float(row[name]) for row in discordant],
        [row["direction"] == "gain" for row in discordant],
    )
    conversations = []
    for sample_id in sorted({str(row["sample_id"]) for row in discordant}):
        selected = [row for row in discordant if row["sample_id"] == sample_id]
        labels = [row["direction"] == "gain" for row in selected]
        if not any(labels) or all(labels):
            continue
        conversations.append({
            "sample_id": sample_id,
            "gains": sum(labels),
            "losses": len(labels) - sum(labels),
            "auc": auc_for_labels([float(row[name]) for row in selected], labels),
        })
    top = sorted(rows, key=lambda row: (-float(row[name]), str(row["question_id"])))[:20]
    top_gains = sum(row["direction"] == "gain" for row in top)
    clauses = {
        "ap_lift_at_least_3": ap >= 3.0 * prevalence,
        "discordant_auc_at_least_0_70": discordant_auc >= 0.70,
        "every_evaluable_conversation_above_0_50": bool(conversations) and all(row["auc"] > 0.50 for row in conversations),
        "top20_at_least_2_gains": top_gains >= 2,
        "finite": all(math.isfinite(value) for value in scores),
    }
    return {
        "feature": name,
        "average_precision": ap,
        "gain_prevalence": prevalence,
        "average_precision_lift": ap / prevalence,
        "gain_vs_loss_auc": discordant_auc,
        "conversation_auc": conversations,
        "top20_gains": top_gains,
        "top20": [{"question_id": row["question_id"], "sample_id": row["sample_id"], "direction": row["direction"], "score": float(row[name])} for row in top],
        "clauses": clauses,
        "passes": all(clauses.values()),
    }


def join_labels(feature_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if sha256_file(LABELS) != LABELS_SHA256:
        raise ProbeError("Accepted TC-009 per-question labels drifted")
    features = _read_csv(feature_path)
    labels = _read_csv(LABELS)
    label_by_key = {(row["sample_id"], int(row["source_index"])): row for row in labels}
    full_cases = adapt_development(DATASET_PATH)
    question_by_key = {(case.sample_id, q.source_index): q for case in full_cases for q in case.questions if q.duplicate_ordinal == 0}
    output = []
    payload_checks = 0
    for feature in features:
        key = (feature["sample_id"], int(feature["source_index"]))
        label = label_by_key[key]
        question = question_by_key[key]
        if label["question_id"] != question.identity or label["question_content_sha256"] != question.content_sha256:
            raise ProbeError("Question content identity join drifted")
        for arm in ("control", "dynamic"):
            if feature[f"{arm}_payload_sha256"] != label[f"{arm}_32000_payload_sha256"]:
                raise ProbeError("Frozen payload identity drifted during label join")
            payload_checks += 1
        if label["eligible"] != "True":
            continue
        control = int(label["control_32000_evidence_delivered"])
        dynamic = int(label["dynamic_32000_evidence_delivered"])
        direction = "gain" if dynamic > control else "loss" if dynamic < control else "tie"
        output.append({
            **feature,
            "question_id": label["question_id"],
            "question_content_sha256": label["question_content_sha256"],
            "population": label["population"],
            "direction": direction,
            "identity_delta": dynamic - control,
            "control_complete": label["control_32000_complete"] == "True",
            "dynamic_complete": label["dynamic_32000_complete"] == "True",
        })
    if len(output) != 868:
        raise ProbeError("Eligible joined population drifted")
    return output, {"rows": len(output), "payload_identity_checks": payload_checks, "content_identity_checks": len(features)}


def synthetic_reachability() -> dict[str, Any]:
    passing = []
    failing = []
    for index in range(100):
        direction = "gain" if index < 5 else "loss" if index < 25 else "tie"
        row = {"question_id": f"q{index:03}", "sample_id": f"c{index % 4}", "direction": direction}
        row["passer"] = 10.0 - index if direction == "gain" else -float(index)
        row["failure"] = float(index)
        passing.append(row)
        failing.append(row)
    good = evaluate_feature(passing, "passer")
    bad = evaluate_feature(failing, "failure")
    return {"signal_reachable": good["passes"], "no_signal_reachable": not bad["passes"], "good": good, "bad": bad}


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    feature_path = output_dir / "features.csv"
    feature = extract_features(feature_path)
    try:
        extract_features(output_dir / "forbidden.csv", forbidden_label_path=LABELS)
    except ProbeError:
        planted = True
    else:
        planted = False
    joined, join_audit = join_labels(feature_path)
    replay = all(
        row["control_payload_sha256"] and row["dynamic_payload_sha256"] for row in joined
    )
    result = {
        "status": "PASS" if planted and replay and synthetic_reachability()["signal_reachable"] and synthetic_reachability()["no_signal_reachable"] else "FAIL",
        "pf1": {"frozen_sha256": sha256_file(FROZEN), "labels_sha256": sha256_file(LABELS), "blind_sha256": sha256_file(BLIND), "feature": feature},
        "pf2": {"identity": "accepted 32k dynamic-only versus dense-only candidates; selectors are not rerun", "planted_trace_tested": True},
        "pf3": {"feature_sha256_before_label_import": feature["sha256"], "planted_early_import_rejected": planted},
        "pf4": synthetic_reachability(),
        "pf5": {"join": join_audit},
        "pf6": {"payload_identity_checks": join_audit["payload_identity_checks"], "expected": 1742, "pass": join_audit["payload_identity_checks"] == 1742},
        "pf7": {"not_applicable": True, "reason": "no feedback mechanism is run"},
        "pf8": {"source_conversations": 4, "can_detect": "within-development direction reversal", "cannot_detect": "new-corpus transfer"},
        "pf9": {"residual": "signal may be exhausted-corpus artifact; no feature certifies safe substitution"},
        "pf10": {"availability_only": True, "reader_registered": False},
        "calls": {"embedding": 0, "llm_or_generative": 0, "cache_misses": feature["cache_misses"]},
    }
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise ProbeError("Preflight failed")
    return result


def run_probe(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    feature_path = PREFLIGHT / "features.csv"
    if preflight["status"] != "PASS" or sha256_file(feature_path) != preflight["pf3"]["feature_sha256_before_label_import"]:
        raise ProbeError("Committed passing Preflight feature anchor is absent or drifted")
    rows, join_audit = join_labels(feature_path)
    metrics = [evaluate_feature(rows, name) for name in FEATURES]
    missing_metrics = [evaluate_feature(rows, name) for name in MISSING_FIELDS]
    passers = [row["feature"] for row in metrics if row["passes"]]
    result = {
        "schema": "tc009-safe-substitution-probe-v1",
        "status": "DESCRIPTIVE_SIGNAL" if passers else "NO_POSITIVE_SIGNAL",
        "passing_features": passers,
        "population": dict(sorted(Counter(row["direction"] for row in rows).items())),
        "complete_direction": {
            "gains": sum(row["dynamic_complete"] and not row["control_complete"] for row in rows),
            "losses": sum(row["control_complete"] and not row["dynamic_complete"] for row in rows),
        },
        "feature_sha256": sha256_file(feature_path),
        "label_join": join_audit,
        "metrics": metrics,
        "missingness_controls": missing_metrics,
        "calls": {"embedding": 0, "llm_or_generative": 0, "cache_misses": 0},
        "claim_boundary": "hypothesis generation on used LoCoMo development; no selector or reader authorized",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(output_dir / "joined_rows.csv", rows)
    return result


__all__ = ["FEATURES", "ProbeError", "evaluate_feature", "extract_features", "feature_row", "run_preflight", "run_probe"]
