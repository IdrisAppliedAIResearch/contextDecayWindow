"""Label-blind Part 1 exploration for TC-015."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from statistics import median
from typing import Any, Sequence

import numpy as np

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import CONVEX_SELECTIONS, _allocation, allocate_subset
from analysis.tc015_opportunity_utility import opportunity_then_utility

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
TC014_SELECTIONS = ROOT / "artifacts" / "tc014" / "preflight" / "selections.jsonl.gz"
OUTPUT = ROOT / "artifacts" / "tc015" / "part1_exploration.json"
BUDGETS = (16_000, 32_000)
TC014_SELECTIONS_SHA256 = "32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7"
CONVEX_SHA256 = "17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202"


class TC015ExplorationError(RuntimeError):
    pass


def _rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(map(json.loads, handle))


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "min": float(min(values)) if values else None,
        "median": float(median(values)) if values else None,
        "max": float(max(values)) if values else None,
        "nonzero": sum(value != 0 for value in values),
    }


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if sha256_file(TC014_SELECTIONS) != TC014_SELECTIONS_SHA256:
        raise TC015ExplorationError("TC-014 selection anchor drift")
    if sha256_file(CONVEX_SELECTIONS) != CONVEX_SHA256:
        raise TC015ExplorationError("CC80 source anchor drift")

    cases = load_blind_manifest(BLIND)
    prepared = {}
    for case in cases:
        dummy = np.zeros(1, dtype=np.float32)
        prepared[case.sample_id] = build_episodes(
            case, {pair.text: dummy for pair in case.pairs}
        )
    prior = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _rows(TC014_SELECTIONS)
    }
    metrics = {
        str(budget): {key: [] for key in (
            "retained", "position_changes", "admitted", "returned", "selected",
            "chars", "selected_set_diff_vs_opportunity",
            "selected_set_diff_vs_utility_pack", "payload_diff_vs_opportunity",
        )}
        for budget in BUDGETS
    }
    set_preservation = 0
    opportunity_reproductions = 0
    rows = _rows(CONVEX_SELECTIONS)
    for source in rows:
        episodes = prepared[source["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(by_id[value] for value in source["arms"]["cc80"]["order"])
        frozen = prior[(source["sample_id"], int(source["source_index"]))]
        for budget in BUDGETS:
            arms = frozen["budgets"][str(budget)]
            opportunity = arms["opportunity"]
            trace = opportunity["trace"]
            ordered = opportunity_then_utility(
                trace["assigned_children"], trace["utility"], trace["emitted_children"]
            )
            if set(ordered) != set(trace["emitted_children"]):
                raise TC015ExplorationError("opportunity set changed")
            set_preservation += 1
            replay = allocate_subset(
                episodes,
                relevance,
                tuple(by_id[value] for value in trace["emitted_children"]),
                budget,
            )
            replay_dict = _allocation(replay)
            if (
                replay_dict["selected_ids"] != opportunity["selected_ids"]
                or replay_dict["payload_sha256"] != opportunity["payload_sha256"]
            ):
                raise TC015ExplorationError("TC-014 opportunity replay failed")
            opportunity_reproductions += 1
            allocation = _allocation(
                allocate_subset(
                    episodes, relevance, tuple(by_id[value] for value in ordered), budget
                )
            )
            values = metrics[str(budget)]
            values["retained"].append(len(ordered))
            values["position_changes"].append(
                sum(a != b for a, b in zip(ordered, trace["emitted_children"], strict=True))
            )
            values["admitted"].append(len(allocation["spread_ids"]))
            values["returned"].append(len(allocation["returned_relevance_ids"]))
            values["selected"].append(len(allocation["selected_ids"]))
            values["chars"].append(allocation["payload_chars"])
            values["selected_set_diff_vs_opportunity"].append(
                int(set(allocation["selected_ids"]) != set(opportunity["selected_ids"]))
            )
            values["selected_set_diff_vs_utility_pack"].append(
                int(set(allocation["selected_ids"]) != set(arms["utility_pack"]["selected_ids"]))
            )
            values["payload_diff_vs_opportunity"].append(
                int(allocation["payload_sha256"] != opportunity["payload_sha256"])
            )

    result = {
        "schema": "tc015-part1-opportunity-utility-v1",
        "mechanism_identity": (
            "TC-014 opportunity admission fixes the child set in parent order; "
            "TC-015 changes only its emission order to descending frozen TC-013 edge utility."
        ),
        "anchors": {
            "tc014_selections_sha256": sha256_file(TC014_SELECTIONS),
            "convex_source_sha256": sha256_file(CONVEX_SELECTIONS),
            "blind_manifest_sha256": sha256_file(BLIND),
        },
        "population": {"rows": len(rows), "budgets": list(BUDGETS)},
        "metrics": {
            budget: {key: _distribution(values) for key, values in groups.items()}
            for budget, groups in metrics.items()
        },
        "absorbing_states": {
            "empty_or_single_retained": {
                budget: sum(value <= 1 for value in metrics[budget]["retained"])
                for budget in map(str, BUDGETS)
            },
            "order_unchanged": {
                budget: sum(value == 0 for value in metrics[budget]["position_changes"])
                for budget in map(str, BUDGETS)
            },
            "all_retained_dropped_by_packer": {
                budget: sum(value == 0 for value in metrics[budget]["admitted"])
                for budget in map(str, BUDGETS)
            },
        },
        "checks": {
            "opportunity_set_preservations": set_preservation,
            "opportunity_reproductions": opportunity_reproductions,
            "expected_each": len(rows) * len(BUDGETS),
        },
        "calls": {"cache": 0, "embedding": 0, "llm_or_generative": 0},
        "boundary": "label-blind mechanism exploration; no evidence or answer outcome opened",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
