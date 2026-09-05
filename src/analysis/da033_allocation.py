"""Blind LongMem varint-plus-atomic allocation for DA-033."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da015_phrase_dictionary import encode
from analysis.da024_audit import _costs as old_costs
from analysis.da027_allocation import _costs as compact_costs
from analysis.da031_allocation import _costs as varint_costs, _descriptors_for_control
from analysis.da031_varint_backrefs import encode_members, encoded_chars

BUDGET = 16_000
DA031_SHA256 = "84c56868ce44a8349a0eee5fccdf5e1c5dde45aff28f17059470558125d25b57"


class DA033Error(RuntimeError):
    pass


def _replay(row: Mapping[str, Any], pair_for: Any) -> tuple[Any, list[str], set[tuple[str, int]], str]:
    descriptors = _descriptors_for_control({**row, "treatment": row["control"]}, pair_for)
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
    order = "\0".join(f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors)
    return role, history, present, order


def _turn_costs(row: Mapping[str, Any], role: Any, history: Sequence[str],
                pair: Sequence[Mapping[str, str]], dictionary: Any) -> tuple[int, ...]:
    if row["treatment"]["codec"] == "VARINT":
        return varint_costs(role, history, pair, row["treatment"]["prefix"])[1]
    if row["control"]["codec"] == "COMPACT":
        return compact_costs(role, history, pair, row["control"]["prefix"])[1]
    return old_costs(row["da023"]["renderer"], role, history, pair,
                     row["da023"]["prefix"], dictionary)[1]


def allocate(row: Mapping[str, Any], pair_for: Any, dictionary: Any) -> dict[str, Any]:
    role, history, present, order = _replay(row, pair_for)
    used = int(row["treatment"]["final_chars"])
    if row["treatment"]["codec"] == "VARINT":
        encoded = encode_members(history, (), row["treatment"]["prefix"])
        actual = role.chars - sum(map(len, history)) + encoded_chars(encoded, row["treatment"]["prefix"])
        if actual != used:
            raise DA033Error("DA-031 varint charge replay differs")
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
            cost = _turn_costs(row, role, history, pair, dictionary)[member_index]
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
            "immutable_order_sha256": hashlib.sha256(order.encode()).hexdigest(),
            "final_chars": used, "actions": actions}


def build_rows(longmem_path: Path, population_path: Path, da031_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da031_path) != DA031_SHA256:
        raise DA033Error("DA-031 blind artifact differs")
    source = [row for row in read_gzip(da031_path) if row["corpus"] == "LONGMEM"]
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        record = records[str(row["question_id"])]
        by_id = {episode.candidate.identity: episode for episode in record.episodes}
        direct_texts = [str(member["text"]) for identity in row["direct_ids"]
                        for member in by_id[identity].members]
        treatment = allocate(row, lambda identity: by_id[identity].members, encode(direct_texts))
        output.append({**row, "da031_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA033Error("DA-033 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, da031_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da031_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da033-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da031_path))
        identical = path.read_bytes() == replay.read_bytes()
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["actions"])
    immutable = all(row["treatment"]["immutable_final_chars"] == row["da031_control"]["final_chars"]
                    and row["treatment"]["codec"] == row["da031_control"]["codec"] for row in rows)
    passed = (identical and immutable and actions["MEMBER"] > 0 and actions["SKIP_MEMBER"] > 0
              and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET)
    result = {"schema": "da033-longmem-varint-atomic-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "actions": dict(actions), "immutable_da031": immutable,
              "max_final_chars": max(row["treatment"]["final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA033Error("DA-033 blind preflight failed")
    return result


__all__ = ["DA033Error", "allocate", "run_preflight"]
