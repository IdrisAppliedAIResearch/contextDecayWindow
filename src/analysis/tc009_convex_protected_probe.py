"""Frozen CC80 relevance inside TC-007's 50/50 A3 allocator."""

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
from analysis.tc005_exploration import evidence_indices, question_population
from analysis.tc007_allocation import allocate, full_relevance, orders, prepare
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_convex_fusion_probe import PREFLIGHT as CONVEX_PREFLIGHT
from analysis.tc009_dependency_graph_probe import BLIND

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
TC007_DIAGNOSTICS = ROOT / "runs" / "tc007" / "run" / "diagnostics.jsonl.gz"
CONVEX_SELECTIONS = CONVEX_PREFLIGHT / "selections.jsonl.gz"
LABELS = ROOT / "runs" / "tc007" / "run" / "per_question.csv"
ARTIFACT = ROOT / "artifacts" / "tc009_convex_protected_probe"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGETS = (16_000, 32_000)
ARMS = ("dense", "cc80", "dense_a3", "cc80_a3")
TC007_SHA256 = "660ae5531277030a3c806668135415971a9038c17bb4737cbd7f69b315c626a3"
CONVEX_SHA256 = "17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202"


class ConvexProtectedProbeError(RuntimeError):
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


def _allocation(value: Any) -> dict[str, Any]:
    return {
        "selected_ids": list(value.selected_ids),
        "payload_sha256": value.payload_sha256,
        "payload_chars": len(value.payload),
        "initial_relevance_ids": list(value.initial_relevance_ids),
        "spread_ids": list(value.spread_ids),
        "returned_relevance_ids": list(value.returned_relevance_ids),
        "spread_duplicate_skips": list(value.skipped_spread_duplicates),
        "half_allowance": value.half_allowance,
    }


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    return {"n": len(values), "min": float(min(values)), "median": float(np.median(values)), "max": float(max(values)), "nonzero": sum(value > 0 for value in values)}


def freeze_selections(output_path: Path, *, forbidden_labels: Path | None = None) -> dict[str, Any]:
    if forbidden_labels is not None:
        raise ConvexProtectedProbeError("Labels are forbidden during selection freeze")
    if sha256_file(CONVEX_SELECTIONS) != CONVEX_SHA256:
        raise ConvexProtectedProbeError("Frozen convex selections drifted")
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    case_by_id = {case.sample_id: case for case in cases}
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        convex_rows = list(map(json.loads, handle))
    prepared = {}
    episodes_by_case = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        episodes_by_case[case.sample_id] = episodes
        prepared[case.sample_id] = prepare(episodes, vectors[case.questions[0].question])
    rows = []
    metrics = {str(budget): {key: [] for key in ("spread", "returned", "initial", "selected", "chars", "sym_dense_a3", "sym_dense")} for budget in BUDGETS}
    for source in convex_rows:
        case = case_by_id[source["sample_id"]]
        episodes = episodes_by_case[case.sample_id]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        dense_order = tuple(by_id[identifier] for identifier in source["arms"]["dense"]["order"])
        cc_order = tuple(by_id[identifier] for identifier in source["arms"]["cc80"]["order"])
        question = next(question for question in case.questions if question.source_index == int(source["source_index"]))
        a3_order = orders(prepared[case.sample_id], question.question, vectors[question.question])["a3"]
        arm_values = {}
        for budget in BUDGETS:
            arm_values.setdefault("dense", {})[str(budget)] = full_relevance(episodes, dense_order, budget)
            arm_values.setdefault("cc80", {})[str(budget)] = full_relevance(episodes, cc_order, budget)
            arm_values.setdefault("dense_a3", {})[str(budget)] = allocate(episodes, dense_order, a3_order, budget)
            arm_values.setdefault("cc80_a3", {})[str(budget)] = allocate(episodes, cc_order, a3_order, budget)
            treatment = arm_values["cc80_a3"][str(budget)]
            baseline = arm_values["dense_a3"][str(budget)]
            dense = arm_values["dense"][str(budget)]
            metric = metrics[str(budget)]
            metric["spread"].append(len(treatment.spread_ids))
            metric["returned"].append(len(treatment.returned_relevance_ids))
            metric["initial"].append(len(treatment.initial_relevance_ids))
            metric["selected"].append(len(treatment.selected_ids))
            metric["chars"].append(len(treatment.payload))
            metric["sym_dense_a3"].append(len(set(treatment.selected_ids) ^ set(baseline.selected_ids)))
            metric["sym_dense"].append(len(set(treatment.selected_ids) ^ set(dense.selected_ids)))
        rows.append({
            "blind_key": source["blind_key"],
            "sample_id": source["sample_id"],
            "source_index": source["source_index"],
            "orders": {"dense": source["arms"]["dense"]["order"], "cc80": source["arms"]["cc80"]["order"], "a3": [episodes[index].identity for index in a3_order]},
            "budgets": {str(budget): {arm: _allocation(arm_values[arm][str(budget)]) for arm in ARMS} for budget in BUDGETS},
        })
    _write_gzip_jsonl(output_path, rows)
    return {"rows": len(rows), "sha256": sha256_file(output_path), "metrics": {budget: {key: _distribution(values) for key, values in metric.items()} for budget, metric in metrics.items()}, "cache_hits": reuse["hits"], "cache_misses": reuse["misses"], "embedding_calls": 0, "llm_or_generative_calls": 0}


def verify_controls_after_freeze(selection_path: Path, selection_sha256: str) -> dict[str, Any]:
    if sha256_file(selection_path) != selection_sha256:
        raise ConvexProtectedProbeError("Selection anchor drifted")
    if sha256_file(TC007_DIAGNOSTICS) != TC007_SHA256:
        raise ConvexProtectedProbeError("TC-007 diagnostics drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    cases = adapt_development(DATASET_PATH)
    question_key = {question.identity: (case.sample_id, question.source_index) for case in cases for question in case.questions if not question.duplicate_ordinal}
    checks = 0
    with gzip.open(TC007_DIAGNOSTICS, "rt", encoding="utf-8") as handle:
        for accepted in map(json.loads, handle):
            row = frozen[question_key[accepted["question_id"]]]
            for budget in BUDGETS:
                for local, prior in (("dense", "control"), ("dense_a3", "a3")):
                    actual = row["budgets"][str(budget)][local]
                    expected = accepted["budgets"][str(budget)][prior]
                    if actual["selected_ids"] != expected["selected_ids"] or actual["payload_sha256"] != expected["payload_sha256"]:
                        raise ConvexProtectedProbeError("TC-007 control reproduction failed")
                    checks += 1
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        for accepted in map(json.loads, handle):
            row = frozen[(accepted["sample_id"], int(accepted["source_index"]))]
            for budget in BUDGETS:
                for local, prior in (("dense", "dense"), ("cc80", "cc80")):
                    actual = row["budgets"][str(budget)][local]
                    expected = accepted["arms"][prior]["selected"][str(budget)]
                    if actual["selected_ids"] != expected["selected_ids"] or actual["payload_sha256"] != expected["payload_sha256"]:
                        raise ConvexProtectedProbeError("Convex control reproduction failed")
                    checks += 1
    return {"checks": checks, "expected": 6968, "selection_sha256_before_label_import": selection_sha256}


def disposition(cells: Mapping[str, Any]) -> dict[str, Any]:
    clauses = {}
    for budget in BUDGETS:
        cell = cells[str(budget)]
        clauses[str(budget)] = {
            "combined_positive": cell["combined"]["gains"] > cell["combined"]["losses"],
            "targeted_nonnegative": cell["targeted"]["gains"] >= cell["targeted"]["losses"],
            "breadth_complete_nonnegative": cell["breadth"]["gains"] >= cell["breadth"]["losses"],
            "breadth_identity_nonnegative": cell["breadth_identity"]["net_identities"] >= 0,
            "conversation_consistent": all(value >= 0 for value in cell["conversation_nets"].values()) and sum(value > 0 for value in cell["conversation_nets"].values()) >= 2,
        }
    breadth_positive = any(cells[str(budget)]["breadth_identity"]["net_identities"] > 0 for budget in BUDGETS)
    passed = breadth_positive and all(all(values.values()) for values in clauses.values())
    return {"status": "DESCRIPTIVE_POSITIVE_SIGNAL" if passed else "NO_POSITIVE_SIGNAL", "clauses": clauses, "breadth_identity_positive_some_budget": breadth_positive}


def _synthetic(good: bool) -> dict[str, Any]:
    return {"combined": {"gains": 3 if good else 1, "losses": 1 if good else 2}, "targeted": {"gains": 1, "losses": 1}, "breadth": {"gains": 1, "losses": 0 if good else 2}, "breadth_identity": {"net_identities": 1 if good else -1}, "conversation_nets": {"a": 1 if good else -1, "b": 1, "c": 0, "d": 0}}


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selection_path = output_dir / "selections.jsonl.gz"
    frozen = freeze_selections(selection_path)
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", forbidden_labels=LABELS)
    except ConvexProtectedProbeError:
        planted = True
    else:
        planted = False
    controls = verify_controls_after_freeze(selection_path, frozen["sha256"])
    reach = {"positive_reachable": disposition({"16000": _synthetic(True), "32000": _synthetic(True)})["status"] == "DESCRIPTIVE_POSITIVE_SIGNAL", "negative_reachable": disposition({"16000": _synthetic(False), "32000": _synthetic(True)})["status"] == "NO_POSITIVE_SIGNAL"}
    metrics = frozen["metrics"]
    passing = frozen["rows"] == 871 and frozen["cache_misses"] == 0 and controls["checks"] == controls["expected"] and planted and all(reach.values()) and all(metrics[str(budget)]["spread"]["nonzero"] == 871 for budget in BUDGETS)
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {"dataset_sha256": sha256_file(DATASET_PATH), "blind_sha256": sha256_file(BLIND), "tc007_sha256": sha256_file(TC007_DIAGNOSTICS), "convex_selection_sha256": sha256_file(CONVEX_SELECTIONS), "labels_sha256": sha256_file(LABELS), "selection_sha256": frozen["sha256"]},
        "pf2": {"identity": "50% relevance solo allowance plus 50% A3 solo allowance, dedup, then relevance-only slack return", "metrics": metrics},
        "pf3": {"selection_sha256_before_label_import": controls["selection_sha256_before_label_import"], "planted_early_label_rejected": planted},
        "pf4": reach,
        "pf5": {"blind_keys": 871, "pair_content_identities": 1365},
        "pf6": controls,
        "pf7": {"not_applicable": True},
        "pf8": {"conversations": 4, "cannot_detect": "new-corpus transfer"},
        "pf9": {"residuals": ["A3 count is not answer breadth", "phase balance is not evidence balance", "availability is not reader use"]},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"cache_hits": frozen["cache_hits"], "cache_misses": frozen["cache_misses"], "embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if result["status"] != "PASS":
        raise ConvexProtectedProbeError("Preflight failed")
    return result


def _paired(rows: Sequence[Mapping[str, Any]], budget: int, treatment: str, baseline: str, population: str) -> dict[str, int]:
    selected = [row for row in rows if population == "combined" or row["population"] == population]
    tk, bk = f"{treatment}_{budget}_complete", f"{baseline}_{budget}_complete"
    gains = sum(row[tk] and not row[bk] for row in selected)
    losses = sum(row[bk] and not row[tk] for row in selected)
    return {"n": len(selected), "baseline": sum(row[bk] for row in selected), "treatment": sum(row[tk] for row in selected), "gains": gains, "losses": losses, "net": gains - losses}


def run_probe(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection_path = PREFLIGHT / "selections.jsonl.gz"
    if preflight["status"] != "PASS" or sha256_file(selection_path) != preflight["pf1"]["selection_sha256"]:
        raise ConvexProtectedProbeError("Passing Preflight anchor absent or drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen_rows = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    rows = []
    for case in adapt_development(DATASET_PATH):
        dummy = np.zeros(1, dtype=np.float32)
        episodes = build_episodes(case, {pair.text: dummy for pair in case.pairs})
        for question in case.questions:
            if question.duplicate_ordinal:
                continue
            population = question_population(case, question)
            if population == "ineligible":
                continue
            evidence = {episodes[index].identity for index in evidence_indices(case, episodes, question)}
            frozen = frozen_rows[(case.sample_id, question.source_index)]
            row = {"question_id": question.identity, "sample_id": case.sample_id, "source_index": question.source_index, "population": population, "evidence_ids": sorted(evidence)}
            for arm in ARMS:
                for budget in BUDGETS:
                    chosen = set(frozen["budgets"][str(budget)][arm]["selected_ids"])
                    row[f"{arm}_{budget}_evidence"] = len(evidence & chosen)
                    row[f"{arm}_{budget}_complete"] = bool(evidence) and evidence <= chosen
            rows.append(row)
    if len(rows) != 868:
        raise ConvexProtectedProbeError("Measured population drifted")
    cells = {}
    for budget in BUDGETS:
        cell = {population: _paired(rows, budget, "cc80_a3", "dense", population) for population in ("combined", "targeted", "breadth", "other")}
        breadth = [row for row in rows if row["population"] == "breadth"]
        gains = sum(max(0, row[f"cc80_a3_{budget}_evidence"] - row[f"dense_{budget}_evidence"]) for row in breadth)
        losses = sum(max(0, row[f"dense_{budget}_evidence"] - row[f"cc80_a3_{budget}_evidence"]) for row in breadth)
        cell["breadth_identity"] = {"gains": gains, "losses": losses, "net_identities": gains - losses}
        cell["conversation_nets"] = {sample_id: sum(row[f"cc80_a3_{budget}_complete"] and not row[f"dense_{budget}_complete"] for row in rows if row["sample_id"] == sample_id) - sum(row[f"dense_{budget}_complete"] and not row[f"cc80_a3_{budget}_complete"] for row in rows if row["sample_id"] == sample_id) for sample_id in sorted({row["sample_id"] for row in rows})}
        cell["versus_full_cc80"] = {population: _paired(rows, budget, "cc80_a3", "cc80", population) for population in ("combined", "targeted", "breadth", "other")}
        cell["versus_dense_a3"] = {population: _paired(rows, budget, "cc80_a3", "dense_a3", population) for population in ("combined", "targeted", "breadth", "other")}
        cells[str(budget)] = cell
    controls = {arm: {str(budget): {population: _paired(rows, budget, arm, "dense", population) for population in ("combined", "targeted", "breadth", "other")} for budget in BUDGETS} for arm in ("cc80", "dense_a3")}
    verdict = disposition(cells)
    result = {"schema": "tc009-convex-protected-probe-v1", **verdict, "cells": cells, "controls": controls, "population": len(rows), "selection_sha256": sha256_file(selection_path), "calls": {"cache": 0, "ranking": 0, "embedding": 0, "llm_or_generative": 0}, "claim_boundary": "used LoCoMo development availability only; no share/coefficient selection, TC-010, deployment, or reader authorized"}
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return result


__all__ = ["ConvexProtectedProbeError", "disposition", "freeze_selections", "run_preflight", "run_probe"]
