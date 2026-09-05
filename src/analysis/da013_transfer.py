"""Transferred DA-004 scoring and frozen blind allocations for DA-013."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da003_edge_features import tokens, weighted_coverage
from analysis.da004_pack_features import FEATURES, perturbation_features, read_gzip
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da010_payloads import member_order, payload_costs
from analysis.da013_preflight import (
    BUDGET,
    BlindQuestion,
    ReadOnlyCache,
    _idf,
    load_blind_population,
    sha256_file,
)
from analysis.nf004_anatomy_analysis import _predict
from analysis.nf005_mechanism import own_score_order, pack

DIRECT_SHA256 = "9544fd5bc6ad85515f5cb99472cb844e2c8b9f97cd1f51a19de2d882da47ff5c"
DA004_BLIND_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
DA004_LABEL_SHA256 = "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca"


class DA013TransferError(RuntimeError):
    pass


def _training(blind_path: Path, label_path: Path) -> tuple[np.ndarray, np.ndarray]:
    if sha256_file(blind_path) != DA004_BLIND_SHA256 or sha256_file(label_path) != DA004_LABEL_SHA256:
        raise DA013TransferError("DA-004 training artifacts differ")
    blind = {
        (row["comparison_key"], int(row["duplicate_ordinal"]), row["seed_id"], row["neighbor_id"]): row
        for row in read_gzip(blind_path)
    }
    labels = read_gzip(label_path)
    rows = []
    target = []
    for label in labels:
        key = (label["comparison_key"], int(label["duplicate_ordinal"]), label["seed_id"], label["neighbor_id"])
        if key not in blind:
            raise DA013TransferError("DA-004 feature/label join is incomplete")
        rows.append([float(blind[key]["features"][name]) for name in FEATURES])
        target.append(int(label["benefit"]))
    if len(rows) != 25_941 or sum(target) != 57:
        raise DA013TransferError("DA-004 training population differs")
    return np.asarray(rows), np.asarray(target)


def _edge_features(
    record: BlindQuestion,
    edge: Mapping[str, Any],
    direct_ids: Sequence[str],
    compact_chars: int,
    scores: np.ndarray,
    vectors: np.ndarray,
    rank: Mapping[str, int],
    by_id: Mapping[str, Any],
    idf: Mapping[str, float],
) -> dict[str, float | int]:
    seed, neighbor = by_id[edge["seed_id"]], by_id[edge["neighbor_id"]]
    seed_index = seed.candidate.parent_index
    neighbor_index = neighbor.candidate.parent_index
    query = tokens(record.question)
    seed_tokens, neighbor_tokens = tokens(seed.candidate.text), tokens(neighbor.candidate.text)
    numeric = {token for token in query if token.isdigit()}
    years = {token for token in numeric if len(token) == 4}
    normalized = vectors / np.linalg.norm(vectors, axis=1)[:, None]
    seed_score, neighbor_score = float(scores[seed_index]), float(scores[neighbor_index])
    seed_neighbor = float(normalized[seed_index] @ normalized[neighbor_index])
    direct_pairs = [by_id[value].members for value in direct_ids]
    context = role_pattern_pairs(direct_pairs)
    order, _ = member_order(record.question, neighbor.members, idf)
    full_cost, turn_costs = payload_costs(context, neighbor.members)
    action_id = None
    action_text = None
    action_chars = 0
    if full_cost <= BUDGET - compact_chars:
        action_id, action_text, action_chars = neighbor.candidate.identity, neighbor.candidate.text, full_cost
    elif turn_costs[order[0]] <= BUDGET - compact_chars:
        action_id = f"{neighbor.candidate.identity}:member:{order[0]}"
        member = neighbor.members[order[0]]
        action_text = f"{member['speaker']}: {member['text']}"
        action_chars = turn_costs[order[0]]
    direct = list(direct_ids)
    treatment = direct + ([action_id] if action_id else [])
    candidate_rows = {
        value: {"chars": by_id[value].candidate.chars, "direct_score": float(scores[by_id[value].candidate.parent_index])}
        for value in direct
    }
    texts = {value: by_id[value].candidate.text for value in direct}
    candidate_rows[neighbor.candidate.identity] = {"chars": neighbor.candidate.chars, "direct_score": neighbor_score}
    texts[neighbor.candidate.identity] = neighbor.candidate.text
    if action_id and action_id != neighbor.candidate.identity:
        candidate_rows[action_id] = {"chars": action_chars, "direct_score": neighbor_score}
        texts[action_id] = str(action_text)
    base = {
        "seed_query_coverage": weighted_coverage(query, seed_tokens, idf),
        "neighbor_query_coverage": weighted_coverage(query, neighbor_tokens, idf),
        "union_query_coverage": weighted_coverage(query, seed_tokens | neighbor_tokens, idf),
        "neighbor_only_query_coverage": weighted_coverage(query, neighbor_tokens - seed_tokens, idf),
        "seed_only_query_coverage": weighted_coverage(query, seed_tokens - neighbor_tokens, idf),
        "seed_query_matches": len(query & seed_tokens), "neighbor_query_matches": len(query & neighbor_tokens),
        "neighbor_only_query_matches": len(query & (neighbor_tokens - seed_tokens)),
        "seed_numeric_matches": len(numeric & seed_tokens), "neighbor_numeric_matches": len(numeric & neighbor_tokens),
        "seed_year_matches": len(years & seed_tokens), "neighbor_year_matches": len(years & neighbor_tokens),
        "seed_query_cosine": seed_score, "neighbor_query_cosine": neighbor_score,
        "neighbor_minus_seed_cosine": neighbor_score - seed_score, "max_query_cosine": max(seed_score, neighbor_score),
        "seed_neighbor_cosine": seed_neighbor, "residual_semantic_score": neighbor_score - seed_neighbor * seed_score,
        "neighbor_chars": neighbor.candidate.chars, "seed_chars": seed.candidate.chars,
        "direct_slack": BUDGET - compact_chars, "counterfactual_packed_chars": compact_chars + action_chars,
        "displaced_count": 0, "displaced_chars": 0, "displaced_score_sum": 0.0, "displaced_score_max": 0.0,
        "displaced_score_min": 0.0, "displaced_score_mean": 0.0,
        "neighbor_minus_displaced_max": neighbor_score, "neighbor_minus_displaced_mean": neighbor_score,
        "neighbor_already_direct": 0, "seed_rank": int(edge["seed_rank"]),
        "neighbor_direct_rank": int(rank[neighbor.candidate.identity]), "signed_direction": int(edge["direction"]),
        "rank_gap": int(rank[neighbor.candidate.identity]) - int(edge["seed_rank"]),
    }
    packed = {
        "features": base, "direct_selected_ids": direct, "counterfactual_selected_ids": treatment,
        "displaced_ids": [], "neighbor_id": neighbor.candidate.identity,
    }
    return perturbation_features(packed, candidate_rows, texts, record.question, idf)


def _allocate(record: BlindQuestion, row: Mapping[str, Any], edges: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {episode.candidate.identity: episode for episode in record.episodes}
    context = role_pattern_pairs([by_id[value].members for value in row["direct_ids"]])
    actions = []
    for edge in edges:
        neighbor = by_id[edge["neighbor_id"]]
        member_ordering, _ = member_order(record.question, neighbor.members, row["idf"])
        full_cost, turn_costs = payload_costs(context, neighbor.members)
        if context.chars + full_cost <= BUDGET:
            context = append_role_pair(context, neighbor.members)
            actions.append({"neighbor_id": edge["neighbor_id"], "kind": "PAIR", "member": None, "cost": full_cost})
        elif context.chars + turn_costs[member_ordering[0]] <= BUDGET:
            member = member_ordering[0]
            context = append_role_pair(context, [neighbor.members[member]])
            actions.append({"neighbor_id": edge["neighbor_id"], "kind": "TURN", "member": member, "cost": turn_costs[member]})
        else:
            actions.append({"neighbor_id": edge["neighbor_id"], "kind": "SKIP", "member": None, "cost": 0})
    return {"chars": context.chars, "actions": actions}


def build_transfer(
    records: Sequence[BlindQuestion], direct_rows: Sequence[Mapping[str, Any]], cache_path: Path,
    train_x: np.ndarray, train_y: np.ndarray,
) -> list[dict[str, Any]]:
    direct = {row["question_id"]: row for row in direct_rows}
    idf = _idf(records)
    cache = ReadOnlyCache(cache_path)
    staged = []
    features = []
    try:
        for record in records:
            row = direct[record.question_id]
            candidates = tuple(episode.candidate for episode in record.episodes)
            query_vector = cache.vector(record.question)
            vectors = np.vstack([cache.vector(candidate.text) for candidate in candidates])
            normalized = vectors / np.linalg.norm(vectors, axis=1)[:, None]
            query = query_vector / np.linalg.norm(query_vector)
            scores = normalized @ query
            order = own_score_order(candidates, vectors, query_vector)
            packed = pack(candidates, order, BUDGET)
            if list(packed.selected) != row["direct_ids"]:
                raise DA013TransferError("Direct identity replay differs")
            rank = {candidates[index].identity: position for position, index in enumerate(order, 1)}
            by_id = {episode.candidate.identity: episode for episode in record.episodes}
            edge_rows = []
            for edge in row["edges"]:
                vector = _edge_features(record, edge, row["direct_ids"], int(row["compact_chars"]), scores, vectors, rank, by_id, idf)
                features.append([float(vector[name]) for name in FEATURES])
                edge_rows.append({**edge, "feature_index": len(features) - 1})
            staged.append((record, row, edge_rows))
    finally:
        cache.close()
    predictions = _predict(train_x, train_y, np.asarray(features), 1.0)
    output = []
    for record, row, edges in staged:
        scored = []
        for edge in edges:
            feature_index = int(edge["feature_index"])
            scored.append(
                {
                    **{key: value for key, value in edge.items() if key != "feature_index"},
                    "benefit_score": float(predictions[feature_index]),
                }
            )
        temporal = sorted(scored, key=lambda edge: (edge["seed_rank"], edge["direction"] > 0, edge["neighbor_id"]))
        benefit = sorted(scored, key=lambda edge: (-edge["benefit_score"], edge["seed_rank"], edge["direction"] > 0, edge["neighbor_id"]))
        allocation_row = {**row, "idf": idf}
        output.append({
            "question_id": record.question_id, "question_type": record.question_type,
            "direct_ids": row["direct_ids"], "compact_chars": row["compact_chars"],
            "edges": scored, "TEMPORAL_ORDER": _allocate(record, allocation_row, temporal),
            "TRANSFER_BENEFIT": _allocate(record, allocation_row, benefit),
        })
    return output


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_transfer_preflight(
    dataset_path: Path,
    population_path: Path,
    cache_path: Path,
    direct_path: Path,
    da004_blind_path: Path,
    da004_label_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if sha256_file(direct_path) != DIRECT_SHA256:
        raise DA013TransferError("DA-013 direct seal differs")
    records = load_blind_population(dataset_path, population_path)
    direct_rows = read_gzip(direct_path)
    train_x, train_y = _training(da004_blind_path, da004_label_path)
    rows = build_transfer(records, direct_rows, cache_path, train_x, train_y)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_transfer_allocations.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da013-transfer-") as directory:
        replay = build_transfer(records, direct_rows, cache_path, train_x, train_y)
        replay_path = Path(directory) / path.name
        write_rows(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    scores = [float(edge["benefit_score"]) for row in rows for edge in row["edges"]]
    actions = {
        arm: {
            kind: sum(action["kind"] == kind for row in rows for action in row[arm]["actions"])
            for kind in ("PAIR", "TURN", "SKIP")
        }
        for arm in ("TEMPORAL_ORDER", "TRANSFER_BENEFIT")
    }
    passed = (
        identical
        and len(rows) == 465
        and sum(len(row["edges"]) for row in rows) == 7_401
        and len(FEATURES) == 73
        and len(set(scores)) > 1
        and all(actions[arm]["PAIR"] and actions[arm]["TURN"] and actions[arm]["SKIP"] for arm in actions)
    )
    result = {
        "schema": "da013-blind-transfer-preflight-v1",
        "status": "PASS" if passed else "FAIL",
        "population": {"questions": len(rows), "edges": sum(len(row["edges"]) for row in rows)},
        "training": {"edges": len(train_y), "benefits": int(train_y.sum()), "features": len(FEATURES), "penalty": 1.0},
        "scores": {"min": min(scores), "p50": float(np.median(scores)), "max": max(scores), "unique": len(set(scores))},
        "actions": actions,
        "allocation_sha256": sha256_file(path),
        "replay_byte_identical": identical,
        "calls": {"embedding": 0, "model": 0, "cache_misses": 0, "cache_mode": "read-only"},
    }
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA013TransferError("DA-013 transfer preflight failed")
    return result


__all__ = ["DA013TransferError", "_training", "build_transfer", "run_transfer_preflight", "write_rows"]
