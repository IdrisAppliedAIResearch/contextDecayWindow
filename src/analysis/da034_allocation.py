"""Blind NF sentinel-varint allocation for DA-034."""

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
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, decode_role_pairs, role_pattern_pairs
from analysis.da013_preflight import sha256_file
from analysis.da031_allocation import _descriptors_for_control
from analysis.da034_sentinel_backrefs import decode_members, encode_members, encoded_chars, sentinel_for
from analysis.nf004_anatomy_features import load_blind_cases

BUDGET = 16_000
DA031_SHA256 = "84c56868ce44a8349a0eee5fccdf5e1c5dde45aff28f17059470558125d25b57"


class DA034Error(RuntimeError):
    pass


def _descriptors(row: Mapping[str, Any], pair_for: Any) -> list[tuple[str, tuple[int, ...]]]:
    descriptors = _descriptors_for_control({**row, "treatment": row["control"]}, pair_for)
    for action in row["treatment"]["actions"]:
        neighbor = str(action["neighbor_id"])
        if action["kind"] == "PAIR":
            descriptors.append((neighbor, tuple(range(len(pair_for(neighbor))))))
        elif action["kind"] == "TURN":
            descriptors.append((neighbor, (int(action["member"]),)))
    return descriptors


def _candidate_texts(row: Mapping[str, Any], pair_for: Any) -> list[str]:
    identities = list(map(str, row["direct_ids"]))
    identities.extend(str(action["neighbor_id"]) for action in row["baseline_actions"])
    return [str(member["text"]) for identity in dict.fromkeys(identities) for member in pair_for(identity)]


def _costs(role: Any, history: Sequence[str], pair: Sequence[Mapping[str, str]],
           sentinel: str) -> tuple[int, tuple[int, ...]]:
    texts = [str(member["text"]) for member in pair]
    pair_encoded = encode_members(texts, history, sentinel)
    if decode_members(pair_encoded, history, sentinel) != tuple(texts):
        raise DA034Error("Sentinel pair decode differs")
    full = (append_role_pair(role, pair).chars - role.chars - sum(map(len, texts))
            + encoded_chars(pair_encoded, sentinel, len(history)))
    turns = []
    for member, text in zip(pair, texts):
        encoded = encode_members([text], history, sentinel)
        if decode_members(encoded, history, sentinel) != (text,):
            raise DA034Error("Sentinel member decode differs")
        turns.append(append_role_pair(role, [member]).chars - role.chars - len(text)
                     + encoded_chars(encoded, sentinel, len(history)))
    return full, tuple(turns)


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    descriptors = _descriptors(row, pair_for)
    payloads = [[pair_for(identity)[index] for index in members] for identity, members in descriptors]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    all_texts = _candidate_texts(row, pair_for)
    sentinel = sentinel_for(all_texts)
    if any(sentinel in text for text in all_texts) or (len(sentinel) > 1 and
                                                       not any(sentinel[:-1] in text for text in all_texts)):
        raise DA034Error("Sentinel is not shortest absent delimiter")
    encoded = encode_members(history, (), sentinel)
    if decode_members(encoded, (), sentinel) != tuple(history):
        raise DA034Error("Sentinel immutable decode differs")
    sentinel_chars = role.chars - sum(map(len, history)) + encoded_chars(encoded, sentinel)
    control_chars = int(row["treatment"]["final_chars"])
    expected = ["\n".join(f"{member['speaker']}: {member['text']}" for member in payload)
                for payload in payloads]
    if decode_role_pairs(role) != expected:
        raise DA034Error("Immutable role sequence differs")
    order = [f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors]
    digest = hashlib.sha256("\0".join(order).encode()).hexdigest()
    if sentinel_chars >= control_chars:
        return {"codec": "DA031", "sentinel": sentinel, "control_chars": control_chars,
                "sentinel_chars": sentinel_chars, "selected_chars": control_chars,
                "savings": 0, "final_chars": control_chars,
                "immutable_order_sha256": digest, "actions": []}
    used, seen = sentinel_chars, {identity for identity, _ in descriptors}
    actions = []
    for source in row["da023"]["additions"]:
        if source["kind"] != "SKIP":
            continue
        neighbor = str(source["neighbor_id"])
        if neighbor in seen:
            continue
        seen.add(neighbor)
        pair = pair_for(neighbor)
        full, turns = _costs(role, history, pair, sentinel)
        member = int(source["member"])
        if used + full <= BUDGET:
            kind, selected, cost, payload = "PAIR", None, full, pair
        elif used + turns[member] <= BUDGET:
            kind, selected, cost, payload = "TURN", member, turns[member], [pair[member]]
        else:
            kind, selected, cost, payload = "SKIP", member, 0, []
        if payload:
            role = append_role_pair(role, payload)
            history.extend(str(item["text"]) for item in payload)
            used += cost
        actions.append({"position": int(source["position"]), "seed_id": source.get("seed_id"),
                        "neighbor_id": neighbor, "kind": kind, "member": selected,
                        "cost": cost, "full_cost": full, "turn_cost": turns[member]})
    return {"codec": "SENTINEL", "sentinel": sentinel, "control_chars": control_chars,
            "sentinel_chars": sentinel_chars, "selected_chars": sentinel_chars,
            "savings": control_chars - sentinel_chars, "final_chars": used,
            "immutable_order_sha256": digest, "actions": actions}


def build_rows(locomo_path: Path, da031_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da031_path) != DA031_SHA256:
        raise DA034Error("DA-031 blind artifact differs")
    source = [row for row in read_gzip(da031_path) if row["corpus"] == "NF004"]
    nf_members, _ = _member_maps(locomo_path, load_blind_cases(locomo_path))
    output = []
    for row in source:
        treatment = allocate(row, lambda identity: nf_members[identity])
        output.append({**row, "da031_control": row["treatment"], "treatment": treatment})
    if len(output) != 1098:
        raise DA034Error("DA-034 population differs")
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
    with tempfile.TemporaryDirectory(prefix="da034-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(locomo_path, da031_path))
        identical = path.read_bytes() == replay.read_bytes()
    codecs = Counter(row["treatment"]["codec"] for row in rows)
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["actions"])
    savings = [row["treatment"]["savings"] for row in rows]
    passed = (identical and codecs["SENTINEL"] > 0 and actions["PAIR"] > 0
              and actions["TURN"] > 0 and actions["SKIP"] > 0
              and float(np.median(savings)) >= 64
              and all(row["treatment"]["selected_chars"] <= row["da031_control"]["final_chars"] for row in rows)
              and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET)
    result = {"schema": "da034-sentinel-preflight-v1", "status": "PASS" if passed else "FAIL",
              "questions": len(rows), "codecs": dict(codecs), "actions": dict(actions),
              "median_selected_savings": float(np.median(savings)),
              "p10_selected_savings": float(np.percentile(savings, 10)),
              "p90_selected_savings": float(np.percentile(savings, 90)),
              "max_final_chars": max(row["treatment"]["final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA034Error("DA-034 blind preflight failed")
    return result


__all__ = ["DA034Error", "allocate", "run_preflight"]

