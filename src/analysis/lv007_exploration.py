"""Label-blind Part 1 exploration for compact semantic-community rendering."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np
import spacy

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc011_spread import extract_facets, facet_idf
from analysis.tc013_fanout import weighted_facet_overlap


ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_007"
OUTPUT = ROOT / "artifacts" / "part1_exploration.json"
LV005_PROMPTS = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "live_validation_005"
    / "artifacts"
    / "preflight"
    / "prompts.jsonl.gz"
)
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
LV005_PROMPTS_SHA256 = "d0a3ac38e15c1738387c9d3216de532195959dd4c8ac7515a03209bbfebe8b80"
TC014_SELECTIONS_SHA256 = "32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7"

ALPHAS = (1.0, 0.8, 0.5)
THRESHOLDS = (0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05)
CAPS: tuple[int | None, ...] = (4, 6, 8, 12, None)
SELECTED_ALPHA = 0.8
SELECTED_THRESHOLD = 0.04
SELECTED_CAP = 8


class LV007ExplorationError(RuntimeError):
    pass


def _read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": len(ordered),
        "min": ordered[0],
        "median": float(median(ordered)),
        "max": ordered[-1],
    }


def _percentiles(values: Sequence[float]) -> dict[str, float]:
    points = (0, 10, 25, 50, 75, 90, 95, 99, 100)
    measured = np.percentile(np.asarray(values, dtype=np.float64), points)
    return {f"p{point}": float(value) for point, value in zip(points, measured, strict=True)}


def sequential_communities(
    affinity: np.ndarray,
    *,
    threshold: float,
    cap: int | None,
) -> tuple[tuple[int, ...], ...]:
    """Assign relevance-ordered nodes to the best mean-affinity open group."""

    count = int(affinity.shape[0])
    if affinity.shape != (count, count) or not np.isfinite(affinity).all():
        raise LV007ExplorationError("invalid affinity matrix")
    groups: list[list[int]] = []
    for node in range(count):
        options = []
        for group_index, group in enumerate(groups):
            if cap is not None and len(group) >= cap:
                continue
            score = float(np.mean(affinity[node, np.asarray(group, dtype=np.int64)]))
            options.append((score, -group_index, group_index))
        winner = max(options) if options else None
        if winner is not None and winner[0] >= threshold:
            groups[winner[2]].append(node)
        else:
            groups.append([node])
    emitted = [node for group in groups for node in group]
    if sorted(emitted) != list(range(count)):
        raise LV007ExplorationError("community assignment changed node identity")
    return tuple(tuple(group) for group in groups)


def _summarize_configuration(
    prepared_rows: Sequence[Mapping[str, Any]],
    *,
    alpha: float,
    threshold: float,
    cap: int | None,
) -> dict[str, Any]:
    group_counts: list[int] = []
    group_sizes: list[int] = []
    singleton_counts: list[int] = []
    cap_bound_counts: list[int] = []
    route_mixed_counts: list[int] = []
    within: list[float] = []
    between: list[float] = []
    reordered = 0
    for row in prepared_rows:
        affinity = alpha * row["cosine"] + (1.0 - alpha) * row["facet_ochiai"]
        groups = sequential_communities(affinity, threshold=threshold, cap=cap)
        group_counts.append(len(groups))
        group_sizes.extend(len(group) for group in groups)
        singleton_counts.append(sum(len(group) == 1 for group in groups))
        cap_bound_counts.append(
            sum(cap is not None and len(group) == cap for group in groups)
        )
        route_mixed_counts.append(
            sum(
                len({row["selected_ids"][node] in row["spread_ids"] for node in group}) == 2
                for group in groups
            )
        )
        chronological = [
            node
            for group in groups
            for node in sorted(group, key=lambda item: (row["turns"][item], row["selected_ids"][item]))
        ]
        reordered += chronological != list(range(len(row["selected_ids"])))
        label = {node: group_index for group_index, group in enumerate(groups) for node in group}
        for left in range(len(row["selected_ids"])):
            for right in range(left + 1, len(row["selected_ids"])):
                target = within if label[left] == label[right] else between
                target.append(float(affinity[left, right]))
    return {
        "alpha": alpha,
        "threshold": threshold,
        "cap": cap,
        "groups_per_prompt": _distribution(group_counts),
        "group_size": _distribution(group_sizes),
        "singletons_per_prompt": _distribution(singleton_counts),
        "cap_bound_per_prompt": _distribution(cap_bound_counts),
        "route_mixed_per_prompt": _distribution(route_mixed_counts),
        "within_affinity": _percentiles(within),
        "between_affinity": _percentiles(between),
        "median_within_minus_between": float(median(within) - median(between)),
        "reordered_prompts": reordered,
    }


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if sha256_file(LV005_PROMPTS) != LV005_PROMPTS_SHA256:
        raise LV007ExplorationError("LV-005 prompt anchor drift")
    if sha256_file(TC014_SELECTIONS) != TC014_SELECTIONS_SHA256:
        raise LV007ExplorationError("TC-014 selection anchor drift")

    prompt_rows = _read_gzip(LV005_PROMPTS)
    keys = {(row["sample_id"], int(row["source_index"])) for row in prompt_rows}
    selection_rows = [
        row
        for row in _read_gzip(TC014_SELECTIONS)
        if (row["sample_id"], int(row["source_index"])) in keys
    ]
    if len(prompt_rows) != 17 or len(selection_rows) != 17:
        raise LV007ExplorationError("frozen live population drift")

    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    prepared: dict[str, tuple[Any, np.ndarray, np.ndarray]] = {}
    facet_family_counts: Counter[str] = Counter()
    for case in cases:
        episodes = build_episodes(case, vectors)
        matrix = np.stack(
            [np.asarray(episode.record["embedding"], dtype=np.float64) for episode in episodes]
        )
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
        docs = list(nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        facets = tuple(extract_facets(doc) for doc in docs)
        idf, families = facet_idf(facets)
        facet_family_counts.update(families)
        totals, overlap = weighted_facet_overlap(facets, idf)
        denominator = np.sqrt(np.outer(totals, totals))
        ochiai = np.divide(
            overlap,
            denominator,
            out=np.zeros_like(overlap),
            where=denominator > 0,
        )
        prepared[case.sample_id] = (episodes, matrix, ochiai)

    selected_pair_cosines: list[float] = []
    selected_pair_facets: list[float] = []
    prepared_rows: list[dict[str, Any]] = []
    selected_episode_count = 0
    for row in sorted(selection_rows, key=lambda item: (item["sample_id"], int(item["source_index"]))):
        allocation = row["budgets"]["32000"]["opportunity"]
        selected_ids = list(allocation["selected_ids"])
        episodes, matrix, ochiai = prepared[row["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        indices = [by_id[identity] for identity in selected_ids]
        selected_cosine = matrix[np.ix_(indices, indices)]
        selected_ochiai = ochiai[np.ix_(indices, indices)]
        upper = np.triu_indices(len(indices), 1)
        selected_pair_cosines.extend(map(float, selected_cosine[upper]))
        selected_pair_facets.extend(map(float, selected_ochiai[upper]))
        prepared_rows.append(
            {
                "sample_id": row["sample_id"],
                "source_index": int(row["source_index"]),
                "selected_ids": selected_ids,
                "spread_ids": set(allocation["spread_ids"]),
                "turns": [int(episodes[index].record["turn_number"]) for index in indices],
                "cosine": selected_cosine,
                "facet_ochiai": selected_ochiai,
            }
        )
        selected_episode_count += len(selected_ids)

    sweep = []
    for alpha in ALPHAS:
        for threshold in THRESHOLDS:
            for cap in CAPS:
                sweep.append(
                    _summarize_configuration(
                        prepared_rows,
                        alpha=alpha,
                        threshold=threshold,
                        cap=cap,
                    )
                )
    selected = next(
        row
        for row in sweep
        if row["alpha"] == SELECTED_ALPHA
        and row["threshold"] == SELECTED_THRESHOLD
        and row["cap"] == SELECTED_CAP
    )
    pure_cosine_same_shape = next(
        row
        for row in sweep
        if row["alpha"] == 1.0
        and row["threshold"] == SELECTED_THRESHOLD
        and row["cap"] == SELECTED_CAP
    )
    no_cap_same_affinity = next(
        row
        for row in sweep
        if row["alpha"] == SELECTED_ALPHA
        and row["threshold"] == SELECTED_THRESHOLD
        and row["cap"] is None
    )

    result = {
        "schema": "lv007-part1-exploration-v1",
        "status": "COMPLETE",
        "behavioral_identity": {
            "pairwise": "LV-005 TEMPORAL_GUIDANCE renders each selected semantic item as its own group with at most its assigned selected spread child",
            "semantic_community": "in frozen relevance order, assign each selected episode to the open group with greatest mean 80% embedding-cosine plus 20% IDF-weighted facet-Ochiai affinity when that mean is at least .04 and the group has fewer than 8 items; otherwise open a group",
            "chronology": "after grouping, order unchanged episode elements by numeric conversation turn only within each group",
            "question_repeat": "the exact question string occurs before the memory and again in the unchanged answer cue; it does not alter selected evidence or grouping",
        },
        "inputs": {
            "prompt_rows": len(prompt_rows),
            "selected_episodes": selected_episode_count,
            "lv005_prompts_sha256": sha256_file(LV005_PROMPTS),
            "tc014_selections_sha256": sha256_file(TC014_SELECTIONS),
            "embedding_cache": reuse,
            "spacy": spacy.__version__,
            "parser_model": "en_core_web_sm",
            "facet_family_occurrences": dict(sorted(facet_family_counts.items())),
        },
        "distributions": {
            "selected_pair_cosine": _percentiles(selected_pair_cosines),
            "selected_pair_facet_ochiai": _percentiles(selected_pair_facets),
        },
        "sweep": sweep,
        "selected_configuration": selected,
        "controls": {
            "pure_cosine_same_threshold_and_cap": pure_cosine_same_shape,
            "same_affinity_without_cap": no_cap_same_affinity,
            "pairwise_groups": {
                "singleton": 452,
                "paired": 617,
                "total": 1069,
                "source": "LV-005 Part 1 and passing Preflight",
            },
        },
        "absorbing_states": {
            "all_singletons": "reachable above the observed maximum off-diagonal affinity",
            "capacity_partition": "reachable below the observed minimum mean affinity; the cap then determines groups",
            "selected_cap_binding": selected["cap_bound_per_prompt"],
        },
        "selection_reason": "Among the label-blind sweep, alpha=.8, threshold=.04 and cap=8 reduce the 1069 pairwise groups without creating groups above eight; the cap binds on a minority of groups and the selected configuration separates within- from between-group affinity. This is a structural choice, not an outcome optimum.",
        "surrogate_audit": {
            "can_pass_while_false": True,
            "residual": "A compact group can be topically incoherent even when its average mathematical affinity exceeds the threshold; shared facets can be generic and embedding cosines are weakly separated in the query-filtered set.",
        },
        "calls": {
            "embedding_cache_hits": reuse["hits"],
            "embedding_cache_misses": reuse["misses"],
            "embedding": 0,
            "llm_or_generative": 0,
        },
        "labels_opened": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
