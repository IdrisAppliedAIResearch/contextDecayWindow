"""TC-010 relevance-qualified least-redundant protected spread."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_exploration import evidence_indices, question_population
from analysis.tc007_allocation import Allocation, full_relevance
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_convex_fusion_probe import PREFLIGHT as CONVEX_PREFLIGHT
from analysis.tc009_convex_protected_probe import PREFLIGHT as PROTECTED_PREFLIGHT
from analysis.tc009_dependency_graph_probe import BLIND
from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._render import render_stm_payload
from episodic._selection import additive_weight

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
REGISTRATION = ROOT / "TC_010_PRE_REGISTRATION.md"
CONVEX_SELECTIONS = CONVEX_PREFLIGHT / "selections.jsonl.gz"
PROTECTED_SELECTIONS = PROTECTED_PREFLIGHT / "selections.jsonl.gz"
LABELS = ROOT / "artifacts" / "tc009_convex_protected_probe" / "result" / "per_question.csv"
ARTIFACT = ROOT / "artifacts" / "tc010"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGETS = (16_000, 32_000)
ARMS = ("cc80", "qualified", "global_bottom", "cc80_a3")
POOL_FRACTION = 0.25
REGISTRATION_SHA256 = "307b781e6aeda103446a1aa4c03d9650a431cfc88f7c2994291e23ba85b99388"
CONVEX_SHA256 = "17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202"
PROTECTED_SHA256 = "916632ff25c22c03e8bcc06d18592555eed30e3ffbf656903587e6052ca7a376"


class TC010Error(RuntimeError):
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


def _unit_matrix(episodes: Sequence[Any]) -> np.ndarray:
    matrix = np.stack([np.asarray(episode.record["embedding"], dtype=np.float32) for episode in episodes])
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.all(np.isfinite(norms)) or np.any(norms == 0):
        raise TC010Error("Non-finite or zero candidate vector")
    return matrix / norms


def qualified_order(
    episodes: Sequence[Any],
    relevance_order: Sequence[int],
    initial_ids: Sequence[str],
    similarity: np.ndarray,
    fraction: float = POOL_FRACTION,
) -> tuple[tuple[int, ...], tuple[float, ...], int]:
    """Greedy minimum maximum-cosine order inside CC80's top quarter."""

    if fraction != POOL_FRACTION:
        raise TC010Error("Unregistered pool fraction")
    expected = list(range(len(episodes)))
    if sorted(relevance_order) != expected or similarity.shape != (len(episodes), len(episodes)):
        raise TC010Error("Candidate order or similarity shape drift")
    by_id = {episode.identity: index for index, episode in enumerate(episodes)}
    if len(by_id) != len(episodes) or any(identifier not in by_id for identifier in initial_ids):
        raise TC010Error("Initial identity drift")
    cutoff = math.ceil(len(episodes) * fraction)
    ranks = {index: rank for rank, index in enumerate(relevance_order)}
    initial = np.asarray(sorted(by_id[identifier] for identifier in initial_ids), dtype=np.int64)
    initial_set = set(map(int, initial))
    remaining = np.asarray([index for index in relevance_order[:cutoff] if index not in initial_set], dtype=np.int64)
    redundancy = similarity[np.ix_(remaining, initial)].max(axis=1) if initial.size else np.full(remaining.size, -1.0)
    chosen: list[int] = []
    scores: list[float] = []
    while remaining.size:
        rank_values = np.asarray([ranks[int(candidate)] for candidate in remaining])
        position = int(np.lexsort((rank_values, redundancy))[0])
        candidate = int(remaining[position])
        chosen.append(candidate)
        scores.append(float(redundancy[position]))
        remaining = np.delete(remaining, position)
        redundancy = np.delete(redundancy, position)
        if remaining.size:
            redundancy = np.maximum(redundancy, similarity[remaining, candidate])
    if len(chosen) != len(set(chosen)) or any(index not in relevance_order[:cutoff] for index in chosen):
        raise TC010Error("Qualified recurrence escaped or repeated")
    if any(scores[index] > scores[index + 1] + 1e-7 for index in range(len(scores) - 1)):
        raise TC010Error("Greedy redundancy score failed to update monotonically")
    return tuple(chosen), tuple(scores), cutoff


def allocate_subset(
    episodes: Sequence[Any],
    relevance_order: Sequence[int],
    spread_order: Sequence[int],
    total_budget: int,
) -> Allocation:
    """TC-007 allocator with a registered subset allowed to claim spread."""

    if total_budget not in BUDGETS:
        raise TC010Error("Unregistered budget")
    expected = list(range(len(episodes)))
    if sorted(relevance_order) != expected:
        raise TC010Error("Relevance must permute the store")
    if len(set(spread_order)) != len(spread_order) or any(index not in expected for index in spread_order):
        raise TC010Error("Spread order must be a unique candidate subset")
    records = [episode.record for episode in episodes]
    half = total_budget // 2
    initial = pack_stm_payload([], [records[index] for index in relevance_order], half)
    initial_ids = tuple(initial.selected_ids)
    admitted = set(initial_ids)
    spread_candidates = [records[index] for index in spread_order if episodes[index].identity not in admitted]
    duplicate_ids = tuple(episodes[index].identity for index in spread_order if episodes[index].identity in admitted)
    spread = pack_stm_payload([], spread_candidates, half)
    spread_ids = tuple(spread.selected_ids)
    admitted.update(spread_ids)
    by_id = {episode.identity: episode.record for episode in episodes}
    final_records = [by_id[identifier] for identifier in (*initial_ids, *spread_ids)]
    current_chars = len(render_stm_payload([], final_records))
    returned: list[str] = []
    dropped_relevance: list[str] = []
    for index in relevance_order:
        identifier = episodes[index].identity
        if identifier in admitted:
            continue
        cost = additive_weight(records[index])
        if current_chars + cost <= total_budget:
            final_records.append(records[index])
            admitted.add(identifier)
            returned.append(identifier)
            current_chars += cost
        else:
            dropped_relevance.append(identifier)
    payload = render_stm_payload([], final_records)
    if len(payload) != current_chars or current_chars > total_budget:
        raise TC010Error("Exact allocation accounting failed")
    selected = tuple(str(record["id"]) for record in final_records)
    if len(selected) != len(set(selected)):
        raise TC010Error("Duplicate serialized identity")
    return Allocation(
        payload=payload,
        selected_ids=selected,
        initial_relevance_ids=initial_ids,
        spread_ids=spread_ids,
        returned_relevance_ids=tuple(returned),
        skipped_spread_duplicates=duplicate_ids,
        dropped_relevance_ids=tuple(dropped_relevance),
        dropped_spread_ids=tuple(spread.skipped_k_ids),
        owner={**{identifier: "relevance" for identifier in initial_ids}, **{identifier: "spread" for identifier in spread_ids}, **{identifier: "relevance" for identifier in returned}},
        phase={**{identifier: "initial_relevance" for identifier in initial_ids}, **{identifier: "protected_spread" for identifier in spread_ids}, **{identifier: "returned_relevance" for identifier in returned}},
        total_budget=total_budget,
        half_allowance=half,
        initial_relevance_solo_chars=len(initial.payload),
        spread_solo_chars=len(spread.payload),
        merged_initial_chars=len(render_stm_payload([], [by_id[identifier] for identifier in (*initial_ids, *spread_ids)])),
        wrapper_savings=len(initial.payload) + len(spread.payload) - len(render_stm_payload([], [by_id[identifier] for identifier in (*initial_ids, *spread_ids)])),
        returned_capacity=total_budget - len(render_stm_payload([], [by_id[identifier] for identifier in (*initial_ids, *spread_ids)])),
    )


def _allocation(value: Allocation, **extra: Any) -> dict[str, Any]:
    return {
        "selected_ids": list(value.selected_ids), "payload_sha256": value.payload_sha256,
        "payload_chars": len(value.payload), "initial_relevance_ids": list(value.initial_relevance_ids),
        "spread_ids": list(value.spread_ids), "returned_relevance_ids": list(value.returned_relevance_ids),
        "spread_duplicate_skips": list(value.skipped_spread_duplicates), "dropped_spread_ids": list(value.dropped_spread_ids),
        "half_allowance": value.half_allowance, **extra,
    }


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    return {"n": len(values), "min": float(min(values)) if values else None, "median": float(median(values)) if values else None, "max": float(max(values)) if values else None, "nonzero": sum(value != 0 for value in values)}


def disposition(cells: Mapping[str, Any], qualified_counts: Mapping[str, int], global_counts: Mapping[str, int]) -> dict[str, Any]:
    clauses = {}
    for budget in BUDGETS:
        cell = cells[str(budget)]
        clauses[str(budget)] = {
            "combined_positive": cell["combined"]["gains"] > cell["combined"]["losses"],
            "targeted_nonnegative": cell["targeted"]["gains"] >= cell["targeted"]["losses"],
            "breadth_positive": cell["breadth"]["gains"] > cell["breadth"]["losses"],
            "breadth_identity_positive": cell["breadth_identity"]["net_identities"] > 0,
            "conversation_consistent": all(value >= 0 for value in cell["conversation_nets"].values()) and sum(value > 0 for value in cell["conversation_nets"].values()) >= 2,
        }
    passes = {budget: all(values.values()) for budget, values in clauses.items()}
    control = {str(budget): qualified_counts[str(budget)] > global_counts[str(budget)] for budget in BUDGETS}
    if all(passes.values()) and all(control.values()):
        status = "QUALIFIED_SPREAD_WORKS"
    elif sum(passes.values()) == 1 and all(control.values()):
        other = next(budget for budget, passed in passes.items() if not passed)
        cell = cells[other]
        nonnegative = all(cell[key]["net"] >= 0 for key in ("combined", "targeted", "breadth")) and cell["breadth_identity"]["net_identities"] >= 0
        status = "QUALIFIED_SPREAD_CARRIES_SIGNAL" if nonnegative else "NO_SPLIT_SELECTED"
    elif not all(control.values()):
        status = "CONTROL_FAILURE"
    else:
        status = "NO_SPLIT_SELECTED"
    return {"status": status, "clauses": clauses, "budget_passes": passes, "qualified_beats_global_bottom": control}


def _synthetic_cell(good: bool, neutral: bool = False) -> dict[str, Any]:
    if neutral:
        return {"combined": {"gains": 1, "losses": 1, "net": 0}, "targeted": {"gains": 1, "losses": 1, "net": 0}, "breadth": {"gains": 1, "losses": 1, "net": 0}, "breadth_identity": {"net_identities": 0}, "conversation_nets": {"a": 0, "b": 0, "c": 0, "d": 0}}
    return {"combined": {"gains": 3 if good else 1, "losses": 1 if good else 3, "net": 2 if good else -2}, "targeted": {"gains": 1, "losses": 1 if good else 2, "net": 0 if good else -1}, "breadth": {"gains": 2 if good else 0, "losses": 0 if good else 2, "net": 2 if good else -2}, "breadth_identity": {"net_identities": 2 if good else -2}, "conversation_nets": {"a": 1 if good else -1, "b": 1, "c": 0, "d": 0}}


def _reachability() -> dict[str, bool]:
    good = {str(b): _synthetic_cell(True) for b in BUDGETS}
    bad = {str(b): _synthetic_cell(False) for b in BUDGETS}
    mixed = {"16000": _synthetic_cell(True), "32000": _synthetic_cell(True, neutral=True)}
    return {
        "works": disposition(good, {"16000": 3, "32000": 3}, {"16000": 2, "32000": 2})["status"] == "QUALIFIED_SPREAD_WORKS",
        "carries": disposition(mixed, {"16000": 3, "32000": 3}, {"16000": 2, "32000": 2})["status"] == "QUALIFIED_SPREAD_CARRIES_SIGNAL",
        "control_failure": disposition(bad, {"16000": 1, "32000": 3}, {"16000": 2, "32000": 2})["status"] == "CONTROL_FAILURE",
        "no_split": disposition(bad, {"16000": 3, "32000": 3}, {"16000": 2, "32000": 2})["status"] == "NO_SPLIT_SELECTED",
    }


def freeze_selections(output_path: Path, *, forbidden_labels: Path | None = None) -> dict[str, Any]:
    if forbidden_labels is not None:
        raise TC010Error("Label artifact forbidden before selection freeze")
    if sha256_file(REGISTRATION) != REGISTRATION_SHA256 or sha256_file(CONVEX_SELECTIONS) != CONVEX_SHA256 or sha256_file(PROTECTED_SELECTIONS) != PROTECTED_SHA256:
        raise TC010Error("Registration or predecessor anchor drift")
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    by_case = {case.sample_id: case for case in cases}
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        convex = list(map(json.loads, handle))
    with gzip.open(PROTECTED_SELECTIONS, "rt", encoding="utf-8") as handle:
        protected = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    prepared = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        matrix = _unit_matrix(episodes)
        prepared[case.sample_id] = (episodes, matrix @ matrix.T)
    rows = []
    metrics = {str(b): {arm: {key: [] for key in ("initial", "spread", "returned", "selected", "chars", "spread_cc80_rank", "qualified_remaining", "redundancy", "pool_exhausted", "spread_binding")} for arm in ("qualified", "global_bottom")} for b in BUDGETS}
    state_checks = 0
    for source in convex:
        episodes, similarity = prepared[source["sample_id"]]
        identity_to_index = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(identity_to_index[identifier] for identifier in source["arms"]["cc80"]["order"])
        rank = {episode.identity: position + 1 for position, episode_index in enumerate(relevance) for episode in (episodes[episode_index],)}
        budget_values = {}
        for budget in BUDGETS:
            cc80 = full_relevance(episodes, relevance, budget)
            initial = pack_stm_payload([], [episodes[index].record for index in relevance], budget // 2)
            qualified, scores, cutoff = qualified_order(episodes, relevance, initial.selected_ids, similarity)
            treatment = allocate_subset(episodes, relevance, qualified, budget)
            global_bottom = allocate_subset(episodes, relevance, tuple(reversed(relevance)), budget)
            prior = protected[(source["sample_id"], int(source["source_index"]))]["budgets"][str(budget)]["cc80_a3"]
            budget_values[str(budget)] = {
                "cc80": _allocation(cc80),
                "qualified": _allocation(treatment, qualified_pool_ids=[episodes[index].identity for index in qualified], qualified_cutoff=cutoff, redundancy_scores=list(scores)),
                "global_bottom": _allocation(global_bottom),
                "cc80_a3": prior,
            }
            for arm, value in (("qualified", treatment), ("global_bottom", global_bottom)):
                metric = metrics[str(budget)][arm]
                metric["initial"].append(len(value.initial_relevance_ids)); metric["spread"].append(len(value.spread_ids)); metric["returned"].append(len(value.returned_relevance_ids)); metric["selected"].append(len(value.selected_ids)); metric["chars"].append(len(value.payload)); metric["spread_cc80_rank"].extend(rank[identifier] for identifier in value.spread_ids)
                metric["qualified_remaining"].append(len(qualified)); metric["pool_exhausted"].append(int(arm == "qualified" and len(value.spread_ids) + len(value.dropped_spread_ids) == len(qualified))); metric["spread_binding"].append(int(bool(value.dropped_spread_ids)))
                if arm == "qualified": metric["redundancy"].extend(scores)
            state_checks += len(qualified)
        rows.append({"blind_key": source["blind_key"], "sample_id": source["sample_id"], "source_index": source["source_index"], "cc80_order": source["arms"]["cc80"]["order"], "budgets": budget_values})
    _write_gzip_jsonl(output_path, rows)
    return {"rows": len(rows), "sha256": sha256_file(output_path), "metrics": {budget: {arm: {key: _distribution(values) for key, values in values.items()} for arm, values in arms.items()} for budget, arms in metrics.items()}, "state_checks": state_checks, "cache_hits": reuse["hits"], "cache_misses": reuse["misses"]}


def _verify_controls(selection_path: Path) -> dict[str, int]:
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    checks = 0
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        for source in map(json.loads, handle):
            row = frozen[(source["sample_id"], int(source["source_index"]))]
            for budget in BUDGETS:
                actual = row["budgets"][str(budget)]["cc80"]
                expected = source["arms"]["cc80"]["selected"][str(budget)]
                if actual["selected_ids"] != expected["selected_ids"] or actual["payload_sha256"] != expected["payload_sha256"]:
                    raise TC010Error("CC80 control reproduction failed")
                checks += 1
    with gzip.open(PROTECTED_SELECTIONS, "rt", encoding="utf-8") as handle:
        for source in map(json.loads, handle):
            row = frozen[(source["sample_id"], int(source["source_index"]))]
            for budget in BUDGETS:
                actual = row["budgets"][str(budget)]["cc80_a3"]
                expected = source["budgets"][str(budget)]["cc80_a3"]
                if actual["selected_ids"] != expected["selected_ids"] or actual["payload_sha256"] != expected["payload_sha256"]:
                    raise TC010Error("CC80+A3 control reproduction failed")
                checks += 1
    return {"checks": checks, "expected": 3484}


def run_preflight(output_dir: Path = PREFLIGHT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selections = output_dir / "selections.jsonl.gz"
    frozen = freeze_selections(selections)
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", forbidden_labels=LABELS)
    except TC010Error:
        planted = True
    else:
        planted = False
    controls = _verify_controls(selections)
    reach = _reachability()
    metrics = frozen["metrics"]
    active = all(metrics[str(b)][arm]["spread"]["nonzero"] == 871 for b in BUDGETS for arm in ("qualified", "global_bottom"))
    alternatives = all(metrics[str(b)]["qualified"]["pool_exhausted"]["nonzero"] > 0 and metrics[str(b)]["qualified"]["spread_binding"]["nonzero"] > 0 for b in BUDGETS)
    passing = frozen["rows"] == 871 and frozen["cache_misses"] == 0 and controls["checks"] == controls["expected"] and planted and all(reach.values()) and active and alternatives
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {"registration_sha256": sha256_file(REGISTRATION), "dataset_sha256": sha256_file(DATASET_PATH), "blind_sha256": sha256_file(BLIND), "convex_sha256": sha256_file(CONVEX_SELECTIONS), "protected_sha256": sha256_file(PROTECTED_SELECTIONS), "labels_sha256": sha256_file(LABELS), "selection_sha256": frozen["sha256"], "rows": frozen["rows"]},
        "pf2": {"identity": "minimum maximum pair cosine inside CC80 top ceil(25%), then relevance-only slack return", "metrics": metrics},
        "pf3": {"selection_sha256_before_labels": frozen["sha256"], "planted_early_label_rejected": planted},
        "pf4": {"dispositions": reach, "active": active, "real_exhausted_and_binding_alternatives": alternatives},
        "pf5": {"blind_keys": 871, "candidate_content_identities": 1365},
        "pf6": controls,
        "pf7": {"complete_state_updates": frozen["state_checks"], "no_outside_pool": True, "no_repeats": True, "absorbing_pool_exhaustion": 1742},
        "pf8": {"conversations": 4, "cannot_detect": "new-corpus or reader transfer"},
        "pf9": {"residuals": ["low redundancy is not evidence breadth", "session count is not completeness", "identity gains are not complete questions", "availability is not use"]},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"cache_hits": frozen["cache_hits"], "cache_misses": frozen["cache_misses"], "embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if not passing:
        raise TC010Error("Preflight failed")
    return result


def _paired(rows: Sequence[Mapping[str, Any]], budget: int, treatment: str, baseline: str, population: str) -> dict[str, int]:
    subset = [row for row in rows if population == "combined" or row["population"] == population]
    tk, bk = f"{treatment}_{budget}_complete", f"{baseline}_{budget}_complete"
    gains = sum(row[tk] and not row[bk] for row in subset)
    losses = sum(row[bk] and not row[tk] for row in subset)
    return {"n": len(subset), "baseline": sum(row[bk] for row in subset), "treatment": sum(row[tk] for row in subset), "gains": gains, "losses": losses, "net": gains - losses}


def run_study(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection_path = PREFLIGHT / "selections.jsonl.gz"
    if preflight["status"] != "PASS" or sha256_file(selection_path) != preflight["pf1"]["selection_sha256"]:
        raise TC010Error("Passing Preflight anchor absent or drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
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
            source = frozen[(case.sample_id, question.source_index)]
            row = {"question_id": question.identity, "sample_id": case.sample_id, "source_index": question.source_index, "category": question.category, "population": population, "evidence_ids": sorted(evidence)}
            for arm in ARMS:
                for budget in BUDGETS:
                    selected = set(source["budgets"][str(budget)][arm]["selected_ids"])
                    row[f"{arm}_{budget}_evidence"] = len(evidence & selected)
                    row[f"{arm}_{budget}_complete"] = bool(evidence) and evidence <= selected
            rows.append(row)
    if len(rows) != 868:
        raise TC010Error("Measured population drift")
    cells = {}
    for budget in BUDGETS:
        cell = {population: _paired(rows, budget, "qualified", "cc80", population) for population in ("combined", "targeted", "breadth", "other")}
        breadth = [row for row in rows if row["population"] == "breadth"]
        identity_gains = sum(max(0, row[f"qualified_{budget}_evidence"] - row[f"cc80_{budget}_evidence"]) for row in breadth)
        identity_losses = sum(max(0, row[f"cc80_{budget}_evidence"] - row[f"qualified_{budget}_evidence"]) for row in breadth)
        cell["breadth_identity"] = {"gains": identity_gains, "losses": identity_losses, "net_identities": identity_gains - identity_losses}
        cell["conversation_nets"] = {sample_id: sum(row[f"qualified_{budget}_complete"] and not row[f"cc80_{budget}_complete"] for row in rows if row["sample_id"] == sample_id) - sum(row[f"cc80_{budget}_complete"] and not row[f"qualified_{budget}_complete"] for row in rows if row["sample_id"] == sample_id) for sample_id in sorted({row["sample_id"] for row in rows})}
        cell["versus_cc80_a3"] = {population: _paired(rows, budget, "qualified", "cc80_a3", population) for population in ("combined", "targeted", "breadth", "other")}
        cell["versus_global_bottom"] = {population: _paired(rows, budget, "qualified", "global_bottom", population) for population in ("combined", "targeted", "breadth", "other")}
        cells[str(budget)] = cell
    totals = {arm: {str(budget): sum(row[f"{arm}_{budget}_complete"] for row in rows) for budget in BUDGETS} for arm in ARMS}
    verdict = disposition(cells, totals["qualified"], totals["global_bottom"])
    result = {"schema": "tc010-qualified-bottom-spread-v1", **verdict, "cells": cells, "totals": totals, "population": len(rows), "selection_sha256": sha256_file(selection_path), "calls": {"cache": 0, "ranking": 0, "embedding": 0, "llm_or_generative": 0}, "claim_boundary": "used LoCoMo development availability only; no reader, deployment, share or pool tuning authorized"}
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return result


__all__ = ["TC010Error", "allocate_subset", "disposition", "freeze_selections", "qualified_order", "run_preflight", "run_study"]
