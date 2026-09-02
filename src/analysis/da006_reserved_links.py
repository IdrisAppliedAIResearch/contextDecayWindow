"""Blind reserved-headroom and compact-turn link construction for DA-006."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da003_edge_features import corpus_idf, tokens, weighted_coverage, write_rows
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file

EDGE_SHA256 = "0d669cc7a0b2da9b0bfa7439fdd7c182ee4ea6f60a0bf6e0c8fdf79567b02c5c"
PROVENANCE_SHA256 = "25c6f2f8731b19341c440236418e47de95334eb706728b4a5d580cafe7cac8ca"
BUDGET = 16_000
RESERVES = (256, 512, 1024, 2048)
ARMS = tuple(f"{renderer}_R{reserve}" for renderer in ("PAIR", "TURN") for reserve in RESERVES)
SESSION = re.compile(r"session_(\d+)")


class DA006Error(RuntimeError):
    pass


def read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def digest(identities: Sequence[str]) -> str:
    return hashlib.sha256("\0".join(identities).encode("ascii")).hexdigest()


def pack_ids(order: Sequence[str], chars: Mapping[str, int], budget: int) -> tuple[list[str], int]:
    selected, used = [], 0
    for identity in order:
        if used + chars[identity] > budget:
            continue
        selected.append(identity)
        used += chars[identity]
    return selected, used


def choose_turn(question: str, members: Sequence[Mapping[str, str]], idf: Mapping[str, float]) -> int:
    query = tokens(question)
    coverage = [weighted_coverage(query, tokens(f"{member['speaker']}: {member['text']}"), idf) for member in members]
    return max(range(len(members)), key=lambda index: (coverage[index], -index))


def _member_maps(dataset_path: Path, cases: Sequence[Mapping[str, Any]]) -> tuple[dict[str, list[dict[str, str]]], dict[tuple[str, int], str]]:
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    by_sample = {row["sample_id"]: row for row in raw}
    members, questions = {}, {}
    for case in cases:
        row = by_sample[case["sample_id"]]
        candidate_index = 0
        sessions = sorted(((int(SESSION.fullmatch(key).group(1)), key) for key in row["conversation"] if SESSION.fullmatch(key)))
        for _, session_key in sessions:
            turns = row["conversation"][session_key]
            for start in range(0, len(turns), 2):
                candidate = case["candidates"][candidate_index]
                candidate_index += 1
                group = [{"dialogue_id": str(turn["dia_id"]), "speaker": str(turn["speaker"]),
                          "text": str(turn["text"])} for turn in turns[start:start + 2]]
                serialized = "\n".join(f"{item['speaker']}: {item['text']}" for item in group)
                if serialized != candidate.text:
                    raise DA006Error("DA-006 member serialization differs from candidate")
                members[candidate.identity] = group
        if candidate_index != len(case["candidates"]):
            raise DA006Error("DA-006 candidate/member population differs")
        for question in case["questions"]:
            questions[(question["comparison_key"], int(question["duplicate_ordinal"]))] = question["text"]
    return members, questions


def build_rows(dataset_path: Path, edge_path: Path, provenance_path: Path) -> list[dict[str, Any]]:
    if sha256_file(edge_path) != EDGE_SHA256 or sha256_file(provenance_path) != PROVENANCE_SHA256:
        raise DA006Error("DA-006 sealed input hash differs")
    cases = load_blind_cases(dataset_path)
    idf = corpus_idf(cases)
    members, questions = _member_maps(dataset_path, cases)
    provenance = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in read_gzip(provenance_path)}
    output = []
    for edge in read_gzip(edge_path):
        key = (edge["comparison_key"], int(edge["duplicate_ordinal"]))
        candidate_rows = provenance[key]["candidates"]
        order = [identity for identity, _ in sorted(candidate_rows.items(), key=lambda item: int(item[1]["direct_rank"]))]
        chars = {identity: int(detail["chars"]) for identity, detail in candidate_rows.items()}
        direct, direct_chars = pack_ids(order, chars, BUDGET)
        if direct != edge["direct_selected_ids"]:
            raise DA006Error("DA-006 direct control differs from DA-003")
        neighbor = edge["neighbor_id"]
        arm_rows = {}
        for reserve in RESERVES:
            core, core_chars = pack_ids(order, chars, BUDGET - reserve)
            removed = [identity for identity in direct if identity not in set(core)]
            for renderer in ("PAIR", "TURN"):
                if renderer == "PAIR":
                    payload_chars = chars[neighbor]
                    dialogue_ids = [member["dialogue_id"] for member in members[neighbor]]
                    member_index = None
                else:
                    member_index = choose_turn(questions[key], members[neighbor], idf)
                    member = members[neighbor][member_index]
                    serialized = f"{member['speaker']}: {member['text']}"
                    payload_chars = len(serialized)
                    dialogue_ids = [member["dialogue_id"]]
                admitted = neighbor not in set(core) and payload_chars <= reserve
                linked_dialogues = dialogue_ids if admitted else []
                core_dialogues = [member["dialogue_id"] for identity in core for member in members[identity]]
                total = core_chars + (payload_chars if admitted else 0)
                if total > BUDGET:
                    raise DA006Error("DA-006 treatment exceeded total budget")
                arm_rows[f"{renderer}_R{reserve}"] = {
                    "core_ids": core, "core_sha256": digest(core), "core_chars": core_chars,
                    "core_count": len(core), "removed_direct_ids": removed,
                    "link_admitted": admitted, "payload_type": renderer, "payload_chars": payload_chars,
                    "linked_pair_id": neighbor, "linked_dialogue_ids": linked_dialogues,
                    "selected_member_index": member_index, "selected_dialogue_ids": core_dialogues + linked_dialogues,
                    "total_chars": total, "unused_reserve": reserve - (payload_chars if admitted else 0),
                }
        output.append({"comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": edge["sample_id"],
                       "source_index": edge["source_index"], "seed_id": edge["seed_id"], "neighbor_id": neighbor,
                       "direct_ids": direct, "direct_sha256": digest(direct), "direct_chars": direct_chars,
                       "arms": arm_rows})
    if len(output) != 26_100 or any(set(row["arms"]) != set(ARMS) for row in output):
        raise DA006Error("DA-006 blind population differs")
    return output


def run_preflight(dataset_path: Path, edge_path: Path, provenance_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(dataset_path, edge_path, provenance_path)
    path = output_dir / "blind_reserved_links.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da006-") as directory:
        replay = build_rows(dataset_path, edge_path, provenance_path)
        replay_path = Path(directory) / path.name
        write_rows(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    admissions = {arm: sum(row["arms"][arm]["link_admitted"] for row in rows) for arm in ARMS}
    removals = {arm: sum(bool(row["arms"][arm]["removed_direct_ids"]) for row in rows) for arm in ARMS}
    fit_disagreements = {reserve: sum(row["arms"][f"TURN_R{reserve}"]["link_admitted"] and
                                      not row["arms"][f"PAIR_R{reserve}"]["link_admitted"] for row in rows)
                         for reserve in RESERVES}
    if any(not admissions[arm] or not removals[arm] for arm in ARMS) or not any(fit_disagreements.values()):
        raise DA006Error("DA-006 preflight reachability failed")
    source = Path(__file__).read_text(encoding="utf-8").lower()
    declaration = "forbidden_tokens ="
    forbidden_tokens = ("nf004_measurement", "g6_holdout_outcomes", '["answer"]', '["evidence"]', "embeddingcache")
    scanned = "\n".join(line for line in source.splitlines() if declaration not in line)
    clean = not any(token in scanned for token in forbidden_tokens)
    result = {"schema": "da006-reserved-link-preflight-v1", "status": "PASS" if identical and clean else "FAIL",
              "rows": len(rows), "arms": list(ARMS), "admissions": admissions, "core_removal_rows": removals,
              "turn_only_fit": fit_disagreements, "selection_sha256": sha256_file(path),
              "replay_byte_identical": identical, "leakage_and_cache_scan_clean": clean,
              "calls": {"embedding": 0, "model": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise DA006Error("DA-006 blind preflight failed")
    return result


__all__ = ["ARMS", "DA006Error", "choose_turn", "pack_ids", "run_preflight"]
