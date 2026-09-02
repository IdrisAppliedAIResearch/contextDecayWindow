"""Protected DA-038 re-encoding with globally shortest sentinel parses."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da034_allocation import _descriptors
from analysis.da034_sentinel_backrefs import (
    decode_members,
    encode_members as greedy_encode,
    encoded_chars,
)
from analysis.da078_optimal_sentinel import encode_members as optimal_encode

BUDGET = 16_000
DA038_SHA256 = "7758e13562c536fd5123583ccbf0082fd8f3315ddf29a68d74f10f12ee42703e"


class DA078Error(RuntimeError):
    pass


def _protected_descriptors(row: Mapping[str, Any], pair_for: Any) -> list[tuple[str, tuple[int, ...]]]:
    da031_row = {**row, "treatment": row["da031_control"]}
    descriptors = _descriptors(da031_row, pair_for)
    for control in (row["da033_control"], row["treatment"]):
        for action in control["actions"]:
            if action["kind"] == "MEMBER":
                descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
    return descriptors


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    descriptors = _protected_descriptors(row, pair_for)
    payloads = [[pair_for(identity)[index] for index in members] for identity, members in descriptors]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    sentinel = str(row["treatment"]["sentinel"])
    greedy = greedy_encode(history, (), sentinel)
    optimal = optimal_encode(history, (), sentinel)
    if decode_members(optimal, (), sentinel) != tuple(history):
        raise DA078Error("Optimal protected decode differs")
    fixed_chars = role.chars - sum(map(len, history))
    greedy_chars = fixed_chars + encoded_chars(greedy, sentinel)
    optimal_chars = fixed_chars + encoded_chars(optimal, sentinel)
    control_chars = int(row["treatment"]["final_chars"])
    if row["treatment"]["codec"] == "SENTINEL" and greedy_chars != control_chars:
        raise DA078Error("Reconstructed DA-038 charge differs")
    if optimal_chars > greedy_chars:
        raise DA078Error("Optimal parse expands over greedy parse")
    order = "\0".join(
        f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors
    )
    digest = hashlib.sha256(order.encode()).hexdigest()
    if optimal_chars >= control_chars:
        return {
            "codec": "DA038",
            "sentinel": sentinel,
            "control_chars": control_chars,
            "optimal_chars": optimal_chars,
            "selected_chars": control_chars,
            "savings": 0,
            "final_chars": control_chars,
            "immutable_order_sha256": digest,
            "actions": [],
        }

    used = optimal_chars
    present = {(identity, index) for identity, members in descriptors for index in members}
    attempted: set[tuple[str, int]] = set()
    actions = []
    for position, source in enumerate(row["baseline_actions"]):
        neighbor = str(source["neighbor_id"])
        pair = pair_for(neighbor)
        for member_index, member in enumerate(pair):
            key = (neighbor, member_index)
            if key in present or key in attempted:
                continue
            attempted.add(key)
            text = str(member["text"])
            next_role = append_role_pair(role, [member])
            encoded = optimal_encode([text], history, sentinel)
            if decode_members(encoded, history, sentinel) != (text,):
                raise DA078Error("Optimal appended decode differs")
            cost = (
                next_role.chars - role.chars - len(text)
                + encoded_chars(encoded, sentinel, len(history))
            )
            if used + cost > BUDGET:
                actions.append({
                    "position": position,
                    "seed_id": source.get("seed_id"),
                    "neighbor_id": neighbor,
                    "kind": "SKIP_MEMBER",
                    "member": member_index,
                    "cost": 0,
                    "attempt_cost": cost,
                })
                continue
            role = next_role
            history.append(text)
            used += cost
            present.add(key)
            actions.append({
                "position": position,
                "seed_id": source.get("seed_id"),
                "neighbor_id": neighbor,
                "kind": "MEMBER",
                "member": member_index,
                "cost": cost,
            })
    return {
        "codec": "OPTIMAL_SENTINEL",
        "sentinel": sentinel,
        "control_chars": control_chars,
        "optimal_chars": optimal_chars,
        "selected_chars": optimal_chars,
        "savings": control_chars - optimal_chars,
        "final_chars": used,
        "immutable_order_sha256": digest,
        "actions": actions,
    }


def build_rows(longmem_path: Path, population_path: Path,
               da038_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da038_path) != DA038_SHA256:
        raise DA078Error("Sealed DA-038 allocation differs")
    source = list(read_gzip(da038_path))
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
    }
    output = []
    for row in source:
        by_id = {
            episode.candidate.identity: episode
            for episode in records[str(row["question_id"])].episodes
        }
        treatment = allocate(row, lambda identity: by_id[identity].members)
        output.append({**row, "da038_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA078Error("DA-078 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_preflight(longmem_path: Path, population_path: Path,
                  da038_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da038_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_allocations.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da078-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(longmem_path, population_path, da038_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    codecs = Counter(row["treatment"]["codec"] for row in rows)
    actions = Counter(
        action["kind"] for row in rows for action in row["treatment"]["actions"]
    )
    savings = [int(row["treatment"]["savings"]) for row in rows]
    passed = (
        identical
        and codecs["OPTIMAL_SENTINEL"] > 0
        and actions["MEMBER"] > 0
        and actions["SKIP_MEMBER"] > 0
        and all(row["treatment"]["selected_chars"] <= row["da038_control"]["final_chars"] for row in rows)
        and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET
    )
    result = {
        "schema": "da078-protected-optimal-sentinel-preflight-v1",
        "status": "PASS" if passed else "FAIL",
        "questions": len(rows),
        "codecs": dict(codecs),
        "actions": dict(actions),
        "immutable_da038": True,
        "median_selected_savings": float(np.median(savings)),
        "p10_selected_savings": float(np.percentile(savings, 10)),
        "p90_selected_savings": float(np.percentile(savings, 90)),
        "max_final_chars": max(row["treatment"]["final_chars"] for row in rows),
        "replay_byte_identical": identical,
        "allocation_sha256": sha256_file(artifact),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
    }
    (output_dir / "preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not passed:
        raise DA078Error("DA-078 blind preflight failed")
    return result


__all__ = ["DA078Error", "allocate", "build_rows", "run_preflight"]
