"""Blind NF-004 phrase-coded benefit-order allocation for DA-017."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_analysis import fast_auc
from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da008_analysis import grouped_benefit_scores
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da010_analysis import allocate_turn_payloads
from analysis.da015_phrase_dictionary import encode
from analysis.da016_allocation import _payload_cost, encode_existing
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file

PHRASE_SHA256 = "7ccc9908c04acc951d90cdb118bb0ca1d974f141e1f623b9670167e774231fe4"
PAYLOAD_SHA256 = "51e0e648f66bf2c5a7ab6161c5fbcbc9efaadff306beb9b98ffac6a2f19d47b3"
ROLE_SHA256 = "0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb"
PERTURBATION_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
LABEL_SHA256 = "d111229d791477171b22a49899b42bbc9870b0e829e9d6925402ff9c5b467bca"
G6_SHA256 = "86690f54465e1e755ce897e7206283f29acc477bec2afead44d0a53cb742391b"
BUDGET = 16_000


class DA017Error(RuntimeError):
    pass


def _qkey(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["comparison_key"]), int(row["duplicate_ordinal"])


def _ekey(row: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return (*_qkey(row), str(row["seed_id"]), str(row["neighbor_id"]))


def _tie(row: Mapping[str, Any]) -> tuple[float, int, str]:
    features = row["features"]
    return float(features["seed_rank"]), 0 if float(features["signed_direction"]) < 0 else 1, str(row["neighbor_id"])


def build_rows(dataset_path: Path, phrase_path: Path, payload_path: Path, role_path: Path,
               perturbation_path: Path, label_path: Path, g6_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected = ((phrase_path, PHRASE_SHA256), (payload_path, PAYLOAD_SHA256), (role_path, ROLE_SHA256),
                (perturbation_path, PERTURBATION_SHA256), (label_path, LABEL_SHA256), (g6_path, G6_SHA256))
    if any(sha256_file(path) != digest for path, digest in expected):
        raise DA017Error("DA-017 sealed input differs")
    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    roles = {_qkey(row): row for row in read_gzip(role_path)}
    phrases = {(row["key"].rsplit(":", 1)[0], int(row["key"].rsplit(":", 1)[1])): row
               for row in read_gzip(phrase_path) if row["corpus"] == "NF004"}
    payloads = {_ekey(row): row for row in read_gzip(payload_path)}
    labels = {_ekey(row): row for row in read_gzip(label_path)}
    primary = {_qkey(row): bool(row["primary_eligible"])
               for row in json.loads(g6_path.read_text(encoding="utf-8"))["rows"]}
    edges = []
    for edge in read_gzip(perturbation_path):
        if not primary[_qkey(edge)]:
            continue
        label = labels[_ekey(edge)]
        edges.append({**edge, "benefit": bool(label["benefit"]), "harm": bool(label["harm"])})
    counts = Counter("BENEFIT" if row["benefit"] else "HARM" if row["harm"] else "NEUTRAL" for row in edges)
    if len(edges) != 25_941 or counts != Counter({"BENEFIT": 57, "HARM": 40, "NEUTRAL": 25_844}):
        raise DA017Error("DA-017 edge population differs")
    scores = grouped_benefit_scores(edges)
    auc = fast_auc(scores, [int(row["benefit"]) for row in edges])
    if abs(auc - .823401708567509) > 1e-15:
        raise DA017Error("DA-004 grouped benefit replay differs")
    for edge, score in zip(edges, scores, strict=True):
        edge["benefit_score"] = float(score)
    by_question: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        by_question[_qkey(edge)].append(edge)
    output = []
    control_totals = Counter()
    for key in sorted(by_question):
        role_row = roles[key]
        direct_ids = list(role_row["direct_ids"])
        direct_set = set(direct_ids)
        direct_pairs = [members[value] for value in direct_ids]
        role = role_pattern_pairs(direct_pairs)
        direct_texts = [str(member["text"]) for pair in direct_pairs for member in pair]
        dictionary = encode(direct_texts)
        phrase_chars = role.chars - sum(map(len, direct_texts)) + dictionary.content_chars + dictionary.declaration_chars
        if role.chars - phrase_chars != int(phrases[key]["incremental_savings"]):
            raise DA017Error("DA-015 NF-004 savings reproduction differs")
        eligible = [edge for edge in by_question[key] if edge["neighbor_id"] not in direct_set]
        ordered = sorted(eligible, key=lambda edge: (-edge["benefit_score"], *_tie(edge)))
        control = allocate_turn_payloads(role, direct_ids, ordered, members, payloads, "PAIR_THEN_TURN")
        for field in ("pair_admissions", "member_admissions", "pair_overflows", "member_overflows"):
            control_totals[field] += int(control[field])
        used = phrase_chars
        seen_pairs: set[str] = set()
        seen_dialogues: set[str] = set()
        actions = []
        for edge in ordered:
            neighbor_id = str(edge["neighbor_id"])
            if neighbor_id in direct_set or neighbor_id in seen_pairs:
                actions.append({"neighbor_id": neighbor_id, "kind": "DUPLICATE", "member": None, "cost": 0})
                continue
            seen_pairs.add(neighbor_id)
            pair = members[neighbor_id]
            payload = payloads[_ekey(edge)]
            raw_texts = [str(member["text"]) for member in pair]
            full_encoded = encode_existing(raw_texts, dictionary)
            full_cost = _payload_cost(role, pair, dictionary)
            selected = int(payload["selected_member_index"])
            turn_encoded = encode_existing([raw_texts[selected]], dictionary)
            turn_cost = _payload_cost(role, [pair[selected]], dictionary)
            if used + full_cost <= BUDGET:
                kind, member_index, cost = "PAIR", None, full_cost
                role = append_role_pair(role, pair)
                seen_dialogues.update(str(member["dialogue_id"]) for member in pair)
            else:
                dialogue_id = str(pair[selected]["dialogue_id"])
                if dialogue_id in seen_dialogues:
                    kind, member_index, cost = "DUPLICATE", selected, 0
                elif used + turn_cost <= BUDGET:
                    kind, member_index, cost = "TURN", selected, turn_cost
                    role = append_role_pair(role, [pair[selected]])
                    seen_dialogues.add(dialogue_id)
                else:
                    kind, member_index, cost = "SKIP", selected, 0
            used += cost
            actions.append({"seed_id": edge["seed_id"], "neighbor_id": neighbor_id,
                            "kind": kind, "member": member_index, "cost": cost,
                            "full_cost": full_cost, "turn_cost": turn_cost,
                            "full_dictionary_savings": sum(map(len, raw_texts)) - full_encoded.content_chars,
                            "turn_dictionary_savings": len(raw_texts[selected]) - turn_encoded.content_chars})
        output.append({"comparison_key": key[0], "duplicate_ordinal": key[1],
                       "sample_id": role_row["sample_id"], "source_index": role_row["source_index"],
                       "direct_ids": direct_ids, "role_chars": int(role_row["role_compact_chars"]),
                       "phrase_chars": phrase_chars, "prefix": dictionary.prefix,
                       "phrases": list(dictionary.phrases), "declaration_chars": dictionary.declaration_chars,
                       "final_chars": used, "actions": actions})
    expected_control = Counter({"pair_admissions": 2_535, "member_admissions": 1_176,
                                "pair_overflows": 11_445, "member_overflows": 10_269})
    if len(output) != 1_098 or control_totals != expected_control:
        raise DA017Error(f"DA-010 mechanical control differs: {control_totals}")
    return output, {"benefit_auc": auc, "control": dict(control_totals)}


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, phrase_path: Path, payload_path: Path, role_path: Path,
                  perturbation_path: Path, label_path: Path, g6_path: Path, output_dir: Path) -> dict[str, Any]:
    rows, anchor = build_rows(dataset_path, phrase_path, payload_path, role_path, perturbation_path, label_path, g6_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da017-") as directory:
        replay, replay_anchor = build_rows(dataset_path, phrase_path, payload_path, role_path, perturbation_path, label_path, g6_path)
        replay_path = Path(directory) / path.name
        _write(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes() and anchor == replay_anchor
    actions = Counter(action["kind"] for row in rows for action in row["actions"])
    coded = sum(action.get("full_dictionary_savings", 0) > 0 or action.get("turn_dictionary_savings", 0) > 0
                for row in rows for action in row["actions"])
    differs = actions["PAIR"] != 2_535 or actions["TURN"] != 1_176
    passed = identical and actions["PAIR"] and actions["TURN"] and actions["SKIP"] and coded and differs
    result = {"schema": "da017-blind-allocation-v1", "status": "PASS" if passed else "FAIL",
              "questions": len(rows), "edges": sum(len(row["actions"]) for row in rows),
              "benefit_auc": anchor["benefit_auc"], "control": anchor["control"],
              "actions": dict(sorted(actions.items())), "coded_payload_edges": coded,
              "median_phrase_chars": sorted(row["phrase_chars"] for row in rows)[548],
              "median_final_chars": sorted(row["final_chars"] for row in rows)[548],
              "allocation_sha256": sha256_file(path), "replay_byte_identical": identical,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA017Error("DA-017 preflight failed")
    return result


__all__ = ["DA017Error", "build_rows", "run_preflight"]
