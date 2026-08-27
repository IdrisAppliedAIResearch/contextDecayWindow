"""TC-014 registered traversal ablation Preflight and offline outcome."""

from __future__ import annotations

import argparse
import ast
import csv
import gzip
import itertools
import json
import math
import tempfile
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np
import spacy

from analysis.locomo_nf_development import adapt_development, sha256_file
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_exploration import evidence_indices, question_population
from analysis.tc007_allocation import full_relevance
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import CONVEX_SELECTIONS, LABELS, _allocation, allocate_subset
from analysis.tc011_spread import extract_facets, facet_idf
from analysis.tc011_study import _initial_indices, _score_vector
from analysis.tc013_fanout import weighted_facet_overlap
from analysis.tc014_exploration import opportunity_order
from analysis.tc014_traversal import (
    edge_matrices,
    global_assignment,
    sequential_assignment,
    unit_similarity,
    utility_order,
)

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
REGISTRATION = ROOT / "TC_014_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "tc014" / "part1_exploration.json"
TC013_SELECTIONS = ROOT / "artifacts" / "tc013" / "preflight" / "selections.jsonl.gz"
ARTIFACT = ROOT / "artifacts" / "tc014"
PREFLIGHT = ARTIFACT / "preflight"
RESULT = ARTIFACT / "result"
BUDGETS = (16_000, 32_000)
TREATMENTS = ("parent_bound", "global_match", "utility_pack", "opportunity", "combined")
ARMS = ("cc80", "fanout", *TREATMENTS)
REGISTRATION_SHA256 = "8ea94784042fd6fd6be14febc65e042079c98f49502b55a00930f98112b06375"
PART1_SHA256 = "d22fe26de2aa88edf1f574a7e59620a8c298255f7e3067f2e53540b489e91f84"
TC013_SELECTIONS_SHA256 = "117784d28859eb336cdd185598f8a132e6e52bfac045590ddb2a29e093ce920e"
CONVEX_SHA256 = "17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202"
LABELS_SHA256 = "c4b52ead85535a1250e9ac8952bc60201a8b10304846272dbe838bbba9ee12c6"
FORBIDDEN = ("q_facts_key", "rubric", "resolved_evidence", "answer_key")


class TC014Error(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "min": float(min(values)) if values else None,
        "median": float(median(values)) if values else None,
        "max": float(max(values)) if values else None,
        "nonzero": sum(value != 0 for value in values),
    }


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(map(json.loads, handle))


def _trace_dict(trace: Any, episodes: Sequence[Any], order: Sequence[int]) -> dict[str, Any]:
    return {
        "parents": [episodes[index].identity for index in trace.parents],
        "assigned_children": [episodes[index].identity for index in trace.children],
        "emitted_children": [episodes[index].identity for index in order],
        "parent_for_child": [episodes[index].identity for index in trace.parent_for_child],
        "utility": list(trace.utility),
        "raw_marginal": list(trace.raw_marginal),
        "parent_cosine": list(trace.parent_cosine),
        "no_child": trace.no_child,
    }


def _audit_mechanisms(path: Path | None = None) -> dict[str, Any]:
    sources = [path] if path else [
        Path(__file__).with_name("tc014_traversal.py"),
        Path(__file__).with_name("tc014_exploration.py"),
    ]
    violations: list[str] = []
    imports: set[str] = set()
    for source in sources:
        text = source.read_text(encoding="utf-8")
        violations.extend(f"{source.name}:{token}" for token in FORBIDDEN if token in text.casefold())
        tree = ast.parse(text, filename=str(source))
        imports.update(node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
    if violations:
        raise TC014Error(f"mechanism leakage: {violations}")
    return {"files": {str(source): sha256_file(source) for source in sources}, "imports": sorted(imports)}


def _planted_leakage_control() -> bool:
    with tempfile.TemporaryDirectory(prefix="tc014-leakage-") as directory:
        path = Path(directory) / "bad.py"
        path.write_text('KEY = "resolved_evidence"\n', encoding="utf-8")
        try:
            _audit_mechanisms(path)
        except TC014Error:
            return True
    return False


def _metric_container() -> dict[tuple[int, str, str], list[float]]:
    metrics: dict[tuple[int, str, str], list[float]] = {}
    for budget in BUDGETS:
        for arm in TREATMENTS:
            for key in (
                "proposed", "admitted", "returned", "selected", "chars", "set_diff",
                "utility", "raw", "parent_cosine", "no_child", "dropped",
            ):
                metrics[(budget, arm, key)] = []
        for key in ("accepted", "rejected_value", "rejected_capacity", "lost_count", "child_value", "displaced_value"):
            metrics[(budget, "opportunity", key)] = []
    return metrics


def freeze_selections(output_path: Path, *, forbidden_labels: Path | None = None) -> dict[str, Any]:
    if forbidden_labels is not None:
        raise TC014Error("label artifact forbidden before selection freeze")
    anchors = {
        REGISTRATION: REGISTRATION_SHA256,
        PART1: PART1_SHA256,
        TC013_SELECTIONS: TC013_SELECTIONS_SHA256,
        CONVEX_SELECTIONS: CONVEX_SHA256,
    }
    if any(sha256_file(path) != expected for path, expected in anchors.items()):
        raise TC014Error("registration, Part 1 or source anchor drift")

    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    prepared: dict[str, tuple[Any, ...]] = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        docs = list(nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        facets = tuple(extract_facets(doc) for doc in docs)
        idf, _ = facet_idf(facets)
        facet_weight, overlap = weighted_facet_overlap(facets, idf)
        prepared[case.sample_id] = (episodes, facet_weight, overlap, unit_similarity(episodes))

    tc013 = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _load_rows(TC013_SELECTIONS)
    }
    convex = _load_rows(CONVEX_SELECTIONS)
    metrics = _metric_container()
    rows: list[dict[str, Any]] = []
    controls = 0
    assignment_differences = {str(budget): 0 for budget in BUDGETS}
    packing_differences = {str(budget): 0 for budget in BUDGETS}
    combined_differences = {str(budget): 0 for budget in BUDGETS}
    uniqueness_checks = 0
    opportunity_decisions = 0

    for source in convex:
        episodes, facet_weight, overlap, similarity = prepared[source["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(by_id[identifier] for identifier in source["arms"]["cc80"]["order"])
        scores = _score_vector(source, relevance, len(episodes))
        prior = tc013[(source["sample_id"], int(source["source_index"]))]
        budget_rows: dict[str, Any] = {}
        for budget in BUDGETS:
            parents = _initial_indices(episodes, relevance, budget)
            raw, base, bound = edge_matrices(episodes, facet_weight, overlap, scores, parents, budget // 2, similarity)
            baseline = sequential_assignment(parents, base, raw, relevance, similarity)
            expected_fanout = prior["budgets"][str(budget)]["fanout"]
            expected_children = tuple(by_id[identifier] for identifier in expected_fanout["proposed_ids"])
            expected_parents = tuple(by_id[identifier] for identifier in expected_fanout["parent_for_child"])
            if baseline.children != expected_children or baseline.parent_for_child != expected_parents:
                raise TC014Error("TC-013 edge reproduction failed")
            fanout = allocate_subset(episodes, relevance, baseline.children, budget)
            fanout_dict = _allocation(fanout)
            if fanout_dict["selected_ids"] != expected_fanout["selected_ids"] or fanout_dict["payload_sha256"] != expected_fanout["payload_sha256"]:
                raise TC014Error("TC-013 allocation reproduction failed")
            controls += 1
            cc80 = full_relevance(episodes, relevance, budget)
            expected_cc80 = prior["budgets"][str(budget)]["cc80"]
            cc80_dict = _allocation(cc80)
            if cc80_dict["selected_ids"] != expected_cc80["selected_ids"] or cc80_dict["payload_sha256"] != expected_cc80["payload_sha256"]:
                raise TC014Error("full CC80 reproduction failed")
            controls += 1

            parent_bound = sequential_assignment(parents, bound, raw, relevance, similarity)
            global_match = global_assignment(parents, base, raw, relevance, similarity)
            utility_pack_order = utility_order(baseline)
            opportunity, opportunity_meta = opportunity_order(episodes, relevance, baseline, budget, scores, facet_weight)
            combined_trace = global_assignment(parents, bound, raw, relevance, similarity)
            orders = {
                "parent_bound": parent_bound.children,
                "global_match": global_match.children,
                "utility_pack": utility_pack_order,
                "opportunity": opportunity,
                "combined": utility_order(combined_trace),
            }
            traces = {
                "parent_bound": parent_bound,
                "global_match": global_match,
                "utility_pack": baseline,
                "opportunity": baseline,
                "combined": combined_trace,
            }
            allocations = {arm: allocate_subset(episodes, relevance, order, budget) for arm, order in orders.items()}
            assignment_differences[str(budget)] += set(global_match.children) != set(baseline.children)
            packing_differences[str(budget)] += allocations["utility_pack"].selected_ids != fanout.selected_ids
            combined_differences[str(budget)] += allocations["combined"].selected_ids != fanout.selected_ids
            arm_rows: dict[str, Any] = {"cc80": cc80_dict, "fanout": fanout_dict}
            for arm, allocation in allocations.items():
                trace = traces[arm]
                values = metrics
                values[(budget, arm, "proposed")].append(len(orders[arm]))
                values[(budget, arm, "admitted")].append(len(allocation.spread_ids))
                values[(budget, arm, "returned")].append(len(allocation.returned_relevance_ids))
                values[(budget, arm, "selected")].append(len(allocation.selected_ids))
                values[(budget, arm, "chars")].append(len(allocation.payload))
                values[(budget, arm, "set_diff")].append(int(set(allocation.selected_ids) != set(fanout.selected_ids)))
                values[(budget, arm, "utility")].extend(trace.utility)
                values[(budget, arm, "raw")].extend(trace.raw_marginal)
                values[(budget, arm, "parent_cosine")].extend(trace.parent_cosine)
                values[(budget, arm, "no_child")].append(trace.no_child)
                values[(budget, arm, "dropped")].append(len(allocation.dropped_spread_ids))
                arm_rows[arm] = _allocation(allocation, trace=_trace_dict(trace, episodes, orders[arm]))
                uniqueness_checks += len(order := orders[arm]) == len(set(order))
            metrics[(budget, "opportunity", "accepted")].append(opportunity_meta["accepted"])
            metrics[(budget, "opportunity", "rejected_value")].append(opportunity_meta["rejected_value"])
            metrics[(budget, "opportunity", "rejected_capacity")].append(opportunity_meta["rejected_capacity"])
            metrics[(budget, "opportunity", "lost_count")].extend(opportunity_meta["lost_counts"])
            metrics[(budget, "opportunity", "child_value")].extend(opportunity_meta["child_values"])
            metrics[(budget, "opportunity", "displaced_value")].extend(opportunity_meta["displaced_values"])
            opportunity_decisions += opportunity_meta["accepted"] + opportunity_meta["rejected_value"] + opportunity_meta["rejected_capacity"]
            arm_rows["opportunity"]["opportunity"] = opportunity_meta
            budget_rows[str(budget)] = arm_rows
        rows.append({"blind_key": source["blind_key"], "sample_id": source["sample_id"], "source_index": source["source_index"], "budgets": budget_rows})

    _write_gzip_jsonl(output_path, rows)
    return {
        "rows": len(rows),
        "sha256": sha256_file(output_path),
        "controls": controls,
        "metrics": {f"{budget}:{arm}:{key}": _distribution(values) for (budget, arm, key), values in metrics.items() if values},
        "identity_differences": {
            "global_assignment_vs_tc013": assignment_differences,
            "utility_pack_vs_tc013": packing_differences,
            "combined_vs_tc013": combined_differences,
        },
        "uniqueness_checks": uniqueness_checks,
        "opportunity_decisions": opportunity_decisions,
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }


def summarize_frozen_selections(selection_path: Path) -> dict[str, Any]:
    """Rebuild Preflight summaries from a complete label-blind selection file."""

    rows = _load_rows(selection_path)
    if len(rows) != 871:
        raise TC014Error("incomplete frozen selection file")
    tc013 = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _load_rows(TC013_SELECTIONS)
    }
    metrics = _metric_container()
    controls = 0
    uniqueness_checks = 0
    opportunity_decisions = 0
    assignment_differences = {str(budget): 0 for budget in BUDGETS}
    packing_differences = {str(budget): 0 for budget in BUDGETS}
    combined_differences = {str(budget): 0 for budget in BUDGETS}
    for row in rows:
        prior = tc013[(row["sample_id"], int(row["source_index"]))]
        for budget in BUDGETS:
            values = row["budgets"][str(budget)]
            expected = prior["budgets"][str(budget)]
            for arm in ("cc80", "fanout"):
                actual = values[arm]
                control = expected[arm]
                if actual["selected_ids"] != control["selected_ids"] or actual["payload_sha256"] != control["payload_sha256"]:
                    raise TC014Error(f"stored {arm} control drift")
                controls += 1
            baseline_ids = values["fanout"]["selected_ids"]
            baseline_children = set(expected["fanout"]["proposed_ids"])
            for arm in TREATMENTS:
                allocation = values[arm]
                trace = allocation["trace"]
                emitted = trace["emitted_children"]
                metrics[(budget, arm, "proposed")].append(len(emitted))
                metrics[(budget, arm, "admitted")].append(len(allocation["spread_ids"]))
                metrics[(budget, arm, "returned")].append(len(allocation["returned_relevance_ids"]))
                metrics[(budget, arm, "selected")].append(len(allocation["selected_ids"]))
                metrics[(budget, arm, "chars")].append(allocation["payload_chars"])
                metrics[(budget, arm, "set_diff")].append(int(set(allocation["selected_ids"]) != set(baseline_ids)))
                metrics[(budget, arm, "utility")].extend(trace["utility"])
                metrics[(budget, arm, "raw")].extend(trace["raw_marginal"])
                metrics[(budget, arm, "parent_cosine")].extend(trace["parent_cosine"])
                metrics[(budget, arm, "no_child")].append(trace["no_child"])
                metrics[(budget, arm, "dropped")].append(len(allocation["dropped_spread_ids"]))
                uniqueness_checks += len(emitted) == len(set(emitted))
            opportunity = values["opportunity"]["opportunity"]
            metrics[(budget, "opportunity", "accepted")].append(opportunity["accepted"])
            metrics[(budget, "opportunity", "rejected_value")].append(opportunity["rejected_value"])
            metrics[(budget, "opportunity", "rejected_capacity")].append(opportunity["rejected_capacity"])
            metrics[(budget, "opportunity", "lost_count")].extend(opportunity["lost_counts"])
            metrics[(budget, "opportunity", "child_value")].extend(opportunity["child_values"])
            metrics[(budget, "opportunity", "displaced_value")].extend(opportunity["displaced_values"])
            opportunity_decisions += opportunity["accepted"] + opportunity["rejected_value"] + opportunity["rejected_capacity"]
            assignment_differences[str(budget)] += set(values["global_match"]["trace"]["assigned_children"]) != baseline_children
            packing_differences[str(budget)] += values["utility_pack"]["selected_ids"] != baseline_ids
            combined_differences[str(budget)] += values["combined"]["selected_ids"] != baseline_ids
    part1 = json.loads(PART1.read_text(encoding="utf-8"))
    return {
        "rows": len(rows),
        "sha256": sha256_file(selection_path),
        "controls": controls,
        "metrics": {f"{budget}:{arm}:{key}": _distribution(values) for (budget, arm, key), values in metrics.items() if values},
        "identity_differences": {
            "global_assignment_vs_tc013": assignment_differences,
            "utility_pack_vs_tc013": packing_differences,
            "combined_vs_tc013": combined_differences,
        },
        "uniqueness_checks": uniqueness_checks,
        "opportunity_decisions": opportunity_decisions,
        "cache_hits": part1["calls"]["cache_hits"],
        "cache_misses": part1["calls"]["cache_misses"],
    }


def _cell(direction: str) -> dict[str, Any]:
    if direction == "helps":
        return {"combined": {"net": 2}, "targeted": {"net": 1}, "breadth": {"net": 1}, "other": {"net": 0}, "breadth_identity": {"net": 1}}
    if direction == "neutral":
        return {key: {"net": 0} for key in ("combined", "targeted", "breadth", "other", "breadth_identity")}
    return {"combined": {"net": -1}, "targeted": {"net": 0}, "breadth": {"net": -1}, "other": {"net": 0}, "breadth_identity": {"net": -1}}


def cell_direction(cell: Mapping[str, Any]) -> str:
    if cell["combined"]["net"] > 0 and cell["targeted"]["net"] >= 0 and cell["breadth"]["net"] >= 0 and cell["breadth_identity"]["net"] >= 0:
        return "HELPS"
    if all(cell[key]["net"] == 0 for key in ("combined", "targeted", "breadth", "other")):
        return "NEUTRAL"
    return "HURTS"


def arm_disposition(directions: Mapping[str, str]) -> str:
    helped = sum(value == "HELPS" for value in directions.values())
    if helped == 2:
        return "TRANSFERABLE_HELP"
    if helped == 1:
        return "BUDGET_SPECIFIC_HELP"
    return "NO_HELP"


def _reachability() -> dict[str, bool]:
    helps = cell_direction(_cell("helps"))
    neutral = cell_direction(_cell("neutral"))
    hurts = cell_direction(_cell("hurts"))
    weights = np.asarray([[10.0, 9.0], [8.0, 1.0]])
    exhaustive = max(sum(weights[row, perm[row]] for row in range(2)) for perm in itertools.permutations(range(2)))
    from analysis.tc014_traversal import _hungarian_min
    assigned = _hungarian_min(weights.max() - weights)
    optimum = sum(weights[row, assigned[row]] for row in range(2))
    return {
        "cell_helps": helps == "HELPS",
        "cell_neutral": neutral == "NEUTRAL",
        "cell_hurts": hurts == "HURTS",
        "transferable": arm_disposition({"16000": helps, "32000": helps}) == "TRANSFERABLE_HELP",
        "budget_specific": arm_disposition({"16000": helps, "32000": hurts}) == "BUDGET_SPECIFIC_HELP",
        "no_help": arm_disposition({"16000": neutral, "32000": hurts}) == "NO_HELP",
        "matching_exhaustive_optimum": bool(optimum == exhaustive),
    }


def run_preflight(output_dir: Path = PREFLIGHT, *, reuse_complete_selection: bool = False) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selections = output_dir / "selections.jsonl.gz"
    frozen = (
        summarize_frozen_selections(selections)
        if reuse_complete_selection
        else freeze_selections(selections)
    )
    try:
        freeze_selections(output_dir / "forbidden.jsonl.gz", forbidden_labels=LABELS)
    except TC014Error:
        early_labels_rejected = True
    else:
        early_labels_rejected = False
    part1 = json.loads(PART1.read_text(encoding="utf-8"))
    part1_reproduced = frozen["metrics"] == part1["metrics"] and frozen["identity_differences"] == part1["identity_differences"]
    reachability = _reachability()
    leakage = _audit_mechanisms()
    planted = _planted_leakage_control()
    active = all(frozen["metrics"][f"{budget}:{arm}:set_diff"]["nonzero"] > 0 for budget in BUDGETS for arm in TREATMENTS)
    opportunity_alternatives = all(
        frozen["metrics"][f"{budget}:opportunity:accepted"]["nonzero"] > 0
        and frozen["metrics"][f"{budget}:opportunity:rejected_value"]["nonzero"] > 0
        for budget in BUDGETS
    )
    passing = (
        frozen["rows"] == 871
        and frozen["controls"] == 3_484
        and frozen["cache_misses"] == 0
        and part1_reproduced
        and early_labels_rejected
        and planted
        and all(reachability.values())
        and active
        and opportunity_alternatives
        and frozen["uniqueness_checks"] == 8_710
    )
    result = {
        "status": "PASS" if passing else "FAIL",
        "pf1": {"registration_sha256": sha256_file(REGISTRATION), "part1_sha256": sha256_file(PART1), "dataset_sha256": sha256_file(DATASET_PATH), "blind_sha256": sha256_file(BLIND), "convex_sha256": sha256_file(CONVEX_SELECTIONS), "tc013_sha256": sha256_file(TC013_SELECTIONS), "labels_sha256": sha256_file(LABELS), "selection_sha256": frozen["sha256"], "rows": frozen["rows"], "parser": {"spacy": spacy.__version__, "model": "en_core_web_sm"}},
        "pf2": {"part1_reproduced": part1_reproduced, "metrics": frozen["metrics"], "identity_differences": frozen["identity_differences"]},
        "pf3": {"selection_sha256_before_labels": frozen["sha256"], "early_labels_rejected": early_labels_rejected, "leakage": leakage, "planted_leakage_rejected": planted},
        "pf4": {"reachability": reachability, "active": active, "opportunity_alternatives": opportunity_alternatives},
        "pf5": {"content_identity_only": True, "rows": frozen["rows"]},
        "pf6": {"controls": frozen["controls"], "expected": 3_484},
        "pf7": {"unique_assignment_checks": frozen["uniqueness_checks"], "expected": 8_710, "opportunity_decisions": frozen["opportunity_decisions"], "matching_exhaustive_control": reachability["matching_exhaustive_optimum"], "depth": 1},
        "pf8": {"conversations": 4, "cannot_detect": "new-corpus or reader transfer"},
        "pf9": {"residuals": ["parent coherence is not evidence", "maximum summed utility can harm an individual query", "utility-first packing can select redundant evidence", "ASPECT-valued displacement can preserve wrong semantic identities"]},
        "pf10": {"availability_only": True, "reader_authorized": False},
        "calls": {"cache_hits": frozen["cache_hits"], "cache_misses": frozen["cache_misses"], "embedding": 0, "llm_or_generative": 0},
    }
    _write_json(output_dir / "preflight.json", result)
    if not passing:
        raise TC014Error("Preflight failed")
    return result


def _exact_two_sided(gains: int, losses: int) -> float:
    discordant = gains + losses
    if not discordant:
        return 1.0
    tail = min(gains, losses)
    return min(1.0, 2.0 * sum(math.comb(discordant, k) for k in range(tail + 1)) / (2 ** discordant))


def _paired(rows: Sequence[Mapping[str, Any]], budget: int, treatment: str, baseline: str, population: str) -> dict[str, Any]:
    subset = [row for row in rows if population == "combined" or row["population"] == population]
    treatment_key = f"{treatment}_{budget}_complete"
    baseline_key = f"{baseline}_{budget}_complete"
    gains = sum(row[treatment_key] and not row[baseline_key] for row in subset)
    losses = sum(row[baseline_key] and not row[treatment_key] for row in subset)
    return {"n": len(subset), "baseline": sum(bool(row[baseline_key]) for row in subset), "treatment": sum(bool(row[treatment_key]) for row in subset), "gains": gains, "losses": losses, "net": gains - losses, "two_sided_exact_p": _exact_two_sided(gains, losses)}


def _cells(rows: Sequence[Mapping[str, Any]], treatment: str, baseline: str) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for budget in BUDGETS:
        cell = {population: _paired(rows, budget, treatment, baseline, population) for population in ("combined", "targeted", "breadth", "other")}
        breadth = [row for row in rows if row["population"] == "breadth"]
        identity_gains = sum(max(0, int(row[f"{treatment}_{budget}_evidence"]) - int(row[f"{baseline}_{budget}_evidence"])) for row in breadth)
        identity_losses = sum(max(0, int(row[f"{baseline}_{budget}_evidence"]) - int(row[f"{treatment}_{budget}_evidence"])) for row in breadth)
        cell["breadth_identity"] = {"gains": identity_gains, "losses": identity_losses, "net": identity_gains - identity_losses}
        cell["conversation_nets"] = {
            sample_id: sum(row[f"{treatment}_{budget}_complete"] and not row[f"{baseline}_{budget}_complete"] for row in rows if row["sample_id"] == sample_id)
            - sum(row[f"{baseline}_{budget}_complete"] and not row[f"{treatment}_{budget}_complete"] for row in rows if row["sample_id"] == sample_id)
            for sample_id in sorted({row["sample_id"] for row in rows})
        }
        cell["evidence_states"] = {
            arm: {
                "zero": sum(int(row[f"{arm}_{budget}_evidence"]) == 0 for row in rows),
                "partial": sum(int(row[f"{arm}_{budget}_evidence"]) > 0 and not row[f"{arm}_{budget}_complete"] for row in rows),
                "complete": sum(bool(row[f"{arm}_{budget}_complete"]) for row in rows),
            }
            for arm in (baseline, treatment)
        }
        cell["direction"] = cell_direction(cell)
        cells[str(budget)] = cell
    return cells


def run_study(output_dir: Path = RESULT) -> dict[str, Any]:
    preflight = json.loads((PREFLIGHT / "preflight.json").read_text(encoding="utf-8"))
    selection_path = PREFLIGHT / "selections.jsonl.gz"
    if preflight["status"] != "PASS" or sha256_file(selection_path) != preflight["pf1"]["selection_sha256"]:
        raise TC014Error("passing Preflight selection anchor absent or drifted")
    if sha256_file(LABELS) != LABELS_SHA256:
        raise TC014Error("label artifact drifted")
    with gzip.open(selection_path, "rt", encoding="utf-8") as handle:
        frozen = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}

    rows: list[dict[str, Any]] = []
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
            row: dict[str, Any] = {"question_id": question.identity, "sample_id": case.sample_id, "source_index": question.source_index, "category": question.category, "population": population, "evidence_ids": "|".join(sorted(evidence))}
            for arm in ARMS:
                for budget in BUDGETS:
                    selected = set(source["budgets"][str(budget)][arm]["selected_ids"])
                    found = len(evidence & selected)
                    row[f"{arm}_{budget}_evidence"] = found
                    row[f"{arm}_{budget}_complete"] = bool(evidence) and evidence <= selected
            rows.append(row)
    if len(rows) != 868:
        raise TC014Error("measured population drift")

    treatments: dict[str, Any] = {}
    for arm in TREATMENTS:
        cells = _cells(rows, arm, "fanout")
        directions = {budget: cell["direction"] for budget, cell in cells.items()}
        treatments[arm] = {"disposition": arm_disposition(directions), "directions": directions, "versus_fanout": cells}
    combined_vs_cc80 = _cells(rows, "combined", "cc80")
    full_cc80_signal = {
        budget: (
            cell["combined"]["net"] > 0
            and cell["targeted"]["net"] >= 0
            and cell["breadth"]["net"] > 0
            and cell["breadth_identity"]["net"] > 0
        )
        for budget, cell in combined_vs_cc80.items()
    }
    totals = {
        arm: {
            str(budget): {
                population: sum(bool(row[f"{arm}_{budget}_complete"]) for row in rows if population == "combined" or row["population"] == population)
                for population in ("combined", "targeted", "breadth", "other")
            }
            for budget in BUDGETS
        }
        for arm in ARMS
    }
    result = {
        "schema": "tc014-traversal-component-ablation-v1",
        "status": "CHARACTERIZED",
        "treatments": treatments,
        "combined_vs_full_cc80": combined_vs_cc80,
        "combined_full_cc80_signal": full_cc80_signal,
        "totals": totals,
        "population": len(rows),
        "selection_sha256": sha256_file(selection_path),
        "calls": {"cache": 0, "ranking": 0, "embedding": 0, "llm_or_generative": 0},
        "claim_boundary": "LoCoMo development evidence availability only; no reader, transfer, tuning, winner-selection or adoption claim",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result.json", result)
    with (output_dir / "per_question.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "finalize-preflight", "run", "all"))
    args = parser.parse_args()
    if args.phase in {"preflight", "all"}:
        run_preflight()
    if args.phase == "finalize-preflight":
        run_preflight(reuse_complete_selection=True)
    if args.phase in {"run", "all"}:
        result = run_study()
        print(json.dumps({"totals": result["totals"], "dispositions": {arm: value["disposition"] for arm, value in result["treatments"].items()}}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
