"""Blind immutable-prefix reserve construction for DA-007."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da003_edge_features import write_rows
from analysis.da006_reserved_links import ARMS, BUDGET, RESERVES, _member_maps, read_gzip
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file

DA006_SHA256 = "81625474d8fa044f797dd9c15c292c57150d83f28ffabcc17665658c85b0ff86"
DA002_SHA256 = "25c6f2f8731b19341c440236418e47de95334eb706728b4a5d580cafe7cac8ca"


class DA007Error(RuntimeError):
    pass


def immutable_prefix(direct: Sequence[str], chars: Mapping[str, int], budget: int) -> tuple[list[str], list[str], int]:
    retained = list(direct)
    used = sum(chars[item] for item in retained)
    while retained and used > budget:
        used -= chars[retained.pop()]
    removed = list(direct[len(retained):])
    if retained != list(direct[:len(retained)]) or used > budget:
        raise DA007Error("DA-007 core is not a valid direct prefix")
    return retained, removed, used


def build_rows(dataset_path: Path, da006_path: Path, provenance_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da006_path) != DA006_SHA256 or sha256_file(provenance_path) != DA002_SHA256:
        raise DA007Error("DA-007 sealed input hash differs")
    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    provenance = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in read_gzip(provenance_path)}
    output = []
    for row in read_gzip(da006_path):
        key = (row["comparison_key"], int(row["duplicate_ordinal"]))
        candidate_rows = provenance[key]["candidates"]
        chars = {identity: int(detail["chars"]) for identity, detail in candidate_rows.items()}
        arms = {}
        for reserve in RESERVES:
            core, removed, core_chars = immutable_prefix(row["direct_ids"], chars, BUDGET - reserve)
            for renderer in ("PAIR", "TURN"):
                old = row["arms"][f"{renderer}_R{reserve}"]
                neighbor = row["neighbor_id"]
                if renderer == "PAIR":
                    intended = [member["dialogue_id"] for member in members[neighbor]]
                else:
                    index = int(old["selected_member_index"])
                    intended = [members[neighbor][index]["dialogue_id"]]
                admitted = neighbor not in set(core) and int(old["payload_chars"]) <= reserve
                linked = intended if admitted else []
                total = core_chars + (int(old["payload_chars"]) if admitted else 0)
                if total > BUDGET:
                    raise DA007Error("DA-007 total budget overflow")
                arms[f"{renderer}_R{reserve}"] = {
                    "core_ids": core, "removed_direct_ids": removed, "core_chars": core_chars,
                    "link_admitted": admitted, "payload_chars": int(old["payload_chars"]),
                    "linked_dialogue_ids": linked, "selected_member_index": old["selected_member_index"],
                    "total_chars": total, "unused_reserve": reserve - (int(old["payload_chars"]) if admitted else 0),
                }
        output.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": row["sample_id"],
                       "source_index": row["source_index"], "seed_id": row["seed_id"], "neighbor_id": row["neighbor_id"],
                       "direct_ids": row["direct_ids"], "direct_sha256": row["direct_sha256"], "arms": arms})
    if len(output) != 26_100:
        raise DA007Error("DA-007 blind population differs")
    return output


def run_preflight(dataset_path: Path, da006_path: Path, provenance_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(dataset_path, da006_path, provenance_path)
    path = output_dir / "blind_immutable_prefix.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da007-") as directory:
        replay = build_rows(dataset_path, da006_path, provenance_path)
        replay_path = Path(directory) / path.name
        write_rows(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    admissions = {arm: sum(row["arms"][arm]["link_admitted"] for row in rows) for arm in ARMS}
    removals = {arm: sum(bool(row["arms"][arm]["removed_direct_ids"]) for row in rows) for arm in ARMS}
    turn_only = {reserve: sum(row["arms"][f"TURN_R{reserve}"]["link_admitted"] and not row["arms"][f"PAIR_R{reserve}"]["link_admitted"] for row in rows)
                 for reserve in RESERVES}
    if any(not admissions[arm] or not removals[arm] for arm in ARMS) or not any(turn_only.values()):
        raise DA007Error("DA-007 reachability failed")
    result = {"schema": "da007-prefix-preflight-v1", "status": "PASS" if identical else "FAIL",
              "rows": len(rows), "arms": list(ARMS), "admissions": admissions,
              "core_removal_rows": removals, "turn_only_fit": turn_only,
              "selection_sha256": sha256_file(path), "replay_byte_identical": identical,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise DA007Error("DA-007 preflight failed")
    return result


__all__ = ["DA007Error", "immutable_prefix", "run_preflight"]
