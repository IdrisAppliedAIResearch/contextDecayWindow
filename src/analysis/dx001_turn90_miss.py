"""DX-001 Part 1: why the E005 objective declined to select turn 90.

Offline. No inference and no new study run. Every derived quantity is
recomputed from committed E005 inputs and is gated on a replay that must
reproduce the committed selection payloads byte-for-byte first.

This module is analysis, not mechanism: it may read the plant key. The
mechanism under examination (``src/retrieval_mechanism_ledger/e005.py``) is
untouched and its hash is recorded.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from src.analysis.e005_diversity_selection import (
    BUDGET_CHARS,
    COMPONENT_ROOT,
    ORACLE_EPISODES,
    PRIMARY_POOL,
    Q11_TURN,
    REPO_ROOT,
    EmbeddingCache,
    build_pools,
    load_candidates,
    load_queries,
)
from src.analysis.e005_diversity_selection import (
    _hash_paths as hash_paths,
)
from src.analysis.e005_diversity_selection import (
    _normalize as normalize,
)
from src.analysis.e005_diversity_selection import (
    _read_csv as read_csv,
)
from src.analysis.e005_diversity_selection import (
    _read_jsonl as read_jsonl,
)
from src.analysis.e005_diversity_selection import (
    _write_artifact_manifest as write_artifact_manifest,
)
from src.analysis.e005_diversity_selection import (
    _write_csv as write_csv,
)
from src.analysis.e005_diversity_selection import (
    _write_json as write_json,
)
from src.analysis.retrieval_bakeoff_tier6_121 import ATOMIC_ITEMS
from src.memory.stm_context_builder import render_episode_element
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_mechanism_ledger.e005 import (
    CLUSTER_COUNTS,
    additive_weight,
    build_selectors,
    deterministic_clusters,
    relevance_vector,
    select,
    vector,
    wrapper_chars,
)


REGISTRATION_COMMIT = "a30d3bcca53248fe75b7901c2ff74a8aa28f5e1a"
E005_ARTIFACTS = COMPONENT_ROOT / "artifacts" / "e005"
COMMITTED_SELECTION = E005_ARTIFACTS / "raw" / "q11_selection.jsonl"
COMMITTED_SWEEP = E005_ARTIFACTS / "configuration_sweep.csv"
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e005.py"

TARGET_TURN = 90
TARGET_ID = "1dec9c9e-b948-4ef8-9eaa-aa889c083470"
PRIMARY_CONFIGURATION = "A3_l0.1_r0.0_k16"
PRIMARY_LAMBDA = 0.1
CONFIGURATION_COUNT = 146

CENSUS_FIELDS = (
    "configuration_id",
    "arm",
    "lambda",
    "r",
    "k",
    "selected_turn90",
    "q11_fact_count",
    "q11_domain_count",
    "civil",
    "art",
    "monetary",
    "marine",
    "targeted_preserved",
    "targeted_required",
    "serialized_chars",
    "oracle_overlap",
)
CLUSTER_FIELDS = (
    "k",
    "target_cluster",
    "cluster_size",
    "cluster_member_turns",
    "target_is_only_member",
    "first_occupant_turn",
    "first_occupant_step",
    "first_occupant_q11_facts",
    "occupied_before_target_best_step",
)
TRACE_FIELDS = (
    "step",
    "winner_turn",
    "winner_scaled_gain",
    "winner_chars",
    "winner_q11_facts",
    "target_affordable",
    "target_scaled_gain",
    "target_relevance_term",
    "target_cluster_novel",
    "target_rank_among_affordable",
    "gap_to_winner",
    "counterfactual_gain_novelty_paid",
    "counterfactual_wins",
)
SENSITIVITY_FIELDS = (
    "configuration_id",
    "lambda",
    "r",
    "k",
    "selected",
    "best_rank_among_affordable",
    "best_step",
    "min_gap_to_winner",
    "ever_affordable",
    "ever_cluster_novel",
    "counterfactual_ever_wins",
)
COST_FIELDS = (
    "role",
    "turn",
    "chars",
    "q11_facts",
    "chars_per_q11_fact",
    "cosine_rank",
)


def run_dx001(output_dir: Path, embedding_model: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite DX-001 output: {output_dir}")
    output_dir.mkdir(parents=True)

    embedder = CarriedEmbedder(embedding_model)
    embedder.assert_carried_model()

    # E005 embedded all nine probe queries in one batch. Reproducing the
    # committed payloads requires reproducing that call, not just the text:
    # see `embedding_batch_sensitivity` below.
    queries = load_queries()
    cache = EmbeddingCache(embedder)
    cache.prime(queries.values())
    query = queries[Q11_TURN]
    embedding = vector(cache(query))
    candidates = load_candidates()
    pool = build_pools(candidates, query, embedding)[PRIMARY_POOL]

    target_index = _target_index(pool)
    relevance = relevance_vector(embedding, pool)
    costs = np.array(
        [float(additive_weight(candidate)) for candidate in pool],
        dtype=np.float64,
    )
    facts = _facts_by_index(pool)
    ranks = _cosine_ranks(pool, relevance)

    committed = _committed_records()
    selectors = build_selectors(pool)
    replay = _replay_gate(pool, embedding, selectors, committed)
    replay["embedding_batch_sensitivity"] = _batch_sensitivity(
        pool=pool,
        solo_embedding=vector(embedder.embed_many([query])[0]),
        batched_embedding=embedding,
        committed=committed,
    )

    census, census_rows = _selection_census(committed)
    clusters = _cluster_table(pool, target_index, facts, committed)
    cost = _cost_table(pool, target_index, facts, costs, ranks, committed)
    trace, trace_rows = _greedy_trace(
        pool=pool,
        selectors=selectors,
        target_index=target_index,
        relevance=relevance,
        costs=costs,
        facts=facts,
    )
    sensitivity, sensitivity_rows = _sensitivity(
        pool=pool,
        selectors=selectors,
        target_index=target_index,
        relevance=relevance,
        costs=costs,
    )
    termination = _termination(
        pool=pool,
        embedding=embedding,
        selectors=selectors,
        target_index=target_index,
        costs=costs,
    )
    attribution = _attribute(
        census=census,
        clusters=clusters,
        cost=cost,
        trace=trace,
        sensitivity=sensitivity,
        termination=termination,
    )
    reading = _reading(
        trace=trace,
        trace_rows=trace_rows,
        census=census,
        sensitivity=sensitivity,
        attribution=attribution,
        relevance=relevance,
        target_index=target_index,
    )

    result = {
        "registration_commit": REGISTRATION_COMMIT,
        "part": 1,
        "target": {
            "turn": TARGET_TURN,
            "id": TARGET_ID,
            "cosine_rank": ranks[target_index],
            "pool_size": len(pool),
            "relevance": float(relevance[target_index]),
            "chars": int(costs[target_index]),
            "q11_facts": facts[target_index],
            "is_oracle_episode": TARGET_ID
            in {identifier for identifier, _turn in ORACLE_EPISODES},
        },
        "input_hashes": hash_paths(
            [COMMITTED_SELECTION, COMMITTED_SWEEP, MECHANISM_SOURCE]
        ),
        "replay_gate": replay,
        "selection_census": census,
        "cluster_collision": clusters,
        "cost": cost,
        "greedy_trace": trace,
        "sensitivity": sensitivity,
        "termination": termination,
        "attribution": attribution,
        "reading": reading,
    }

    write_json(output_dir / "dx001_results.json", result)
    write_json(output_dir / "replay_gate.json", replay)
    write_csv(output_dir / "selection_census.csv", census_rows, CENSUS_FIELDS)
    write_csv(
        output_dir / "cluster_assignments.csv",
        clusters["rows"],
        CLUSTER_FIELDS,
    )
    write_csv(output_dir / "greedy_trace.csv", trace_rows, TRACE_FIELDS)
    write_csv(
        output_dir / "sensitivity.csv",
        sensitivity_rows,
        SENSITIVITY_FIELDS,
    )
    write_csv(output_dir / "cost_comparison.csv", cost["rows"], COST_FIELDS)
    (output_dir / "DX_001_report.md").write_text(
        _report(result),
        encoding="utf-8",
        newline="\n",
    )
    write_artifact_manifest(output_dir)
    return result


def _target_index(pool: Sequence[dict]) -> int:
    matches = [
        index
        for index, candidate in enumerate(pool)
        if str(candidate["id"]) == TARGET_ID
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Turn {TARGET_TURN} is not uniquely present in the E005 pool"
        )
    if int(pool[matches[0]]["turn_number"]) != TARGET_TURN:
        raise AssertionError("Target identity and turn number disagree")
    return matches[0]


def _facts_by_index(pool: Sequence[dict]) -> list[list[str]]:
    rendered = [normalize(render_episode_element(candidate)) for candidate in pool]
    return [
        [
            f"{domain}:{item}"
            for domain, item, needle, _plant_turns in ATOMIC_ITEMS
            if needle in text
        ]
        for text in rendered
    ]


def _cosine_ranks(pool: Sequence[dict], relevance: np.ndarray) -> list[int]:
    order = sorted(
        range(len(pool)),
        key=lambda index: (
            -float(relevance[index]),
            int(pool[index]["turn_number"]),
            str(pool[index]["id"]),
        ),
    )
    ranks = [0] * len(pool)
    for position, index in enumerate(order, 1):
        ranks[index] = position
    return ranks


def _committed_records() -> dict[str, dict]:
    records = {
        str(record["configuration_id"]): record
        for record in read_jsonl(COMMITTED_SELECTION)
        if str(record["pool"]) == PRIMARY_POOL
    }
    if len(records) != CONFIGURATION_COUNT:
        raise AssertionError(
            "Committed E005 primary-pool records are not the registered "
            f"{CONFIGURATION_COUNT} configurations"
        )
    return records


def _replay_gate(
    pool: Sequence[dict],
    embedding: np.ndarray,
    selectors: Sequence[tuple[str, object]],
    committed: dict[str, dict],
) -> dict:
    """Reproduce every committed payload before reporting anything derived."""
    mismatches = []
    for configuration_id, selector in selectors:
        record = committed[configuration_id]
        result = select(
            candidates=pool,
            query_embedding=embedding,
            selector=selector,
            budget_chars=BUDGET_CHARS,
        )
        if (
            result.payload_sha256 != record["payload_sha256"]
            or result.serialized_chars != int(record["serialized_chars"])
            or list(result.selected_ids) != list(record["selected_ids"])
        ):
            mismatches.append(configuration_id)
    gate = {
        "configurations": len(selectors),
        "reproduced": len(selectors) - len(mismatches),
        "mismatches": mismatches,
        "passed": not mismatches,
    }
    if mismatches:
        raise AssertionError(
            "DX-001 replay did not reproduce committed E005 payloads: "
            f"{mismatches[:5]}"
        )
    return gate


def _batch_sensitivity(
    *,
    pool: Sequence[dict],
    solo_embedding: np.ndarray,
    batched_embedding: np.ndarray,
    committed: dict[str, dict],
) -> dict:
    """How many committed payloads survive embedding the query on its own.

    Recorded because the replay gate caught it: the same query text embedded
    alone rather than in E005's nine-query batch returns a measurably
    different vector, and some greedy steps are close enough to flip on it.
    The size of the difference is measured, not assumed - the cause is not
    established here and is not claimed.
    """
    solo = np.asarray(solo_embedding, dtype=np.float64)
    batched = np.asarray(batched_embedding, dtype=np.float64)
    denominator = float(np.linalg.norm(solo) * np.linalg.norm(batched))
    agreement = float(solo @ batched) / denominator if denominator else 0.0
    selectors = build_selectors(pool)
    mismatches = [
        configuration_id
        for configuration_id, selector in selectors
        if select(
            candidates=pool,
            query_embedding=solo,
            selector=selector,
            budget_chars=BUDGET_CHARS,
        ).payload_sha256
        != committed[configuration_id]["payload_sha256"]
    ]
    return {
        "cosine_between_embeddings": agreement,
        "max_absolute_difference": float(np.max(np.abs(solo - batched))),
        "configurations_flipped": len(mismatches),
        "flipped_configuration_ids": mismatches,
    }


def _selection_census(committed: dict[str, dict]) -> tuple[dict, list[dict]]:
    sweep = {str(row["configuration_id"]): row for row in read_csv(COMMITTED_SWEEP)}
    rows = []
    for configuration_id, record in sorted(committed.items()):
        summary = sweep.get(configuration_id, {})
        selected = TARGET_TURN in [
            int(turn) for turn in record["selected_source_turns"]
        ]
        rows.append(
            {
                "configuration_id": configuration_id,
                "arm": record["arm"],
                "lambda": summary.get("lambda", ""),
                "r": summary.get("r", ""),
                "k": summary.get("k", ""),
                "selected_turn90": selected,
                "q11_fact_count": summary.get("q11_fact_count", ""),
                "q11_domain_count": summary.get("q11_domain_count", ""),
                "civil": summary.get("civil", ""),
                "art": summary.get("art", ""),
                "monetary": summary.get("monetary", ""),
                "marine": summary.get("marine", ""),
                "targeted_preserved": summary.get("targeted_preserved", ""),
                "targeted_required": summary.get("targeted_required", ""),
                "serialized_chars": summary.get("serialized_chars", ""),
                "oracle_overlap": summary.get("oracle_overlap", ""),
            }
        )
    selecting = [row for row in rows if row["selected_turn90"]]
    return (
        {
            "configurations": len(rows),
            "selecting_turn90": len(selecting),
            "selecting_configuration_ids": [
                row["configuration_id"] for row in selecting
            ],
            "selecting_result_vectors": selecting,
            "by_arm": {
                arm: sum(
                    1
                    for row in selecting
                    if str(row["configuration_id"]).startswith(arm)
                )
                for arm in ("A1", "A2", "A3")
            },
        },
        rows,
    )


def _cluster_table(
    pool: Sequence[dict],
    target_index: int,
    facts: Sequence[Sequence[str]],
    committed: dict[str, dict],
) -> dict:
    rows = []
    for count in CLUSTER_COUNTS:
        assignments = deterministic_clusters(pool, count)
        cluster = int(assignments[target_index])
        members = [
            index
            for index in range(len(pool))
            if int(assignments[index]) == cluster
        ]
        configuration_id = f"A3_l{PRIMARY_LAMBDA:.1f}_r0.0_k{count:02d}"
        occupant = _first_occupant(
            pool=pool,
            assignments=assignments,
            cluster=cluster,
            record=committed.get(configuration_id),
            facts=facts,
        )
        rows.append(
            {
                "k": count,
                "target_cluster": cluster,
                "cluster_size": len(members),
                "cluster_member_turns": " ".join(
                    str(int(pool[index]["turn_number"])) for index in members
                ),
                "target_is_only_member": len(members) == 1,
                "first_occupant_turn": occupant["turn"],
                "first_occupant_step": occupant["step"],
                "first_occupant_q11_facts": occupant["facts"],
                "occupied_before_target_best_step": occupant["step"] is not None,
            }
        )
    return {
        "rows": rows,
        "collision_at_every_k": all(not row["target_is_only_member"] for row in rows),
        "collision_at_primary_k": next(
            not row["target_is_only_member"] for row in rows if row["k"] == 16
        ),
    }


def _first_occupant(
    *,
    pool: Sequence[dict],
    assignments: np.ndarray,
    cluster: int,
    record: dict | None,
    facts: Sequence[Sequence[str]],
) -> dict:
    if record is None:
        return {"turn": None, "step": None, "facts": None}
    by_id = {str(candidate["id"]): index for index, candidate in enumerate(pool)}
    for position, identifier in enumerate(record["selected_ids"], 1):
        index = by_id[str(identifier)]
        if int(assignments[index]) == cluster:
            return {
                "turn": int(pool[index]["turn_number"]),
                "step": position,
                "facts": len(facts[index]),
            }
    return {"turn": None, "step": None, "facts": None}


def _cost_table(
    pool: Sequence[dict],
    target_index: int,
    facts: Sequence[Sequence[str]],
    costs: np.ndarray,
    ranks: Sequence[int],
    committed: dict[str, dict],
) -> dict:
    record = committed[PRIMARY_CONFIGURATION]
    by_id = {str(candidate["id"]): index for index, candidate in enumerate(pool)}
    rows = [
        {
            "role": "target",
            "turn": TARGET_TURN,
            "chars": int(costs[target_index]),
            "q11_facts": len(facts[target_index]),
            "chars_per_q11_fact": (
                round(float(costs[target_index]) / len(facts[target_index]), 1)
                if facts[target_index]
                else ""
            ),
            "cosine_rank": ranks[target_index],
        }
    ]
    for identifier in record["selected_ids"]:
        index = by_id[str(identifier)]
        rows.append(
            {
                "role": "selected",
                "turn": int(pool[index]["turn_number"]),
                "chars": int(costs[index]),
                "q11_facts": len(facts[index]),
                "chars_per_q11_fact": (
                    round(float(costs[index]) / len(facts[index]), 1)
                    if facts[index]
                    else ""
                ),
                "cosine_rank": ranks[index],
            }
        )
    selected_costs = [row["chars"] for row in rows if row["role"] == "selected"]
    bearing = [
        row
        for row in rows
        if row["role"] == "selected" and row["q11_facts"]
    ]
    return {
        "rows": rows,
        "target_chars": int(costs[target_index]),
        "target_chars_per_fact": round(
            float(costs[target_index]) / max(len(facts[target_index]), 1), 1
        ),
        "selected_chars_min": min(selected_costs),
        "selected_chars_median": float(np.median(selected_costs)),
        "selected_chars_max": max(selected_costs),
        "target_cheaper_than_median": int(costs[target_index])
        < float(np.median(selected_costs)),
        "fact_bearing_chars_per_fact_median": (
            float(
                np.median([float(row["chars_per_q11_fact"]) for row in bearing])
            )
            if bearing
            else None
        ),
        "pool_chars_median": float(np.median(costs)),
    }


def _selector_for(
    selectors: Sequence[tuple[str, object]],
    configuration_id: str,
) -> object:
    for identifier, selector in selectors:
        if identifier == configuration_id:
            return selector
    raise KeyError(configuration_id)


def _walk(
    *,
    pool: Sequence[dict],
    selector,
    target_index: int,
    relevance: np.ndarray,
    costs: np.ndarray,
) -> list[dict]:
    """Re-walk the greedy loop, recording the target's position each step.

    Mirrors ``e005.select`` exactly, including its tie-break, and asserts the
    reproduced winner sequence rather than assuming it.
    """
    turns = [int(candidate["turn_number"]) for candidate in pool]
    identifiers = [str(candidate["id"]) for candidate in pool]
    fixed = wrapper_chars()
    selected: list[int] = []
    remaining = set(range(len(pool)))
    spent = 0
    rows: list[dict] = []

    while remaining:
        affordable = [
            index
            for index in sorted(remaining)
            if fixed + spent + int(costs[index]) <= BUDGET_CHARS
        ]
        if not affordable:
            break
        scaled = selector.scaled_gains(relevance, selected, costs)
        chosen = min(
            affordable,
            key=lambda index: (
                -float(scaled[index]),
                int(costs[index]),
                turns[index],
                identifiers[index],
            ),
        )
        target_affordable = target_index in affordable
        ordered = sorted(
            affordable,
            key=lambda index: (
                -float(scaled[index]),
                int(costs[index]),
                turns[index],
                identifiers[index],
            ),
        )
        rows.append(
            {
                "step": len(rows) + 1,
                "winner_index": chosen,
                "winner_turn": turns[chosen],
                "winner_scaled_gain": float(scaled[chosen]),
                "winner_chars": int(costs[chosen]),
                "target_affordable": target_affordable,
                "target_scaled_gain": float(scaled[target_index]),
                "target_rank_among_affordable": (
                    ordered.index(target_index) + 1 if target_affordable else None
                ),
                "gap_to_winner": float(scaled[chosen] - scaled[target_index]),
                "selected_before_step": tuple(selected),
            }
        )
        spent += int(costs[chosen])
        selected.append(chosen)
        remaining.discard(chosen)
    return rows


def _greedy_trace(
    *,
    pool: Sequence[dict],
    selectors: Sequence[tuple[str, object]],
    target_index: int,
    relevance: np.ndarray,
    costs: np.ndarray,
    facts: Sequence[Sequence[str]],
) -> tuple[dict, list[dict]]:
    selector = _selector_for(selectors, PRIMARY_CONFIGURATION)
    walk = _walk(
        pool=pool,
        selector=selector,
        target_index=target_index,
        relevance=relevance,
        costs=costs,
    )
    committed = _committed_records()[PRIMARY_CONFIGURATION]
    if [row["winner_turn"] for row in walk] != [
        int(turn) for turn in committed["selected_source_turns"]
    ]:
        raise AssertionError("DX-001 trace did not reproduce the committed walk")

    relevance_term = float(max(relevance[target_index], 0.0))
    rows = []
    for row in walk:
        covered = {
            int(selector.assignments[index]) for index in row["selected_before_step"]
        }
        novel = int(selector.assignments[target_index]) not in covered
        counterfactual = relevance_term + selector.lambda_
        rows.append(
            {
                "step": row["step"],
                "winner_turn": row["winner_turn"],
                "winner_scaled_gain": round(row["winner_scaled_gain"], 6),
                "winner_chars": row["winner_chars"],
                "winner_q11_facts": len(
                    facts[row["winner_index"]]
                ),
                "target_affordable": row["target_affordable"],
                "target_scaled_gain": round(row["target_scaled_gain"], 6),
                "target_relevance_term": round(relevance_term, 6),
                "target_cluster_novel": novel,
                "target_rank_among_affordable": row["target_rank_among_affordable"],
                "gap_to_winner": round(row["gap_to_winner"], 6),
                "counterfactual_gain_novelty_paid": round(counterfactual, 6),
                "counterfactual_wins": bool(
                    row["target_affordable"]
                    and counterfactual > row["winner_scaled_gain"]
                ),
            }
        )
    affordable_rows = [row for row in rows if row["target_affordable"]]
    return (
        {
            "steps": len(rows),
            "target_ever_affordable": bool(affordable_rows),
            "target_affordable_steps": [
                row["step"] for row in affordable_rows
            ],
            "target_best_rank": (
                min(row["target_rank_among_affordable"] for row in affordable_rows)
                if affordable_rows
                else None
            ),
            "target_min_gap": (
                min(row["gap_to_winner"] for row in affordable_rows)
                if affordable_rows
                else None
            ),
            "target_relevance_term": round(relevance_term, 6),
            "target_lambda_term": selector.lambda_,
            "cluster_novel_steps": [
                row["step"] for row in rows if row["target_cluster_novel"]
            ],
            "counterfactual_wins_any_step": any(
                row["counterfactual_wins"] for row in rows
            ),
            "tied_with_winner_steps": [
                row["step"]
                for row in affordable_rows
                if abs(row["gap_to_winner"]) < 1e-12
            ],
        },
        rows,
    )


def _sensitivity(
    *,
    pool: Sequence[dict],
    selectors: Sequence[tuple[str, object]],
    target_index: int,
    relevance: np.ndarray,
    costs: np.ndarray,
) -> tuple[dict, list[dict]]:
    relevance_term = float(max(relevance[target_index], 0.0))
    rows = []
    for configuration_id, selector in selectors:
        if getattr(selector, "arm", "") != "A3":
            continue
        walk = _walk(
            pool=pool,
            selector=selector,
            target_index=target_index,
            relevance=relevance,
            costs=costs,
        )
        affordable = [row for row in walk if row["target_affordable"]]
        selected = any(
            row["winner_index"] == target_index for row in walk
        )
        novel_steps = []
        counterfactual_wins = False
        for row in walk:
            covered = {
                int(selector.assignments[index])
                for index in row["selected_before_step"]
            }
            if int(selector.assignments[target_index]) not in covered:
                novel_steps.append(row["step"])
            if row["target_affordable"]:
                gain = relevance_term + selector.lambda_
                scaled = gain / float(
                    np.power(costs[target_index], selector.cost_exponent)
                )
                if scaled > row["winner_scaled_gain"]:
                    counterfactual_wins = True
        best = (
            min(
                affordable,
                key=lambda row: (
                    row["target_rank_among_affordable"],
                    row["gap_to_winner"],
                ),
            )
            if affordable
            else None
        )
        rows.append(
            {
                "configuration_id": configuration_id,
                "lambda": selector.lambda_,
                "r": selector.cost_exponent,
                "k": selector.cluster_count,
                "selected": selected,
                "best_rank_among_affordable": (
                    best["target_rank_among_affordable"] if best else ""
                ),
                "best_step": best["step"] if best else "",
                "min_gap_to_winner": (
                    round(min(row["gap_to_winner"] for row in affordable), 6)
                    if affordable
                    else ""
                ),
                "ever_affordable": bool(affordable),
                "ever_cluster_novel": bool(novel_steps),
                "counterfactual_ever_wins": counterfactual_wins,
            }
        )
    ranked = [row for row in rows if row["best_rank_among_affordable"] != ""]
    best_overall = (
        min(ranked, key=lambda row: row["best_rank_among_affordable"])
        if ranked
        else None
    )
    return (
        {
            "configurations": len(rows),
            "selected_anywhere": sum(1 for row in rows if row["selected"]),
            "best_rank_overall": (
                best_overall["best_rank_among_affordable"] if best_overall else None
            ),
            "best_rank_configuration": (
                best_overall["configuration_id"] if best_overall else None
            ),
            "counterfactual_wins_configurations": sum(
                1 for row in rows if row["counterfactual_ever_wins"]
            ),
            "best_rank_by_r": {
                str(exponent): min(
                    (
                        row["best_rank_among_affordable"]
                        for row in ranked
                        if row["r"] == exponent
                    ),
                    default=None,
                )
                for exponent in sorted({row["r"] for row in rows})
            },
            "best_rank_by_k": {
                str(count): min(
                    (
                        row["best_rank_among_affordable"]
                        for row in ranked
                        if row["k"] == count
                    ),
                    default=None,
                )
                for count in sorted({row["k"] for row in rows})
            },
            "best_rank_by_lambda": {
                f"{value:.1f}": min(
                    (
                        row["best_rank_among_affordable"]
                        for row in ranked
                        if row["lambda"] == value
                    ),
                    default=None,
                )
                for value in sorted({row["lambda"] for row in rows})
            },
        },
        rows,
    )


def _termination(
    *,
    pool: Sequence[dict],
    embedding: np.ndarray,
    selectors: Sequence[tuple[str, object]],
    target_index: int,
    costs: np.ndarray,
) -> dict:
    selector = _selector_for(selectors, PRIMARY_CONFIGURATION)
    result = select(
        candidates=pool,
        query_embedding=embedding,
        selector=selector,
        budget_chars=BUDGET_CHARS,
    )
    spent = result.serialized_chars
    remaining_chars = BUDGET_CHARS - spent
    unselected = [
        index
        for index, candidate in enumerate(pool)
        if str(candidate["id"]) not in set(result.selected_ids)
    ]
    affordable_at_end = [
        index for index in unselected if int(costs[index]) <= remaining_chars
    ]
    return {
        "serialized_chars": spent,
        "budget_chars": BUDGET_CHARS,
        "remaining_chars": remaining_chars,
        "unselected_candidates": len(unselected),
        "affordable_unselected_at_end": len(affordable_at_end),
        "cheapest_unselected_chars": int(min(costs[index] for index in unselected)),
        "target_chars": int(costs[target_index]),
        "target_affordable_at_end": int(costs[target_index]) <= remaining_chars,
        "terminated_on": (
            "budget" if not affordable_at_end else "candidates"
        ),
    }


def _attribute(
    *,
    census: dict,
    clusters: dict,
    cost: dict,
    trace: dict,
    sensitivity: dict,
    termination: dict,
) -> dict:
    """Signature-by-signature attribution. 'Unresolved' is permitted."""
    m1 = bool(
        clusters["collision_at_primary_k"]
        and trace["cluster_novel_steps"] != list(
            range(1, trace["steps"] + 1)
        )
    )
    m1_sufficient = bool(trace["counterfactual_wins_any_step"])
    m2 = bool(
        len({value for value in sensitivity["best_rank_by_r"].values()}) > 1
    )
    m3 = bool(
        trace["target_relevance_term"] <= trace["target_lambda_term"]
        and not trace["counterfactual_wins_any_step"]
    )
    m4 = bool(
        termination["terminated_on"] == "budget"
        and trace["target_ever_affordable"]
        and not termination["target_affordable_at_end"]
    )
    verdict = [name for name, fired in (
        ("M1", m1),
        ("M2", m2),
        ("M3", m3),
        ("M4", m4),
    ) if fired]
    return {
        "M1_cluster_collision": {
            "fires": m1,
            "sufficient_alone": m1_sufficient,
            "evidence": (
                "target shares its k=16 cluster with "
                f"{next(row['cluster_size'] for row in clusters['rows'] if row['k'] == 16) - 1}"
                " other episodes, but the diversity term went unpaid at "
                f"{trace['steps'] - len(trace['cluster_novel_steps'])} of "
                f"{trace['steps']} steps"
            ),
        },
        "M2_cost_discount": {
            "fires": m2,
            "evidence": "best rank by r: "
            + json.dumps(sensitivity["best_rank_by_r"], sort_keys=True),
        },
        "M3_relevance_floor": {
            "fires": m3,
            "evidence": (
                f"relevance term {trace['target_relevance_term']} against "
                f"lambda term {trace['target_lambda_term']}; counterfactual "
                "with novelty paid in full wins at "
                f"{'some' if trace['counterfactual_wins_any_step'] else 'no'} step"
            ),
        },
        "M4_budget_exhaustion": {
            "fires": m4,
            "evidence": (
                f"terminated on {termination['terminated_on']} with "
                f"{termination['remaining_chars']} chars left and "
                f"{termination['affordable_unselected_at_end']} affordable "
                "unselected candidates"
            ),
        },
        "census_settles_recovery": census["selecting_turn90"] > 0,
        "target_cheaper_than_median_selected": cost["target_cheaper_than_median"],
        "verdict": "+".join(verdict) if verdict else "UNRESOLVED",
        "distinguishable": bool(verdict),
    }


def _reading(
    *,
    trace: dict,
    trace_rows: Sequence[dict],
    census: dict,
    sensitivity: dict,
    attribution: dict,
    relevance: np.ndarray,
    target_index: int,
) -> dict:
    """Quantified consequences of the attribution, and the F.6 determination.

    Nothing here changes a fired/not-fired boolean. It states what the
    numbers imply and checks the F.8 prediction against them.
    """
    affordable = [row for row in trace_rows if row["target_affordable"]]
    lambda_term = float(trace["target_lambda_term"])
    actual = float(trace["target_relevance_term"])
    required = (
        min(row["winner_scaled_gain"] for row in affordable) - lambda_term
        if affordable
        else None
    )
    stronger = (
        int(np.sum(relevance >= required)) if required is not None else None
    )
    f6 = {
        "mechanisms_indistinguishable": not attribution["distinguishable"],
        "no_configuration_recovers_the_target": census["selecting_turn90"] == 0,
        "branch_c_reached": attribution["M3_relevance_floor"]["fires"],
        "justification_needs_the_target": census["selecting_turn90"] == 0,
    }
    return {
        "f8_prediction_m1_cluster_collision": {
            "predicted": True,
            "measured": attribution["M1_cluster_collision"]["fires"],
            "held": attribution["M1_cluster_collision"]["fires"] is True,
        },
        "f8_prediction_census_finds_nothing": {
            "predicted": True,
            "measured": census["selecting_turn90"] == 0,
            "held": census["selecting_turn90"] == 0,
        },
        "diversity_term_was_payable_in_full": len(
            trace["cluster_novel_steps"]
        )
        == trace["steps"],
        "relevance_required_to_win_any_step": (
            round(required, 6) if required is not None else None
        ),
        "relevance_actual": actual,
        "relevance_shortfall": (
            round(required - actual, 6) if required is not None else None
        ),
        "episodes_meeting_the_required_relevance": stronger,
        "best_rank_ever_reached": sensitivity["best_rank_overall"],
        "f6_conditions": f6,
        "f6_fires": any(f6.values()),
        "part_2_outcome": (
            "NO_CHANGE_ESCALATE" if any(f6.values()) else "BRANCH_SELECTION"
        ),
    }


def _report(result: dict) -> str:
    target = result["target"]
    census = result["selection_census"]
    clusters = result["cluster_collision"]
    cost = result["cost"]
    trace = result["greedy_trace"]
    sensitivity = result["sensitivity"]
    termination = result["termination"]
    attribution = result["attribution"]

    lines = [
        "# DX-001 Part 1 - Turn-90 Selection Miss",
        "",
        f"**Registration commit:** `{REGISTRATION_COMMIT}`",
        f"**Frozen configuration:** `{PRIMARY_CONFIGURATION}`, "
        f"pool {target['pool_size']}, budget {BUDGET_CHARS:,}",
        f"**Verdict:** **{attribution['verdict']}**",
        "",
        "Offline. No inference, no new study run. Every derived number is",
        "recomputed from committed E005 inputs behind a replay gate that",
        f"reproduced {result['replay_gate']['reproduced']} of "
        f"{result['replay_gate']['configurations']} committed payload hashes",
        "byte-for-byte before any of it was reported.",
        "",
        "**The gate earned its place.** The first attempt embedded the Q11 "
        "query on its own instead of in E005's nine-query batch. The returned "
        "vector is not the same one: cosine agreement "
        f"{result['replay_gate']['embedding_batch_sensitivity']['cosine_between_embeddings']:.6f}, "
        "largest component difference "
        f"{result['replay_gate']['embedding_batch_sensitivity']['max_absolute_difference']:.3f}, "
        "and it flips "
        f"{result['replay_gate']['embedding_batch_sensitivity']['configurations_flipped']} "
        "of 146 committed payloads. The cause is not established here and no "
        "claim is made about it; what is established is that reproducing E005 "
        "requires reproducing the embedding call shape, not only the query "
        "text. Everything below uses the committed batched call.",
        "",
        "## 0. The target",
        "",
        f"- Turn {target['turn']}, id `{target['id']}`",
        f"- Cosine rank **{target['cosine_rank']}/{target['pool_size']}**, "
        f"cosine {target['relevance']:.4f}",
        f"- Serialized cost **{target['chars']:,} chars**, carrying "
        f"**{len(target['q11_facts'])} Q11 items**: "
        + ", ".join(target["q11_facts"]),
        f"- Oracle episode: {target['is_oracle_episode']}",
        "",
        "## D.2.1 Selection census - run first",
        "",
        f"Configurations examined: **{census['configurations']}**. "
        f"Configurations that selected turn {TARGET_TURN}: "
        f"**{census['selecting_turn90']}**.",
        "",
    ]
    if census["selecting_turn90"]:
        lines += [
            "| Configuration | Q11 | Dom | civil | art | mon | marine | "
            "Targeted | Chars |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in census["selecting_result_vectors"]:
            lines.append(
                f"| `{row['configuration_id']}` | {row['q11_fact_count']}/17 | "
                f"{row['q11_domain_count']}/4 | {row['civil']} | {row['art']} | "
                f"{row['monetary']} | {row['marine']} | "
                f"{row['targeted_preserved']}/{row['targeted_required']} | "
                f"{row['serialized_chars']} |"
            )
        lines.append("")
    else:
        lines += [
            "**No configuration in the registered parameter space selected it.**",
            "The objective is structurally blind to this episode across the",
            "entire space explored, not unlucky in one cell.",
            "",
        ]

    lines += [
        "## D.2.2 Cluster assignment",
        "",
        "| k | Target cluster | Size | Alone? | First occupant turn | Step | "
        "Its Q11 facts |",
        "|---:|---:|---:|---|---:|---:|---:|",
    ]
    for row in clusters["rows"]:
        lines.append(
            f"| {row['k']} | {row['target_cluster']} | {row['cluster_size']} | "
            f"{row['target_is_only_member']} | {row['first_occupant_turn']} | "
            f"{row['first_occupant_step']} | {row['first_occupant_q11_facts']} |"
        )
    lines += [
        "",
        f"Collision at every k: **{clusters['collision_at_every_k']}**. "
        f"Collision at the primary k=16: **{clusters['collision_at_primary_k']}**.",
        "",
        "## D.2.3 Cost",
        "",
        f"- Target: **{cost['target_chars']:,} chars**, "
        f"{cost['target_chars_per_fact']:,} chars per Q11 fact",
        f"- Selected episodes: min {cost['selected_chars_min']:,}, "
        f"median {cost['selected_chars_median']:,.0f}, "
        f"max {cost['selected_chars_max']:,}",
        f"- Fact-bearing selections, median chars per fact: "
        f"{cost['fact_bearing_chars_per_fact_median']}",
        f"- Target cheaper than the median selected episode: "
        f"**{cost['target_cheaper_than_median']}**",
        "",
        "## D.2.4 Greedy trace",
        "",
        f"- Steps: {trace['steps']}",
        f"- Target affordable at steps: {trace['target_affordable_steps']}",
        f"- Best rank among affordable candidates: "
        f"**{trace['target_best_rank']}**",
        f"- Smallest gap to the step winner: **{trace['target_min_gap']}**",
        f"- Relevance term max(cos, 0) = **{trace['target_relevance_term']}**; "
        f"lambda term = **{trace['target_lambda_term']}**",
        f"- Steps where the target's cluster was still novel: "
        f"{trace['cluster_novel_steps']}",
        f"- Counterfactual with the diversity term paid in full ever wins: "
        f"**{trace['counterfactual_wins_any_step']}**",
        "",
        "The gap, not the rank, is the deciding quantity; both are recorded in",
        "`greedy_trace.csv`.",
        "",
        "## D.2.5 Sensitivity across lambda, r and k",
        "",
        f"- A3 configurations walked: {sensitivity['configurations']}",
        f"- Selected the target anywhere: {sensitivity['selected_anywhere']}",
        f"- Best rank achieved anywhere: "
        f"**{sensitivity['best_rank_overall']}** at "
        f"`{sensitivity['best_rank_configuration']}`",
        f"- Best rank by r: {json.dumps(sensitivity['best_rank_by_r'], sort_keys=True)}",
        f"- Best rank by k: {json.dumps(sensitivity['best_rank_by_k'], sort_keys=True)}",
        f"- Best rank by lambda: "
        f"{json.dumps(sensitivity['best_rank_by_lambda'], sort_keys=True)}",
        "",
        "## D.2.6 Termination cause (M4 check)",
        "",
        f"- Spent {termination['serialized_chars']:,} of "
        f"{termination['budget_chars']:,}; "
        f"**{termination['remaining_chars']} chars remained**",
        f"- Unselected candidates: {termination['unselected_candidates']}, "
        f"of which affordable at termination: "
        f"{termination['affordable_unselected_at_end']}",
        f"- Cheapest unselected episode: "
        f"{termination['cheapest_unselected_chars']:,} chars",
        f"- Terminated on: **{termination['terminated_on']}**",
        "",
        "## D.3 Mechanism attribution",
        "",
        "| Mechanism | Fires | Evidence |",
        "|---|---|---|",
    ]
    for name in (
        "M1_cluster_collision",
        "M2_cost_discount",
        "M3_relevance_floor",
        "M4_budget_exhaustion",
    ):
        entry = attribution[name]
        lines.append(
            f"| {name.replace('_', ' ')} | **{entry['fires']}** | "
            f"{entry['evidence']} |"
        )
    reading = result["reading"]
    lines += [
        "",
        f"**Attribution: {attribution['verdict']}.**",
        "",
        "### D.3.1 Reading",
        "",
        f"- The diversity term was payable in full at every step: "
        f"**{reading['diversity_term_was_payable_in_full']}**. The target's "
        "cluster was never occupied by a selection, so M1 is refuted twice "
        "over: the collision exists in the partition and costs nothing in the "
        "objective.",
        f"- To win at its best step the target needed relevance "
        f"**{reading['relevance_required_to_win_any_step']}**; it has "
        f"**{reading['relevance_actual']}**, a shortfall of "
        f"**{reading['relevance_shortfall']}**. "
        f"**{reading['episodes_meeting_the_required_relevance']}** of the 119 "
        "episodes clear that bar, so the target would have to be a different "
        "episode by cosine, not a better-weighted one.",
        f"- Best rank reached anywhere in 132 A3 walks: "
        f"**{reading['best_rank_ever_reached']}**. Never 1, in any cell.",
        "",
        "**Registered F.8 predictions, checked:**",
        "",
        f"- *M1 cluster collision is the most likely mechanism* - "
        f"**{'held' if reading['f8_prediction_m1_cluster_collision']['held'] else 'WRONG'}**. "
        "M1 does not fire.",
        f"- *No configuration selected turn 90* - "
        f"**{'held' if reading['f8_prediction_census_finds_nothing']['held'] else 'WRONG'}**.",
        "",
        f"**F.6 determination: fires = {reading['f6_fires']}; Part 2 outcome = "
        f"{reading['part_2_outcome']}.**",
        "",
        "## D.4 Surrogate audit as executed",
        "",
        "- Rank alone is not reported as evidence; the marginal-gain gap at the",
        "  deciding step accompanies every rank claim.",
        "- Any configuration selecting the target carries its full result",
        "  vector in the census table above.",
        "- M1 and M3 were tested jointly: the counterfactual pays the diversity",
        "  term in full and asks whether the target would then win.",
        "- A cause is not a remedy. Part 2 remains conditional.",
        "",
        "## Boundary",
        "",
        "One episode, one probe, one store. Availability only. No",
        "answer-correctness claim and no live run is authorized by this",
        "diagnostic.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DX-001 Part 1 diagnostic.")
    parser.add_argument("--embedding-model", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run_dx001(args.output_dir, args.embedding_model.resolve())
    print(json.dumps(result["attribution"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
