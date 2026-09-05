"""Evidence join and benefit-ranked compact-link analysis for DA-008."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da003_edge_features import write_rows
from analysis.da004_pack_analysis import fast_auc
from analysis.da004_pack_features import FEATURES, read_gzip
from analysis.da006_reserved_links import BUDGET, _member_maps
from analysis.da008_compact_direct import CompactContext, DA008Error, compact_pairs, incremental_pair_cost
from analysis.nf004_anatomy_analysis import _predict
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

DA004_BLIND_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
DA004_LABEL_SHA256 = "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca"
ARMS = ("BENEFIT_MODEL", "QUERY_COVERAGE", "TEMPORAL_ORDER")


def _edge_key(row: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return row["comparison_key"], int(row["duplicate_ordinal"]), row["seed_id"], row["neighbor_id"]


def _question_key(row: Mapping[str, Any]) -> tuple[str, int]:
    return row["comparison_key"], int(row["duplicate_ordinal"])


def grouped_benefit_scores(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    matrix = np.asarray([[float(row["features"][name]) for name in FEATURES] for row in rows], dtype=float)
    labels = np.asarray([int(row["benefit"]) for row in rows], dtype=int)
    groups = np.asarray([row["sample_id"] for row in rows])
    predictions = np.zeros(len(rows), dtype=float)
    for group in sorted(set(groups)):
        test = groups == group
        predictions[test] = _predict(matrix[~test], labels[~test], matrix[test], 1.0)
    return predictions


def allocate_links(
    direct_context: CompactContext,
    direct_ids: Sequence[str],
    ordered_edges: Sequence[Mapping[str, Any]],
    members: Mapping[str, Sequence[Mapping[str, str]]],
    budget: int = BUDGET,
) -> dict[str, Any]:
    context = direct_context
    selected = set(direct_ids)
    linked: list[str] = []
    linked_costs: list[int] = []
    linked_positions: list[int] = []
    overflow_skips = 0
    duplicate_skips = 0
    for position, edge in enumerate(ordered_edges, 1):
        neighbor = str(edge["neighbor_id"])
        if neighbor in selected:
            duplicate_skips += 1
            continue
        cost = incremental_pair_cost(context, members[neighbor])
        if context.chars + cost > budget:
            overflow_skips += 1
            continue
        linked.append(neighbor)
        linked_costs.append(cost)
        linked_positions.append(position)
        selected.add(neighbor)
        context = compact_pairs([*[
            [{"speaker": context.speakers[code], "text": text} for code, text in pair]
            for pair in context.pairs
        ], members[neighbor]])
    return {
        "linked_ids": linked, "linked_costs": linked_costs, "linked_positions": linked_positions,
        "link_chars": sum(linked_costs),
        "total_chars": context.chars, "unused_slack": budget - context.chars,
        "overflow_skips": overflow_skips, "duplicate_skips": duplicate_skips,
    }


def _tie(row: Mapping[str, Any]) -> tuple[float, int, str]:
    features = row["features"]
    return float(features["seed_rank"]), 0 if float(features["signed_direction"]) < 0 else 1, str(row["neighbor_id"])


def _distribution(values: Sequence[int | float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, quantile)) for name, quantile in (("p10", 10), ("p50", 50), ("p90", 90))}


def _exact_sign_p(left_only: int, right_only: int) -> float:
    discordant = left_only + right_only
    if not discordant:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(left_only, right_only) + 1)) / (2 ** discordant)
    return min(1.0, 2 * tail)


def run_analysis(
    dataset_path: Path,
    compact_path: Path,
    preflight_path: Path,
    perturbation_path: Path,
    labels_path: Path,
    g6_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(compact_path) != preflight["selection_sha256"]:
        raise DA008Error("Committed DA-008 compact seal is absent or drifted")
    if sha256_file(perturbation_path) != DA004_BLIND_SHA256 or sha256_file(labels_path) != DA004_LABEL_SHA256:
        raise DA008Error("DA-004 sealed inputs differ")

    blind = read_gzip(perturbation_path)
    labels = {_edge_key(row): row for row in read_gzip(labels_path)}
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"])
               for row in json.loads(g6_path.read_text(encoding="utf-8"))["rows"]}
    rows = []
    for row in blind:
        key = _question_key(row)
        edge_key = _edge_key(row)
        if not primary[key]:
            continue
        if edge_key not in labels:
            raise DA008Error("DA-008 edge label join is incomplete")
        rows.append({**row, "benefit": bool(labels[edge_key]["benefit"]), "harm": bool(labels[edge_key]["harm"])})
    if len(rows) != 25_941 or Counter("BENEFIT" if row["benefit"] else "HARM" if row["harm"] else "NEUTRAL" for row in rows) != Counter({"BENEFIT": 57, "HARM": 40, "NEUTRAL": 25_844}):
        raise DA008Error("DA-008 DA-004 population differs")
    predictions = grouped_benefit_scores(rows)
    for row, score in zip(rows, predictions, strict=True):
        row["benefit_score"] = float(score)

    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    compact_rows = {_question_key(row): row for row in read_gzip(compact_path)}
    evidence: dict[tuple[str, int], set[str]] = {}
    candidate_dialogues: dict[str, set[str]] = {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            candidate_dialogues[source.candidate.identity] = set(source.dialogue_ids)
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = set(question.resolved_dialogue_ids)

    by_question: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_question[_question_key(row)].append(row)
    allocations = []
    direct_complete_count = 0
    oracle_complete_count = 0
    outcomes = {arm: [] for arm in ARMS}
    for key in sorted(by_question):
        compact_row = compact_rows[key]
        direct_ids = compact_row["direct_ids"]
        direct_context = compact_pairs([members[identity] for identity in direct_ids])
        if direct_context.chars != int(compact_row["compact_chars"]):
            raise DA008Error("DA-008 compact replay differs")
        direct_dialogues = set().union(*(candidate_dialogues[identity] for identity in direct_ids))
        direct_complete = evidence[key] <= direct_dialogues
        direct_complete_count += direct_complete
        eligible = [row for row in by_question[key] if row["neighbor_id"] not in set(direct_ids)]
        eligible_ids = {row["neighbor_id"] for row in eligible}
        eligible_dialogues = set().union(*(candidate_dialogues[identity] for identity in eligible_ids)) if eligible_ids else set()
        oracle_complete_count += evidence[key] <= direct_dialogues | eligible_dialogues
        orders = {
            "BENEFIT_MODEL": sorted(eligible, key=lambda row: (-row["benefit_score"], *_tie(row))),
            "QUERY_COVERAGE": sorted(eligible, key=lambda row: (-float(row["features"]["added_query_coverage"]), *_tie(row))),
            "TEMPORAL_ORDER": sorted(eligible, key=_tie),
        }
        arm_rows = {}
        for arm in ARMS:
            allocation = allocate_links(direct_context, direct_ids, orders[arm], members)
            linked_dialogues = set().union(*(candidate_dialogues[identity] for identity in allocation["linked_ids"])) if allocation["linked_ids"] else set()
            complete = evidence[key] <= direct_dialogues | linked_dialogues
            gain, loss = complete and not direct_complete, direct_complete and not complete
            missing = evidence[key] - direct_dialogues
            if loss or (gain and (not missing or not missing <= linked_dialogues)):
                raise DA008Error("DA-008 loss or link causal-accounting failure")
            gain_depth = None
            if gain:
                carriers = {identity for identity in allocation["linked_ids"] if missing & candidate_dialogues[identity]}
                gain_depth = max(position for identity, position in zip(allocation["linked_ids"], allocation["linked_positions"], strict=True) if identity in carriers)
            result_row = {**allocation, "complete": complete, "gain": gain, "loss": loss, "gain_depth": gain_depth}
            outcomes[arm].append({"sample_id": compact_row["sample_id"], "key": key, **result_row})
            arm_rows[arm] = result_row
        allocations.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": compact_row["sample_id"],
                            "source_index": compact_row["source_index"], "direct_complete": direct_complete, "arms": arm_rows})
    if len(allocations) != 1_098 or direct_complete_count != 935:
        raise DA008Error("DA-008 direct evidence reproduction differs")

    matrix = {}
    for arm in ARMS:
        arm_outcomes = outcomes[arm]
        by_conversation = {}
        for sample_id in sorted({row["sample_id"] for row in arm_outcomes}):
            selected = [row for row in arm_outcomes if row["sample_id"] == sample_id]
            gains, losses = sum(row["gain"] for row in selected), sum(row["loss"] for row in selected)
            by_conversation[sample_id] = {"gains": gains, "losses": losses, "net": gains - losses,
                                          "complete": sum(row["complete"] for row in selected)}
        matrix[arm] = {
            "complete": sum(row["complete"] for row in arm_outcomes), "gains": sum(row["gain"] for row in arm_outcomes),
            "losses": sum(row["loss"] for row in arm_outcomes), "links_admitted": sum(len(row["linked_ids"]) for row in arm_outcomes),
            "questions_with_links": sum(bool(row["linked_ids"]) for row in arm_outcomes),
            "distinct_linked_pairs": len({identity for row in arm_outcomes for identity in row["linked_ids"]}),
            "overflow_skips": sum(row["overflow_skips"] for row in arm_outcomes),
            "by_conversation": by_conversation,
            "distributions": {field: _distribution([row[field] for row in arm_outcomes])
                              for field in ("link_chars", "total_chars", "unused_slack")},
            "gain_depth": _distribution([row["gain_depth"] for row in arm_outcomes if row["gain_depth"] is not None]),
        }
    discordance = {}
    for control in ("QUERY_COVERAGE", "TEMPORAL_ORDER"):
        discordance[control] = {
            "benefit_only_complete": sum(left["complete"] and not right["complete"] for left, right in zip(outcomes["BENEFIT_MODEL"], outcomes[control], strict=True)),
            "control_only_complete": sum(right["complete"] and not left["complete"] for left, right in zip(outcomes["BENEFIT_MODEL"], outcomes[control], strict=True)),
        }
        discordance[control]["exact_two_sided_p"] = _exact_sign_p(
            discordance[control]["benefit_only_complete"], discordance[control]["control_only_complete"]
        )
    all_nonnegative = all(value["net"] >= 0 for value in matrix["BENEFIT_MODEL"]["by_conversation"].values())
    signal = (matrix["BENEFIT_MODEL"]["gains"] > 0 and not matrix["BENEFIT_MODEL"]["losses"] and all_nonnegative
              and all(matrix["BENEFIT_MODEL"]["complete"] > matrix[control]["complete"] for control in ("QUERY_COVERAGE", "TEMPORAL_ORDER")))
    result = {
        "schema": "da008-compact-ranked-result-v1", "status": "RANKED_COMPACT_SIGNAL" if signal else "NO_RANKED_COMPACT_SIGNAL",
        "part_a": {"status": "COMPACT_DIRECT_VALIDATED", "direct_complete": direct_complete_count,
                   "savings": _distribution([row["savings"] for row in compact_rows.values() if primary[_question_key(row)]]),
                   "slack": _distribution([row["slack"] for row in compact_rows.values() if primary[_question_key(row)]])},
        "population": {"questions": len(allocations), "edges": len(rows), "direct_complete": direct_complete_count,
                       "all_eligible_oracle_complete": oracle_complete_count,
                       "all_eligible_oracle_gains": oracle_complete_count - direct_complete_count},
        "benefit_model_oof_auc": fast_auc(predictions, [int(row["benefit"]) for row in rows]),
        "direct_vs_benefit_exact_two_sided_p": _exact_sign_p(matrix["BENEFIT_MODEL"]["gains"], matrix["BENEFIT_MODEL"]["losses"]),
        "matrix": matrix, "discordance": discordance,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "spent-corpus availability diagnostic; no reader, renderer adoption, threshold, or live policy",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_rows(output_dir / "allocations.jsonl.gz", allocations)
    return result


__all__ = ["allocate_links", "grouped_benefit_scores", "run_analysis"]
