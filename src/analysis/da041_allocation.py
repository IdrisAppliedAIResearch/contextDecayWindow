"""Blind constant-cost head reference for the DA-038 dependency frontier."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da040_allocation import BUDGET, DA038_SHA256, _protected_descriptors


class DA041Error(RuntimeError):
    pass


def head_code(sentinel: str) -> str:
    if not sentinel or set(sentinel) != {"~"}:
        raise DA041Error("Invalid frontier sentinel")
    return f"{sentinel}H{sentinel}"


def parse_head(code: str, sentinel: str) -> None:
    if code != head_code(sentinel):
        raise DA041Error("Noncanonical frontier head")


def _targets(row: Mapping[str, Any], present: set[tuple[str, int]], pair_for: Any) -> list[tuple[str, int]]:
    seen: set[tuple[str, int]] = set()
    output = []
    for source in row["baseline_actions"]:
        neighbor = str(source["neighbor_id"])
        for member in range(len(pair_for(neighbor))):
            target = (neighbor, member)
            if target in present or target in seen:
                continue
            seen.add(target)
            output.append(target)
    return output


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    descriptors = _protected_descriptors(row, pair_for)
    order = "\0".join(f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors)
    digest = hashlib.sha256(order.encode()).hexdigest()
    present = {(identity, member) for identity, members in descriptors for member in members}
    targets = _targets(row, present, pair_for)
    sentinel = str(row["treatment"]["sentinel"])
    code = head_code(sentinel)
    parse_head(code, sentinel)
    used = int(row["treatment"]["final_chars"])
    admitted = bool(targets) and used + len(code) <= BUDGET
    final = used + len(code) if admitted else used
    return {"codec": "FRONTIER_HEAD", "immutable_final_chars": used,
            "immutable_order_sha256": digest, "sentinel": sentinel,
            "kind": "HEAD" if admitted else "SKIP_HEAD", "code": code,
            "cost": len(code) if admitted else 0, "attempt_cost": len(code),
            "targets": [[identity, member] for identity, member in targets],
            "final_chars": final}


def build_rows(longmem_path: Path, population_path: Path, da038_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da038_path) != DA038_SHA256:
        raise DA041Error("DA-038 blind artifact differs")
    source = list(read_gzip(da038_path))
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        by_id = {episode.candidate.identity: episode for episode in records[str(row["question_id"])].episodes}
        treatment = allocate(row, lambda identity: by_id[identity].members)
        output.append({**row, "da038_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA041Error("DA-041 population differs")
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
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_heads.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da041-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da038_path))
        identical = path.read_bytes() == replay.read_bytes()
    kinds = Counter(row["treatment"]["kind"] for row in rows)
    immutable = all(row["treatment"]["immutable_final_chars"] == row["da038_control"]["final_chars"]
                    for row in rows)
    resolved = True
    for row in rows:
        by_id = {episode.candidate.identity: episode
                 for episode in records[str(row["question_id"])].episodes}
        pair_for = lambda identity, mapping=by_id: mapping[identity].members
        base = {**row, "treatment": row["da038_control"]}
        descriptors = _protected_descriptors(base, pair_for)
        present = {(identity, member) for identity, members in descriptors for member in members}
        expected = [[identity, member] for identity, member in _targets(base, present, pair_for)]
        if row["treatment"]["targets"] != expected:
            resolved = False
            break
    passed = (identical and immutable and resolved and kinds["HEAD"] > 0 and kinds["SKIP_HEAD"] > 0
              and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET)
    result = {"schema": "da041-frontier-head-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "kinds": dict(kinds), "immutable_da038": immutable,
              "complete_target_resolution": resolved,
              "head_costs": sorted({row["treatment"]["attempt_cost"] for row in rows}),
              "resolved_targets": sum(len(row["treatment"]["targets"]) for row in rows
                                      if row["treatment"]["kind"] == "HEAD"),
              "max_final_chars": max(row["treatment"]["final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA041Error("DA-041 blind preflight failed")
    return result


__all__ = ["DA041Error", "allocate", "head_code", "parse_head", "run_preflight"]
