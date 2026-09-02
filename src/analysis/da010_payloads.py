"""Evidence-blind linked payload choices and costs for DA-010."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da003_edge_features import corpus_idf, tokens, weighted_coverage, write_rows
from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file

DA009_BLIND_SHA256 = "0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb"
DA004_BLIND_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"


class DA010Error(RuntimeError):
    pass


def member_order(question: str, members: Sequence[Mapping[str, str]], idf: Mapping[str, float]) -> tuple[tuple[int, ...], tuple[float, ...]]:
    query = tokens(question)
    coverage = tuple(weighted_coverage(query, tokens(f"{member['speaker']}: {member['text']}"), idf) for member in members)
    order = tuple(sorted(range(len(members)), key=lambda index: (-coverage[index], index)))
    return order, coverage


def payload_costs(context: Any, members: Sequence[Mapping[str, str]]) -> tuple[int, tuple[int, ...]]:
    full = append_role_pair(context, members).chars - context.chars
    turns = tuple(append_role_pair(context, [member]).chars - context.chars for member in members)
    return full, turns


def build_rows(dataset_path: Path, role_path: Path, perturbation_path: Path) -> list[dict[str, Any]]:
    if sha256_file(role_path) != DA009_BLIND_SHA256 or sha256_file(perturbation_path) != DA004_BLIND_SHA256:
        raise DA010Error("DA-010 sealed blind input differs")
    cases = load_blind_cases(dataset_path)
    idf = corpus_idf(cases)
    members, questions = _member_maps(dataset_path, cases)
    roles = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in read_gzip(role_path)}
    contexts = {key: role_pattern_pairs([members[identity] for identity in row["direct_ids"]]) for key, row in roles.items()}
    output = []
    for edge in read_gzip(perturbation_path):
        key = (edge["comparison_key"], int(edge["duplicate_ordinal"]))
        neighbor_members = members[edge["neighbor_id"]]
        order, coverage = member_order(questions[key], neighbor_members, idf)
        full_cost, turn_costs = payload_costs(contexts[key], neighbor_members)
        direct_speakers = set(contexts[key].speakers)
        output.append({
            "comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": edge["sample_id"],
            "source_index": edge["source_index"], "seed_id": edge["seed_id"], "neighbor_id": edge["neighbor_id"],
            "direct_ids": roles[key]["direct_ids"], "direct_sha256": roles[key]["direct_sha256"],
            "role_compact_chars": roles[key]["role_compact_chars"], "slack": roles[key]["slack"],
            "member_order": list(order), "member_coverage": list(coverage),
            "member_dialogue_ids": [member["dialogue_id"] for member in neighbor_members],
            "member_speakers": [member["speaker"] for member in neighbor_members],
            "full_pair_cost": full_cost, "turn_costs": list(turn_costs),
            "selected_member_index": order[0], "selected_turn_cost": turn_costs[order[0]],
            "coverage_tie": len(set(coverage)) < len(coverage),
            "new_speaker_members": sum(member["speaker"] not in direct_speakers for member in neighbor_members),
        })
    if len(output) != 26_100:
        raise DA010Error("DA-010 blind edge population differs")
    return output


def run_preflight(dataset_path: Path, role_path: Path, perturbation_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(dataset_path, role_path, perturbation_path)
    path = output_dir / "blind_payloads.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da010-") as directory:
        replay_path = Path(directory) / path.name
        write_rows(replay_path, build_rows(dataset_path, role_path, perturbation_path))
        identical = path.read_bytes() == replay_path.read_bytes()
    selected = {index: sum(row["selected_member_index"] == index for row in rows) for index in (0, 1)}
    reachability = {
        "selected_member_indices": selected,
        "coverage_ties": sum(row["coverage_tie"] for row in rows),
        "pair_turn_cost_differences": sum(row["full_pair_cost"] != row["selected_turn_cost"] for row in rows),
        "new_speaker_members": sum(row["new_speaker_members"] for row in rows),
        "turn_fits_when_pair_does_not": sum(row["selected_turn_cost"] <= row["slack"] < row["full_pair_cost"] for row in rows),
    }
    passed = (identical and all(selected.values()) and reachability["coverage_ties"]
              and reachability["pair_turn_cost_differences"] and reachability["turn_fits_when_pair_does_not"])
    result = {"schema": "da010-payload-preflight-v1", "status": "PASS" if passed else "FAIL",
              "rows": len(rows), "questions": len({(row["comparison_key"], row["duplicate_ordinal"]) for row in rows}),
              "conversations": sorted({row["sample_id"] for row in rows}), "reachability": reachability,
              "selection_sha256": sha256_file(path), "replay_byte_identical": identical,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA010Error("DA-010 blind payload preflight failed")
    return result


__all__ = ["DA010Error", "member_order", "payload_costs", "run_preflight"]

