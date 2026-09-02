"""Blind compact dependency frontier appended after immutable DA-038."""

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
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da031_varint_backrefs import decode_uint, encode_uint
from analysis.da034_allocation import _descriptors

BUDGET = 16_000
DA038_SHA256 = "7758e13562c536fd5123583ccbf0082fd8f3315ddf29a68d74f10f12ee42703e"


class DA040Error(RuntimeError):
    pass


def reference_code(sentinel: str, position: int, member: int) -> str:
    if not sentinel or set(sentinel) != {"~"} or position < 0 or member < 0:
        raise DA040Error("Invalid dependency reference")
    return f"{sentinel}L{encode_uint(position)}{encode_uint(member)}{sentinel}"


def parse_reference(code: str, sentinel: str) -> tuple[int, int]:
    opening = sentinel + "L"
    if not code.startswith(opening) or not code.endswith(sentinel):
        raise DA040Error("Malformed dependency reference")
    body = code[len(opening):-len(sentinel)]
    position, cursor = decode_uint(body, 0)
    member, cursor = decode_uint(body, cursor)
    if cursor != len(body) or reference_code(sentinel, position, member) != code:
        raise DA040Error("Noncanonical dependency reference")
    return position, member


def _protected_descriptors(row: Mapping[str, Any], pair_for: Any) -> list[tuple[str, tuple[int, ...]]]:
    da031_row = {**row, "treatment": row["da031_control"]}
    descriptors = _descriptors(da031_row, pair_for)
    for action in row["da033_control"]["actions"]:
        if action["kind"] == "MEMBER":
            descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
    for action in row["treatment"]["actions"]:
        if action["kind"] == "MEMBER":
            descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
    return descriptors


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    descriptors = _protected_descriptors(row, pair_for)
    order = "\0".join(f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors)
    digest = hashlib.sha256(order.encode()).hexdigest()
    present = {(identity, member) for identity, members in descriptors for member in members}
    attempted: set[tuple[str, int]] = set()
    used = int(row["treatment"]["final_chars"])
    sentinel = str(row["treatment"]["sentinel"])
    actions = []
    for position, source in enumerate(row["baseline_actions"]):
        neighbor = str(source["neighbor_id"])
        pair = pair_for(neighbor)
        for member in range(len(pair)):
            target = (neighbor, member)
            if target in present or target in attempted:
                continue
            attempted.add(target)
            code = reference_code(sentinel, position, member)
            resolved_position, resolved_member = parse_reference(code, sentinel)
            resolved_neighbor = str(row["baseline_actions"][resolved_position]["neighbor_id"])
            if (resolved_neighbor, resolved_member) != target:
                raise DA040Error("Dependency reference resolves to another member")
            if used + len(code) > BUDGET:
                actions.append({"position": position, "neighbor_id": neighbor,
                                "member": member, "kind": "SKIP_REF",
                                "code": code, "cost": 0, "attempt_cost": len(code)})
                continue
            used += len(code)
            actions.append({"position": position, "neighbor_id": neighbor,
                            "member": member, "kind": "REF", "code": code,
                            "cost": len(code)})
    return {"codec": "LOCAL_MEMBER_REF", "immutable_final_chars": int(row["treatment"]["final_chars"]),
            "immutable_order_sha256": digest, "sentinel": sentinel,
            "final_chars": used, "actions": actions}


def build_rows(longmem_path: Path, population_path: Path, da038_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da038_path) != DA038_SHA256:
        raise DA040Error("DA-038 blind artifact differs")
    source = list(read_gzip(da038_path))
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        by_id = {episode.candidate.identity: episode for episode in records[str(row["question_id"])].episodes}
        treatment = allocate(row, lambda identity: by_id[identity].members)
        output.append({**row, "da038_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA040Error("DA-040 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, da038_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da038_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_frontier.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da040-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da038_path))
        identical = path.read_bytes() == replay.read_bytes()
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["actions"])
    refs = [action for row in rows for action in row["treatment"]["actions"] if action["kind"] == "REF"]
    immutable = all(row["treatment"]["immutable_final_chars"] == row["da038_control"]["final_chars"]
                    for row in rows)
    passed = (identical and immutable and actions["REF"] > 0 and actions["SKIP_REF"] > 0
              and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET
              and len({(row["question_id"], action["neighbor_id"], action["member"])
                       for row in rows for action in row["treatment"]["actions"]
                       if action["kind"] == "REF"}) == len(refs))
    result = {"schema": "da040-compact-dependency-frontier-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "actions": dict(actions), "immutable_da038": immutable,
              "reference_cost": {"p10": float(np.percentile([row["cost"] for row in refs], 10)),
                                 "p50": float(np.percentile([row["cost"] for row in refs], 50)),
                                 "p90": float(np.percentile([row["cost"] for row in refs], 90))},
              "max_final_chars": max(row["treatment"]["final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA040Error("DA-040 blind preflight failed")
    return result


__all__ = ["DA040Error", "allocate", "parse_reference", "reference_code", "run_preflight"]
