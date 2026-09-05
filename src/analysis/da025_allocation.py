"""Blind LongMem atomic additive allocation for DA-025."""

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


class DA025Error(RuntimeError):
    pass


def allocate_atomic(row: Mapping[str, Any], pair_for: Any, dictionary: Any) -> dict[str, Any]:
    payloads = _baseline_payloads(row, pair_for)
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    used = int(row["treatment"]["baseline_chars"])
    actions = []
    second_attempts = second_admissions = 0
    for position, source in enumerate(row["baseline_actions"]):
        if source["kind"] != "SKIP":
            continue
        neighbor = str(source["neighbor_id"])
        pair = pair_for(neighbor)
        full, _ = _costs(row["treatment"]["renderer"], role, history, pair,
                         row["treatment"]["prefix"], dictionary)
        if used + full <= BUDGET:
            role = append_role_pair(role, pair)
            history.extend(str(member["text"]) for member in pair)
            used += full
            actions.append({"position": position, "seed_id": source.get("seed_id"),
                            "neighbor_id": neighbor, "kind": "PAIR", "member": None, "cost": full})
            continue
        first = int(source["member"])
        admitted = []
        for ordinal, member_index in enumerate((first, 1 - first)):
            if ordinal:
                second_attempts += 1
            _, turns = _costs(row["treatment"]["renderer"], role, history, pair,
                              row["treatment"]["prefix"], dictionary)
            cost = turns[member_index]
            if used + cost > BUDGET:
                actions.append({"position": position, "seed_id": source.get("seed_id"),
                                "neighbor_id": neighbor, "kind": "SKIP_MEMBER", "member": member_index,
                                "member_ordinal": ordinal, "cost": 0, "attempt_cost": cost})
                continue
            member = pair[member_index]
            role = append_role_pair(role, [member])
            history.append(str(member["text"]))
            used += cost
            admitted.append(member_index)
            second_admissions += int(ordinal == 1)
            actions.append({"position": position, "seed_id": source.get("seed_id"),
                            "neighbor_id": neighbor, "kind": "MEMBER", "member": member_index,
                            "member_ordinal": ordinal, "cost": cost})
    return {"renderer": row["treatment"]["renderer"], "prefix": row["treatment"]["prefix"],
            "baseline_chars": row["treatment"]["baseline_chars"], "final_chars": used,
            "second_member_attempts": second_attempts, "second_member_admissions": second_admissions,
            "actions": actions}


def build_rows(longmem_path: Path, population_path: Path,
               da023_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da023_path) != DA023_SHA256:
        raise DA025Error("DA-023 blind artifact differs")
    source = [row for row in read_gzip(da023_path) if row["corpus"] == "LONGMEM"]
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        record = records[str(row["question_id"])]
        by_id = {episode.candidate.identity: episode for episode in record.episodes}
        direct_texts = [str(member["text"]) for identity in row["direct_ids"] for member in by_id[identity].members]
        treatment = allocate_atomic(row, lambda identity: by_id[identity].members, encode(direct_texts))
        output.append({"question_id": row["question_id"], "question_type": row["question_type"],
                       "direct_ids": row["direct_ids"], "baseline_actions": row["baseline_actions"],
                       "da023_additions": row["treatment"]["additions"], "treatment": treatment})
    if len(output) != 465:
        raise DA025Error("DA-025 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path,
                  da023_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da023_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da025-") as directory:
        replay_rows = build_rows(longmem_path, population_path, da023_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = path.read_bytes() == replay.read_bytes()
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["actions"])
    attempts = sum(row["treatment"]["second_member_attempts"] for row in rows)
    admissions = sum(row["treatment"]["second_member_admissions"] for row in rows)
    differs = any([(row["treatment"]["actions"] != row["da023_additions"]) for row in rows])
    passed = identical and attempts > 0 and admissions > 0 and actions["PAIR"] and actions["MEMBER"] and actions["SKIP_MEMBER"] and differs and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET
    result = {"schema": "da025-atomic-preflight-v1", "status": "PASS" if passed else "FAIL",
              "questions": len(rows), "actions": dict(actions),
              "second_member_attempts": attempts, "second_member_admissions": admissions,
              "differs_from_da023": differs, "replay_byte_identical": identical,
              "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA025Error("DA-025 blind preflight failed")
    return result


__all__ = ["DA025Error", "allocate_atomic", "run_preflight"]

