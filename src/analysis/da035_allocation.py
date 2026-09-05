"""Blind NF sentinel-capacity atomic allocation for DA-035."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import sha256_file
from analysis.da034_allocation import DA031_SHA256, _candidate_texts, _costs, _descriptors
from analysis.da034_sentinel_backrefs import decode_members, encode_members, encoded_chars, sentinel_for
from analysis.nf004_anatomy_features import load_blind_cases

BUDGET = 16_000


class DA035Error(RuntimeError):
    pass


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    descriptors = _descriptors(row, pair_for)
    payloads = [[pair_for(identity)[index] for index in members] for identity, members in descriptors]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    sentinel = sentinel_for(_candidate_texts(row, pair_for))
    encoded = encode_members(history, (), sentinel)
    if decode_members(encoded, (), sentinel) != tuple(history):
        raise DA035Error("Sentinel immutable decode differs")
    sentinel_chars = role.chars - sum(map(len, history)) + encoded_chars(encoded, sentinel)
    control_chars = int(row["treatment"]["final_chars"])
    order = [f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors]
    digest = hashlib.sha256("\0".join(order).encode()).hexdigest()
    if sentinel_chars >= control_chars:
        return {"codec": "DA031", "sentinel": sentinel, "control_chars": control_chars,
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
            cost = _costs(role, history, pair, sentinel)[1][member_index]
            if used + cost > BUDGET:
                actions.append({"position": position, "seed_id": source.get("seed_id"),
                                "neighbor_id": neighbor, "kind": "SKIP_MEMBER",
                                "member": member_index, "cost": 0, "attempt_cost": cost})
                continue
            member = pair[member_index]
            role = append_role_pair(role, [member])
            history.append(str(member["text"]))
            used += cost
            present.add(key)
            actions.append({"position": position, "seed_id": source.get("seed_id"),
                            "neighbor_id": neighbor, "kind": "MEMBER",
                            "member": member_index, "cost": cost})
    return {"codec": "SENTINEL", "sentinel": sentinel, "control_chars": control_chars,
            "sentinel_chars": sentinel_chars, "selected_chars": sentinel_chars,
            "savings": control_chars - sentinel_chars, "final_chars": used,
            "immutable_order_sha256": digest, "actions": actions}


def build_rows(locomo_path: Path, da031_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da031_path) != DA031_SHA256:
        raise DA035Error("DA-031 blind artifact differs")
    source = [row for row in read_gzip(da031_path) if row["corpus"] == "NF004"]
    nf_members, _ = _member_maps(locomo_path, load_blind_cases(locomo_path))
    output = []
    for row in source:
        treatment = allocate(row, lambda identity: nf_members[identity])
        output.append({**row, "da031_control": row["treatment"], "treatment": treatment})
    if len(output) != 1098:
        raise DA035Error("DA-035 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(locomo_path: Path, da031_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(locomo_path, da031_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da035-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(locomo_path, da031_path))
        identical = path.read_bytes() == replay.read_bytes()
    codecs = Counter(row["treatment"]["codec"] for row in rows)
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["actions"])
    immutable = all(row["treatment"]["selected_chars"] <= row["da031_control"]["final_chars"] for row in rows)
    passed = (identical and immutable and codecs["SENTINEL"] > 0 and actions["MEMBER"] > 0
              and actions["SKIP_MEMBER"] > 0
              and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET)
    result = {"schema": "da035-nf-sentinel-atomic-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "codecs": dict(codecs), "actions": dict(actions), "immutable_da031": immutable,
              "max_final_chars": max(row["treatment"]["final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA035Error("DA-035 blind preflight failed")
    return result


__all__ = ["DA035Error", "allocate", "run_preflight"]

