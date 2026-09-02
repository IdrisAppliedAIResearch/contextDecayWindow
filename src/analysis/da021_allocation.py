"""Blind immutable-pack joint phrase coding and additive allocation for DA-021."""

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
from analysis.da015_phrase_dictionary import PhraseContext, Segment, decode, encode
from analysis.da016_allocation import BUDGET, _payload_cost, encode_existing
from analysis.nf004_anatomy_features import load_blind_cases

DA019_SHA256 = "b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f"


class DA021Error(RuntimeError):
    pass


def _texts(payloads: Sequence[Sequence[Mapping[str, str]]]) -> list[str]:
    return [str(member["text"]) for payload in payloads for member in payload]


def _compressed_chars(role: Any, texts: Sequence[str], dictionary: PhraseContext) -> int:
    encoded = encode_existing(texts, dictionary)
    if decode(encoded) != tuple(texts):
        raise DA021Error("DA-021 existing dictionary decode differs")
    return role.chars - sum(map(len, texts)) + encoded.content_chars + dictionary.declaration_chars


def choose_renderer(role: Any, texts: Sequence[str], control_chars: int,
                    control_dictionary: PhraseContext | None) -> tuple[str, PhraseContext | None, int]:
    if control_dictionary is None:
        if role.chars != control_chars:
            raise DA021Error("DA-021 plain control charge differs")
    elif _compressed_chars(role, texts, control_dictionary) != control_chars:
        raise DA021Error("DA-021 phrase control charge differs")
    joint = encode(texts)
    if decode(joint) != tuple(texts):
        raise DA021Error("DA-021 joint dictionary decode differs")
    joint_chars = _compressed_chars(role, texts, joint)
    if joint_chars < control_chars:
        return "JOINT", joint, joint_chars
    return "CONTROL", control_dictionary, control_chars


def _baseline_payloads(row: Mapping[str, Any], pair_for: Any) -> list[list[Mapping[str, str]]]:
    payloads = [list(pair_for(identity)) for identity in row["direct_ids"]]
    for action in row["baseline_actions"]:
        if action["kind"] == "PAIR":
            payloads.append(list(pair_for(str(action["neighbor_id"]))))
        elif action["kind"] == "TURN":
            pair = pair_for(str(action["neighbor_id"]))
            payloads.append([pair[int(action["member"])]])
    return payloads


def _allocate(row: Mapping[str, Any], pair_for: Any, control_dictionary: PhraseContext | None) -> dict[str, Any]:
    payloads = _baseline_payloads(row, pair_for)
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    texts = _texts(payloads)
    control_chars = int(row["baseline_actions"][-1]["final_chars"])
    renderer, dictionary, used = choose_renderer(role, texts, control_chars, control_dictionary)
    seen = set(map(str, row["direct_ids"]))
    seen.update(str(action["neighbor_id"]) for action in row["baseline_actions"]
                if action["kind"] in {"PAIR", "TURN"})
    additions = []
    for position, action in enumerate(row["baseline_actions"]):
        if action["kind"] != "SKIP":
            continue
        neighbor = str(action["neighbor_id"])
        if neighbor in seen:
            additions.append({"position": position, "neighbor_id": neighbor, "kind": "DUPLICATE",
                              "member": None, "cost": 0})
            continue
        seen.add(neighbor)
        pair = pair_for(neighbor)
        if dictionary is None:
            full_cost = append_role_pair(role, pair).chars - role.chars
            member = int(action["member"])
            turn_cost = append_role_pair(role, [pair[member]]).chars - role.chars
        else:
            full_cost = _payload_cost(role, pair, dictionary)
            member = int(action["member"])
            turn_cost = _payload_cost(role, [pair[member]], dictionary)
        if used + full_cost <= BUDGET:
            kind, selected, cost, payload = "PAIR", None, full_cost, pair
        elif used + turn_cost <= BUDGET:
            kind, selected, cost, payload = "TURN", member, turn_cost, [pair[member]]
        else:
            kind, selected, cost, payload = "SKIP", member, 0, []
        if payload:
            role = append_role_pair(role, payload)
            used += cost
        additions.append({"position": position, "seed_id": action.get("seed_id"),
                          "neighbor_id": neighbor, "kind": kind, "member": selected,
                          "cost": cost, "full_cost": full_cost, "turn_cost": turn_cost})
    decoded = decode_role_pairs(role)
    expected_payload_texts = ["\n".join(f"{member['speaker']}: {member['text']}" for member in payload)
                              for payload in payloads]
    if decoded[:len(payloads)] != expected_payload_texts:
        raise DA021Error("DA-021 immutable role decode differs")
    dictionary_phrases = tuple() if dictionary is None else dictionary.phrases
    return {"renderer": renderer, "control_chars": control_chars, "baseline_chars": int(used - sum(a["cost"] for a in additions)),
            "recovered_chars": control_chars - (int(used) - sum(a["cost"] for a in additions)),
            "final_chars": used, "dictionary_entries": len(dictionary_phrases),
            "dictionary_sha256": hashlib.sha256("\0".join(dictionary_phrases).encode()).hexdigest(),
            "immutable_payload_count": len(payloads),
            "immutable_decode_sha256": hashlib.sha256("\0".join(expected_payload_texts).encode()).hexdigest(),
            "additions": additions}


def build_rows(locomo_path: Path, longmem_path: Path, population_path: Path,
               da019_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da019_path) != DA019_SHA256:
        raise DA021Error("DA-019 blind input differs")
    source = list(read_gzip(da019_path))
    cases = load_blind_cases(locomo_path)
    nf_members, _ = _member_maps(locomo_path, cases)
    long_records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        if row["corpus"] == "NF004":
            treatment = _allocate(row, lambda identity: nf_members[identity], None)
            output.append({"corpus": "NF004", "comparison_key": row["comparison_key"],
                           "duplicate_ordinal": row["duplicate_ordinal"], "sample_id": row["sample_id"],
                           "source_index": row["source_index"], "direct_ids": row["direct_ids"],
                           "baseline_actions": row["baseline_actions"], "treatment": treatment})
        else:
            record = long_records[str(row["question_id"])]
            by_id = {episode.candidate.identity: episode for episode in record.episodes}
            direct_texts = [str(member["text"]) for identity in row["direct_ids"] for member in by_id[identity].members]
            direct_dictionary = encode(direct_texts)
            treatment = _allocate(row, lambda identity: by_id[identity].members, direct_dictionary)
            output.append({"corpus": "LONGMEM", "question_id": row["question_id"],
                           "question_type": row["question_type"], "direct_ids": row["direct_ids"],
                           "baseline_actions": row["baseline_actions"], "treatment": treatment})
    if Counter(row["corpus"] for row in output) != Counter({"NF004": 1_098, "LONGMEM": 465}):
        raise DA021Error("DA-021 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(locomo_path: Path, longmem_path: Path, population_path: Path,
                  da019_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(locomo_path, longmem_path, population_path, da019_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da021-") as directory:
        replay_rows = build_rows(locomo_path, longmem_path, population_path, da019_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = path.read_bytes() == replay.read_bytes()
    corpora = {}
    passed = identical
    for corpus in ("NF004", "LONGMEM"):
        subset = [row for row in rows if row["corpus"] == corpus]
        savings = [row["treatment"]["recovered_chars"] for row in subset]
        actions = Counter(action["kind"] for row in subset for action in row["treatment"]["additions"])
        cell = {"questions": len(subset), "joint_renderers": sum(row["treatment"]["renderer"] == "JOINT" for row in subset),
                "median_recovered_chars": float(np.median(savings)),
                "p10_recovered_chars": float(np.percentile(savings, 10)),
                "p90_recovered_chars": float(np.percentile(savings, 90)),
                "added_pairs": actions["PAIR"], "added_turns": actions["TURN"],
                "remaining_skips": actions["SKIP"], "duplicates": actions["DUPLICATE"],
                "max_final_chars": max(row["treatment"]["final_chars"] for row in subset),
                "expanding_rows": sum(row["treatment"]["baseline_chars"] > row["treatment"]["control_chars"] for row in subset)}
        corpora[corpus] = cell
        passed = passed and cell["joint_renderers"] > 0 and cell["median_recovered_chars"] >= 64 and cell["added_pairs"] > 0 and cell["added_turns"] > 0 and cell["remaining_skips"] > 0 and not cell["expanding_rows"] and cell["max_final_chars"] <= BUDGET
    result = {"schema": "da021-immutable-pack-preflight-v1",
              "status": "IMMUTABLE_PACK_MECHANICAL_PASS" if passed else "NO_IMMUTABLE_PACK_CAPACITY_SIGNAL",
              "corpora": corpora, "rows": len(rows), "replay_byte_identical": identical,
              "allocation_sha256": sha256_file(path), "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["DA021Error", "build_rows", "choose_renderer", "run_preflight"]

