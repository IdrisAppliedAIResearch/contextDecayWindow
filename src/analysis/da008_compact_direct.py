"""Blind reversible direct rendering for DA-008 Part A."""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da003_edge_features import write_rows
from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import BUDGET, _member_maps, digest
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file

DA004_BLIND_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
DA002_SHA256 = "25c6f2f8731b19341c440236418e47de95334eb706728b4a5d580cafe7cac8ca"


class DA008Error(RuntimeError):
    pass


def _text_digest(values: Sequence[str]) -> str:
    return hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CompactContext:
    speakers: tuple[str, ...]
    pairs: tuple[tuple[tuple[int, str], ...], ...]

    @property
    def dictionary_chars(self) -> int:
        return sum(len(f"@{index}={speaker}") for index, speaker in enumerate(self.speakers))

    @property
    def pair_chars(self) -> tuple[int, ...]:
        return tuple(sum(len(f"{code}:{text}") for code, text in pair) + max(0, len(pair) - 1) for pair in self.pairs)

    @property
    def chars(self) -> int:
        return self.dictionary_chars + sum(self.pair_chars)


def compact_pairs(pairs: Sequence[Sequence[Mapping[str, str]]]) -> CompactContext:
    speakers: list[str] = []
    codes: dict[str, int] = {}
    encoded = []
    for pair in pairs:
        compact_pair = []
        for member in pair:
            speaker, text = str(member["speaker"]), str(member["text"])
            if speaker not in codes:
                codes[speaker] = len(speakers)
                speakers.append(speaker)
            compact_pair.append((codes[speaker], text))
        encoded.append(tuple(compact_pair))
    return CompactContext(tuple(speakers), tuple(encoded))


def decode_pairs(context: CompactContext) -> list[str]:
    output = []
    for pair in context.pairs:
        try:
            output.append("\n".join(f"{context.speakers[code]}: {text}" for code, text in pair))
        except IndexError as exc:
            raise DA008Error("Compact speaker code is out of range") from exc
    return output


def incremental_pair_cost(context: CompactContext, pair: Sequence[Mapping[str, str]]) -> int:
    speakers = list(context.speakers)
    codes = {speaker: index for index, speaker in enumerate(speakers)}
    dictionary_cost = 0
    member_cost = 0
    for index, member in enumerate(pair):
        speaker, text = str(member["speaker"]), str(member["text"])
        if speaker not in codes:
            code = len(speakers)
            codes[speaker] = code
            speakers.append(speaker)
            dictionary_cost += len(f"@{code}={speaker}")
        member_cost += len(f"{codes[speaker]}:{text}") + (1 if index else 0)
    return dictionary_cost + member_cost


def build_rows(dataset_path: Path, perturbation_path: Path, provenance_path: Path) -> list[dict[str, Any]]:
    if sha256_file(perturbation_path) != DA004_BLIND_SHA256 or sha256_file(provenance_path) != DA002_SHA256:
        raise DA008Error("DA-008 sealed blind input differs")
    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    provenance = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in read_gzip(provenance_path)}
    edges = read_gzip(perturbation_path)
    by_question: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for edge in edges:
        key = (edge["comparison_key"], int(edge["duplicate_ordinal"]))
        by_question.setdefault(key, []).append(edge)
    rows = []
    for key in sorted(by_question):
        question_edges = by_question[key]
        direct = list(question_edges[0]["direct_selected_ids"])
        if any(edge["direct_selected_ids"] != direct for edge in question_edges):
            raise DA008Error("DA-008 direct identities differ within question")
        selected_members = [members[identity] for identity in direct]
        compact = compact_pairs(selected_members)
        decoded = decode_pairs(compact)
        originals = ["\n".join(f"{member['speaker']}: {member['text']}" for member in pair) for pair in selected_members]
        if decoded != originals:
            raise DA008Error("DA-008 compact decode differs")
        candidate_rows = provenance[key]["candidates"]
        original_chars = sum(int(candidate_rows[identity]["chars"]) for identity in direct)
        if original_chars != sum(map(len, originals)) or compact.chars > original_chars:
            raise DA008Error("DA-008 direct charging differs or expands")
        eligible = {edge["neighbor_id"] for edge in question_edges if edge["neighbor_id"] not in set(direct)}
        rows.append({
            "comparison_key": key[0], "duplicate_ordinal": key[1],
            "sample_id": question_edges[0]["sample_id"], "source_index": question_edges[0]["source_index"],
            "direct_ids": direct, "direct_sha256": digest(direct), "direct_count": len(direct),
            "original_chars": original_chars, "compact_chars": compact.chars,
            "dictionary_chars": compact.dictionary_chars, "pair_chars": list(compact.pair_chars),
            "savings": original_chars - compact.chars, "slack": BUDGET - compact.chars,
            "speakers": list(compact.speakers), "decode_sha256": _text_digest(originals),
            "eligible_neighbor_count": len(eligible), "edge_count": len(question_edges),
        })
    if len(rows) != 1_104 or {row["sample_id"] for row in rows} != {case["sample_id"] for case in cases}:
        raise DA008Error("DA-008 blind question population differs")
    return rows


def run_preflight(dataset_path: Path, perturbation_path: Path, provenance_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(dataset_path, perturbation_path, provenance_path)
    path = output_dir / "blind_compact_direct.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da008-") as directory:
        replay = build_rows(dataset_path, perturbation_path, provenance_path)
        replay_path = Path(directory) / path.name
        write_rows(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    savings = sorted(int(row["savings"]) for row in rows)
    median = (savings[551] + savings[552]) / 2
    reachability = {
        "positive_slack_rows": sum(int(row["slack"]) > 0 for row in rows),
        "positive_savings_rows": sum(int(row["savings"]) > 0 for row in rows),
        "expanding_rows": sum(int(row["savings"]) < 0 for row in rows),
        "eligible_neighbor_rows": sum(int(row["eligible_neighbor_count"]) > 0 for row in rows),
    }
    status = "PASS" if identical and not reachability["expanding_rows"] and median >= 256 else "FAIL"
    result = {
        "schema": "da008-compact-direct-preflight-v1", "status": status, "rows": len(rows),
        "conversations": sorted({row["sample_id"] for row in rows}), "median_savings": median,
        "min_savings": min(savings), "max_savings": max(savings), "reachability": reachability,
        "selection_sha256": sha256_file(path), "replay_byte_identical": identical,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
    }
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if status != "PASS":
        raise DA008Error("DA-008 Part A preflight failed")
    return result


__all__ = ["CompactContext", "DA008Error", "compact_pairs", "decode_pairs", "incremental_pair_cost", "run_preflight"]
