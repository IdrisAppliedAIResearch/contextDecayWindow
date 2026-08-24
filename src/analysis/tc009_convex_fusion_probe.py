"""Frozen normalized dense/BM25 convex-fusion probe."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_exploration import evidence_indices, pack_order, question_population
from analysis.tc005_ranking import prepare_rankers, rank_all
from analysis.tc008_study import load_blind_manifest, load_blind_vectors

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
BLIND = ROOT / "runs" / "tc009" / "g0" / "label_blind_selection_manifest.json.gz"
TC005_DIAGNOSTICS = ROOT / "runs" / "tc005" / "run" / "diagnostics.jsonl.gz"
LABELS = ROOT / "runs" / "tc005" / "run" / "per_question.csv"
ARTIFACT = ROOT / "artifacts" / "tc009_convex_fusion_probe"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGETS = (16_000, 32_000)
ARMS = ("dense", "rrf", "cc80")
ALPHA_DENSE = 0.8
ACCEPTED_SHA256 = "1da39937d08b5847722879f8fb35889a5290ea9a2fd0e72f2a2cd0d7fde78ca0"
LABELS_SHA256 = "d0ff30408ffba10afdaac6c49d5c13fb91d7466496bce2ecd0dc565444d45f39"


class ConvexFusionProbeError(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def normalize_scores(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    score_range = float(array.max() - array.min())
    if not np.isfinite(array).all() or score_range <= 0:
        raise ConvexFusionProbeError("Score range is non-finite or degenerate")
    return (array - array.min()) / score_range


def convex_scores(dense: Sequence[float], bm25: Sequence[float]) -> np.ndarray:
    return ALPHA_DENSE * normalize_scores(dense) + (1.0 - ALPHA_DENSE) * normalize_scores(bm25)


def score_order(case: Any, scores: Sequence[float]) -> tuple[int, ...]:
    return tuple(sorted(range(len(case.pairs)), key=lambda index: (-float(scores[index]), case.pairs[index].session_order, case.pairs[index].pair_order, case.pairs[index].identity)))


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    return {"n": len(values), "min": float(min(values)), "median": float(np.median(values)), "max": float(max(values)), "mean": float(np.mean(values))}


def freeze_selections(output_path: Path, *, forbidden_labels: Path | None = None) -> dict[str, Any]:
    if forbidden_labels is not None:
        raise ConvexFusionProbeError("Outcome labels are forbidden during selection freeze")
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    rows = []
    dense_ranges = []
    bm25_ranges = []
    top20_changes = []
    order_diff_dense = 0
    order_diff_rrf = 0
    selected_diff = {str(budget): {"dense": 0, "rrf": 0} for budget in BUDGETS}
    for case in cases:
        episodes = build_episodes(case, vectors)
        prepared = prepare_rankers(episodes)
        for question in case.questions:
            rankings = rank_all(episodes, question.question, vectors[question.question], prepared)
            dense = np.asarray(rankings["dense"].scores, dtype=np.float64)
            bm25 = np.asarray(rankings["bm25"].scores, dtype=np.float64)
            scores = convex_scores(dense, bm25)
            cc_order = score_order(case, scores)
            dense_ranges.append(float(dense.max() - dense.min()))
            bm25_ranges.append(float(bm25.max() - bm25.min()))
            order_diff_dense += cc_order != rankings["dense"].order
            order_diff_rrf += cc_order != rankings["hybrid"].order
            top20_changes.append(sum(left != right for left, right in zip(cc_order[:20], rankings["dense"].order[:20], strict=True)))
            orders = {"dense": rankings["dense"].order, "rrf": rankings["hybrid"].order, "cc80": cc_order}
            packs = {arm: {budget: pack_order(episodes, order, budget) for budget in BUDGETS} for arm, order in orders.items()}
            for budget in BUDGETS:
                selected_diff[str(budget)]["dense"] += set(packs["cc80"][budget].selected_ids) != set(packs["dense"][budget].selected_ids)
                selected_diff[str(budget)]["rrf"] += set(packs["cc80"][budget].selected_ids) != set(packs["rrf"][budget].selected_ids)
            dense_normalized = normalize_scores(dense)
            bm25_normalized = normalize_scores(bm25)
            rows.append({
                "blind_key": question.blind_key,
                "sample_id": case.sample_id,
                "source_index": question.source_index,
                "arms": {
                    arm: {
                        "order": [episodes[index].identity for index in order],
                        "selected": {str(budget): {"selected_ids": list(packs[arm][budget].selected_ids), "payload_sha256": hashlib.sha256(packs[arm][budget].payload.encode("utf-8")).hexdigest(), "payload_chars": len(packs[arm][budget].payload)} for budget in BUDGETS},
                    }
                    for arm, order in orders.items()
                },
                "cc80": {
                    "scores_in_order": [float(scores[index]) for index in cc_order],
                    "dense_contribution_in_order": [float(ALPHA_DENSE * dense_normalized[index]) for index in cc_order],
                    "bm25_contribution_in_order": [float((1.0 - ALPHA_DENSE) * bm25_normalized[index]) for index in cc_order],
                    "dense_range": dense_ranges[-1],
                    "bm25_range": bm25_ranges[-1],
                },
            })
    _write_gzip_jsonl(output_path, rows)
    return {
        "rows": len(rows),
        "sha256": sha256_file(output_path),
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
        "dense_ranges": _distribution(dense_ranges),
        "bm25_ranges": _distribution(bm25_ranges),
        "order_diff_dense": order_diff_dense,
        "order_diff_rrf": order_diff_rrf,
        "selected_set_diff": selected_diff,
        "top20_position_changes": _distribution(top20_changes),
        "embedding_calls": 0,
        "llm_or_generative_calls": 0,
    }


def verify_accepted_after_freeze(selection_path: Path, selection_sha256: str) -> dict[str, Any]:
    """Open label-bearing predecessor artifact only after selection bytes close."""

    if sha256_file(selection_path) != selection_sha256:
        raise ConvexFusionProbeError("Selection anchor drifted before accepted verification")
    if sha256_file(TC005_DIAGNOSTICS) != ACCEPTED_SHA256:
        raise ConvexFusionProbeError("Accepted TC-005 diagnostics drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    checks = 0
    with gzip.open(TC005_DIAGNOSTICS, "rt", encoding="utf-8") as handle:
        for accepted in map(json.loads, handle):
            row = frozen[(accepted["sample_id"], int(accepted["source_index"]))]
            for local, prior in (("dense", "dense"), ("rrf", "hybrid")):
                if row["arms"][local]["order"] != accepted["arms"][prior]["order"]:
                    raise ConvexFusionProbeError("Accepted order reproduction failed")
                for budget in BUDGETS:
                    actual = row["arms"][local]["selected"][str(budget)]
                    expected = accepted["arms"][prior]["budgets"][str(budget)]
                    if actual["selected_ids"] != expected["selected_ids"] or actual["payload_sha256"] != expected["payload_sha256"]:
                        raise ConvexFusionProbeError("Accepted payload reproduction failed")
                    checks += 1
    return {"checks": checks, "questions": len(frozen), "selection_sha256_before_accepted_import": selection_sha256}


def disposition(cells: Mapping[str, Any]) -> dict[str, Any]:
    clauses = {}
    for budget in BUDGETS:
        cell = cells[str(budget)]
        clauses[str(budget)] = {
            "combined_positive": cell["combined"]["gains"] > cell["combined"]["losses"],
            "targeted_nonnegative": cell["targeted"]["gains"] >= cell["targeted"]["losses"],
            "breadth_identity_nonnegative": cell["breadth_identity"]["net_identities"] >= 0,
            "breadth_complete_nonnegative": cell["breadth"]["gains"] >= cell["breadth"]["losses"],
            "conversation_consistent": all(value >= 0 for value in cell["conversation_nets"].values()) and sum(value > 0 for value in cell["conversation_nets"].values()) >= 2,
        }
    breadth_positive = any(cells[str(budget)]["breadth_identity"]["net_identities"] > 0 for budget in BUDGETS)
    passed = breadth_positive and all(all(values.values()) for values in clauses.values())
    return {"status": "DESCRIPTIVE_POSITIVE_SIGNAL" if passed else "NO_POSITIVE_SIGNAL", "clauses": clauses, "breadth_identity_positive_some_budget": breadth_positive}


def synthetic_reachability() -> dict[str, Any]:
    def cell(good: bool) -> dict[str, Any]:
        return {"combined": {"gains": 3 if good else 1, "losses": 1 if good else 2}, "targeted": {"gains": 1, "losses": 1 if good else 2}, "breadth": {"gains": 1, "losses": 0 if good else 2}, "breadth_identity": {"net_identities": 1 if good else -1}, "conversation_nets": {"a": 1 if good else -1, "b": 1, "c": 0, "d": 0}}
    return {"positive_reachable": disposition({"16000": cell(True), "32000": cell(True)})["status"] == "DESCRIPTIVE_POSITIVE_SIGNAL", "negative_reachable": disposition({"16000": cell(False), "32000": cell(True)})["status"] == "NO_POSITIVE_SIGNAL"}


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selection_path = output_dir / "selections.jsonl.gz"
    frozen = freeze_selections(selection_path)
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", forbidden_labels=LABELS)
    except ConvexFusionProbeError:
        planted_rejection = True
    else:
        planted_rejection = False
    accepted = verify_accepted_after_freeze(selection_path, frozen["sha256"])
    reach = synthetic_reachability()
    expected_diff = {"16000": {"dense": 869, "rrf": 871}, "32000": {"dense": 871, "rrf": 871}}
    passing = frozen["rows"] == 871 and frozen["cache_misses"] == 0 and frozen["order_diff_dense"] == frozen["order_diff_rrf"] == 871 and frozen["selected_set_diff"] == expected_diff and accepted["checks"] == 3484 and planted_rejection and all(reach.values())
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {"dataset_sha256": sha256_file(DATASET_PATH), "blind_sha256": sha256_file(BLIND), "accepted_tc005_sha256": sha256_file(TC005_DIAGNOSTICS), "labels_sha256": sha256_file(LABELS), "selection_sha256": frozen["sha256"]},
        "pf2": {"identity": "independent query-wise min-max dense/BM25 normalization followed by fixed 0.8/0.2 convex score fusion", "exploration": {key: frozen[key] for key in ("dense_ranges", "bm25_ranges", "order_diff_dense", "order_diff_rrf", "selected_set_diff", "top20_position_changes")}},
        "pf3": {"selection_sha256_before_accepted_import": accepted["selection_sha256_before_accepted_import"], "planted_early_label_rejected": planted_rejection},
        "pf4": reach,
        "pf5": {"blind_keys": 871, "pair_content_identities": 1365},
        "pf6": {"accepted_dense_rrf_order_and_payload_checks": accepted["checks"], "expected": 3484},
        "pf7": {"not_applicable": True},
        "pf8": {"conversations": 4, "cannot_detect": "new-corpus transfer"},
        "pf9": {"residuals": ["min-max can amplify weak BM25 differences", "20% lexical can displace strong dense evidence", "availability is not reader use"]},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"cache_hits": frozen["cache_hits"], "cache_misses": frozen["cache_misses"], "embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if result["status"] != "PASS":
        raise ConvexFusionProbeError("Preflight failed")
    return result


def _paired(rows: Sequence[Mapping[str, Any]], budget: int, treatment: str, baseline: str, population: str) -> dict[str, int]:
    selected = [row for row in rows if population == "combined" or row["population"] == population]
    t_key = f"{treatment}_{budget}_complete"
    b_key = f"{baseline}_{budget}_complete"
    gains = sum(row[t_key] and not row[b_key] for row in selected)
    losses = sum(row[b_key] and not row[t_key] for row in selected)
    return {"n": len(selected), "baseline": sum(row[b_key] for row in selected), "treatment": sum(row[t_key] for row in selected), "gains": gains, "losses": losses, "net": gains - losses}


def run_probe(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection_path = PREFLIGHT / "selections.jsonl.gz"
    if preflight["status"] != "PASS" or sha256_file(selection_path) != preflight["pf1"]["selection_sha256"]:
        raise ConvexFusionProbeError("Passing Preflight selection anchor absent or drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        selections = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    cases = adapt_development(DATASET_PATH)
    rows = []
    for case in cases:
        dummy = np.zeros(1, dtype=np.float32)
        episodes = build_episodes(case, {pair.text: dummy for pair in case.pairs})
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            population = question_population(case, question)
            if population == "ineligible":
                continue
            evidence = {episodes[index].identity for index in evidence_indices(case, episodes, question)}
            frozen = selections[(case.sample_id, question.source_index)]
            row = {"question_id": question.identity, "sample_id": case.sample_id, "source_index": question.source_index, "population": population, "evidence_ids": sorted(evidence)}
            for arm in ARMS:
                for budget in BUDGETS:
                    chosen = set(frozen["arms"][arm]["selected"][str(budget)]["selected_ids"])
                    row[f"{arm}_{budget}_evidence"] = len(evidence & chosen)
                    row[f"{arm}_{budget}_complete"] = bool(evidence) and evidence <= chosen
            rows.append(row)
    if len(rows) != 868:
        raise ConvexFusionProbeError("Measured population drifted")
    cells = {}
    rrf_cells = {}
    for budget in BUDGETS:
        cell = {population: _paired(rows, budget, "cc80", "dense", population) for population in ("combined", "targeted", "breadth", "other")}
        breadth = [row for row in rows if row["population"] == "breadth"]
        gains = sum(max(0, row[f"cc80_{budget}_evidence"] - row[f"dense_{budget}_evidence"]) for row in breadth)
        losses = sum(max(0, row[f"dense_{budget}_evidence"] - row[f"cc80_{budget}_evidence"]) for row in breadth)
        cell["breadth_identity"] = {"gains": gains, "losses": losses, "net_identities": gains - losses}
        cell["conversation_nets"] = {sample_id: sum(row[f"cc80_{budget}_complete"] and not row[f"dense_{budget}_complete"] for row in rows if row["sample_id"] == sample_id) - sum(row[f"dense_{budget}_complete"] and not row[f"cc80_{budget}_complete"] for row in rows if row["sample_id"] == sample_id) for sample_id in sorted({row["sample_id"] for row in rows})}
        cell["versus_rrf"] = {population: _paired(rows, budget, "cc80", "rrf", population) for population in ("combined", "targeted", "breadth", "other")}
        cells[str(budget)] = cell
        rrf_cells[str(budget)] = {population: _paired(rows, budget, "rrf", "dense", population) for population in ("combined", "targeted", "breadth", "other")}
    verdict = disposition(cells)
    result = {"schema": "tc009-convex-fusion-probe-v1", **verdict, "cells": cells, "rrf_replay": rrf_cells, "population": len(rows), "selection_sha256": sha256_file(selection_path), "calls": {"cache": 0, "embedding": 0, "bm25": 0, "llm_or_generative": 0}, "claim_boundary": "used LoCoMo development availability only; no coefficient selection, TC-010, deployment, or reader authorized"}
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return result


__all__ = ["ConvexFusionProbeError", "convex_scores", "disposition", "normalize_scores", "run_preflight", "run_probe"]
