"""Blind phrase-coded temporal allocation for DA-016."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da003_edge_features import corpus_idf
from analysis.da004_pack_features import read_gzip
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da010_payloads import member_order
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da015_phrase_dictionary import PhraseContext, Segment, _replace, decode, encode

PHRASE_SHA256 = "7ccc9908c04acc951d90cdb118bb0ca1d974f141e1f623b9670167e774231fe4"
DIRECT_SHA256 = "9544fd5bc6ad85515f5cb99472cb844e2c8b9f97cd1f51a19de2d882da47ff5c"
BUDGET = 16_000


class DA016Error(RuntimeError):
    pass


def encode_existing(texts: Sequence[str], dictionary: PhraseContext) -> PhraseContext:
    if any(f"{dictionary.prefix}p" in text for text in texts):
        raise DA016Error("Direct-derived code prefix collides with link literal")
    members: tuple[tuple[Segment, ...], ...] = tuple((Segment("literal", text),) for text in texts)
    for index, phrase in enumerate(dictionary.phrases):
        members = _replace(members, phrase, index)
    result = PhraseContext(dictionary.prefix, dictionary.phrases, members, 0)
    if decode(result) != tuple(texts):
        raise DA016Error("Existing-dictionary payload decode differs")
    return result


def _payload_cost(role: Any, members: Sequence[Mapping[str, str]], dictionary: PhraseContext) -> int:
    texts = [str(member["text"]) for member in members]
    encoded = encode_existing(texts, dictionary)
    raw = append_role_pair(role, members).chars - role.chars
    return raw - sum(map(len, texts)) + encoded.content_chars


def build_rows(longmem_path: Path, population_path: Path, direct_path: Path,
               phrase_path: Path) -> list[dict[str, Any]]:
    if sha256_file(direct_path) != DIRECT_SHA256 or sha256_file(phrase_path) != PHRASE_SHA256:
        raise DA016Error("DA-016 sealed blind input differs")
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    direct_rows = {row["question_id"]: row for row in read_gzip(direct_path)}
    phrase_rows = {row["key"]: row for row in read_gzip(phrase_path) if row["corpus"] == "DA013"}
    idf = corpus_idf([{"candidates": [episode.candidate for record in records.values() for episode in record.episodes]}])
    output = []
    for question_id in sorted(records):
        record, direct, sealed = records[question_id], direct_rows[question_id], phrase_rows[question_id]
        by_id = {episode.candidate.identity: episode for episode in record.episodes}
        direct_pairs = [by_id[value].members for value in direct["direct_ids"]]
        role = role_pattern_pairs(direct_pairs)
        direct_texts = [str(member["text"]) for pair in direct_pairs for member in pair]
        dictionary = encode(direct_texts)
        phrase_chars = role.chars - sum(map(len, direct_texts)) + dictionary.content_chars + dictionary.declaration_chars
        if role.chars - phrase_chars != int(sealed["incremental_savings"]):
            raise DA016Error("DA-015 LongMem savings reproduction differs")
        used = phrase_chars
        actions = []
        for edge in direct["edges"]:
            neighbor = by_id[edge["neighbor_id"]]
            ordering, _ = member_order(record.question, neighbor.members, idf)
            raw_texts = [str(member["text"]) for member in neighbor.members]
            full_encoded = encode_existing(raw_texts, dictionary)
            turn_encoded = [encode_existing([text], dictionary) for text in raw_texts]
            full_cost = _payload_cost(role, neighbor.members, dictionary)
            turn_costs = tuple(_payload_cost(role, [member], dictionary) for member in neighbor.members)
            if used + full_cost <= BUDGET:
                action, selected, cost = "PAIR", None, full_cost
                role = append_role_pair(role, neighbor.members)
            elif used + turn_costs[ordering[0]] <= BUDGET:
                action, selected, cost = "TURN", ordering[0], turn_costs[ordering[0]]
                role = append_role_pair(role, [neighbor.members[selected]])
            else:
                action, selected, cost = "SKIP", None, 0
            used += cost
            actions.append({"seed_id": edge["seed_id"], "neighbor_id": edge["neighbor_id"],
                            "seed_rank": edge["seed_rank"], "direction": edge["direction"],
                            "kind": action, "member": selected, "cost": cost,
                            "full_cost": full_cost, "turn_costs": list(turn_costs),
                            "full_dictionary_savings": sum(map(len, raw_texts)) - full_encoded.content_chars,
                            "turn_dictionary_savings": [len(text) - encoded.content_chars for text, encoded in zip(raw_texts, turn_encoded, strict=True)]})
        output.append({"question_id": question_id, "question_type": record.question_type,
                       "direct_ids": direct["direct_ids"], "role_chars": role_pattern_pairs(direct_pairs).chars,
                       "phrase_chars": phrase_chars, "prefix": dictionary.prefix,
                       "phrases": list(dictionary.phrases), "declaration_chars": dictionary.declaration_chars,
                       "final_chars": used, "actions": actions})
    if len(output) != 465 or sum(len(row["actions"]) for row in output) != 7_401:
        raise DA016Error("DA-016 allocation population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, direct_path: Path,
                  phrase_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, direct_path, phrase_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da016-") as directory:
        replay = build_rows(longmem_path, population_path, direct_path, phrase_path)
        replay_path = Path(directory) / path.name
        _write(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    actions = {kind: sum(action["kind"] == kind for row in rows for action in row["actions"])
               for kind in ("PAIR", "TURN", "SKIP")}
    coded_payloads = sum(
        action["full_dictionary_savings"] > 0 or any(value > 0 for value in action["turn_dictionary_savings"])
        for row in rows for action in row["actions"]
    )
    differs_from_da013 = actions != {"PAIR": 51, "TURN": 507, "SKIP": 6_843}
    passed = identical and all(actions.values()) and coded_payloads and differs_from_da013
    result = {"schema": "da016-blind-allocation-v1", "status": "PASS" if passed else "FAIL",
              "questions": len(rows), "edges": sum(len(row["actions"]) for row in rows),
              "actions": actions, "coded_payload_edges": coded_payloads,
              "differs_from_da013_action_counts": differs_from_da013,
              "median_phrase_chars": sorted(row["phrase_chars"] for row in rows)[232],
              "median_final_chars": sorted(row["final_chars"] for row in rows)[232],
              "allocation_sha256": sha256_file(path), "replay_byte_identical": identical,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA016Error("DA-016 blind preflight failed")
    return result


__all__ = ["DA016Error", "build_rows", "encode_existing", "run_preflight"]
