"""Causal accounting for DA-013 one-hop-reachable misses."""

from __future__ import annotations

import gzip
import itertools
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da010_payloads import member_order, payload_costs
from analysis.da013_analysis import NF005_OUTCOMES_SHA256
from analysis.da013_preflight import POPULATION_SHA256, _idf, load_blind_population, sha256_file
from analysis.nf005_measurement import adapt_population

ALLOCATION_SHA256 = "58eda0276af9a97056e4b38fdaf8b8d1def346f52a1e9afa2b37eb025347475a"
OUTCOMES_SHA256 = "832b85bff370fdfb0de619df2b4b280f5b50e375ebfee0190fb22bfa488c2f49"
BUDGET = 16_000


class DA014Error(RuntimeError):
    pass


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA014Error("NF-003 population differs")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in payload["rows"])


def _trace(record: Any, allocation: Mapping[str, Any], idf: Mapping[str, float]) -> dict[str, dict[str, Any]]:
    by_id = {episode.candidate.identity: episode for episode in record.episodes}
    context = role_pattern_pairs([by_id[value].members for value in allocation["direct_ids"]])
    output = {}
    for action in allocation["TEMPORAL_ORDER"]["actions"]:
        neighbor = by_id[action["neighbor_id"]]
        ordering, coverage = member_order(record.question, neighbor.members, idf)
        full, turns = payload_costs(context, neighbor.members)
        output[action["neighbor_id"]] = {
            "arrival_slack": BUDGET - context.chars,
            "full_cost": full,
            "turn_costs": list(turns),
            "selected_member": ordering[0],
            "member_coverage": list(coverage),
            "action": action["kind"],
        }
        expected = "PAIR" if full <= BUDGET - context.chars else "TURN" if turns[ordering[0]] <= BUDGET - context.chars else "SKIP"
        if action["kind"] != expected:
            raise DA014Error("Frozen action does not replay at arrival")
        if expected == "PAIR":
            context = append_role_pair(context, neighbor.members)
        elif expected == "TURN":
            if int(action["member"]) != ordering[0]:
                raise DA014Error("Frozen singleton member differs")
            context = append_role_pair(context, [neighbor.members[ordering[0]]])
    if context.chars != int(allocation["TEMPORAL_ORDER"]["chars"]):
        raise DA014Error("Frozen final character count differs")
    return output


def _minimum_carriers(missing: set[str], carriers: Mapping[str, set[str]]) -> tuple[int, tuple[str, ...]]:
    identities = sorted(carriers)
    for count in range(1, len(identities) + 1):
        for chosen in itertools.combinations(identities, count):
            if missing <= set().union(*(carriers[value] for value in chosen)):
                return count, chosen
    raise DA014Error("One-hop oracle lacks a complete carrier set")


def classify(
    missing: set[str], carriers: Mapping[str, set[str]], initial: Mapping[str, Mapping[str, Any]],
    arrival: Mapping[str, Mapping[str, Any]], member_ids: Mapping[str, tuple[str, str]],
) -> tuple[str, dict[str, Any]]:
    minimum, chosen = _minimum_carriers(missing, carriers)
    if minimum > 1:
        return "MULTI_CARRIER_CONJUNCTION", {"minimum_carriers": minimum, "one_minimum_set": list(chosen)}
    sufficient = [identity for identity, carried in carriers.items() if missing <= carried]
    for identity in sufficient:
        required = [index for index, turn_id in enumerate(member_ids[identity]) if turn_id in missing]
        if len(required) == 1:
            evidence_member = required[0]
            trace = arrival[identity]
            if trace["turn_costs"][evidence_member] <= trace["arrival_slack"] and trace["selected_member"] != evidence_member:
                return "WRONG_MEMBER_CHOICE", {"carrier": identity, "evidence_member": evidence_member}
    for identity in sufficient:
        required = [index for index, turn_id in enumerate(member_ids[identity]) if turn_id in missing]
        initial_cost = initial[identity]["full_cost"] if len(required) > 1 else initial[identity]["turn_costs"][required[0]]
        arrival_cost = arrival[identity]["full_cost"] if len(required) > 1 else arrival[identity]["turn_costs"][required[0]]
        if initial_cost <= initial[identity]["initial_slack"] and arrival_cost > arrival[identity]["arrival_slack"]:
            return "PRIOR_CONSUMPTION", {"carrier": identity, "initial_cost": initial_cost, "arrival_cost": arrival_cost}
    if all(
        (initial[identity]["full_cost"] if len([x for x in member_ids[identity] if x in missing]) > 1
         else initial[identity]["turn_costs"][[index for index, x in enumerate(member_ids[identity]) if x in missing][0]])
        > initial[identity]["initial_slack"] for identity in sufficient
    ):
        return "INITIAL_PAYLOAD_TOO_LARGE", {"sufficient_carriers": sufficient}
    return "UNACCOUNTED", {"sufficient_carriers": sufficient}


def audit(dataset_path: Path, population_path: Path, nf005_path: Path, allocation_path: Path,
          outcomes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(nf005_path) != NF005_OUTCOMES_SHA256 or sha256_file(allocation_path) != ALLOCATION_SHA256 or sha256_file(outcomes_path) != OUTCOMES_SHA256:
        raise DA014Error("DA-014 sealed input differs")
    ids = _population_ids(population_path)
    blind_records = {record.question_id: record for record in load_blind_population(dataset_path, population_path)}
    evidence_records = {record.question_id: record for record in adapt_population(dataset_path, ids)}
    allocations = {row["question_id"]: row for row in read_gzip(allocation_path)}
    outcomes = {row["question_id"]: row for row in read_gzip(outcomes_path)}
    idf = _idf(tuple(blind_records.values()))
    rows = []
    for question_id, outcome in outcomes.items():
        if outcome["DIRECT_ORIGINAL"] or not outcome["ONE_HOP_ORACLE"]:
            continue
        blind, evidence, allocation = blind_records[question_id], evidence_records[question_id], allocations[question_id]
        episode_turns = {episode.candidate.identity: episode.turn_identities for episode in evidence.episodes}
        targets = {turn.candidate.identity for turn in evidence.turns if turn.is_target}
        direct_turns = set().union(*(episode_turns[value] for value in allocation["direct_ids"]))
        missing = targets - direct_turns
        carriers = {edge["neighbor_id"]: set(episode_turns[edge["neighbor_id"]]) & missing for edge in allocation["edges"]}
        carriers = {identity: carried for identity, carried in carriers.items() if carried}
        arrival = _trace(blind, allocation, idf)
        by_id = {episode.candidate.identity: episode for episode in blind.episodes}
        initial_context = role_pattern_pairs([by_id[value].members for value in allocation["direct_ids"]])
        initial = {}
        for identity in carriers:
            full, turns = payload_costs(initial_context, by_id[identity].members)
            initial[identity] = {"initial_slack": BUDGET - initial_context.chars, "full_cost": full, "turn_costs": list(turns)}
        if outcome["TEMPORAL_ORDER"]:
            label, detail = "RESCUED", {}
        else:
            label, detail = classify(missing, carriers, initial, arrival, episode_turns)
        rows.append({"question_id": question_id, "question_type": outcome["question_type"], "class": label,
                     "missing_targets": sorted(missing), "carrier_count": len(carriers), "detail": detail,
                     "carriers": [{"neighbor_id": identity, "carried": sorted(carriers[identity]),
                                   "initial": initial[identity], "arrival": arrival[identity]} for identity in sorted(carriers)]})
    counts = Counter(row["class"] for row in rows)
    if len(rows) != 86 or counts["RESCUED"] != 7 or counts["UNACCOUNTED"]:
        raise DA014Error(f"DA-014 accounting differs: {counts}")
    blockers = {key: value for key, value in counts.items() if key != "RESCUED"}
    modal = max(blockers, key=lambda key: (blockers[key], key))
    status = ("PAYLOAD_SELECTION_BLOCKER" if modal == "WRONG_MEMBER_CHOICE" else
              "CONJUNCTION_BLOCKER" if modal == "MULTI_CARRIER_CONJUNCTION" else
              "CAPACITY_BLOCKER" if modal in {"PRIOR_CONSUMPTION", "INITIAL_PAYLOAD_TOO_LARGE"} else "MIXED_BLOCKERS")
    result = {"schema": "da014-gap-audit-v1", "status": status,
              "population": {"reachable": len(rows), "rescued": counts["RESCUED"], "misses": len(rows) - counts["RESCUED"]},
              "classes": dict(sorted(counts.items())),
              "by_question_type": {kind: dict(sorted(Counter(row["class"] for row in rows if row["question_type"] == kind).items()))
                                   for kind in sorted({row["question_type"] for row in rows})},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "post-outcome spent-data causal accounting only"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_audit(dataset_path: Path, population_path: Path, nf005_path: Path, allocation_path: Path,
              outcomes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(dataset_path, population_path, nf005_path, allocation_path, outcomes_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "traces.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da014-") as directory:
        replay_result, replay_rows = audit(dataset_path, population_path, nf005_path, allocation_path, outcomes_path)
        replay_path = Path(directory) / path.name
        _write(replay_path, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay_path.read_bytes()
    result.update({"replay_byte_identical": identical, "traces_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA014Error("DA-014 replay differs")
    return result


__all__ = ["DA014Error", "audit", "classify", "run_audit"]
