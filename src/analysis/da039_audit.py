"""Residual dependency audit after the protected DA-038 sentinel tail."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import POPULATION_SHA256, load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.da034_allocation import _costs, _descriptors
from analysis.da034_sentinel_backrefs import encode_members, encoded_chars
from analysis.nf005_measurement import adapt_population

BUDGET = 16_000
ALLOCATION_SHA256 = "7758e13562c536fd5123583ccbf0082fd8f3315ddf29a68d74f10f12ee42703e"
OUTCOME_SHA256 = "639b693b925ee7e92e5fef57276f2403f62e7834b9b69dfd1a991e5c1b1c9232"
PRIOR_SHA256 = "9e5fff17f02a5576593c84629b2c2d73641485d645609e02301ec56f2b3b94ef"


class DA039Error(RuntimeError):
    pass


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA039Error("LongMem population differs")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in data["rows"])


def _states(row: Mapping[str, Any], pair_for: Any) -> tuple[dict[str, Any], dict[tuple[str, int], dict[str, int]], dict[str, Any], set[tuple[str, int]]]:
    da031_row = {**row, "treatment": row["da031_control"]}
    descriptors = _descriptors(da031_row, pair_for)
    for action in row["da033_control"]["actions"]:
        if action["kind"] == "MEMBER":
            descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
    payloads = [[pair_for(identity)[index] for index in members] for identity, members in descriptors]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    present = {(identity, index) for identity, members in descriptors for index in members}
    if row["treatment"]["codec"] == "DA033":
        used = int(row["da033_control"]["final_chars"])
    else:
        sentinel = str(row["treatment"]["sentinel"])
        encoded = encode_members(history, (), sentinel)
        used = role.chars - sum(map(len, history)) + encoded_chars(encoded, sentinel)
        if used != int(row["treatment"]["selected_chars"]):
            raise DA039Error("Protected sentinel initial charge differs")
    initial = {"used": used, "role": role, "history": list(history)}
    arrivals: dict[tuple[str, int], dict[str, int]] = {}
    sentinel = str(row["treatment"]["sentinel"])
    for action in row["treatment"]["actions"]:
        neighbor = str(action["neighbor_id"])
        member = int(action["member"])
        pair = pair_for(neighbor)
        cost = int(_costs(role, history, pair, sentinel)[1][member])
        expected = int(action["cost"] if action["kind"] == "MEMBER" else action["attempt_cost"])
        if cost != expected:
            raise DA039Error(f"DA-038 arrival cost differs: {neighbor}:{member} {cost}!={expected}")
        arrivals[(neighbor, member)] = {"used": used, "cost": cost,
                                         "position": int(action["position"])}
        if action["kind"] == "MEMBER":
            role = append_role_pair(role, [pair[member]])
            history.append(str(pair[member]["text"]))
            used += cost
            present.add((neighbor, member))
    if used != int(row["treatment"]["final_chars"]):
        raise DA039Error("DA-038 final charge differs")
    return initial, arrivals, {"used": used, "role": role, "history": history}, present


def _classify(key: str, row: Mapping[str, Any], missing: set[str], pair_for: Any,
              identities: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    initial, arrivals, final, present = _states(row, pair_for)
    delivered = {identities[candidate][member] for candidate, member in present}
    remaining = missing - delivered
    if not remaining:
        raise DA039Error("Remaining miss has no missing identity")
    carriers = list(dict.fromkeys(str(action["neighbor_id"]) for action in row["baseline_actions"]
                                 if set(identities[str(action["neighbor_id"])]) & remaining))
    union = set().union(*(set(identities[value]) for value in carriers)) if carriers else set()
    if not remaining <= union:
        raise DA039Error("Residual exposed union differs")
    single = [carrier for carrier in carriers if remaining <= set(identities[carrier])]
    base = {"corpus": "LONGMEM", "key": key, "missing": sorted(missing),
            "remaining_missing": sorted(remaining), "carrier_count": len(carriers),
            "initial_slack": BUDGET - initial["used"], "final_slack": BUDGET - final["used"]}
    if not single:
        return {**base, "blocker": "MULTI_CARRIER_CONJUNCTION", "postpack_fits": False}
    carrier = single[0]
    required = [index for index, identity in enumerate(identities[carrier]) if identity in remaining]
    absent = [member for member in required if (carrier, member) not in present]
    if len(absent) > 1:
        return {**base, "blocker": "MULTI_MEMBER_CONJUNCTION", "carrier": carrier,
                "required_members": absent, "postpack_fits": False}
    if not absent:
        raise DA039Error("Required identity is already present")
    member = absent[0]
    if row["treatment"]["codec"] == "DA033":
        return {**base, "blocker": "RETAINED_DA033_NO_TAIL", "carrier": carrier,
                "required_member": member, "postpack_fits": False}
    arrival = arrivals.get((carrier, member))
    if arrival is None:
        raise DA039Error("Sentinel member was not attempted")
    pair = pair_for(carrier)
    sentinel = str(row["treatment"]["sentinel"])
    initial_cost = int(_costs(initial["role"], initial["history"], pair, sentinel)[1][member])
    final_cost = int(_costs(final["role"], final["history"], pair, sentinel)[1][member])
    if initial["used"] + initial_cost > BUDGET:
        blocker = "INITIAL_SENTINEL_ATOMIC_SIZE"
    elif arrival["used"] + arrival["cost"] > BUDGET:
        blocker = "PRIOR_SENTINEL_ATOMIC_CONSUMPTION"
    else:
        blocker = "UNACCOUNTED"
    return {**base, "blocker": blocker, "carrier": carrier, "required_member": member,
            "initial_cost": initial_cost, "arrival_cost": arrival["cost"],
            "final_cost": final_cost, "arrival_used": arrival["used"],
            "arrival_slack": BUDGET - arrival["used"], "position": arrival["position"],
            "postpack_fits": final["used"] + final_cost <= BUDGET}


def audit(longmem_path: Path, population_path: Path, allocation_path: Path,
          outcome_path: Path, prior_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((allocation_path, ALLOCATION_SHA256), (outcome_path, OUTCOME_SHA256),
             (prior_path, PRIOR_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA039Error("Sealed input differs")
    allocations = {str(row["question_id"]): row for row in read_gzip(allocation_path)}
    outcomes = {str(row["question_id"]): row for row in read_gzip(outcome_path)}
    prior = {str(row["key"]): row for row in read_gzip(prior_path)}
    blind = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    evidence = {record.question_id: record for record in adapt_population(longmem_path, _population_ids(population_path))}
    rows = []
    for key, old in prior.items():
        if outcomes[key]["TREATMENT"]:
            continue
        allocation, blind_record, evidence_record = allocations[key], blind[key], evidence[key]
        by_id = {episode.candidate.identity: episode for episode in blind_record.episodes}
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in evidence_record.episodes}
        rows.append(_classify(key, allocation, set(old["remaining_missing"]),
                              lambda identity: by_id[identity].members, identities))
    counts = Counter(row["blocker"] for row in rows)
    if len(rows) != 18 or counts["UNACCOUNTED"]:
        raise DA039Error(f"Residual accounting differs: n={len(rows)}, counts={counts}")
    top, number = counts.most_common(1)[0]
    finite = [row for row in rows if "initial_cost" in row]
    result = {"schema": "da039-protected-sentinel-residual-audit-v1",
              "status": f"DOMINANT_{top}" if number / len(rows) >= .6 else "MIXED_RESIDUAL_BLOCKERS",
              "n": len(rows), "blockers": dict(counts),
              "postpack_fits": sum(row["postpack_fits"] for row in rows),
              "initial_slack": distribution([row["initial_slack"] for row in rows]),
              "arrival_slack": distribution([row["arrival_slack"] for row in finite]),
              "final_slack": distribution([row["final_slack"] for row in rows]),
              "final_cost": distribution([row["final_cost"] for row in finite]),
              "anchors": {"control": 232, "ceiling": 250},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent evidence-aware causal audit only"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_audit(longmem_path: Path, population_path: Path, allocation_path: Path,
              outcome_path: Path, prior_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(longmem_path, population_path, allocation_path, outcome_path, prior_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "classifications.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da039-") as directory:
        replay_result, replay_rows = audit(longmem_path, population_path, allocation_path,
                                           outcome_path, prior_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "classifications_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA039Error("Audit replay differs")
    return result


__all__ = ["DA039Error", "audit", "run_audit"]
