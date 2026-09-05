"""Residual fit accounting after DA-078 optimal parsing."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.da034_sentinel_backrefs import decode_members, encoded_chars
from analysis.da078_allocation import BUDGET, _protected_descriptors
from analysis.da078_optimal_sentinel import encode_members

ALLOCATION_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
PRIOR_SHA256 = "b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727"


class DA079Error(RuntimeError):
    pass


def _member_cost(role: Any, history: Sequence[str], member: Mapping[str, Any],
                 sentinel: str) -> tuple[int, Any]:
    text = str(member["text"])
    next_role = append_role_pair(role, [member])
    encoded = encode_members([text], history, sentinel)
    if decode_members(encoded, history, sentinel) != (text,):
        raise DA079Error("Required-member decode differs")
    cost = (
        next_role.chars - role.chars - len(text)
        + encoded_chars(encoded, sentinel, len(history))
    )
    return cost, next_role


def audit(longmem_path: Path, population_path: Path, allocation_path: Path,
          prior_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(allocation_path) != ALLOCATION_SHA256 or sha256_file(prior_path) != PRIOR_SHA256:
        raise DA079Error("Sealed input differs")
    selections = {str(row["question_id"]): row for row in read_gzip(allocation_path)}
    requirements = {str(row["key"]): row for row in read_gzip(prior_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in requirements
    }
    rows = []
    resolved = 0
    for question_id in sorted(requirements):
        requirement = requirements[question_id]
        selection = selections[question_id]
        record = records[question_id]
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        pair_for = lambda identity: by_id[identity].members
        required_key = (str(requirement["carrier"]), int(requirement["required_member"]))
        admitted = {
            (str(action["neighbor_id"]), int(action["member"]))
            for action in selection["treatment"]["actions"]
            if action["kind"] == "MEMBER"
        }
        if required_key in admitted:
            resolved += 1
            continue

        da038_row = {**selection, "treatment": selection["da038_control"]}
        descriptors = _protected_descriptors(da038_row, pair_for)
        payloads = [
            [pair_for(identity)[index] for index in members]
            for identity, members in descriptors
        ]
        direct_count = len(selection["direct_ids"])
        role = role_pattern_pairs(payloads[:direct_count])
        for payload in payloads[direct_count:]:
            role = append_role_pair(role, payload)
        history = [str(member["text"]) for payload in payloads for member in payload]
        sentinel = str(selection["treatment"]["sentinel"])
        required_member = pair_for(required_key[0])[required_key[1]]
        initial_cost, _ = _member_cost(role, history, required_member, sentinel)
        used = int(selection["treatment"]["selected_chars"])
        initial_slack = BUDGET - used
        arrival = None
        for action in selection["treatment"]["actions"]:
            neighbor = str(action["neighbor_id"])
            member_index = int(action["member"])
            member = pair_for(neighbor)[member_index]
            cost, next_role = _member_cost(role, history, member, sentinel)
            expected = int(
                action["cost"] if action["kind"] == "MEMBER" else action["attempt_cost"]
            )
            if cost != expected:
                raise DA079Error(
                    f"Frozen DA-078 action cost differs: {question_id} "
                    f"{neighbor}:{member_index} {cost}!={expected}"
                )
            if (neighbor, member_index) == required_key:
                arrival = {"used": used, "cost": cost, "position": int(action["position"])}
            if action["kind"] == "MEMBER":
                role = next_role
                history.append(str(member["text"]))
                used += cost
        if arrival is None:
            raise DA079Error("Required member has no frozen arrival")
        if used != int(selection["treatment"]["final_chars"]):
            raise DA079Error("Frozen DA-078 final charge differs")
        final_cost, _ = _member_cost(role, history, required_member, sentinel)
        final_slack = BUDGET - used
        initial_fit = initial_cost <= initial_slack
        arrival_fit = int(arrival["cost"]) <= BUDGET - int(arrival["used"])
        final_fit = final_cost <= final_slack
        if final_fit:
            blocker = "POSTPACK_FIT"
        elif not initial_fit:
            blocker = "INITIAL_OPTIMAL_ATOMIC_SIZE"
        elif not arrival_fit:
            blocker = "PRIOR_OPTIMAL_ATOMIC_CONSUMPTION"
        else:
            raise DA079Error("Residual blocker is unaccounted")
        rows.append({
            "key": question_id,
            "question_type": record.question_type,
            "carrier": required_key[0],
            "required_member": required_key[1],
            "blocker": blocker,
            "initial_used": int(selection["treatment"]["selected_chars"]),
            "initial_cost": initial_cost,
            "initial_slack": initial_slack,
            "arrival_used": int(arrival["used"]),
            "arrival_cost": int(arrival["cost"]),
            "arrival_slack": BUDGET - int(arrival["used"]),
            "position": int(arrival["position"]),
            "final_used": used,
            "final_cost": final_cost,
            "final_slack": final_slack,
            "initial_fit": initial_fit,
            "arrival_fit": arrival_fit,
            "final_fit": final_fit,
        })
    if resolved != 5 or len(rows) != 13:
        raise DA079Error("DA-078 residual population differs")
    blockers = Counter(row["blocker"] for row in rows)
    result = {
        "schema": "da079-optimal-parse-residual-audit-v1",
        "status": "POSTHOC_OPTIMAL_PARSE_RESIDUALS_CHARACTERIZED",
        "prior_residuals": len(requirements),
        "da078_resolved": resolved,
        "remaining": len(rows),
        "blockers": dict(blockers),
        "initial_slack": distribution([row["initial_slack"] for row in rows]),
        "initial_cost": distribution([row["initial_cost"] for row in rows]),
        "arrival_slack": distribution([row["arrival_slack"] for row in rows]),
        "arrival_cost": distribution([row["arrival_cost"] for row in rows]),
        "final_slack": distribution([row["final_slack"] for row in rows]),
        "final_cost": distribution([row["final_cost"] for row in rows]),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "spent residual causal anatomy only; no allocation, reader, runtime, transfer, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_audit(longmem_path: Path, population_path: Path, allocation_path: Path,
              prior_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(longmem_path, population_path, allocation_path, prior_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "classifications.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da079-") as directory:
        replay_result, replay_rows = audit(
            longmem_path, population_path, allocation_path, prior_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["classifications_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA079Error("DA-079 replay differs")
    return result


__all__ = ["DA079Error", "audit", "run_audit"]
