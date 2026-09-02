"""Blind residual-tail atomic allocation for DA-026."""

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
from analysis.da015_phrase_dictionary import encode
from analysis.da016_allocation import BUDGET
from analysis.da024_audit import _baseline_payloads, _costs

DA023_SHA256 = "2982a79056945933267525701281ce8ae7882224ad5e9f2427e008c53fa221e4"


class DA026Error(RuntimeError):
    pass


def allocate_tail(row: Mapping[str, Any], pair_for: Any, dictionary: Any) -> dict[str, Any]:
    payloads = _baseline_payloads(row, pair_for)
    present: set[tuple[str, int]] = set()
    for identity in row["direct_ids"]:
        present.update((str(identity), index) for index in (0, 1))
    for action in row["baseline_actions"]:
        neighbor = str(action["neighbor_id"])
        if action["kind"] == "PAIR":
            present.update((neighbor, index) for index in (0, 1))
        elif action["kind"] == "TURN":
            present.add((neighbor, int(action["member"])))

    for action in row["treatment"]["additions"]:
        neighbor = str(action["neighbor_id"])
        pair = pair_for(neighbor)
        if action["kind"] == "PAIR":
            payloads.append(list(pair))
            present.update((neighbor, index) for index in (0, 1))
        elif action["kind"] == "TURN":
            member = int(action["member"])
            payloads.append([pair[member]])
            present.add((neighbor, member))

    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    used = int(row["treatment"]["final_chars"])
    actions = []
    attempted: set[tuple[str, int]] = set()
    for position, source in enumerate(row["baseline_actions"]):
        neighbor = str(source["neighbor_id"])
        pair = pair_for(neighbor)
        for member_index in (0, 1):
            key = (neighbor, member_index)
            if key in present or key in attempted:
                continue
            attempted.add(key)
            _, turns = _costs(row["treatment"]["renderer"], role, history, pair,
                              row["treatment"]["prefix"], dictionary)
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
    return {"renderer": row["treatment"]["renderer"], "prefix": row["treatment"]["prefix"],
            "immutable_final_chars": int(row["treatment"]["final_chars"]),
            "final_chars": used, "actions": actions}


def build_rows(longmem_path: Path, population_path: Path, da023_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da023_path) != DA023_SHA256:
        raise DA026Error("DA-023 blind artifact differs")
    source = [row for row in read_gzip(da023_path) if row["corpus"] == "LONGMEM"]
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        record = records[str(row["question_id"])]
        by_id = {episode.candidate.identity: episode for episode in record.episodes}
        direct_texts = [str(member["text"]) for identity in row["direct_ids"]
                        for member in by_id[identity].members]
        tail = allocate_tail(row, lambda identity: by_id[identity].members, encode(direct_texts))
        output.append({"question_id": row["question_id"], "question_type": row["question_type"],
                       "direct_ids": row["direct_ids"], "baseline_actions": row["baseline_actions"],
                       "da023": row["treatment"], "tail": tail})
    if len(output) != 465:
        raise DA026Error("DA-026 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, da023_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da023_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da026-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da023_path))
        identical = path.read_bytes() == replay.read_bytes()
    actions = Counter(action["kind"] for row in rows for action in row["tail"]["actions"])
    immutable = all(row["tail"]["immutable_final_chars"] == row["da023"]["final_chars"] for row in rows)
    passed = (identical and immutable and actions["MEMBER"] > 0 and actions["SKIP_MEMBER"] > 0
              and max(row["tail"]["final_chars"] for row in rows) <= BUDGET)
    result = {"schema": "da026-protected-tail-preflight-v1", "status": "PASS" if passed else "FAIL",
              "questions": len(rows), "actions": dict(actions), "immutable_da023": immutable,
              "max_final_chars": max(row["tail"]["final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA026Error("DA-026 blind preflight failed")
    return result


__all__ = ["DA026Error", "allocate_tail", "run_preflight"]

