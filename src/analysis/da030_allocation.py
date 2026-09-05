"""Blind compact-plus-atomic composition allocation for DA-030."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da015_phrase_dictionary import encode
from analysis.da024_audit import _costs as old_costs
from analysis.da027_allocation import _costs as compact_costs, _descriptors
from analysis.nf004_anatomy_features import load_blind_cases

BUDGET = 16_000
DA028_SHA256 = "0ae01f5cdbc4d244c3188778f1b90292211101a56d118e467bd8c9f32b44f21a"


class DA030Error(RuntimeError):
    pass


def _replay(row: Mapping[str, Any], pair_for: Any, dictionary: Any) -> tuple[Any, list[str], set[tuple[str, int]]]:
    source = {**row, "treatment": row["da023"]}
    descriptors = _descriptors(source, pair_for)
    for action in row["treatment"]["actions"]:
        neighbor = str(action["neighbor_id"])
        if action["kind"] == "PAIR":
            descriptors.append((neighbor, tuple(range(len(pair_for(neighbor))))))
        elif action["kind"] == "TURN":
            descriptors.append((neighbor, (int(action["member"]),)))
    payloads = [[pair_for(identity)[index] for index in members] for identity, members in descriptors]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    present = {(identity, index) for identity, members in descriptors for index in members}
    return role, history, present


def allocate(row: Mapping[str, Any], pair_for: Any, dictionary: Any) -> dict[str, Any]:
    role, history, present = _replay(row, pair_for, dictionary)
    used = int(row["treatment"]["final_chars"])
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
            if row["treatment"]["codec"] == "COMPACT":
                _, turns, _, _ = compact_costs(role, history, pair, row["treatment"]["prefix"])
            else:
                _, turns = old_costs(row["da023"]["renderer"], role, history, pair,
                                     row["da023"]["prefix"], dictionary)
            cost = turns[member_index]
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
    return {"codec": row["treatment"]["codec"],
            "immutable_final_chars": int(row["treatment"]["final_chars"]),
            "immutable_order_sha256": row["treatment"]["immutable_order_sha256"],
            "final_chars": used, "actions": actions}


def build_rows(locomo_path: Path, longmem_path: Path, population_path: Path,
               da028_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da028_path) != DA028_SHA256:
        raise DA030Error("DA-028 blind artifact differs")
    source = list(read_gzip(da028_path))
    nf_members, _ = _member_maps(locomo_path, load_blind_cases(locomo_path))
    long_records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        if row["corpus"] == "NF004":
            treatment = allocate(row, lambda identity: nf_members[identity], None)
            output.append({**row, "control": row["treatment"], "treatment": treatment})
        else:
            record = long_records[str(row["question_id"])]
            by_id = {episode.candidate.identity: episode for episode in record.episodes}
            direct_texts = [str(member["text"]) for identity in row["direct_ids"]
                            for member in by_id[identity].members]
            treatment = allocate(row, lambda identity: by_id[identity].members, encode(direct_texts))
            output.append({**row, "control": row["treatment"], "treatment": treatment})
    if Counter(row["corpus"] for row in output) != Counter({"NF004": 1098, "LONGMEM": 465}):
        raise DA030Error("DA-030 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(locomo_path: Path, longmem_path: Path, population_path: Path,
                  da028_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(locomo_path, longmem_path, population_path, da028_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da030-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(locomo_path, longmem_path, population_path, da028_path))
        identical = path.read_bytes() == replay.read_bytes()
    corpora = {}
    passed = identical
    for corpus in ("NF004", "LONGMEM"):
        subset = [row for row in rows if row["corpus"] == corpus]
        actions = Counter(action["kind"] for row in subset for action in row["treatment"]["actions"])
        immutable = all(row["treatment"]["immutable_final_chars"] == row["control"]["final_chars"]
                        and row["treatment"]["codec"] == row["control"]["codec"]
                        and row["treatment"]["immutable_order_sha256"] == row["control"]["immutable_order_sha256"]
                        for row in subset)
        cell = {"questions": len(subset), "actions": dict(actions), "immutable_da028": immutable,
                "max_final_chars": max(row["treatment"]["final_chars"] for row in subset)}
        corpora[corpus] = cell
        passed = passed and immutable and actions["MEMBER"] > 0 and actions["SKIP_MEMBER"] > 0
        passed = passed and cell["max_final_chars"] <= BUDGET
    result = {"schema": "da030-compact-atomic-preflight-v1", "status": "PASS" if passed else "FAIL",
              "rows": len(rows), "corpora": corpora, "replay_byte_identical": identical,
              "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA030Error("DA-030 blind preflight failed")
    return result


__all__ = ["DA030Error", "allocate", "run_preflight"]
