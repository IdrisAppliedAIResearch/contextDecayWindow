"""Grouped carrier ranking and frozen fallback evaluation for DA-012."""

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
from analysis.da006_reserved_links import _member_maps
from analysis.da008_analysis import grouped_benefit_scores
from analysis.da009_role_pattern import role_pattern_pairs
from analysis.da011_analysis import trace_fallback
from analysis.da012_carrier import DA012Error, HASHES, edge_tie
from analysis.nf004_anatomy_analysis import _predict, average_precision
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

ARMS = ("BENEFIT_ORDER", "CARRIER_ORDER", "NEIGHBOR_COVERAGE")


def _qkey(row: Mapping[str, Any]) -> tuple[str, int]:
    return row["comparison_key"], int(row["duplicate_ordinal"])


def _ekey(row: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return (*_qkey(row), row["seed_id"], row["neighbor_id"])


def carrier_label(neighbor_dialogues: set[str], missing_direct: set[str]) -> bool:
    return bool(neighbor_dialogues & missing_direct)


def grouped_carrier_predictions(rows: Sequence[Mapping[str, Any]]) -> tuple[np.ndarray, dict[str, Any]]:
    matrix = np.asarray([[float(row["features"][name]) for name in FEATURES] for row in rows], dtype=float)
    labels = np.asarray([int(row["carrier"]) for row in rows], dtype=int)
    population = np.asarray([bool(row["carrier_population"]) for row in rows])
    groups = np.asarray([row["sample_id"] for row in rows])
    predictions = np.zeros(len(rows), dtype=float)
    audit = {}
    for group in sorted(set(groups)):
        train = population & (groups != group)
        test_all = groups == group
        test_eval = population & test_all
        if len(set(labels[train])) != 2 or len(set(labels[test_eval])) != 2:
            raise DA012Error("DA-012 carrier fold is not evaluable")
        predictions[test_all] = _predict(matrix[train], labels[train], matrix[test_all], 1.0)
        audit[str(group)] = {"train": int(train.sum()), "test_all": int(test_all.sum()), "test_evaluable": int(test_eval.sum()),
                             "train_positives": int(labels[train].sum()), "test_positives": int(labels[test_eval].sum()),
                             "overlap": int(np.logical_and(train, test_all).sum()),
                             "auc": fast_auc(predictions[test_eval], labels[test_eval])}
    evaluation = population
    metrics = {"n": int(evaluation.sum()), "positives": int(labels[evaluation].sum()),
               "prevalence": float(labels[evaluation].mean()),
               "auc": fast_auc(predictions[evaluation], labels[evaluation]),
               "average_precision": average_precision(predictions[evaluation], labels[evaluation]),
               "brier": float(np.mean((predictions[evaluation] - labels[evaluation]) ** 2)),
               "by_conversation": audit}
    metrics["status"] = "STABLE_CARRIER_PREDICTOR" if metrics["auc"] >= .65 and all(row["auc"] >= .5 for row in audit.values()) else "NO_STABLE_CARRIER_PREDICTOR"
    return predictions, metrics


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


def run_analysis(dataset_path: Path, preflight_path: Path, paths: Mapping[str, Path], g6_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or {name: sha256_file(path) for name, path in paths.items()} != HASHES:
        raise DA012Error("DA-012 mechanical preflight or input seal differs")
    payloads = {_ekey(row): row for row in read_gzip(paths["payload"])}
    committed = {_qkey(row): row for row in read_gzip(paths["da010_allocations"])}
    roles = {_qkey(row): row for row in read_gzip(paths["role"])}
    benefit_labels = {_ekey(row): row for row in read_gzip(paths["labels"])}
    primary = {(row["comparison_key"], int(row["duplicate_ordinal"])): bool(row["primary_eligible"])
               for row in json.loads(g6_path.read_text(encoding="utf-8"))["rows"]}

    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    evidence: dict[tuple[str, int], set[str]] = {}
    pair_dialogues: dict[str, set[str]] = {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            pair_dialogues[source.candidate.identity] = set(source.dialogue_ids)
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = set(question.resolved_dialogue_ids)

    primary_edges = []
    eligible_edges = []
    for row in read_gzip(paths["perturbation"]):
        key = _qkey(row)
        if not primary[key]:
            continue
        label = benefit_labels.get(_ekey(row))
        if label is None:
            raise DA012Error("DA-012 benefit-label join is incomplete")
        primary_row = {**row, "benefit": bool(label["benefit"]), "harm": bool(label["harm"])}
        primary_edges.append(primary_row)
        if row["neighbor_id"] in set(roles[key]["direct_ids"]):
            continue
        direct_dialogues = set().union(*(pair_dialogues[identity] for identity in roles[key]["direct_ids"]))
        missing = evidence[key] - direct_dialogues
        eligible_edges.append({**primary_row, "carrier": carrier_label(pair_dialogues[row["neighbor_id"]], missing),
                               "carrier_population": bool(missing)})
    if len(primary_edges) != 25_941:
        raise DA012Error("DA-012 primary edge population differs")
    direct_incomplete_questions = {_qkey(row) for row in eligible_edges if row["carrier_population"]}
    if len(direct_incomplete_questions) != 163:
        raise DA012Error("DA-012 direct-incomplete question population differs")
    benefit_scores = grouped_benefit_scores(primary_edges)
    if abs(fast_auc(benefit_scores, [int(row["benefit"]) for row in primary_edges]) - .823401708567509) > 1e-15:
        raise DA012Error("DA-012 benefit score replay differs")
    benefit_by_edge = {_ekey(row): float(score) for row, score in zip(primary_edges, benefit_scores, strict=True)}
    carrier_scores, carrier_metrics = grouped_carrier_predictions(eligible_edges)
    for row, score in zip(eligible_edges, carrier_scores, strict=True):
        row["benefit_score"] = benefit_by_edge[_ekey(row)]
        row["carrier_score"] = float(score)

    population_rows = [row for row in eligible_edges if row["carrier_population"]]
    raw_labels = [int(row["carrier"]) for row in population_rows]
    raw_scores = [float(row["features"]["neighbor_query_coverage"]) for row in population_rows]
    raw_by_group = {}
    for group in sorted({row["sample_id"] for row in population_rows}):
        selected = [row for row in population_rows if row["sample_id"] == group]
        raw_by_group[group] = fast_auc([float(row["features"]["neighbor_query_coverage"]) for row in selected], [int(row["carrier"]) for row in selected])
    raw_metrics = {"auc": fast_auc(raw_scores, raw_labels), "by_conversation": raw_by_group}

    by_question: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible_edges:
        by_question[_qkey(row)].append(row)
    allocations = []
    direct_total = oracle_total = 0
    carrier_ranks = {arm: [] for arm in ARMS}
    conjunction_questions = set()
    for key in sorted(by_question):
        role = roles[key]
        direct_ids = role["direct_ids"]
        context = role_pattern_pairs([members[identity] for identity in direct_ids])
        direct_dialogues = set().union(*(pair_dialogues[identity] for identity in direct_ids))
        missing = evidence[key] - direct_dialogues
        direct_complete = not missing
        direct_total += direct_complete
        edges = by_question[key]
        carrier_ids = {row["neighbor_id"] for row in edges if row["carrier"]}
        if len(carrier_ids) > 1:
            conjunction_questions.add(key)
        oracle_total += evidence[key] <= direct_dialogues | set().union(*(pair_dialogues[row["neighbor_id"]] for row in edges))
        orders = {
            "BENEFIT_ORDER": sorted(edges, key=lambda row: (-row["benefit_score"], *edge_tie(row))),
            "CARRIER_ORDER": sorted(edges, key=lambda row: (-row["carrier_score"], *edge_tie(row))),
            "NEIGHBOR_COVERAGE": sorted(edges, key=lambda row: (-float(row["features"]["neighbor_query_coverage"]), *edge_tie(row))),
        }
        arm_rows = {}
        for arm, order in orders.items():
            positions = {row["neighbor_id"]: index for index, row in enumerate(order, 1)}
            carrier_ranks[arm].extend(positions[identity] for identity in carrier_ids)
            trace = trace_fallback(context, direct_ids, order, members, payloads, missing)
            if arm == "BENEFIT_ORDER" and trace["linked_dialogue_ids"] != committed[key]["arms"]["PAIR_THEN_TURN"]["linked_dialogue_ids"]:
                raise DA012Error("DA-012 benefit allocation replay differs")
            complete = evidence[key] <= direct_dialogues | set(trace["linked_dialogue_ids"])
            gain, loss = complete and not direct_complete, direct_complete and not complete
            if loss or (gain and not missing <= set(trace["linked_dialogue_ids"])):
                raise DA012Error("DA-012 direct loss or causal-accounting failure")
            arm_rows[arm] = {"complete": complete, "gain": gain, "loss": loss,
                             "linked_dialogue_ids": trace["linked_dialogue_ids"], "link_chars": trace["link_chars"],
                             "total_chars": trace["total_chars"], "unused_slack": trace["unused_slack"]}
        allocations.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": role["sample_id"],
                            "source_index": role["source_index"], "direct_complete": direct_complete,
                            "carrier_pair_count": len(carrier_ids), "arms": arm_rows})
    if len(allocations) != 1_098 or direct_total != 935 or oracle_total != 986:
        raise DA012Error("DA-012 outcome population differs")

    matrix = {}
    for arm in ARMS:
        cells = [row["arms"][arm] for row in allocations]
        by_conversation = {}
        for group in sorted({row["sample_id"] for row in allocations}):
            subset = [row["arms"][arm] for row in allocations if row["sample_id"] == group]
            by_conversation[group] = {"complete": sum(cell["complete"] for cell in subset),
                                      "gains": sum(cell["gain"] for cell in subset), "losses": sum(cell["loss"] for cell in subset)}
        matrix[arm] = {"complete": sum(cell["complete"] for cell in cells), "gains": sum(cell["gain"] for cell in cells),
                       "losses": sum(cell["loss"] for cell in cells), "by_conversation": by_conversation,
                       "carrier_rank": _distribution(carrier_ranks[arm]),
                       "conjunction_complete": sum(row["arms"][arm]["complete"] for row in allocations if _qkey(row) in conjunction_questions),
                       "distributions": {field: _distribution([cell[field] for cell in cells]) for field in ("link_chars", "total_chars", "unused_slack")}}
    if matrix["BENEFIT_ORDER"]["complete"] != 970:
        raise DA012Error("DA-012 benefit total differs")
    discordance = {}
    for arm in ARMS[1:]:
        arm_only = sum(row["arms"][arm]["complete"] and not row["arms"]["BENEFIT_ORDER"]["complete"] for row in allocations)
        benefit_only = sum(row["arms"]["BENEFIT_ORDER"]["complete"] and not row["arms"][arm]["complete"] for row in allocations)
        discordance[arm] = {"arm_only_complete": arm_only, "benefit_only_complete": benefit_only,
                            "exact_two_sided_p": _sign_p(arm_only, benefit_only)}
    no_group_regression = all(matrix["CARRIER_ORDER"]["by_conversation"][group]["complete"] >= cell["complete"]
                              for group, cell in matrix["BENEFIT_ORDER"]["by_conversation"].items())
    signal = (carrier_metrics["status"] == "STABLE_CARRIER_PREDICTOR" and matrix["CARRIER_ORDER"]["complete"] > 970
              and not matrix["CARRIER_ORDER"]["losses"] and no_group_regression)
    result = {"schema": "da012-carrier-ranking-v1", "status": "CARRIER_RANK_SIGNAL" if signal else "NO_CARRIER_RANK_SIGNAL",
              "population": {"questions": len(allocations), "direct_incomplete_questions": len(direct_incomplete_questions),
                             "primary_edges": len(primary_edges), "eligible_edges": len(eligible_edges),
                             "carrier_model_edges": len(population_rows), "carrier_positives": sum(raw_labels),
                             "direct_complete": direct_total, "oracle_complete": oracle_total},
              "carrier_model": carrier_metrics, "neighbor_coverage": raw_metrics,
              "matrix": matrix, "discordance": discordance,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "grouped spent-corpus carrier availability; no fresh validation, reader, or adoption"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_rows(output_dir / "allocations.jsonl.gz", allocations)
    return result


__all__ = ["carrier_label", "grouped_carrier_predictions", "run_analysis"]

