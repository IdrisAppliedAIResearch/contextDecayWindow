"""Part 1 exploration for frozen TC-014 context organization."""

from __future__ import annotations

import gzip
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT
from analysis.tc008_study import load_blind_manifest
from analysis.tc009_dependency_graph_probe import BLIND


TC014_SELECTIONS = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "tier_cost"
    / "artifacts"
    / "tc014"
    / "preflight"
    / "selections.jsonl.gz"
)
LV002_PROMPTS = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "live_validation_002"
    / "artifacts"
    / "preflight"
    / "prompts.jsonl.gz"
)
ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_005"
OUTPUT = ROOT / "artifacts" / "part1_exploration.json"


class LV005ExplorationError(RuntimeError):
    pass


def _read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _distribution(values: Sequence[int]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "min": min(ordered),
        "p25": ordered[len(ordered) // 4],
        "median": statistics.median(ordered),
        "p75": ordered[(3 * len(ordered)) // 4],
        "max": max(ordered),
        "sum": sum(ordered),
        "values": list(values),
    }


def _inspect_row(
    row: Mapping[str, Any], turn_by_id: Mapping[str, int]
) -> dict[str, Any]:
    allocation = row["budgets"]["32000"]["opportunity"]
    trace = allocation["trace"]
    parent_for_child = dict(
        zip(trace["assigned_children"], trace["parent_for_child"], strict=True)
    )
    selected = list(allocation["selected_ids"])
    selected_set = set(selected)
    spread = list(allocation["spread_ids"])
    mapped = [child for child in spread if parent_for_child.get(child) in selected_set]
    earlier_children = [
        child
        for child in mapped
        if turn_by_id[child] < turn_by_id[parent_for_child[child]]
    ]
    grouped = []
    child_by_parent = {parent_for_child[child]: child for child in mapped}
    emitted: set[str] = set()
    for identity in selected:
        if identity in spread:
            continue
        group = [identity]
        child = child_by_parent.get(identity)
        if child is not None:
            group.append(child)
        grouped.extend(group)
        emitted.update(group)
    return {
        "sample_id": row["sample_id"],
        "source_index": int(row["source_index"]),
        "selected": len(selected),
        "semantic": len(selected) - len(spread),
        "spread": len(spread),
        "mapped_children": len(mapped),
        "earlier_children": len(earlier_children),
        "later_children": len(mapped) - len(earlier_children),
        "group_count": len(selected) - len(spread),
        "grouped_identity_exact": len(grouped) == len(selected)
        and len(set(grouped)) == len(grouped)
        and set(grouped) == selected_set,
        "grouping_changes_order": grouped != selected,
    }


def explore() -> dict[str, Any]:
    cases = {case.sample_id: case for case in load_blind_manifest(BLIND)}
    selections = _read_gzip(TC014_SELECTIONS)
    live_prompts = _read_gzip(LV002_PROMPTS)
    live_keys = {
        (row["sample_id"], int(row["source_index"])) for row in live_prompts
    }
    inspected = []
    for row in selections:
        case = cases[row["sample_id"]]
        turn_by_id = {
            pair.identity: index for index, pair in enumerate(case.pairs, start=1)
        }
        inspected.append(_inspect_row(row, turn_by_id))
    live = [
        row
        for row in inspected
        if (row["sample_id"], row["source_index"]) in live_keys
    ]
    if len(inspected) != 871 or len(live) != 17:
        raise LV005ExplorationError("population drift")
    if not all(row["grouped_identity_exact"] for row in inspected):
        raise LV005ExplorationError("parent-child grouping is not identity preserving")

    def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            name: _distribution([int(row[name]) for row in rows])
            for name in (
                "selected",
                "semantic",
                "spread",
                "mapped_children",
                "earlier_children",
                "later_children",
                "group_count",
            )
        } | {
            "identity_exact": sum(bool(row["grouped_identity_exact"]) for row in rows),
            "order_changed": sum(bool(row["grouping_changes_order"]) for row in rows),
            "rows": len(rows),
        }

    result = {
        "schema": "lv005-part1-exploration-v1",
        "behavioral_identity": (
            "At 32k every frozen opportunity spread episode has exactly one "
            "selected TC-014 semantic parent, so adjacency grouping can reorder "
            "all selected content without adding, dropping, or duplicating an episode."
        ),
        "inputs": {
            "tc014_selections_sha256": sha256_file(TC014_SELECTIONS),
            "lv002_prompts_sha256": sha256_file(LV002_PROMPTS),
        },
        "all_questions": summarize(inspected),
        "live_discordant_population": summarize(live),
        "name_checks": {
            "group": "one selected query-ranked TC-014 parent plus its one selected spread child, if any",
            "chronology": "LoCoMo adjacent-pair conversation position, not a wall-clock timestamp and not proof of correction",
            "latest": "the greater conversation position inside one group, not automatically the true or current fact",
            "supersession": "not identifiable because LoCoMo carries no explicit update key or supersedes edge",
        },
        "degenerate_states": {
            "unmapped_selected_spread": sum(
                int(row["spread"]) - int(row["mapped_children"]) for row in inspected
            ),
            "groups_without_children": sum(
                int(row["semantic"]) - int(row["spread"]) for row in inspected
            ),
            "children_earlier_than_parent": sum(
                int(row["earlier_children"]) for row in inspected
            ),
            "children_later_than_parent": sum(
                int(row["later_children"]) for row in inspected
            ),
            "absorbing_feedback": False,
        },
        "design_consequence": (
            "Test identity-preserving related-pair grouping, chronology within each "
            "group, and explicit earlier/later rendering separately. Do not label "
            "natural LoCoMo statements as superseded or current."
        ),
        "calls": {"embedding": 0, "llm_or_generative": 0},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(explore(), indent=2, sort_keys=True))
