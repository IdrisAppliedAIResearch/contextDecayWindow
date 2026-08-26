"""Label-blind Part 1 exploration for TC-014 traversal ablations."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np
import spacy

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import CONVEX_SELECTIONS, _allocation, allocate_subset
from analysis.tc011_spread import extract_facets, facet_idf
from analysis.tc011_study import _initial_indices, _score_vector
from analysis.tc013_fanout import weighted_facet_overlap
from analysis.tc014_traversal import (
    EdgeTrace,
    edge_matrices,
    global_assignment,
    sequential_assignment,
    unit_similarity,
    utility_order,
)

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
TC013_SELECTIONS = ROOT / "artifacts" / "tc013" / "preflight" / "selections.jsonl.gz"
OUTPUT = ROOT / "artifacts" / "tc014" / "part1_exploration.json"
BUDGETS = (16_000, 32_000)
TREATMENTS = ("parent_bound", "global_match", "utility_pack", "opportunity", "combined")
TC013_SELECTIONS_SHA256 = "117784d28859eb336cdd185598f8a132e6e52bfac045590ddb2a29e093ce920e"
CONVEX_SHA256 = "17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202"


class TC014ExplorationError(RuntimeError):
    pass


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "min": float(min(values)) if values else None,
        "median": float(median(values)) if values else None,
        "max": float(max(values)) if values else None,
        "nonzero": sum(value != 0 for value in values),
    }


def opportunity_order(
    episodes: Sequence[Any],
    relevance: Sequence[int],
    trace: EdgeTrace,
    budget: int,
    scores: np.ndarray,
    facet_weight: np.ndarray,
) -> tuple[tuple[int, ...], dict[str, Any]]:
    """Keep edges whose raw value covers their exact semantic displacement."""

    by_id = {episode.identity: index for index, episode in enumerate(episodes)}
    kept: list[int] = []
    accepted = 0
    rejected_value = 0
    rejected_capacity = 0
    lost_counts: list[int] = []
    child_values: list[float] = []
    displaced_values: list[float] = []
    current = allocate_subset(episodes, relevance, (), budget)
    for position, child in enumerate(trace.children):
        with_child = allocate_subset(episodes, relevance, tuple((*kept, child)), budget)
        if episodes[child].identity not in with_child.spread_ids:
            rejected_capacity += 1
            continue
        lost = set(current.selected_ids) - set(with_child.selected_ids)
        displaced = sum(
            float(scores[by_id[identifier]] * facet_weight[by_id[identifier]])
            for identifier in lost
        )
        child_value = float(trace.raw_marginal[position])
        child_values.append(child_value)
        displaced_values.append(displaced)
        lost_counts.append(len(lost))
        if child_value + 1e-12 >= displaced:
            kept.append(child)
            current = with_child
            accepted += 1
        else:
            rejected_value += 1
    return tuple(kept), {
        "accepted": accepted,
        "rejected_value": rejected_value,
        "rejected_capacity": rejected_capacity,
        "lost_counts": lost_counts,
        "child_values": child_values,
        "displaced_values": displaced_values,
    }


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(map(json.loads, handle))


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if sha256_file(TC013_SELECTIONS) != TC013_SELECTIONS_SHA256:
        raise TC014ExplorationError("TC-013 selection anchor drift")
    if sha256_file(CONVEX_SELECTIONS) != CONVEX_SHA256:
        raise TC014ExplorationError("CC80 source anchor drift")
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
        prepared[case.sample_id] = (
            episodes,
            facet_weight,
            overlap,
            unit_similarity(episodes),
        )
    tc013 = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _load_rows(TC013_SELECTIONS)
    }
    convex = _load_rows(CONVEX_SELECTIONS)
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
    baseline_reproductions = 0
    assignment_differences = {str(budget): 0 for budget in BUDGETS}
    packing_differences = {str(budget): 0 for budget in BUDGETS}
    combined_differences = {str(budget): 0 for budget in BUDGETS}

    for source in convex:
        episodes, facet_weight, overlap, similarity = prepared[source["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(by_id[identifier] for identifier in source["arms"]["cc80"]["order"])
        scores = _score_vector(source, relevance, len(episodes))
        prior = tc013[(source["sample_id"], int(source["source_index"]))]
        for budget in BUDGETS:
            parents = _initial_indices(episodes, relevance, budget)
            raw, base, bound = edge_matrices(
                episodes,
                facet_weight,
                overlap,
                scores,
                parents,
                budget // 2,
                similarity,
            )
            baseline = sequential_assignment(parents, base, raw, relevance, similarity)
            expected = prior["budgets"][str(budget)]["fanout"]
            expected_children = tuple(by_id[identifier] for identifier in expected["proposed_ids"])
            expected_parents = tuple(by_id[identifier] for identifier in expected["parent_for_child"])
            if baseline.children != expected_children or baseline.parent_for_child != expected_parents:
                raise TC014ExplorationError("TC-013 edge reproduction failed")
            baseline_allocation = allocate_subset(episodes, relevance, baseline.children, budget)
            baseline_actual = _allocation(baseline_allocation)
            if baseline_actual["selected_ids"] != expected["selected_ids"] or baseline_actual["payload_sha256"] != expected["payload_sha256"]:
                raise TC014ExplorationError("TC-013 allocation reproduction failed")
            baseline_reproductions += 1

            parent_bound = sequential_assignment(parents, bound, raw, relevance, similarity)
            global_match = global_assignment(parents, base, raw, relevance, similarity)
            utility_pack_order = utility_order(baseline)
            opportunity, opportunity_meta = opportunity_order(
                episodes, relevance, baseline, budget, scores, facet_weight
            )
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
            allocations = {
                arm: allocate_subset(episodes, relevance, order, budget)
                for arm, order in orders.items()
            }
            assignment_differences[str(budget)] += set(global_match.children) != set(baseline.children)
            packing_differences[str(budget)] += allocations["utility_pack"].selected_ids != baseline_allocation.selected_ids
            combined_differences[str(budget)] += allocations["combined"].selected_ids != baseline_allocation.selected_ids
            for arm, allocation in allocations.items():
                trace = traces[arm]
                values = metrics
                values[(budget, arm, "proposed")].append(len(orders[arm]))
                values[(budget, arm, "admitted")].append(len(allocation.spread_ids))
                values[(budget, arm, "returned")].append(len(allocation.returned_relevance_ids))
                values[(budget, arm, "selected")].append(len(allocation.selected_ids))
                values[(budget, arm, "chars")].append(len(allocation.payload))
                values[(budget, arm, "set_diff")].append(int(set(allocation.selected_ids) != set(baseline_allocation.selected_ids)))
                values[(budget, arm, "utility")].extend(trace.utility)
                values[(budget, arm, "raw")].extend(trace.raw_marginal)
                values[(budget, arm, "parent_cosine")].extend(trace.parent_cosine)
                values[(budget, arm, "no_child")].append(trace.no_child)
                values[(budget, arm, "dropped")].append(len(allocation.dropped_spread_ids))
            metrics[(budget, "opportunity", "accepted")].append(opportunity_meta["accepted"])
            metrics[(budget, "opportunity", "rejected_value")].append(opportunity_meta["rejected_value"])
            metrics[(budget, "opportunity", "rejected_capacity")].append(opportunity_meta["rejected_capacity"])
            metrics[(budget, "opportunity", "lost_count")].extend(opportunity_meta["lost_counts"])
            metrics[(budget, "opportunity", "child_value")].extend(opportunity_meta["child_values"])
            metrics[(budget, "opportunity", "displaced_value")].extend(opportunity_meta["displaced_values"])

    result = {
        "schema": "tc014-part1-exploration-v1",
        "status": "COMPLETE",
        "behavioral_identity": {
            "parent_bound": "TC-013 sequential one-hop assignment with edge utility multiplied by max(0,parent-child cosine)",
            "global_match": "maximum-total base ASPECT utility one-to-one assignment, emitted in parent order",
            "utility_pack": "unchanged TC-013 edges sorted by descending base edge utility before packing",
            "opportunity": "unchanged TC-013 edges retained only when raw edge value covers exact semantic identities displaced at insertion",
            "combined": "parent-bound maximum-weight assignment sorted by bound utility before packing",
        },
        "metrics": {
            f"{budget}:{arm}:{key}": _distribution(values)
            for (budget, arm, key), values in metrics.items()
            if values
        },
        "identity_differences": {
            "global_assignment_vs_tc013": assignment_differences,
            "utility_pack_vs_tc013": packing_differences,
            "combined_vs_tc013": combined_differences,
        },
        "controls": {"tc013_reproductions": baseline_reproductions, "expected": 1_742},
        "calls": {"cache_hits": reuse["hits"], "cache_misses": reuse["misses"], "embedding": 0, "llm_or_generative": 0},
        "labels_opened": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
