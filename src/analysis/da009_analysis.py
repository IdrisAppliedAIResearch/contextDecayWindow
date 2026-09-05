"""Frozen benefit allocation over DA-009 role-pattern rendering."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da003_edge_features import write_rows
from analysis.da004_pack_analysis import fast_auc
from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import BUDGET, _member_maps
from analysis.da008_analysis import allocate_links, grouped_benefit_scores
from analysis.da008_compact_direct import compact_pairs
from analysis.da009_role_pattern import DA009Error, RolePatternContext, append_role_pair, role_pattern_pairs
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

DA009_BLIND_SHA256 = "0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb"
DA004_BLIND_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
DA004_LABEL_SHA256 = "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca"


def allocate_role_links(
    direct_context: RolePatternContext,
    direct_ids: Sequence[str],
    ordered_edges: Sequence[Mapping[str, Any]],
    members: Mapping[str, Sequence[Mapping[str, str]]],
    budget: int = BUDGET,
) -> dict[str, Any]:
    context = direct_context
    selected = set(direct_ids)
    linked: list[str] = []
    costs: list[int] = []
    positions: list[int] = []
    overflow_skips = duplicate_skips = 0
    for position, edge in enumerate(ordered_edges, 1):
        neighbor = str(edge["neighbor_id"])
        if neighbor in selected:
            duplicate_skips += 1
            continue
        updated = append_role_pair(context, members[neighbor])
        cost = updated.chars - context.chars
        if updated.chars > budget:
            overflow_skips += 1
            continue
        context = updated
        selected.add(neighbor)
        linked.append(neighbor)
        costs.append(cost)
        positions.append(position)
    return {"linked_ids": linked, "linked_costs": costs, "linked_positions": positions,
            "link_chars": sum(costs), "total_chars": context.chars, "unused_slack": budget - context.chars,
            "overflow_skips": overflow_skips, "duplicate_skips": duplicate_skips}


def _key(row: Mapping[str, Any]) -> tuple[str, int]:
    return row["comparison_key"], int(row["duplicate_ordinal"])


def _edge_key(row: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return (*_key(row), row["seed_id"], row["neighbor_id"])


def _tie(row: Mapping[str, Any]) -> tuple[float, int, str]:
    feature = row["features"]
    return float(feature["seed_rank"]), 0 if float(feature["signed_direction"]) < 0 else 1, str(row["neighbor_id"])


def _distribution(values: Sequence[int | float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def _sign_p(left: int, right: int) -> float:
    total = left + right
    if not total:
        return 1.0
    tail = sum(math.comb(total, index) for index in range(min(left, right) + 1)) / 2 ** total
    return min(1.0, 2 * tail)


def run_analysis(dataset_path: Path, role_path: Path, preflight_path: Path, perturbation_path: Path,
                 labels_path: Path, g6_path: Path, output_dir: Path) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(role_path) != DA009_BLIND_SHA256:
        raise DA009Error("DA-009 committed blind seal is absent or drifted")
    if sha256_file(perturbation_path) != DA004_BLIND_SHA256 or sha256_file(labels_path) != DA004_LABEL_SHA256:
        raise DA009Error("DA-004 sealed inputs differ")
    labels = {_edge_key(row): row for row in read_gzip(labels_path)}
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"])
               for row in json.loads(g6_path.read_text(encoding="utf-8"))["rows"]}
    edges = []
    for row in read_gzip(perturbation_path):
        if not primary[_key(row)]:
            continue
        label = labels.get(_edge_key(row))
        if label is None:
            raise DA009Error("DA-009 label join is incomplete")
        edges.append({**row, "benefit": bool(label["benefit"]), "harm": bool(label["harm"])})
    counts = Counter("BENEFIT" if row["benefit"] else "HARM" if row["harm"] else "NEUTRAL" for row in edges)
    if len(edges) != 25_941 or counts != Counter({"BENEFIT": 57, "HARM": 40, "NEUTRAL": 25_844}):
        raise DA009Error("DA-009 DA-004 population differs")
    predictions = grouped_benefit_scores(edges)
    if abs(fast_auc(predictions, [int(row["benefit"]) for row in edges]) - 0.823401708567509) > 1e-15:
        raise DA009Error("DA-009 grouped benefit score replay differs")
    for row, score in zip(edges, predictions, strict=True):
        row["benefit_score"] = float(score)

    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    role_rows = {_key(row): row for row in read_gzip(role_path)}
    evidence: dict[tuple[str, int], set[str]] = {}
    dialogues: dict[str, set[str]] = {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            dialogues[source.candidate.identity] = set(source.dialogue_ids)
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = set(question.resolved_dialogue_ids)
    by_question: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        by_question[_key(edge)].append(edge)

    rows = []
    direct_total = da008_total = da009_total = oracle_total = 0
    for key in sorted(by_question):
        role_row = role_rows[key]
        direct_ids = role_row["direct_ids"]
        direct_set = set(direct_ids)
        direct_dialogues = set().union(*(dialogues[identity] for identity in direct_ids))
        direct_complete = evidence[key] <= direct_dialogues
        direct_total += direct_complete
        eligible = [edge for edge in by_question[key] if edge["neighbor_id"] not in direct_set]
        ordered = sorted(eligible, key=lambda edge: (-edge["benefit_score"], *_tie(edge)))
        all_dialogues = set().union(*(dialogues[edge["neighbor_id"]] for edge in eligible)) if eligible else set()
        oracle_total += evidence[key] <= direct_dialogues | all_dialogues
        da008 = allocate_links(compact_pairs([members[identity] for identity in direct_ids]), direct_ids, ordered, members)
        da009 = allocate_role_links(role_pattern_pairs([members[identity] for identity in direct_ids]), direct_ids, ordered, members)
        arm_rows = {}
        for name, allocation in (("DA008", da008), ("DA009", da009)):
            linked_dialogues = set().union(*(dialogues[identity] for identity in allocation["linked_ids"])) if allocation["linked_ids"] else set()
            complete = evidence[key] <= direct_dialogues | linked_dialogues
            gain, loss = complete and not direct_complete, direct_complete and not complete
            missing = evidence[key] - direct_dialogues
            if loss or (gain and not missing <= linked_dialogues):
                raise DA009Error("DA-009 direct protection or gain accounting failed")
            depth = None
            if gain:
                carriers = {identity for identity in allocation["linked_ids"] if missing & dialogues[identity]}
                depth = max(position for identity, position in zip(allocation["linked_ids"], allocation["linked_positions"], strict=True) if identity in carriers)
            arm_rows[name] = {**allocation, "complete": complete, "gain": gain, "loss": loss, "gain_depth": depth}
        da008_total += arm_rows["DA008"]["complete"]
        da009_total += arm_rows["DA009"]["complete"]
        rows.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": role_row["sample_id"],
                     "source_index": role_row["source_index"], "direct_complete": direct_complete, "arms": arm_rows})
    if len(rows) != 1_098 or direct_total != 935 or da008_total != 961:
        raise DA009Error("DA-009 direct or DA-008 reproduction differs")

    matrix = {}
    for arm in ("DA008", "DA009"):
        selected = [row["arms"][arm] for row in rows]
        by_conversation = {}
        for sample_id in sorted({row["sample_id"] for row in rows}):
            cells = [row["arms"][arm] for row in rows if row["sample_id"] == sample_id]
            by_conversation[sample_id] = {"complete": sum(cell["complete"] for cell in cells),
                                          "gains": sum(cell["gain"] for cell in cells), "losses": sum(cell["loss"] for cell in cells)}
        matrix[arm] = {"complete": sum(cell["complete"] for cell in selected), "gains": sum(cell["gain"] for cell in selected),
                       "losses": sum(cell["loss"] for cell in selected), "links_admitted": sum(len(cell["linked_ids"]) for cell in selected),
                       "overflow_skips": sum(cell["overflow_skips"] for cell in selected), "by_conversation": by_conversation,
                       "distributions": {field: _distribution([cell[field] for cell in selected]) for field in ("link_chars", "total_chars", "unused_slack")},
                       "gain_depth": _distribution([cell["gain_depth"] for cell in selected if cell["gain_depth"] is not None])}
    da009_only = sum(row["arms"]["DA009"]["complete"] and not row["arms"]["DA008"]["complete"] for row in rows)
    da008_only = sum(row["arms"]["DA008"]["complete"] and not row["arms"]["DA009"]["complete"] for row in rows)
    no_conversation_regression = all(matrix["DA009"]["by_conversation"][group]["complete"] >= cell["complete"]
                                     for group, cell in matrix["DA008"]["by_conversation"].items())
    signal = da009_total > 961 and not matrix["DA009"]["losses"] and no_conversation_regression
    result = {"schema": "da009-role-pattern-result-v1", "status": "INCREMENTAL_COMPACT_SIGNAL" if signal else "NO_INCREMENTAL_COMPACT_SIGNAL",
              "population": {"questions": len(rows), "edges": len(edges), "direct_complete": direct_total,
                             "one_hop_oracle_complete": oracle_total}, "matrix": matrix,
              "incremental_discordance": {"da009_only_complete": da009_only, "da008_only_complete": da008_only,
                                            "exact_two_sided_p": _sign_p(da009_only, da008_only)},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent-corpus availability diagnostic; no reader, transfer, or adoption"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_rows(output_dir / "allocations.jsonl.gz", rows)
    return result


__all__ = ["allocate_role_links", "run_analysis"]

