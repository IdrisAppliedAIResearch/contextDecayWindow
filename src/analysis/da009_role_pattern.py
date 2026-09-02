"""Blind reversible role-pattern rendering for DA-009."""

from __future__ import annotations

import json
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da003_edge_features import write_rows
from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import BUDGET, _member_maps
from analysis.da008_compact_direct import DA008Error
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file

DA008_BLIND_SHA256 = "73901fe02011f81f29fa97bcaf6da8a2ab68f9e6155143d8f0d50da4cb1b9e72"


class DA009Error(DA008Error):
    pass


@dataclass(frozen=True)
class RolePatternContext:
    speakers: tuple[str, ...]
    default_pattern: tuple[int, ...]
    pairs: tuple[tuple[tuple[int, str], ...], ...]

    @property
    def dictionary_chars(self) -> int:
        return sum(len(f"@{index}={speaker}") for index, speaker in enumerate(self.speakers))

    @property
    def pattern_chars(self) -> int:
        return len("@pair=" + ",".join(map(str, self.default_pattern)))

    @property
    def pair_chars(self) -> tuple[int, ...]:
        output = []
        for pair in self.pairs:
            codes = tuple(code for code, _ in pair)
            if codes == self.default_pattern:
                output.append(sum(len(text) for _, text in pair) + max(0, len(pair) - 1))
            else:
                output.append(sum(len(f"{code}:{text}") for code, text in pair) + max(0, len(pair) - 1))
        return tuple(output)

    @property
    def chars(self) -> int:
        return self.dictionary_chars + self.pattern_chars + sum(self.pair_chars)


def role_pattern_pairs(pairs: Sequence[Sequence[Mapping[str, str]]]) -> RolePatternContext:
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
    counts = Counter(tuple(code for code, _ in pair) for pair in encoded)
    default = min(counts, key=lambda pattern: (-counts[pattern], pattern)) if counts else tuple()
    return RolePatternContext(tuple(speakers), default, tuple(encoded))


def decode_role_pairs(context: RolePatternContext) -> list[str]:
    output = []
    for pair in context.pairs:
        try:
            output.append("\n".join(f"{context.speakers[code]}: {text}" for code, text in pair))
        except IndexError as exc:
            raise DA009Error("Role-pattern speaker code is out of range") from exc
    return output


def append_role_pair(context: RolePatternContext, pair: Sequence[Mapping[str, str]]) -> RolePatternContext:
    speakers = list(context.speakers)
    codes = {speaker: index for index, speaker in enumerate(speakers)}
    encoded = []
    for member in pair:
        speaker = str(member["speaker"])
        if speaker not in codes:
            codes[speaker] = len(speakers)
            speakers.append(speaker)
        encoded.append((codes[speaker], str(member["text"])))
    return RolePatternContext(tuple(speakers), context.default_pattern, (*context.pairs, tuple(encoded)))


def incremental_role_cost(context: RolePatternContext, pair: Sequence[Mapping[str, str]]) -> int:
    return append_role_pair(context, pair).chars - context.chars


def build_rows(dataset_path: Path, da008_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da008_path) != DA008_BLIND_SHA256:
        raise DA009Error("DA-008 blind compact artifact differs")
    cases = load_blind_cases(dataset_path)
    members, _ = _member_maps(dataset_path, cases)
    output = []
    for row in read_gzip(da008_path):
        pairs = [members[identity] for identity in row["direct_ids"]]
        context = role_pattern_pairs(pairs)
        originals = ["\n".join(f"{member['speaker']}: {member['text']}" for member in pair) for pair in pairs]
        if decode_role_pairs(context) != originals:
            raise DA009Error("DA-009 role-pattern decode differs")
        incremental = int(row["compact_chars"]) - context.chars
        if incremental < 0 or context.chars > int(row["compact_chars"]):
            raise DA009Error("DA-009 role-pattern renderer expands")
        signatures = [tuple(code for code, _ in pair) for pair in context.pairs]
        matching = sum(signature == context.default_pattern for signature in signatures)
        output.append({
            **{key: row[key] for key in ("comparison_key", "duplicate_ordinal", "sample_id", "source_index", "direct_ids", "direct_sha256", "direct_count", "original_chars")},
            "da008_compact_chars": int(row["compact_chars"]), "role_compact_chars": context.chars,
            "incremental_savings": incremental, "total_savings": int(row["original_chars"]) - context.chars,
            "slack": BUDGET - context.chars, "speakers": list(context.speakers),
            "default_pattern": list(context.default_pattern), "pattern_chars": context.pattern_chars,
            "matching_pairs": matching, "exception_pairs": len(signatures) - matching,
            "pair_chars": list(context.pair_chars), "decode_sha256": row["decode_sha256"],
            "eligible_neighbor_count": row["eligible_neighbor_count"], "edge_count": row["edge_count"],
        })
    if len(output) != 1_104:
        raise DA009Error("DA-009 blind population differs")
    return output


def run_preflight(dataset_path: Path, da008_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(dataset_path, da008_path)
    path = output_dir / "blind_role_pattern.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da009-") as directory:
        replay_path = Path(directory) / path.name
        write_rows(replay_path, build_rows(dataset_path, da008_path))
        identical = path.read_bytes() == replay_path.read_bytes()
    savings = sorted(int(row["incremental_savings"]) for row in rows)
    median = (savings[551] + savings[552]) / 2
    reachability = {
        "matching_pairs": sum(row["matching_pairs"] for row in rows),
        "exception_pairs": sum(row["exception_pairs"] for row in rows),
        "positive_savings_rows": sum(row["incremental_savings"] > 0 for row in rows),
        "expanding_rows": sum(row["incremental_savings"] < 0 for row in rows),
    }
    status = "PASS" if identical and not reachability["expanding_rows"] and median >= 128 and reachability["exception_pairs"] else "FAIL"
    result = {
        "schema": "da009-role-pattern-preflight-v1", "status": status, "rows": len(rows),
        "conversations": sorted({row["sample_id"] for row in rows}), "median_incremental_savings": median,
        "min_incremental_savings": min(savings), "max_incremental_savings": max(savings),
        "default_patterns": {",".join(map(str, pattern)): count for pattern, count in
                             sorted(Counter(tuple(row["default_pattern"]) for row in rows).items())},
        "reachability": reachability, "selection_sha256": sha256_file(path), "replay_byte_identical": identical,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
    }
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if status != "PASS":
        raise DA009Error("DA-009 blind preflight failed")
    return result


__all__ = ["DA009Error", "RolePatternContext", "append_role_pair", "decode_role_pairs", "incremental_role_cost", "role_pattern_pairs", "run_preflight"]
