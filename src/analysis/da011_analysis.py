"""Evidence-bearing residual trace analysis for DA-011."""

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
from analysis.da009_role_pattern import RolePatternContext, append_role_pair, role_pattern_pairs
from analysis.da011_audit import DA011Error, HASHES, carrier_first, classify_blocker
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split


def _qkey(row: Mapping[str, Any]) -> tuple[str, int]:
    return row["comparison_key"], int(row["duplicate_ordinal"])


def _ekey(row: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return (*_qkey(row), row["seed_id"], row["neighbor_id"])


def _tie(row: Mapping[str, Any]) -> tuple[float, int, str]:
    feature = row["features"]
    return float(feature["seed_rank"]), 0 if float(feature["signed_direction"]) < 0 else 1, str(row["neighbor_id"])


def trace_fallback(context: RolePatternContext, direct_ids: Sequence[str], ordered_edges: Sequence[Mapping[str, Any]],
                   members: Mapping[str, Sequence[Mapping[str, str]]], payloads: Mapping[tuple[str, int, str, str], Mapping[str, Any]],
                   missing_evidence: set[str], *, oracle_member: bool = False, budget: int = BUDGET) -> dict[str, Any]:
    base_chars = context.chars
    direct = set(direct_ids)
    seen: set[str] = set()
    linked: list[str] = []
    actions = []
    for position, edge in enumerate(ordered_edges, 1):
        neighbor = str(edge["neighbor_id"])
        if neighbor in direct or neighbor in seen:
            continue
        seen.add(neighbor)
        payload = payloads[_ekey(edge)]
        pair = members[neighbor]
        arrival_slack = budget - context.chars
        pair_updated = append_role_pair(context, pair)
        pair_cost = pair_updated.chars - context.chars
        action: dict[str, Any] = {"position": position, "neighbor_id": neighbor,
                                  "benefit_score": float(edge["benefit_score"]),
                                  "arrival_slack": arrival_slack, "prior_admitted_chars": context.chars - base_chars,
                                  "full_pair_cost": pair_cost, "pair_overflow": pair_updated.chars > budget,
                                  "pair_admitted": False, "fallback_attempted": False}
        action["members"] = []
        for index, member in enumerate(pair):
            turn_updated = append_role_pair(context, [member])
            dialogue_id = str(member["dialogue_id"])
            action["members"].append({"index": index, "dialogue_id": dialogue_id,
                                      "carries_missing": dialogue_id in missing_evidence,
                                      "cost": turn_updated.chars - context.chars,
                                      "fits": turn_updated.chars <= budget})
        if pair_updated.chars <= budget:
            context = pair_updated
            action["pair_admitted"] = True
            for member in pair:
                linked.append(str(member["dialogue_id"]))
        else:
            action["fallback_attempted"] = True
            lexical_order = [int(index) for index in payload["member_order"]]
            chosen = lexical_order[0]
            if oracle_member:
                evidence_indices = [index for index in lexical_order if str(pair[index]["dialogue_id"]) in missing_evidence]
                if evidence_indices:
                    chosen = evidence_indices[0]
            member = pair[chosen]
            updated = append_role_pair(context, [member])
            admitted = updated.chars <= budget
            action.update({"chosen_member_index": chosen, "chosen_dialogue_id": str(member["dialogue_id"]),
                           "chosen_carries_missing": str(member["dialogue_id"]) in missing_evidence,
                           "chosen_cost": updated.chars - context.chars, "chosen_fit": admitted,
                           "chosen_admitted": admitted})
            if admitted:
                context = updated
                linked.append(str(member["dialogue_id"]))
        actions.append(action)
    return {"linked_dialogue_ids": linked, "actions": actions, "total_chars": context.chars,
            "link_chars": context.chars - base_chars, "unused_slack": budget - context.chars}


def minimum_missing_cost(context: RolePatternContext, ordered_carriers: Sequence[str], missing: set[str],
                         members: Mapping[str, Sequence[Mapping[str, str]]]) -> int:
    start = context.chars
    for identity in ordered_carriers:
        required = [member for member in members[identity] if str(member["dialogue_id"]) in missing]
        if not required:
            continue
        context = append_role_pair(context, members[identity] if len(required) == len(members[identity]) else required)
    return context.chars - start


def _distribution(values: Sequence[int | float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def _sign_p(left: int, right: int) -> float:
    n = left + right
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(left, right) + 1)) / 2 ** n)


def run_analysis(dataset_path: Path, preflight_path: Path, payload_path: Path, da010_result_path: Path,
                 da010_allocations_path: Path, role_path: Path, perturbation_path: Path, labels_path: Path,
                 g6_path: Path, output_dir: Path) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS":
        raise DA011Error("DA-011 mechanical preflight is absent")
    paths = {"payload": payload_path, "da010_result": da010_result_path, "da010_allocations": da010_allocations_path,
             "role": role_path, "perturbation": perturbation_path, "labels": labels_path}
    if {name: sha256_file(path) for name, path in paths.items()} != HASHES:
        raise DA011Error("DA-011 sealed input drifted after preflight")
    payloads = {_ekey(row): row for row in read_gzip(payload_path)}
    committed = {_qkey(row): row for row in read_gzip(da010_allocations_path)}
    roles = {_qkey(row): row for row in read_gzip(role_path)}
    labels = {_ekey(row): row for row in read_gzip(labels_path)}
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"])
               for row in json.loads(g6_path.read_text(encoding="utf-8"))["rows"]}
    edges = []
    for row in read_gzip(perturbation_path):
        if not primary[_qkey(row)]:
            continue
        label = labels.get(_ekey(row))
        if label is None:
            raise DA011Error("DA-011 edge label join is incomplete")
        edges.append({**row, "benefit": bool(label["benefit"]), "harm": bool(label["harm"])})
    scores = grouped_benefit_scores(edges)
    if abs(fast_auc(scores, [int(row["benefit"]) for row in edges]) - .823401708567509) > 1e-15:
        raise DA011Error("DA-011 grouped score replay differs")
    for row, score in zip(edges, scores, strict=True):
        row["benefit_score"] = float(score)
    by_question: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        by_question[_qkey(edge)].append(edge)

    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    evidence: dict[tuple[str, int], set[str]] = {}
    pair_dialogues: dict[str, set[str]] = {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            pair_dialogues[source.candidate.identity] = set(source.dialogue_ids)
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = set(question.resolved_dialogue_ids)

    residuals = []
    baseline_complete: dict[tuple[str, int], bool] = {}
    diagnostics = {"ORACLE_MEMBER": {}, "CARRIER_FIRST": {}}
    direct_total = baseline_total = oracle_total = 0
    replay_checks = 0
    for key in sorted(by_question):
        role = roles[key]
        direct_ids = role["direct_ids"]
        context = role_pattern_pairs([members[identity] for identity in direct_ids])
        direct_dialogues = set().union(*(pair_dialogues[identity] for identity in direct_ids))
        missing = evidence[key] - direct_dialogues
        direct_complete = not missing
        direct_total += direct_complete
        eligible = [edge for edge in by_question[key] if edge["neighbor_id"] not in set(direct_ids)]
        ordered = sorted(eligible, key=lambda edge: (-edge["benefit_score"], *_tie(edge)))
        carrier_ids = {edge["neighbor_id"] for edge in eligible if pair_dialogues[edge["neighbor_id"]] & missing}
        oracle_complete = evidence[key] <= direct_dialogues | set().union(*(pair_dialogues[edge["neighbor_id"]] for edge in eligible))
        oracle_total += oracle_complete
        baseline = trace_fallback(context, direct_ids, ordered, members, payloads, missing)
        if baseline["linked_dialogue_ids"] != committed[key]["arms"]["PAIR_THEN_TURN"]["linked_dialogue_ids"]:
            raise DA011Error("DA-011 baseline dialogue replay differs")
        replay_checks += 1
        complete = evidence[key] <= direct_dialogues | set(baseline["linked_dialogue_ids"])
        baseline_complete[key] = complete
        baseline_total += complete
        oracle_member = trace_fallback(context, direct_ids, ordered, members, payloads, missing, oracle_member=True)
        carrier_order = carrier_first(ordered, carrier_ids)
        carrier_trace = trace_fallback(context, direct_ids, carrier_order, members, payloads, missing)
        diagnostics["ORACLE_MEMBER"][key] = evidence[key] <= direct_dialogues | set(oracle_member["linked_dialogue_ids"])
        diagnostics["CARRIER_FIRST"][key] = evidence[key] <= direct_dialogues | set(carrier_trace["linked_dialogue_ids"])
        if direct_complete or complete or not oracle_complete:
            continue

        ordered_carriers = [edge["neighbor_id"] for edge in ordered if edge["neighbor_id"] in carrier_ids]
        carrier_actions = [action for action in baseline["actions"] if action["neighbor_id"] in carrier_ids]
        both_required = any(pair_dialogues[identity] <= missing for identity in carrier_ids)
        wrong_member_fits = False
        for action in carrier_actions:
            if not action["pair_overflow"] or not action.get("fallback_attempted"):
                continue
            chosen_missing = action.get("chosen_carries_missing", False)
            required_members = [member for member in action["members"] if member["carries_missing"]]
            if required_members and not chosen_missing and all(member["fits"] for member in required_members):
                wrong_member_fits = True
        required_cost = minimum_missing_cost(context, ordered_carriers, missing, members)
        arrival_slack = min((action["arrival_slack"] for action in carrier_actions), default=BUDGET - context.chars)
        blocker = classify_blocker(carrier_pair_count=len(carrier_ids), both_members_required=both_required,
                                   wrong_member_fits=wrong_member_fits, required_cost=required_cost,
                                   initial_slack=BUDGET - context.chars, arrival_slack=arrival_slack)
        if blocker == "OTHER_TRACE_FAILURE":
            raise DA011Error("DA-011 residual remains unclassified")
        residuals.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": role["sample_id"],
                          "source_index": role["source_index"], "blocker": blocker,
                          "missing_dialogue_ids": sorted(missing), "carrier_pair_ids": ordered_carriers,
                          "carrier_pair_count": len(carrier_ids), "both_members_required": both_required,
                          "wrong_member_fits": wrong_member_fits, "initial_slack": BUDGET - context.chars,
                          "arrival_slack": arrival_slack, "required_cost": required_cost,
                          "carrier_actions": carrier_actions,
                          "oracle_member_complete": diagnostics["ORACLE_MEMBER"][key],
                          "carrier_first_complete": diagnostics["CARRIER_FIRST"][key]})
    if (len(edges), direct_total, baseline_total, oracle_total, len(residuals), replay_checks) != (25_941, 935, 970, 986, 16, 1_098):
        raise DA011Error("DA-011 reproduction or residual population differs")

    diagnostic_results = {}
    for name, outcomes in diagnostics.items():
        total = sum(outcomes.values())
        gains = sum(outcomes[key] and not baseline_complete[key] for key in outcomes)
        losses = sum(baseline_complete[key] and not outcomes[key] for key in outcomes)
        by_conversation = {}
        for sample_id in sorted({row["sample_id"] for row in committed.values()}):
            keys = [key for key, row in committed.items() if row["sample_id"] == sample_id]
            by_conversation[sample_id] = {"complete": sum(outcomes[key] for key in keys),
                                          "gains_vs_baseline": sum(outcomes[key] and not baseline_complete[key] for key in keys),
                                          "losses_vs_baseline": sum(baseline_complete[key] and not outcomes[key] for key in keys)}
        diagnostic_results[name] = {"complete": total, "gains_vs_baseline": gains, "losses_vs_baseline": losses,
                                    "exact_two_sided_p": _sign_p(gains, losses), "by_conversation": by_conversation}
    classes = Counter(row["blocker"] for row in residuals)
    result = {"schema": "da011-residual-audit-v1", "population": {"questions": 1_098, "edges": len(edges),
               "direct_complete": direct_total, "fallback_complete": baseline_total,
               "all_eligible_oracle_complete": oracle_total, "residuals": len(residuals)},
              "blocker_classes": dict(sorted(classes.items())),
              "trace_distributions": {field: _distribution([row[field] for row in residuals])
                                      for field in ("initial_slack", "arrival_slack", "required_cost")},
              "carrier_position": _distribution([action["position"] for row in residuals for action in row["carrier_actions"]]),
              "diagnostics": diagnostic_results, "replay_checks": replay_checks,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent-corpus causal audit; oracle diagnostics are non-deployable upper bounds"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_rows(output_dir / "residual_traces.jsonl.gz", residuals)
    return result


__all__ = ["minimum_missing_cost", "run_analysis", "trace_fallback"]
