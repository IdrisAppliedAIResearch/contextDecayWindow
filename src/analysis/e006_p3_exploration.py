from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from episodic import EmbeddingCache
from episodic._render import render_episode_element, render_stm_payload
from src.analysis.e006_chained_retrieval_preflight import (
    content_sha256,
    load_authoritative_packer,
    load_episodes,
)
from src.analysis.e006_p3_reproduction import (
    CAPTURE_CACHE,
    CAPTURE_MANIFEST,
    REPO_ROOT,
)
from src.analysis.e006_p3_tier4a_capture import sha256_file
from src.analysis.e006_rev3_pf11 import load_inputs
from src.retrieval_bakeoff.config import CORPORA
from src.retrieval_bakeoff.corpus import load_queries, load_raw_episodes
from src.retrieval_bakeoff.graph import AssociativeGraphIndex, GraphRetriever
from src.retrieval_bakeoff.models import RankedCandidate
from src.retrieval_bakeoff.serialization import pack_ranked_candidates
from src.retrieval_mechanism_ledger.e006 import retrieve_chained
from src.retrieval_mechanism_ledger.e006_p3 import (
    FrontierSelection,
    UnionKnnGraph,
    assert_mechanism_path_allowed,
    build_union_knn_graph,
    retrieve_associative_frontier,
    retrieve_fixed_query,
)


COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
PROTOCOL = COMPONENT_ROOT / "E006_PART3_S1_ASSOCIATIVE_FRONTIER_EXPLORATION.md"
AUTHORIZATION = COMPONENT_ROOT / "E006_PART3_S1_EXPLORATION_AUTHORIZATION.md"
REV1 = COMPONENT_ROOT / "E006_PART3_REV1_TIER4A_REPRODUCTION_INPUT.md"
REV1_AUTHORIZATION = COMPONENT_ROOT / "E006_PART3_REV1_AUTHORIZATION.md"
REV2 = COMPONENT_ROOT / "E006_PART3_REV2_REPRODUCTION_RUNTIME.md"
REV2_AUTHORIZATION = COMPONENT_ROOT / "E006_PART3_REV2_AUTHORIZATION.md"
REPRODUCTION = COMPONENT_ROOT / "artifacts" / "e006_p3_reproduction_rev2" / "reproduction.json"
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e006_p3.py"
BUDGET_CHARS = 32_000
DEPTHS = (0, 1, 2, 3)
PER_STEP_COUNTS = (3, 5)


def digest_sequence(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("ascii")).hexdigest()


def _connected_components(weights: np.ndarray) -> tuple[tuple[int, ...], ...]:
    remaining = set(range(len(weights)))
    components = []
    while remaining:
        root = min(remaining)
        stack = [root]
        component = set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            neighbors = np.flatnonzero(weights[node] > 0.0)
            stack.extend(int(value) for value in neighbors if int(value) not in component)
        remaining -= component
        components.append(tuple(sorted(component)))
    return tuple(components)


def graph_distribution(
    graph: UnionKnnGraph, source_turns: Sequence[int], gram: np.ndarray
) -> dict[str, Any]:
    degree = np.count_nonzero(graph.weights > 0.0, axis=1)
    components = _connected_components(graph.weights)
    component_for = {
        index: component_id
        for component_id, component in enumerate(components)
        for index in component
    }
    edges = [
        {
            "left_content_sha256": graph.content_hashes[left],
            "right_content_sha256": graph.content_hashes[right],
            "left_source_turn": int(source_turns[left]),
            "right_source_turn": int(source_turns[right]),
            "weight": float(graph.weights[left, right]),
        }
        for left in range(len(graph.weights))
        for right in range(left + 1, len(graph.weights))
        if graph.weights[left, right] > 0.0
    ]
    directed = []
    for source, neighbors in enumerate(graph.directed_neighbors):
        for rank, destination in enumerate(neighbors, start=1):
            directed.append(
                {
                    "source_content_sha256": graph.content_hashes[source],
                    "destination_content_sha256": graph.content_hashes[destination],
                    "rank": rank,
                    "raw_weight": float(gram[source, destination]),
                    "retained_weight": float(graph.weights[source, destination]),
                    "reciprocal": source in graph.directed_neighbors[destination],
                }
            )
    return {
        "policy": "top-8 directed selections, non-negative undirected union",
        "node_count": len(graph.content_hashes),
        "undirected_edge_count": len(edges),
        "isolated_node_count": int(np.sum(degree == 0)),
        "reciprocal_directed_selection_count": sum(row["reciprocal"] for row in directed),
        "directed_selection_count": len(directed),
        "degree_by_node": [
            {
                "content_sha256": graph.content_hashes[index],
                "source_turn": int(source_turns[index]),
                "degree": int(degree[index]),
                "component_id": component_for[index],
            }
            for index in range(len(degree))
        ],
        "component_membership": [
            {
                "component_id": component_id,
                "size": len(component),
                "content_sha256": [graph.content_hashes[index] for index in component],
            }
            for component_id, component in enumerate(components)
        ],
        "retained_edges": edges,
        "directed_neighbor_selections": directed,
    }


def trace_a1(
    query: np.ndarray,
    gram: np.ndarray,
    hashes: Sequence[str],
    depth: int,
    per_step: int,
) -> tuple[dict[str, Any], ...]:
    context_scores = query.copy()
    query_context = 1.0
    seen: set[int] = set()
    rows = []
    for hop in range(depth + 1):
        cue_norm = np.sqrt(0.3**2 + 0.7**2 + 2.0 * 0.3 * 0.7 * query_context)
        scores = (0.3 * query + 0.7 * context_scores) / cue_norm
        order = sorted(
            (index for index in range(len(query)) if index not in seen),
            key=lambda index: (-float(scores[index]), hashes[index]),
        )
        hits = tuple(order[:per_step])
        seen.update(hits)
        hit_array = np.asarray(hits, dtype=np.int64)
        hit_mean_scores = gram[hit_array].mean(axis=0)
        query_hit_mean = float(query[hit_array].mean())
        context_hit_mean = float(context_scores[hit_array].mean())
        hit_mean_norm_squared = float(gram[np.ix_(hit_array, hit_array)].mean())
        context_norm = np.sqrt(
            0.5**2
            + 0.5**2 * hit_mean_norm_squared
            + 2.0 * 0.5 * 0.5 * context_hit_mean
        )
        rows.append(
            {
                "hop": hop,
                "hit_indices": hits,
                "all_scores": tuple(float(value) for value in scores),
                "all_associations": tuple(float(value) for value in context_scores),
            }
        )
        context_scores = (0.5 * context_scores + 0.5 * hit_mean_scores) / context_norm
        query_context = (0.5 * query_context + 0.5 * query_hit_mean) / context_norm
    return tuple(rows)


def _selection_record(
    arm: str,
    selection: FrontierSelection,
    source_turns: Sequence[int],
    content_hashes: Sequence[str],
) -> dict[str, Any]:
    return {
        "arm": arm,
        "D": selection.depth,
        "m": selection.per_step,
        "ranked_seen_indices": list(selection.ranked_seen_indices),
        "ranked_seen_content_sha256": list(selection.ranked_seen_content_sha256),
        "candidate_sha256": digest_sequence(selection.ranked_seen_content_sha256),
        "steps": [
            {
                "hop": step.hop,
                "hit_content_sha256": list(step.hit_content_sha256),
                "hit_source_turns": [int(source_turns[index]) for index in step.hit_indices],
                "hit_scores": list(step.hit_scores),
                "all_scores": list(step.all_scores),
                "all_associations": list(step.all_associations),
                "frontier_neighbor_count": sum(
                    bool(step.predecessor_indices[index])
                    for index in range(len(step.predecessor_indices))
                ),
                "query_only_fallback_count": step.query_only_fallback_count,
                "predecessors": [
                    {
                        "candidate_content_sha256": content_hashes[index],
                        "predecessor_content_sha256": [
                            content_hashes[value] for value in predecessors
                        ],
                    }
                    for index, predecessors in enumerate(step.predecessor_indices)
                    if predecessors
                ],
            }
            for step in selection.steps
        ],
    }


def run_arm_cells() -> tuple[list[dict[str, Any]], Any, UnionKnnGraph]:
    inputs = load_inputs()
    episodes = load_episodes()
    by_id = {str(episode["id"]): episode for episode in episodes}
    source_turns = tuple(int(by_id[value]["turn_number"]) for value in inputs.ids)
    graph = build_union_knn_graph(inputs.gram, inputs.content_hashes, k=8)
    records = []
    for depth in DEPTHS:
        for per_step in PER_STEP_COUNTS:
            a0 = retrieve_fixed_query(
                query_cosines=inputs.query_cosines,
                content_hashes=inputs.content_hashes,
                depth=depth,
                per_step=per_step,
            )
            records.append(
                _selection_record("A0", a0, source_turns, inputs.content_hashes)
            )

            carried = retrieve_chained(
                query_cosines=inputs.query_cosines,
                gram=inputs.gram,
                content_hashes=inputs.content_hashes,
                depth=depth,
                per_step=per_step,
                query_weight=0.3,
                retention=0.5,
            )
            audit_steps = trace_a1(
                inputs.query_cosines,
                inputs.gram,
                inputs.content_hashes,
                depth,
                per_step,
            )
            if tuple(
                tuple(row["hit_indices"]) for row in audit_steps
            ) != tuple(step.hit_indices for step in carried.steps):
                raise AssertionError("A1 exploration trace differs from carried A1")
            records.append(
                {
                    "arm": "A1",
                    "D": depth,
                    "m": per_step,
                    "ranked_seen_indices": list(carried.ranked_seen_indices),
                    "ranked_seen_content_sha256": list(
                        carried.ranked_seen_content_sha256
                    ),
                    "candidate_sha256": digest_sequence(
                        carried.ranked_seen_content_sha256
                    ),
                    "steps": [
                        {
                            "hop": row["hop"],
                            "hit_content_sha256": [
                                inputs.content_hashes[index]
                                for index in row["hit_indices"]
                            ],
                            "hit_source_turns": [
                                int(source_turns[index]) for index in row["hit_indices"]
                            ],
                            "hit_scores": [
                                row["all_scores"][index] for index in row["hit_indices"]
                            ],
                            "all_scores": list(row["all_scores"]),
                            "all_associations": list(row["all_associations"]),
                            "frontier_neighbor_count": 0,
                            "query_only_fallback_count": 0,
                            "predecessors": [],
                        }
                        for row in audit_steps
                    ],
                }
            )

            a2 = retrieve_associative_frontier(
                query_cosines=inputs.query_cosines,
                graph=graph,
                depth=depth,
                per_step=per_step,
            )
            records.append(
                _selection_record("A2", a2, source_turns, inputs.content_hashes)
            )
    if len(records) != 24:
        raise AssertionError("Exploration grid must contain 24 arm cells")
    return records, inputs, graph


def add_packing(records: list[dict[str, Any]], inputs: Any) -> None:
    episodes = load_episodes()
    by_hash = {content_sha256(episode): episode for episode in episodes}
    id_to_hash = {str(episode["id"]): content_sha256(episode) for episode in episodes}
    pack = load_authoritative_packer()
    for record in records:
        candidates = [by_hash[value] for value in record["ranked_seen_content_sha256"]]
        full_payload = render_stm_payload([], candidates)
        individual = [len(render_episode_element(episode)) for episode in candidates]
        packed = pack([], candidates, BUDGET_CHARS)
        selected = [id_to_hash[value] for value in packed.selected_ids]
        skipped = [id_to_hash[value] for value in packed.skipped_k_ids]
        cost_by_hash = dict(zip(record["ranked_seen_content_sha256"], individual, strict=True))
        record.update(
            {
                "candidate_count": len(candidates),
                "candidate_serialized_chars_rank_order": len(full_payload),
                "candidate_individual_episode_chars_sum": sum(individual),
                "selected_content_sha256": selected,
                "selected_episode_count": len(selected),
                "selected_sha256": digest_sequence(selected),
                "payload_sha256": hashlib.sha256(packed.payload.encode("utf-8")).hexdigest(),
                "delivered_chars": packed.serialized_chars,
                "skipped_content_sha256": skipped,
                "skipped_episode_count": len(skipped),
                "skipped_individual_episode_chars": sum(
                    cost_by_hash[value] for value in skipped
                ),
            }
        )


def overlap_distribution(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for depth in DEPTHS:
        for per_step in PER_STEP_COUNTS:
            cells = {
                row["arm"]: row
                for row in records
                if row["D"] == depth and row["m"] == per_step
            }
            for left, right in (("A0", "A1"), ("A0", "A2"), ("A1", "A2")):
                candidate_overlap = set(cells[left]["ranked_seen_content_sha256"]) & set(
                    cells[right]["ranked_seen_content_sha256"]
                )
                packed_overlap = set(cells[left]["selected_content_sha256"]) & set(
                    cells[right]["selected_content_sha256"]
                )
                rows.append(
                    {
                        "D": depth,
                        "m": per_step,
                        "left": left,
                        "right": right,
                        "candidate_overlap_count": len(candidate_overlap),
                        "packed_overlap_count": len(packed_overlap),
                        "candidate_overlap_sha256": digest_sequence(sorted(candidate_overlap)),
                        "packed_overlap_sha256": digest_sequence(sorted(packed_overlap)),
                    }
                )
    return rows


def degenerate_traces() -> dict[str, Any]:
    hashes = tuple(f"{index:064x}" for index in range(6))
    query = np.asarray([0.9, 0.8, 0.7, 0.6, 0.5, 0.4])
    empty = build_union_knn_graph(np.eye(6), hashes, k=1)
    fallback = retrieve_associative_frontier(
        query_cosines=query, graph=empty, depth=1, per_step=2
    )
    negative = np.full((6, 6), -0.5)
    np.fill_diagonal(negative, 1.0)
    negative_graph = build_union_knn_graph(negative, hashes, k=1)
    cycle_weights = np.zeros((6, 6))
    for left, right in ((0, 1), (1, 2), (2, 3), (3, 0)):
        cycle_weights[left, right] = cycle_weights[right, left] = 0.9
    cycle_graph = UnionKnnGraph(
        k=2,
        weights=cycle_weights,
        directed_neighbors=((1, 3), (0, 2), (1, 3), (0, 2), (0, 1), (0, 1)),
        content_hashes=hashes,
    )
    cycle = retrieve_associative_frontier(
        query_cosines=query, graph=cycle_graph, depth=2, per_step=2
    )
    constant = retrieve_associative_frontier(
        query_cosines=np.ones(6), graph=empty, depth=1, per_step=2
    )
    exhausted = None
    try:
        retrieve_associative_frontier(
            query_cosines=query, graph=empty, depth=3, per_step=2
        )
    except ValueError as error:
        exhausted = str(error)
    return {
        "empty_frontier_adjacency": {
            "all_associations_zero": all(
                value == 0.0 for value in fallback.steps[1].all_associations
            ),
            "selected_by_query_fallback": list(fallback.steps[1].hit_indices),
        },
        "all_zero_association": {
            "retained_edge_count": int(np.count_nonzero(empty.weights) // 2)
        },
        "all_negative_association": {
            "retained_edge_count": int(np.count_nonzero(negative_graph.weights) // 2)
        },
        "repeated_frontier": {
            "frontiers": [list(step.hit_indices) for step in cycle.steps],
            "all_disjoint": len({index for step in cycle.steps for index in step.hit_indices})
            == 6,
        },
        "graph_cycle": {
            "cycle_edges": [[0, 1], [1, 2], [2, 3], [3, 0]],
            "frontiers": [list(step.hit_indices) for step in cycle.steps],
        },
        "query_only_fallback": {
            "frontiers": [list(step.hit_indices) for step in fallback.steps]
        },
        "constant_ranking": {
            "frontiers": [list(step.hit_indices) for step in constant.steps],
            "tie_break": "ascending content SHA-256 after equal score and Q",
        },
        "exhausted_unseen_candidates": {"rejected_before_run": exhausted},
    }


def tier4_non_identity() -> dict[str, Any]:
    capture = json.loads(CAPTURE_MANIFEST.read_text(encoding="utf-8"))
    spec = CORPORA["c121_l"]
    candidates = load_raw_episodes(spec)
    graph_index = AssociativeGraphIndex(spec, candidates)
    query = load_queries(spec)[0]
    with EmbeddingCache(
        CAPTURE_CACHE,
        mode="reuse",
        expected_file_sha256=capture["cache"]["file_sha256"],
        expected_content_sha256=capture["cache"]["content_sha256"],
        expected_model_sha256=capture["execution"]["model_sha256"],
    ) as cache:
        query_vector = cache(query.text)
    query_cosines = graph_index.matrix @ query_vector
    gram = graph_index.matrix @ graph_index.matrix.T
    hashes = tuple(
        hashlib.sha256(
            json.dumps(
                {
                    "turn": item.turn_number,
                    "user": item.user_message,
                    "assistant": item.assistant_message,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        for item in graph_index.candidates
    )
    frontier_graph = build_union_knn_graph(gram, hashes, k=8)
    frontier = retrieve_associative_frontier(
        query_cosines=query_cosines,
        graph=frontier_graph,
        depth=2,
        per_step=5,
    )
    ppr_ranked = GraphRetriever(graph_index, embedder=None)._rank(
        graph_index.transition_for("E3"), 2, query_vector
    )
    frontier_scores = frontier.steps[-1].all_scores
    frontier_ranked = [
        RankedCandidate(
            candidate=graph_index.candidates[index],
            score=float(frontier_scores[index]),
            component_scores={"frontier": float(frontier_scores[index])},
        )
        for index in frontier.ranked_seen_indices
    ]
    ppr_payload = pack_ranked_candidates(
        "identity", [(item, "fill") for item in ppr_ranked], BUDGET_CHARS
    )
    frontier_payload = pack_ranked_candidates(
        "identity", [(item, "fill") for item in frontier_ranked], BUDGET_CHARS
    )
    ppr_ids = [item.candidate.candidate_id for item in ppr_ranked]
    frontier_ids = [item.candidate.candidate_id for item in frontier_ranked]
    return {
        "corpus_id": spec.corpus_id,
        "query_id": query.query_id,
        "shared_graph_policy": "exact-cosine top-8 non-negative undirected union",
        "tier4_recurrence": "activation <- 0.15*seed + 0.85*P^T*activation",
        "a2_recurrence": "frontier <- top_m(0.3*Q + 0.7*max_previous_frontier_edge)",
        "tier4_full_ranking_sha256": digest_sequence(ppr_ids),
        "a2_candidate_ranking_sha256": digest_sequence(frontier_ids),
        "ranking_identical": ppr_ids[: len(frontier_ids)] == frontier_ids,
        "tier4_payload_sha256": hashlib.sha256(
            ppr_payload.rendered_block.encode("utf-8")
        ).hexdigest(),
        "a2_payload_sha256": hashlib.sha256(
            frontier_payload.rendered_block.encode("utf-8")
        ).hexdigest(),
        "payload_identical": ppr_payload.rendered_block
        == frontier_payload.rendered_block,
        "tier4_ranked_count": len(ppr_ids),
        "a2_candidate_count": len(frontier_ids),
    }


def mechanism_seal() -> dict[str, Any]:
    source = MECHANISM_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("q_" + "facts_key", "rub" + "ric", "domain_labels")
    found = [value for value in forbidden if value in source]
    planted_rejected = False
    try:
        assert_mechanism_path_allowed("planted/q_" + "facts_key.md")
    except ValueError:
        planted_rejected = True
    return {
        "status": "PASS" if not found and planted_rejected else "FAIL",
        "source_sha256": sha256_file(MECHANISM_SOURCE),
        "imports": imports,
        "forbidden_tokens_found": found,
        "path_interface": "none; mechanism accepts arrays and canonical hashes only",
        "planted_measurement_path_rejected": planted_rejected,
    }


def git_ordering() -> dict[str, Any]:
    anchors = (
        "12f5a3f2",
        "ff8963a6",
        "0ee600f2",
        "b56af453",
        "efab6605",
        "1a2702ee",
        "e966f7df",
        "230a2cd7",
        "086e5d94",
        "680ce6aa",
        "dd9bb245",
    )
    full = []
    for anchor in anchors:
        value = subprocess.check_output(
            ("git", "rev-parse", anchor), cwd=REPO_ROOT, text=True
        ).strip()
        full.append(value)
    for left, right in zip(full, full[1:]):
        subprocess.run(
            ("git", "merge-base", "--is-ancestor", left, right),
            cwd=REPO_ROOT,
            check=True,
        )
    head = subprocess.check_output(
        ("git", "rev-parse", "HEAD"), cwd=REPO_ROOT, text=True
    ).strip()
    subprocess.run(
        ("git", "merge-base", "--is-ancestor", full[-1], head),
        cwd=REPO_ROOT,
        check=True,
    )
    return {
        "status": "PASS",
        "ordered_commits": full,
        "head_at_exploration_execution": head,
    }


def input_inventory(inputs: Any) -> list[dict[str, Any]]:
    paths = (
        PROTOCOL,
        AUTHORIZATION,
        REV1,
        REV1_AUTHORIZATION,
        REV2,
        REV2_AUTHORIZATION,
        REPRODUCTION,
        CAPTURE_MANIFEST,
        CAPTURE_CACHE,
        MECHANISM_SOURCE,
        Path(__file__),
    )
    rows = [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]
    rows.append(
        {
            "logical_input": "Q11 query cosines and episode Gram matrix",
            "candidate_count": len(inputs.ids),
            "gram_shape": list(inputs.gram.shape),
            "content_hash_count": len(inputs.content_hashes),
            "unique_content_hash_count": len(set(inputs.content_hashes)),
        }
    )
    return rows


def build_exploration() -> dict[str, Any]:
    reproduction = json.loads(REPRODUCTION.read_text(encoding="utf-8"))
    if reproduction["status"] != "PASS":
        raise AssertionError("A2 exploration cannot run before reproduction passes")
    records, inputs, graph = run_arm_cells()
    add_packing(records, inputs)
    graph_stats = graph_distribution(
        graph,
        [
            int({str(row["id"]): row for row in load_episodes()}[episode_id]["turn_number"])
            for episode_id in inputs.ids
        ],
        inputs.gram,
    )
    non_identity = tier4_non_identity()
    seal = mechanism_seal()
    status = (
        "PASS"
        if seal["status"] == "PASS"
        and not non_identity["ranking_identical"]
        and not non_identity["payload_identical"]
        and all(row["candidate_count"] == row["m"] * (row["D"] + 1) for row in records)
        else "FAIL"
    )
    return {
        "study": "E006-P3",
        "stage": "Preflight Part 1 label-blind exploration",
        "status": status,
        "decision": "CONTINUE_TO_FINAL_DESIGN_REVIEW" if status == "PASS" else "STOP",
        "zero_model_generation_calls": True,
        "zero_additional_embedding_calls": True,
        "outcome_labels_opened": False,
        "behavioral_identity": {
            "A0": "Each inclusive hop admits the next m unseen episodes under fixed Q; final cumulative ranking is Q.",
            "A1": "Each inclusive hop admits m unseen episodes under the normalized Q/global-context cue and updates that context with the hit mean.",
            "A2": "Hop zero seeds from Q; each later hop admits m unseen episodes by 0.3*Q plus 0.7*the strongest edge from only the immediately prior frontier.",
            "graph": "A non-negative undirected union of each node's top-8 exact-cosine directed selections.",
            "frontier": "Only the immediately previous hop supplies association scores; seen identities are excluded monotonically.",
            "candidate_quota": "Every arm admits exactly m*(D+1) unique candidates before packing.",
            "final_ranking": "A0 uses Q, A1 uses its final cue, and A2 uses the score that selected its final frontier.",
            "packer": "The authoritative compact-XML packer considers native arm rank order, skips overflow episodes, and continues under 32,000 characters.",
        },
        "input_inventory": input_inventory(inputs),
        "git_ordering": git_ordering(),
        "mechanism_seal": seal,
        "graph_distribution": graph_stats,
        "arm_cells": records,
        "pairwise_overlap": overlap_distribution(records),
        "degenerate_traces": degenerate_traces(),
        "tier4a_non_identity": non_identity,
        "a1_reproduction": reproduction["a1_reproduction"],
        "scope_limit": (
            "One offline Q11 depth trace can detect local frontier, fallback, and "
            "packing behavior; it cannot detect cross-turn persistence, targeted "
            "regression, live answer correctness, or inference variance."
        ),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006-P3 label-blind exploration")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = build_exploration()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": result["status"], "decision": result["decision"]}))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
