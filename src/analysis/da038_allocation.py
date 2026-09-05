"""Blind sentinel re-encoding of the protected DA-033 pack."""

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
from analysis.da034_allocation import _candidate_texts, _costs, _descriptors
from analysis.da034_sentinel_backrefs import decode_members, encode_members, encoded_chars, sentinel_for

BUDGET = 16_000
DA033_SHA256 = "22b918036e5ecbd00c0cc032eef61f587b02c1c347505d458b310cd34a961d8e"


class DA038Error(RuntimeError):
    pass


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    da031_row = {**row, "treatment": row["da031_control"]}
    descriptors = _descriptors(da031_row, pair_for)
    for action in row["treatment"]["actions"]:
        if action["kind"] == "MEMBER":
            descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
    payloads = [[pair_for(identity)[index] for index in members] for identity, members in descriptors]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    sentinel = sentinel_for(_candidate_texts(da031_row, pair_for))
    encoded = encode_members(history, (), sentinel)
    if decode_members(encoded, (), sentinel) != tuple(history):
        raise DA038Error("Sentinel protected decode differs")
    sentinel_chars = role.chars - sum(map(len, history)) + encoded_chars(encoded, sentinel)
    control_chars = int(row["treatment"]["final_chars"])
    order = "\0".join(f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors)
    digest = hashlib.sha256(order.encode()).hexdigest()
    if sentinel_chars >= control_chars:
        return {"codec": "DA033", "sentinel": sentinel, "control_chars": control_chars,
                "sentinel_chars": sentinel_chars, "selected_chars": control_chars,
                "savings": 0, "final_chars": control_chars,
                "immutable_order_sha256": digest, "actions": []}
    used = sentinel_chars
    present = {(identity, index) for identity, members in descriptors for index in members}
    attempted: set[tuple[str, int]] = set()
    actions = []
    for position, source in enumerate(row["baseline_actions"]):
        neighbor = str(source["neighbor_id"])
        pair = pair_for(neighbor)
        for member_index in range(len(pair)):
            key = (neighbor, member_index)
            if key in present or key in attempted:
                continue
            attempted.add(key)
            cost = int(_costs(role, history, pair, sentinel)[1][member_index])
            if used + cost > BUDGET:
                actions.append({"position": position, "seed_id": source.get("seed_id"),
                                "neighbor_id": neighbor, "kind": "SKIP_MEMBER",
                                "member": member_index, "cost": 0, "attempt_cost": cost})
                continue
            role = append_role_pair(role, [pair[member_index]])
            history.append(str(pair[member_index]["text"]))
            used += cost
            present.add(key)
            actions.append({"position": position, "seed_id": source.get("seed_id"),
                            "neighbor_id": neighbor, "kind": "MEMBER",
                            "member": member_index, "cost": cost})
    return {"codec": "SENTINEL", "sentinel": sentinel, "control_chars": control_chars,
            "sentinel_chars": sentinel_chars, "selected_chars": sentinel_chars,
            "savings": control_chars - sentinel_chars, "final_chars": used,
            "immutable_order_sha256": digest, "actions": actions}


def build_rows(longmem_path: Path, population_path: Path, da033_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da033_path) != DA033_SHA256:
        raise DA038Error("DA-033 blind artifact differs")
    source = list(read_gzip(da033_path))
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        by_id = {episode.candidate.identity: episode for episode in records[str(row["question_id"])].episodes}
        treatment = allocate(row, lambda identity: by_id[identity].members)
        output.append({**row, "da033_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA038Error("DA-038 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, da033_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da033_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da038-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da033_path))
        identical = path.read_bytes() == replay.read_bytes()
    codecs = Counter(row["treatment"]["codec"] for row in rows)
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["actions"])
    savings = [int(row["treatment"]["savings"]) for row in rows]
    immutable = all(row["treatment"]["selected_chars"] <= row["da033_control"]["final_chars"]
                    for row in rows)
    passed = (identical and immutable and codecs["SENTINEL"] > 0 and actions["MEMBER"] > 0
              and actions["SKIP_MEMBER"] > 0
              and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET)
    result = {"schema": "da038-protected-da033-sentinel-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "codecs": dict(codecs), "actions": dict(actions), "immutable_da033": immutable,
              "median_selected_savings": float(np.median(savings)),
              "p10_selected_savings": float(np.percentile(savings, 10)),
              "p90_selected_savings": float(np.percentile(savings, 90)),
              "max_final_chars": max(row["treatment"]["final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA038Error("DA-038 blind preflight failed")
    return result


__all__ = ["DA038Error", "allocate", "run_preflight"]
