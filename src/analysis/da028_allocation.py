"""Blind shortest-exact-codec allocation for DA-028."""

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
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da027_allocation import DA023_SHA256, _candidate_texts, _costs, _descriptors
from analysis.da027_compact_backrefs import decode_members, encode_members, encoded_chars, prefix_for
from analysis.nf004_anatomy_features import load_blind_cases

BUDGET = 16_000


class DA028Error(RuntimeError):
    pass


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    descriptors = _descriptors(row, pair_for)
    payloads = [[pair_for(identity)[index] for index in members] for identity, members in descriptors]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    texts = [str(member["text"]) for payload in payloads for member in payload]
    prefix = prefix_for(_candidate_texts(row, pair_for))
    encoded = encode_members(texts, (), prefix)
    if decode_members(encoded, ()) != tuple(texts):
        raise DA028Error("Compact immutable decode differs")
    compact = role.chars - sum(map(len, texts)) + encoded_chars(encoded, prefix)
    control = int(row["treatment"]["final_chars"])
    expected = ["\n".join(f"{member['speaker']}: {member['text']}" for member in payload)
                for payload in payloads]
    if decode_role_pairs(role) != expected:
        raise DA028Error("Immutable role payload differs")
    identity_order = [f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors]
    digest = hashlib.sha256("\0".join(identity_order).encode()).hexdigest()
    if compact >= control:
        return {"codec": "DA023", "prefix": row["treatment"]["prefix"],
                "da023_chars": control, "compact_chars": compact, "selected_chars": control,
                "savings": 0, "final_chars": control, "immutable_order_sha256": digest,
                "actions": []}

    used, history = compact, list(texts)
    seen = {identity for identity, _ in descriptors}
    actions = []
    for source in row["treatment"]["additions"]:
        if source["kind"] != "SKIP":
            continue
        neighbor = str(source["neighbor_id"])
        if neighbor in seen:
            continue
        seen.add(neighbor)
        pair = pair_for(neighbor)
        full, turns, _, _ = _costs(role, history, pair, prefix)
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
    return {"codec": "COMPACT", "prefix": prefix, "da023_chars": control,
            "compact_chars": compact, "selected_chars": compact, "savings": control - compact,
            "final_chars": used, "immutable_order_sha256": digest, "actions": actions}


def build_rows(locomo_path: Path, longmem_path: Path, population_path: Path,
               da023_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da023_path) != DA023_SHA256:
        raise DA028Error("DA-023 blind artifact differs")
    source = list(read_gzip(da023_path))
    nf_members, _ = _member_maps(locomo_path, load_blind_cases(locomo_path))
    long_records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        if row["corpus"] == "NF004":
            treatment = allocate(row, lambda identity: nf_members[identity])
            output.append({"corpus": "NF004", "comparison_key": row["comparison_key"],
                           "duplicate_ordinal": row["duplicate_ordinal"], "sample_id": row["sample_id"],
                           "source_index": row["source_index"], "direct_ids": row["direct_ids"],
                           "baseline_actions": row["baseline_actions"], "da023": row["treatment"],
                           "treatment": treatment})
        else:
            record = long_records[str(row["question_id"])]
            by_id = {episode.candidate.identity: episode for episode in record.episodes}
            treatment = allocate(row, lambda identity: by_id[identity].members)
            output.append({"corpus": "LONGMEM", "question_id": row["question_id"],
                           "question_type": row["question_type"], "direct_ids": row["direct_ids"],
                           "baseline_actions": row["baseline_actions"], "da023": row["treatment"],
                           "treatment": treatment})
    if Counter(row["corpus"] for row in output) != Counter({"NF004": 1098, "LONGMEM": 465}):
        raise DA028Error("DA-028 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(locomo_path: Path, longmem_path: Path, population_path: Path,
                  da023_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(locomo_path, longmem_path, population_path, da023_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da028-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(locomo_path, longmem_path, population_path, da023_path))
        identical = path.read_bytes() == replay.read_bytes()
    corpora = {}
    passed = identical
    for corpus in ("NF004", "LONGMEM"):
        subset = [row for row in rows if row["corpus"] == corpus]
        codecs = Counter(row["treatment"]["codec"] for row in subset)
        actions = Counter(action["kind"] for row in subset for action in row["treatment"]["actions"])
        savings = [row["treatment"]["savings"] for row in subset]
        cell = {"questions": len(subset), "codecs": dict(codecs), "actions": dict(actions),
                "median_selected_savings": float(np.median(savings)),
                "p10_selected_savings": float(np.percentile(savings, 10)),
                "p90_selected_savings": float(np.percentile(savings, 90)),
                "max_final_chars": max(row["treatment"]["final_chars"] for row in subset)}
        corpora[corpus] = cell
        passed = passed and all(row["treatment"]["selected_chars"] <= row["treatment"]["da023_chars"]
                                for row in subset)
        passed = passed and codecs["COMPACT"] > 0 and actions["PAIR"] > 0 and actions["TURN"] > 0 and actions["SKIP"] > 0
        passed = passed and cell["median_selected_savings"] >= 64 and cell["max_final_chars"] <= BUDGET
        if corpus == "LONGMEM":
            passed = passed and codecs["DA023"] > 0
    result = {"schema": "da028-shortest-codec-preflight-v1", "status": "PASS" if passed else "FAIL",
              "rows": len(rows), "corpora": corpora, "replay_byte_identical": identical,
              "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA028Error("DA-028 blind preflight failed")
    return result


__all__ = ["DA028Error", "allocate", "run_preflight"]

