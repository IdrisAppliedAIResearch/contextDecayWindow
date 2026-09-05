"""Exact prior-member span references and immutable additive allocation for DA-023."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, decode_role_pairs, role_pattern_pairs
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da015_phrase_dictionary import PhraseContext, encode
from analysis.da016_allocation import BUDGET, _payload_cost
from analysis.nf004_anatomy_features import load_blind_cases

DA019_SHA256 = "b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f"


class DA023Error(RuntimeError):
    pass


@dataclass(frozen=True)
class Backref:
    member: int
    start: int
    length: int


@dataclass(frozen=True)
class EncodedMember:
    segments: tuple[str | Backref, ...]


def prefix_for(texts: Sequence[str]) -> str:
    prefix = "~"
    while any(prefix + "r" in text for text in texts):
        prefix += "~"
    return prefix


def reference_code(prefix: str, ref: Backref) -> str:
    return f"{prefix}r{ref.member},{ref.start},{ref.length}{prefix}"


def _append_literal(segments: list[str | Backref], value: str) -> None:
    if segments and isinstance(segments[-1], str):
        segments[-1] += value
    else:
        segments.append(value)


def encode_members(texts: Sequence[str], prior: Sequence[str], prefix: str) -> tuple[EncodedMember, ...]:
    history = list(prior)
    index: dict[str, list[tuple[int, int]]] = {}
    for member_index, text in enumerate(history):
        for start in range(max(0, len(text) - 3)):
            index.setdefault(text[start:start + 4], []).append((member_index, start))
    output = []
    for text in texts:
        segments: list[str | Backref] = []
        position = 0
        while position < len(text):
            candidates = index.get(text[position:position + 4], ()) if position + 4 <= len(text) else ()
            best_length = 0
            best_source: tuple[int, int] | None = None
            for member_index, start in candidates:
                source = history[member_index]
                limit = min(len(text) - position, len(source) - start)
                length = 4
                while length < limit and text[position + length] == source[start + length]:
                    length += 1
                if length > best_length or (length == best_length and best_source is not None and
                                             (member_index, start) < best_source):
                    best_length, best_source = length, (member_index, start)
            if best_source is not None:
                ref = Backref(best_source[0], best_source[1], best_length)
                if best_length > len(reference_code(prefix, ref)):
                    segments.append(ref)
                    position += best_length
                    continue
            _append_literal(segments, text[position])
            position += 1
        encoded = EncodedMember(tuple(segments))
        output.append(encoded)
        new_index = len(history)
        history.append(text)
        for start in range(max(0, len(text) - 3)):
            index.setdefault(text[start:start + 4], []).append((new_index, start))
    return tuple(output)


def decode_members(encoded: Sequence[EncodedMember], prior: Sequence[str]) -> tuple[str, ...]:
    history = list(prior)
    output = []
    for member in encoded:
        chunks = []
        for segment in member.segments:
            if isinstance(segment, str):
                chunks.append(segment)
            elif 0 <= segment.member < len(history) and 0 <= segment.start and segment.length > 0:
                source = history[segment.member]
                if segment.start + segment.length > len(source):
                    raise DA023Error("Backreference exceeds source member")
                chunks.append(source[segment.start:segment.start + segment.length])
            else:
                raise DA023Error("Backreference is not prior-member valid")
        text = "".join(chunks)
        history.append(text)
        output.append(text)
    return tuple(output)


def encoded_chars(encoded: Sequence[EncodedMember], prefix: str) -> int:
    return sum(len(segment) if isinstance(segment, str) else len(reference_code(prefix, segment))
               for member in encoded for segment in member.segments)


def serialize(encoded: Sequence[EncodedMember]) -> list[list[dict[str, Any]]]:
    return [[{"literal": segment} if isinstance(segment, str) else
             {"member": segment.member, "start": segment.start, "length": segment.length}
             for segment in member.segments] for member in encoded]


def _baseline_payloads(row: Mapping[str, Any], pair_for: Any) -> list[list[Mapping[str, str]]]:
    payloads = [list(pair_for(identity)) for identity in row["direct_ids"]]
    for action in row["baseline_actions"]:
        pair = pair_for(str(action["neighbor_id"]))
        if action["kind"] == "PAIR":
            payloads.append(list(pair))
        elif action["kind"] == "TURN":
            payloads.append([pair[int(action["member"])]])
    return payloads


def _all_candidate_texts(row: Mapping[str, Any], pair_for: Any) -> list[str]:
    identities = list(map(str, row["direct_ids"])) + [str(action["neighbor_id"]) for action in row["baseline_actions"]]
    return [str(member["text"]) for identity in identities for member in pair_for(identity)]


def _control_chars(role: Any, texts: Sequence[str], control: int,
                   dictionary: PhraseContext | None) -> None:
    if dictionary is None:
        actual = role.chars
    else:
        from analysis.da016_allocation import encode_existing
        coded = encode_existing(texts, dictionary)
        actual = role.chars - sum(map(len, texts)) + coded.content_chars + dictionary.declaration_chars
    if actual != control:
        raise DA023Error("DA-023 control renderer differs")


def _allocate(row: Mapping[str, Any], pair_for: Any,
              control_dictionary: PhraseContext | None) -> dict[str, Any]:
    payloads = _baseline_payloads(row, pair_for)
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    texts = [str(member["text"]) for payload in payloads for member in payload]
    control = int(row["baseline_actions"][-1]["final_chars"])
    _control_chars(role, texts, control, control_dictionary)
    prefix = prefix_for(_all_candidate_texts(row, pair_for))
    encoded = encode_members(texts, (), prefix)
    if decode_members(encoded, ()) != tuple(texts):
        raise DA023Error("DA-023 baseline decode differs")
    backref_chars = role.chars - sum(map(len, texts)) + encoded_chars(encoded, prefix)
    if backref_chars < control:
        renderer, used, history = "BACKREF", backref_chars, list(texts)
    else:
        renderer, used, history = "CONTROL", control, list(texts)
    baseline_chars = used
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
                              "member": None, "cost": 0, "segments": []})
            continue
        seen.add(neighbor)
        pair = pair_for(neighbor)
        member = int(action["member"])
        if renderer == "BACKREF":
            pair_texts = [str(item["text"]) for item in pair]
            pair_encoded = encode_members(pair_texts, history, prefix)
            full_cost = append_role_pair(role, pair).chars - role.chars - sum(map(len, pair_texts)) + encoded_chars(pair_encoded, prefix)
            turn_text = str(pair[member]["text"])
            turn_encoded = encode_members([turn_text], history, prefix)
            turn_cost = append_role_pair(role, [pair[member]]).chars - role.chars - len(turn_text) + encoded_chars(turn_encoded, prefix)
        elif control_dictionary is None:
            pair_encoded = turn_encoded = tuple()
            full_cost = append_role_pair(role, pair).chars - role.chars
            turn_cost = append_role_pair(role, [pair[member]]).chars - role.chars
        else:
            pair_encoded = turn_encoded = tuple()
            full_cost = _payload_cost(role, pair, control_dictionary)
            turn_cost = _payload_cost(role, [pair[member]], control_dictionary)
        if used + full_cost <= BUDGET:
            kind, selected, cost, payload, chosen = "PAIR", None, full_cost, pair, pair_encoded
        elif used + turn_cost <= BUDGET:
            kind, selected, cost, payload, chosen = "TURN", member, turn_cost, [pair[member]], turn_encoded
        else:
            kind, selected, cost, payload, chosen = "SKIP", member, 0, [], turn_encoded
        if payload:
            role = append_role_pair(role, payload)
            used += cost
            history.extend(str(item["text"]) for item in payload)
        additions.append({"position": position, "seed_id": action.get("seed_id"), "neighbor_id": neighbor,
                          "kind": kind, "member": selected, "cost": cost, "full_cost": full_cost,
                          "turn_cost": turn_cost, "segments": serialize(chosen)})
    expected = ["\n".join(f"{member['speaker']}: {member['text']}" for member in payload) for payload in payloads]
    if decode_role_pairs(role)[:len(payloads)] != expected:
        raise DA023Error("DA-023 immutable payload decode differs")
    refs = sum(isinstance(segment, Backref) for member in encoded for segment in member.segments)
    return {"renderer": renderer, "prefix": prefix, "control_chars": control,
            "baseline_chars": baseline_chars, "recovered_chars": control - baseline_chars,
            "final_chars": used, "baseline_reference_count": refs,
            "baseline_segments": serialize(encoded) if renderer == "BACKREF" else [],
            "immutable_decode_sha256": hashlib.sha256("\0".join(expected).encode()).hexdigest(),
            "additions": additions}


def build_rows(locomo_path: Path, longmem_path: Path, population_path: Path,
               da019_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da019_path) != DA019_SHA256:
        raise DA023Error("DA-023 DA-019 source differs")
    source = list(read_gzip(da019_path))
    nf_cases = load_blind_cases(locomo_path)
    nf_members, _ = _member_maps(locomo_path, nf_cases)
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
            dictionary = encode(direct_texts)
            treatment = _allocate(row, lambda identity: by_id[identity].members, dictionary)
            output.append({"corpus": "LONGMEM", "question_id": row["question_id"],
                           "question_type": row["question_type"], "direct_ids": row["direct_ids"],
                           "baseline_actions": row["baseline_actions"], "treatment": treatment})
    if Counter(row["corpus"] for row in output) != Counter({"NF004": 1_098, "LONGMEM": 465}):
        raise DA023Error("DA-023 population differs")
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
    with tempfile.TemporaryDirectory(prefix="da023-") as directory:
        replay_rows = build_rows(locomo_path, longmem_path, population_path, da019_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = path.read_bytes() == replay.read_bytes()
    corpora = {}
    passed = identical
    for corpus in ("NF004", "LONGMEM"):
        subset = [row for row in rows if row["corpus"] == corpus]
        actions = Counter(action["kind"] for row in subset for action in row["treatment"]["additions"])
        savings = [row["treatment"]["recovered_chars"] for row in subset]
        cell = {"questions": len(subset),
                "backref_renderers": sum(row["treatment"]["renderer"] == "BACKREF" for row in subset),
                "median_recovered_chars": float(np.median(savings)),
                "p10_recovered_chars": float(np.percentile(savings, 10)),
                "p90_recovered_chars": float(np.percentile(savings, 90)),
                "baseline_references": sum(row["treatment"]["baseline_reference_count"] for row in subset),
                "added_pairs": actions["PAIR"], "added_turns": actions["TURN"],
                "remaining_skips": actions["SKIP"],
                "expanding_rows": sum(row["treatment"]["baseline_chars"] > row["treatment"]["control_chars"] for row in subset),
                "max_final_chars": max(row["treatment"]["final_chars"] for row in subset)}
        corpora[corpus] = cell
        passed = passed and cell["median_recovered_chars"] >= 64 and cell["backref_renderers"] > 0 and cell["baseline_references"] > 0 and cell["added_pairs"] > 0 and cell["added_turns"] > 0 and cell["remaining_skips"] > 0 and not cell["expanding_rows"] and cell["max_final_chars"] <= BUDGET
    result = {"schema": "da023-backreference-preflight-v1",
              "status": "BACKREFERENCE_MECHANICAL_PASS" if passed else "NO_BACKREFERENCE_CAPACITY_SIGNAL",
              "corpora": corpora, "rows": len(rows), "replay_byte_identical": identical,
              "allocation_sha256": sha256_file(path), "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["Backref", "DA023Error", "decode_members", "encode_members", "prefix_for",
           "reference_code", "run_preflight"]

