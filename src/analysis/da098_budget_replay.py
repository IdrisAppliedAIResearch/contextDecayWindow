"""Frozen nested NF 16k/32k architecture replay for DA-098."""

from __future__ import annotations

import gzip
import gc
import hashlib
import json
import platform
import tempfile
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import sha256_file
from analysis.da034_allocation import _costs, _descriptors
from analysis.da034_sentinel_backrefs import decode_members, encode_members, encoded_chars
from analysis.da099_indexed_sentinel import IndexedSentinelCodec, encoded_length
from analysis.da099_role_charge import IncrementalRoleCharge
from analysis.nf004_anatomy_features import load_blind_cases
from analysis.nf004_mechanism import pack, ranking_orders
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256

BUDGET_16 = 16_000
BUDGET_32 = 32_000
DA035_SHA256 = "97ecf4eb74b0c88914dafa6f063643249662e0b264d623a9c311a2b20e35ebd7"


class DA098Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _digest_members(values: Sequence[tuple[str, int]]) -> str:
    return hashlib.sha256(
        "\0".join(f"{identity}:{member}" for identity, member in values).encode()
    ).hexdigest()


def _prefix_inputs(row: Mapping[str, Any], pair_for: Any) -> tuple[
    list[tuple[str, int]], Any, list[str], str
]:
    descriptors = _descriptors({**row, "treatment": row["da031_control"]}, pair_for)
    for action in row["treatment"]["actions"]:
        if action["kind"] == "MEMBER":
            descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
    payloads = [
        [pair_for(identity)[index] for index in members]
        for identity, members in descriptors
    ]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    sentinel = str(row["treatment"]["sentinel"])
    selected = [(identity, index) for identity, members in descriptors for index in members]
    if len(selected) != len(set(selected)):
        raise DA098Error("ARCH_16 contains duplicate members")
    return selected, role, history, sentinel


def _prefix(row: Mapping[str, Any], pair_for: Any) -> tuple[
    list[tuple[str, int]], Any, list[str], str, int
]:
    selected, role, history, sentinel = _prefix_inputs(row, pair_for)
    encoded = encode_members(history, (), sentinel)
    if decode_members(encoded, (), sentinel) != tuple(history):
        raise DA098Error("ARCH_16 prefix decode differs")
    used = role.chars - sum(map(len, history)) + encoded_chars(encoded, sentinel)
    if used != int(row["treatment"]["final_chars"]):
        raise DA098Error("ARCH_16 exact charge differs")

    return selected, role, history, sentinel, used


def _indexed_prefix(row: Mapping[str, Any], pair_for: Any) -> tuple[
    list[tuple[str, int]], Any, list[str], str, int, IndexedSentinelCodec
]:
    selected, role, history, sentinel = _prefix_inputs(row, pair_for)
    codec = IndexedSentinelCodec((), sentinel)
    encoded = codec.encode_and_append(history)
    if decode_members(encoded, (), sentinel) != tuple(history):
        raise DA098Error("Indexed ARCH_16 prefix decode differs")
    used = role.chars - sum(map(len, history)) + encoded_length(encoded, sentinel)
    if used != int(row["treatment"]["final_chars"]):
        raise DA098Error("Indexed ARCH_16 exact charge differs")
    return selected, role, history, sentinel, used, codec


def _result(selected: list[tuple[str, int]], prefix_count: int, prefix_chars: int,
            prefix_digest: str, sentinel: str, used: int,
            actions: list[dict[str, Any]]) -> dict[str, Any]:
    if _digest_members(selected[:prefix_count]) != prefix_digest:
        raise DA098Error("ARCH_16 prefix order changed")
    if used > BUDGET_32 or len(selected) != len(set(selected)):
        raise DA098Error("ARCH_32 budget or duplicate gate fails")
    return {
        "prefix_members": prefix_count,
        "prefix_chars": prefix_chars,
        "prefix_sha256": prefix_digest,
        "sentinel": sentinel,
        "final_chars": used,
        "selected_members": [[identity, index] for identity, index in selected],
        "selected_sha256": _digest_members(selected),
        "actions": actions,
    }


def allocate_32_legacy(row: Mapping[str, Any], pair_for: Any,
                       pair_order: Sequence[str]) -> dict[str, Any]:
    selected, role, history, sentinel, used = _prefix(row, pair_for)
    prefix_count = len(selected)
    present = set(selected)
    prefix_digest = _digest_members(selected)
    actions: list[dict[str, Any]] = []
    for rank, identity in enumerate(pair_order, start=1):
        pair = pair_for(identity)
        for member_index, member in enumerate(pair):
            key = (identity, member_index)
            if key in present:
                actions.append({
                    "rank": rank, "identity": identity, "member": member_index,
                    "kind": "PRESENT", "cost": 0,
                })
                continue
            if sentinel in str(member["text"]):
                raise DA098Error("Frozen sentinel occurs in 32k tail member")
            cost = _costs(role, history, pair, sentinel)[1][member_index]
            if used + cost > BUDGET_32:
                actions.append({
                    "rank": rank, "identity": identity, "member": member_index,
                    "kind": "SKIP_MEMBER", "cost": 0, "attempt_cost": cost,
                })
                continue
            role = append_role_pair(role, [member])
            history.append(str(member["text"]))
            used += cost
            present.add(key)
            selected.append(key)
            actions.append({
                "rank": rank, "identity": identity, "member": member_index,
                "kind": "MEMBER", "cost": cost,
            })
    return _result(selected, prefix_count, int(row["treatment"]["final_chars"]),
                   prefix_digest, sentinel, used, actions)


@contextmanager
def suspended_gc():
    enabled = gc.isenabled()
    if enabled:
        gc.disable()
    try:
        yield
    finally:
        if enabled:
            gc.enable()


def _allocate_32_indexed(row: Mapping[str, Any], pair_for: Any,
                         pair_order: Sequence[str],
                         timing_sink: list[int] | None = None) -> dict[str, Any]:
    started = time.perf_counter_ns()
    selected, role, history, sentinel, used, codec = _indexed_prefix(row, pair_for)
    prefix_count = len(selected)
    present = set(selected)
    prefix_digest = _digest_members(selected)
    role_charge = IncrementalRoleCharge(role)
    actions: list[dict[str, Any]] = []
    for rank, identity in enumerate(pair_order, start=1):
        pair = pair_for(identity)
        texts = [str(member["text"]) for member in pair]
        for member_index, member in enumerate(pair):
            key = (identity, member_index)
            if key in present:
                actions.append({
                    "rank": rank, "identity": identity, "member": member_index,
                    "kind": "PRESENT", "cost": 0,
                })
                continue
            role_cost = role_charge.cost([member])
            cost = (role_cost - len(texts[member_index])
                    + codec.encoded_text_length(texts[member_index]))
            if used + cost > BUDGET_32:
                actions.append({
                    "rank": rank, "identity": identity, "member": member_index,
                    "kind": "SKIP_MEMBER", "cost": 0, "attempt_cost": cost,
                })
                continue
            if role_charge.cost([member], commit=True) != role_cost:
                raise DA098Error("Indexed role charge changed on commit")
            history.append(texts[member_index])
            codec.append([texts[member_index]])
            used += cost
            present.add(key)
            selected.append(key)
            actions.append({
                "rank": rank, "identity": identity, "member": member_index,
                "kind": "MEMBER", "cost": cost,
            })
    result = _result(selected, prefix_count, int(row["treatment"]["final_chars"]),
                     prefix_digest, sentinel, used, actions)
    if timing_sink is not None:
        timing_sink.append(time.perf_counter_ns() - started)
    return result


def allocate_32(row: Mapping[str, Any], pair_for: Any,
                pair_order: Sequence[str],
                timing_sink: list[int] | None = None) -> dict[str, Any]:
    with suspended_gc():
        return _allocate_32_indexed(row, pair_for, pair_order, timing_sink)


def build_rows(dataset_path: Path, cache_path: Path, manifest_path: Path,
               da035_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if sha256_file(da035_path) != DA035_SHA256:
        raise DA098Error("Sealed DA-035 allocation differs")
    from episodic import EmbeddingCache

    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    controls = {
        (str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
        for row in _read(da035_path)
    }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cache_record = manifest["cache"]
    rows: list[dict[str, Any]] = []
    allocation_ns: list[int] = []
    with EmbeddingCache(
        cache_path,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for case in cases:
            candidates = case["candidates"]
            matrix = np.vstack([
                np.asarray(cache(candidate.text), dtype=np.float32)
                for candidate in candidates
            ])
            for question in case["questions"]:
                key = (str(question["comparison_key"]), int(question["duplicate_ordinal"]))
                if key not in controls:
                    continue
                query = np.asarray(cache(question["text"]), dtype=np.float32)
                _, order = ranking_orders(candidates, matrix, query)
                pair_order = [candidates[index].identity for index in order]
                pair16 = pack(candidates, order, BUDGET_16)
                pair32 = pack(candidates, order, BUDGET_32)
                control = controls[key]
                arch32 = allocate_32(control, lambda identity: members[identity], pair_order,
                                     allocation_ns)
                rows.append({
                    "comparison_key": key[0],
                    "duplicate_ordinal": key[1],
                    "sample_id": str(question["sample_id"]),
                    "source_index": int(question["source_index"]),
                    "pair_order_sha256": hashlib.sha256("\0".join(pair_order).encode()).hexdigest(),
                    "pair16": {
                        "selected_ids": list(pair16.selected), "packed_chars": pair16.packed_chars,
                    },
                    "pair32": {
                        "selected_ids": list(pair32.selected), "packed_chars": pair32.packed_chars,
                    },
                    "arch16_member_sha256": arch32["prefix_sha256"],
                    "arch16_chars": arch32["prefix_chars"],
                    "arch32": arch32,
                })
        reuse = cache.record()
        reuse["allocation_ns"] = allocation_ns
    rows.sort(key=lambda row: (row["comparison_key"], row["duplicate_ordinal"]))
    if len(rows) != 1_098 or set(controls) - {
        (row["comparison_key"], row["duplicate_ordinal"]) for row in rows
    }:
        raise DA098Error("DA-098 population differs")
    return rows, reuse


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, cache_path: Path, manifest_path: Path,
                  da035_path: Path, output_dir: Path) -> dict[str, Any]:
    wall_started = time.perf_counter_ns()
    rows, reuse = build_rows(dataset_path, cache_path, manifest_path, da035_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_allocations.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da098-") as directory:
        replay_rows, replay_reuse = build_rows(dataset_path, cache_path, manifest_path, da035_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = artifact.read_bytes() == replay.read_bytes()
    primary = rows
    actions = Counter(
        action["kind"] for row in primary for action in row["arch32"]["actions"]
    )
    timings_ms = np.asarray(reuse["allocation_ns"], dtype=np.float64) / 1_000_000
    replay_timings_ms = np.asarray(replay_reuse["allocation_ns"], dtype=np.float64) / 1_000_000
    passed = (
        len(primary) == 1_098
        and identical
        and reuse["misses"] == replay_reuse["misses"] == 0
        and actions["MEMBER"] > 0
        and actions["SKIP_MEMBER"] > 0
        and max(row["arch32"]["final_chars"] for row in primary) <= BUDGET_32
    )
    result = {
        "schema": "da098-nf-frozen-budget-preflight-v1",
        "status": "PASS" if passed else "FAIL",
        "rows": len(rows),
        "primary": len(primary),
        "actions": dict(actions),
        "arch16_chars": {
            "min": min(row["arch16_chars"] for row in primary),
            "max": max(row["arch16_chars"] for row in primary),
        },
        "arch32_max_chars": max(row["arch32"]["final_chars"] for row in primary),
        "replay_byte_identical": identical,
        "allocation_sha256": sha256_file(artifact),
        "cache": {"hits": reuse["hits"], "misses": reuse["misses"]},
        "runtime": {
            "python": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "allocation_ms": {
                "p50": float(np.percentile(timings_ms, 50)),
                "p95": float(np.percentile(timings_ms, 95)),
                "p99": float(np.percentile(timings_ms, 99)),
                "max": float(np.max(timings_ms)),
                "total": float(np.sum(timings_ms)),
            },
            "replay_allocation_ms": {
                "p50": float(np.percentile(replay_timings_ms, 50)),
                "p95": float(np.percentile(replay_timings_ms, 95)),
                "p99": float(np.percentile(replay_timings_ms, 99)),
                "max": float(np.max(replay_timings_ms)),
                "total": float(np.sum(replay_timings_ms)),
            },
            "total_wall_ms": (time.perf_counter_ns() - wall_started) / 1_000_000,
        },
        "calls": {"embedding": 0, "model": 0, "cache_access": reuse["hits"]},
    }
    (output_dir / "preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not passed:
        raise DA098Error("DA-098 blind preflight failed")
    return result


__all__ = ["DA098Error", "allocate_32", "allocate_32_legacy", "build_rows",
           "run_preflight", "suspended_gc"]
