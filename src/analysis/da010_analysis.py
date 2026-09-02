"""Evidence analysis for DA-010 linked payload granularity."""

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
from analysis.da008_analysis import grouped_benefit_scores
from analysis.da009_analysis import allocate_role_links
from analysis.da009_role_pattern import RolePatternContext, append_role_pair, role_pattern_pairs
from analysis.da010_payloads import DA010Error
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

DA010_BLIND_SHA256 = "51e0e648f66bf2c5a7ab6161c5fbcbc9efaadff306beb9b98ffac6a2f19d47b3"
DA004_BLIND_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
DA004_LABEL_SHA256 = "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca"
ARMS = ("FULL_PAIR", "BEST_TURN", "ATOMIC_TURNS", "PAIR_THEN_TURN")


def allocate_turn_payloads(context: RolePatternContext, direct_ids: Sequence[str], ordered_edges: Sequence[Mapping[str, Any]],
                           members: Mapping[str, Sequence[Mapping[str, str]]], payloads: Mapping[tuple[str, int, str, str], Mapping[str, Any]],
                           mode: str, budget: int = BUDGET) -> dict[str, Any]:
    if mode not in {"BEST_TURN", "ATOMIC_TURNS", "PAIR_THEN_TURN"}:
        raise DA010Error("Unknown DA-010 allocation mode")
    base_chars = context.chars
    direct = set(direct_ids)
    seen_pairs: set[str] = set()
    linked_pairs: list[str] = []
    linked_dialogues: list[str] = []
    positions: dict[str, int] = {}
    pair_admissions = member_admissions = fallback_admissions = 0
    pair_overflows = member_overflows = duplicate_skips = 0
    for position, edge in enumerate(ordered_edges, 1):
        neighbor = str(edge["neighbor_id"])
        if neighbor in direct or neighbor in seen_pairs:
            duplicate_skips += 1
            continue
        seen_pairs.add(neighbor)
        key = (edge["comparison_key"], int(edge["duplicate_ordinal"]), edge["seed_id"], neighbor)
        payload = payloads[key]
        pair_members = members[neighbor]
        if mode == "PAIR_THEN_TURN":
            updated = append_role_pair(context, pair_members)
            if updated.chars <= budget:
                context = updated
                linked_pairs.append(neighbor)
                pair_admissions += 1
                for member in pair_members:
                    dialogue_id = str(member["dialogue_id"])
                    linked_dialogues.append(dialogue_id)
                    positions[dialogue_id] = position
                continue
            pair_overflows += 1
            indices = [int(payload["selected_member_index"])]
        elif mode == "BEST_TURN":
            indices = [int(payload["selected_member_index"])]
        else:
            indices = [int(index) for index in payload["member_order"]]
        admitted_here = False
        for index in indices:
            member = pair_members[index]
            dialogue_id = str(member["dialogue_id"])
            if dialogue_id in positions:
                duplicate_skips += 1
                continue
            updated = append_role_pair(context, [member])
            if updated.chars > budget:
                member_overflows += 1
                continue
            context = updated
            linked_dialogues.append(dialogue_id)
            positions[dialogue_id] = position
            member_admissions += 1
            admitted_here = True
        if admitted_here:
            linked_pairs.append(neighbor)
            fallback_admissions += int(mode == "PAIR_THEN_TURN")
    return {"linked_pair_ids": linked_pairs, "linked_dialogue_ids": linked_dialogues,
            "dialogue_positions": positions, "pair_admissions": pair_admissions,
            "member_admissions": member_admissions, "fallback_admissions": fallback_admissions,
            "pair_overflows": pair_overflows, "member_overflows": member_overflows,
            "duplicate_skips": duplicate_skips, "total_chars": context.chars,
            "link_chars": context.chars - base_chars, "unused_slack": budget - context.chars}


def _qkey(row: Mapping[str, Any]) -> tuple[str, int]:
    return row["comparison_key"], int(row["duplicate_ordinal"])


def _ekey(row: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return (*_qkey(row), row["seed_id"], row["neighbor_id"])


def _tie(row: Mapping[str, Any]) -> tuple[float, int, str]:
    f = row["features"]
    return float(f["seed_rank"]), 0 if float(f["signed_direction"]) < 0 else 1, str(row["neighbor_id"])


def _distribution(values: Sequence[int | float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def _sign_p(left: int, right: int) -> float:
    n = left + right
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(left, right) + 1)) / 2 ** n)


def run_analysis(dataset_path: Path, payload_path: Path, preflight_path: Path, role_path: Path,
                 perturbation_path: Path, labels_path: Path, g6_path: Path, output_dir: Path) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(payload_path) != DA010_BLIND_SHA256:
        raise DA010Error("DA-010 blind payload seal is absent or drifted")
    if sha256_file(perturbation_path) != DA004_BLIND_SHA256 or sha256_file(labels_path) != DA004_LABEL_SHA256:
        raise DA010Error("DA-004 sealed inputs differ")
    payloads = {_ekey(row): row for row in read_gzip(payload_path)}
    labels = {_ekey(row): row for row in read_gzip(labels_path)}
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"])
               for row in json.loads(g6_path.read_text(encoding="utf-8"))["rows"]}
    edges = []
    for row in read_gzip(perturbation_path):
        if not primary[_qkey(row)]:
            continue
        label = labels.get(_ekey(row))
        if label is None or _ekey(row) not in payloads:
            raise DA010Error("DA-010 edge join is incomplete")
        edges.append({**row, "benefit": bool(label["benefit"]), "harm": bool(label["harm"])})
    counts = Counter("BENEFIT" if row["benefit"] else "HARM" if row["harm"] else "NEUTRAL" for row in edges)
    if len(edges) != 25_941 or counts != Counter({"BENEFIT": 57, "HARM": 40, "NEUTRAL": 25_844}):
        raise DA010Error("DA-010 edge population differs")
    scores = grouped_benefit_scores(edges)
    if abs(fast_auc(scores, [int(row["benefit"]) for row in edges]) - .823401708567509) > 1e-15:
        raise DA010Error("DA-010 grouped score replay differs")
    for row, score in zip(edges, scores, strict=True):
        row["benefit_score"] = float(score)

    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    roles = {_qkey(row): row for row in read_gzip(role_path)}
    evidence: dict[tuple[str, int], set[str]] = {}
    dialogues: dict[str, set[str]] = {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            dialogues[source.candidate.identity] = set(source.dialogue_ids)
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = set(question.resolved_dialogue_ids)
    by_question: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        by_question[_qkey(edge)].append(edge)

    rows = []
    direct_total = 0
    for key in sorted(by_question):
        role = roles[key]
        direct_ids = role["direct_ids"]
        context = role_pattern_pairs([members[identity] for identity in direct_ids])
        base_chars = context.chars
        direct_dialogues = set().union(*(dialogues[identity] for identity in direct_ids))
        direct_complete = evidence[key] <= direct_dialogues
        direct_total += direct_complete
        eligible = [edge for edge in by_question[key] if edge["neighbor_id"] not in set(direct_ids)]
        ordered = sorted(eligible, key=lambda edge: (-edge["benefit_score"], *_tie(edge)))
        full_raw = allocate_role_links(context, direct_ids, ordered, members)
        full = {"linked_pair_ids": full_raw["linked_ids"],
                "linked_dialogue_ids": [str(member["dialogue_id"]) for identity in full_raw["linked_ids"] for member in members[identity]],
                "dialogue_positions": {str(member["dialogue_id"]): position for position, identity in
                                       zip(full_raw["linked_positions"], full_raw["linked_ids"], strict=True) for member in members[identity]},
                "pair_admissions": len(full_raw["linked_ids"]), "member_admissions": 0, "fallback_admissions": 0,
                "pair_overflows": full_raw["overflow_skips"], "member_overflows": 0,
                "duplicate_skips": full_raw["duplicate_skips"], "total_chars": full_raw["total_chars"],
                "link_chars": full_raw["total_chars"] - base_chars, "unused_slack": full_raw["unused_slack"]}
        allocations = {"FULL_PAIR": full}
        for arm in ARMS[1:]:
            allocations[arm] = allocate_turn_payloads(context, direct_ids, ordered, members, payloads, arm)
            allocations[arm]["link_chars"] = allocations[arm]["total_chars"] - base_chars
        arm_rows = {}
        for arm, allocation in allocations.items():
            linked_dialogues = set(allocation["linked_dialogue_ids"])
            complete = evidence[key] <= direct_dialogues | linked_dialogues
            gain, loss = complete and not direct_complete, direct_complete and not complete
            missing = evidence[key] - direct_dialogues
            if loss or (gain and (not missing or not missing <= linked_dialogues)):
                raise DA010Error("DA-010 direct protection or causal accounting failed")
            depth = max((allocation["dialogue_positions"][dialogue_id] for dialogue_id in missing), default=None) if gain else None
            both_same_pair = gain and any(set(payloads[_ekey(edge)]["member_dialogue_ids"]) <= missing for edge in eligible)
            arm_rows[arm] = {**allocation, "complete": complete, "gain": gain, "loss": loss,
                             "gain_depth": depth, "gain_requires_both_same_pair": bool(both_same_pair)}
        rows.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": role["sample_id"],
                     "source_index": role["source_index"], "direct_complete": direct_complete, "arms": arm_rows})
    if len(rows) != 1_098 or direct_total != 935 or sum(row["arms"]["FULL_PAIR"]["complete"] for row in rows) != 966:
        raise DA010Error("DA-010 direct or full-pair reproduction differs")

    matrix = {}
    for arm in ARMS:
        cells = [row["arms"][arm] for row in rows]
        by_conversation = {}
        for sample_id in sorted({row["sample_id"] for row in rows}):
            subset = [row["arms"][arm] for row in rows if row["sample_id"] == sample_id]
            by_conversation[sample_id] = {"complete": sum(cell["complete"] for cell in subset),
                                          "gains": sum(cell["gain"] for cell in subset), "losses": sum(cell["loss"] for cell in subset)}
        matrix[arm] = {"complete": sum(cell["complete"] for cell in cells), "gains": sum(cell["gain"] for cell in cells),
                       "losses": sum(cell["loss"] for cell in cells), "pair_admissions": sum(cell["pair_admissions"] for cell in cells),
                       "member_admissions": sum(cell["member_admissions"] for cell in cells),
                       "fallback_admissions": sum(cell["fallback_admissions"] for cell in cells),
                       "pair_overflows": sum(cell["pair_overflows"] for cell in cells),
                       "member_overflows": sum(cell["member_overflows"] for cell in cells), "by_conversation": by_conversation,
                       "gain_requires_both_same_pair": sum(cell["gain_requires_both_same_pair"] for cell in cells),
                       "gain_depth": _distribution([cell["gain_depth"] for cell in cells if cell["gain_depth"] is not None]),
                       "distributions": {field: _distribution([cell[field] for cell in cells]) for field in ("link_chars", "total_chars", "unused_slack")}}
    full_by_conversation = matrix["FULL_PAIR"]["by_conversation"]
    discordance = {}
    statuses = {}
    for arm in ARMS[1:]:
        arm_only = sum(row["arms"][arm]["complete"] and not row["arms"]["FULL_PAIR"]["complete"] for row in rows)
        full_only = sum(row["arms"]["FULL_PAIR"]["complete"] and not row["arms"][arm]["complete"] for row in rows)
        discordance[arm] = {"arm_only_complete": arm_only, "full_only_complete": full_only,
                            "exact_two_sided_p": _sign_p(arm_only, full_only)}
        nonregression = all(matrix[arm]["by_conversation"][group]["complete"] >= cell["complete"] for group, cell in full_by_conversation.items())
        statuses[arm] = "COMPACT_PAYLOAD_SIGNAL" if matrix[arm]["complete"] > 966 and not matrix[arm]["losses"] and nonregression else "NO_COMPACT_PAYLOAD_SIGNAL"
    result = {"schema": "da010-payload-result-v1", "population": {"questions": len(rows), "edges": len(edges), "direct_complete": direct_total},
              "matrix": matrix, "discordance": discordance, "statuses": statuses,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent-corpus availability diagnostic; no payload adoption, reader, or transfer"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_rows(output_dir / "allocations.jsonl.gz", rows)
    return result


__all__ = ["allocate_turn_payloads", "run_analysis"]
