"""Lossless phrase-dictionary rendering for DA-015."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import role_pattern_pairs
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.nf004_anatomy_features import load_blind_cases

WORD = re.compile(r"[A-Za-z0-9]+")
DA009_SHA256 = "0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb"
DA013_DIRECT_SHA256 = "9544fd5bc6ad85515f5cb99472cb844e2c8b9f97cd1f51a19de2d882da47ff5c"


class DA015Error(RuntimeError):
    pass


@dataclass(frozen=True)
class Segment:
    kind: str
    value: str | int


@dataclass(frozen=True)
class PhraseContext:
    prefix: str
    phrases: tuple[str, ...]
    members: tuple[tuple[Segment, ...], ...]
    declaration_chars: int

    @property
    def content_chars(self) -> int:
        return sum(
            len(str(segment.value)) if segment.kind == "literal" else len(code(self.prefix, int(segment.value)))
            for member in self.members for segment in member
        )


def code(prefix: str, index: int) -> str:
    return f"{prefix}p{index}{prefix}"


def _prefix(texts: Sequence[str]) -> str:
    prefix = "~"
    while any(f"{prefix}p" in text for text in texts):
        prefix += "~"
    return prefix


def _declaration(prefix: str, index: int, phrase: str) -> str:
    return f"@{code(prefix, index)}={json.dumps(phrase, ensure_ascii=True)}"


def _candidates(texts: Sequence[str]) -> tuple[str, ...]:
    counts: Counter[str] = Counter()
    for text in texts:
        words = list(WORD.finditer(text))
        seen_in_text: Counter[str] = Counter()
        for start in range(len(words)):
            for width in range(2, 7):
                end = start + width
                if end > len(words):
                    break
                phrase = text[words[start].start() : words[end - 1].end()]
                if len(phrase) <= 80:
                    seen_in_text[phrase] += 1
        counts.update(seen_in_text)
    return tuple(sorted(phrase for phrase, count in counts.items() if count >= 2))


def _occurrences(members: Sequence[Sequence[Segment]], phrase: str) -> int:
    total = 0
    for member in members:
        for segment in member:
            if segment.kind != "literal":
                continue
            text = str(segment.value)
            position = 0
            while (found := text.find(phrase, position)) >= 0:
                total += 1
                position = found + len(phrase)
    return total


def _replace(members: Sequence[Sequence[Segment]], phrase: str, phrase_index: int) -> tuple[tuple[Segment, ...], ...]:
    output = []
    for member in members:
        encoded = []
        for segment in member:
            if segment.kind != "literal":
                encoded.append(segment)
                continue
            text = str(segment.value)
            position = 0
            while (found := text.find(phrase, position)) >= 0:
                if found > position:
                    encoded.append(Segment("literal", text[position:found]))
                encoded.append(Segment("code", phrase_index))
                position = found + len(phrase)
            if position < len(text):
                encoded.append(Segment("literal", text[position:]))
        output.append(tuple(encoded))
    return tuple(output)


def encode(texts: Sequence[str]) -> PhraseContext:
    prefix = _prefix(texts)
    members: tuple[tuple[Segment, ...], ...] = tuple((Segment("literal", text),) for text in texts)
    phrases: list[str] = []
    declaration_chars = 0
    candidates = list(_candidates(texts))
    while True:
        index = len(phrases)
        encoded_code = code(prefix, index)
        choices = []
        still_viable = []
        for phrase in candidates:
            if phrase in phrases:
                continue
            count = _occurrences(members, phrase)
            if count < 2:
                continue
            declaration = len(_declaration(prefix, index, phrase)) + (1 if phrases else 0)
            net = count * (len(phrase) - len(encoded_code)) - declaration
            if net > 0:
                choices.append((net, len(phrase), phrase, count, declaration))
                still_viable.append(phrase)
        if not choices:
            break
        # Replacements only split/remove literal spans, so occurrence counts
        # cannot increase. Code and declaration costs cannot decrease either.
        # A nonpositive candidate can therefore never become viable later.
        candidates = still_viable
        net, _, phrase, _, declaration = min(choices, key=lambda item: (-item[0], -item[1], item[2]))
        before = PhraseContext(prefix, tuple(phrases), members, declaration_chars).content_chars + declaration_chars
        members = _replace(members, phrase, index)
        phrases.append(phrase)
        declaration_chars += declaration
        after = PhraseContext(prefix, tuple(phrases), members, declaration_chars).content_chars + declaration_chars
        if before - after != net:
            raise DA015Error("Phrase net-savings accounting differs")
    return PhraseContext(prefix, tuple(phrases), members, declaration_chars)


def decode(context: PhraseContext) -> tuple[str, ...]:
    output = []
    for member in context.members:
        chunks = []
        for segment in member:
            if segment.kind == "literal":
                chunks.append(str(segment.value))
            elif 0 <= int(segment.value) < len(context.phrases):
                chunks.append(context.phrases[int(segment.value)])
            else:
                raise DA015Error("Phrase code is out of range")
        output.append("".join(chunks))
    return tuple(output)


def _row(corpus: str, key: str, direct_ids: Sequence[str], pairs: Sequence[Sequence[Mapping[str, str]]],
         expected_role_chars: int) -> dict[str, Any]:
    role = role_pattern_pairs(pairs)
    if role.chars != expected_role_chars:
        raise DA015Error(f"{corpus} role-pattern reproduction differs")
    texts = [str(member["text"]) for pair in pairs for member in pair]
    encoded = encode(texts)
    if decode(encoded) != tuple(texts):
        raise DA015Error("Phrase dictionary does not decode exactly")
    compressed = role.chars - sum(map(len, texts)) + encoded.content_chars + encoded.declaration_chars
    if compressed > role.chars:
        encoded = PhraseContext(encoded.prefix, tuple(), tuple((Segment("literal", text),) for text in texts), 0)
        compressed = role.chars
    replacements = sum(segment.kind == "code" for member in encoded.members for segment in member)
    return {
        "corpus": corpus, "key": key, "direct_ids": list(direct_ids), "role_chars": role.chars,
        "phrase_chars": compressed, "incremental_savings": role.chars - compressed,
        "dictionary_entries": len(encoded.phrases), "declaration_chars": encoded.declaration_chars,
        "replacements": replacements, "prefix": encoded.prefix,
        "dictionary_sha256": hashlib.sha256("\0".join(encoded.phrases).encode("utf-8")).hexdigest(),
        "decode_sha256": hashlib.sha256("\0".join(texts).encode("utf-8")).hexdigest(),
    }


def build_rows(locomo_path: Path, da009_path: Path, longmem_path: Path, population_path: Path,
               da013_direct_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da009_path) != DA009_SHA256 or sha256_file(da013_direct_path) != DA013_DIRECT_SHA256:
        raise DA015Error("DA-015 direct input differs")
    cases = load_blind_cases(locomo_path)
    members, _ = _member_maps(locomo_path, cases)
    output = []
    for row in read_gzip(da009_path):
        pairs = [members[value] for value in row["direct_ids"]]
        key = f"{row['comparison_key']}:{int(row['duplicate_ordinal'])}"
        output.append(_row("NF004", key, row["direct_ids"], pairs, int(row["role_compact_chars"])))
    longmem = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    for row in read_gzip(da013_direct_path):
        record = longmem[row["question_id"]]
        by_id = {episode.candidate.identity: episode for episode in record.episodes}
        pairs = [by_id[value].members for value in row["direct_ids"]]
        output.append(_row("DA013", row["question_id"], row["direct_ids"], pairs, int(row["compact_chars"])))
    if Counter(row["corpus"] for row in output) != Counter({"NF004": 1_104, "DA013": 465}):
        raise DA015Error("DA-015 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(locomo_path: Path, da009_path: Path, longmem_path: Path, population_path: Path,
                  da013_direct_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(locomo_path, da009_path, longmem_path, population_path, da013_direct_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_phrase_rows.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da015-") as directory:
        replay = build_rows(locomo_path, da009_path, longmem_path, population_path, da013_direct_path)
        replay_path = Path(directory) / path.name
        _write(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    corpora = {}
    for corpus in ("NF004", "DA013"):
        selected = [row for row in rows if row["corpus"] == corpus]
        savings = [int(row["incremental_savings"]) for row in selected]
        corpora[corpus] = {
            "rows": len(selected), "median_incremental_savings": float(np.median(savings)),
            "p10_incremental_savings": float(np.percentile(savings, 10)),
            "p90_incremental_savings": float(np.percentile(savings, 90)),
            "max_incremental_savings": max(savings), "zero_dictionary_rows": sum(not row["dictionary_entries"] for row in selected),
            "max_dictionary_entries": max(int(row["dictionary_entries"]) for row in selected),
            "total_replacements": sum(int(row["replacements"]) for row in selected),
        }
    passed = identical and all(value["median_incremental_savings"] >= 100 for value in corpora.values())
    result = {"schema": "da015-phrase-preflight-v1", "status": "TRANSFERABLE_CAPACITY_SIGNAL" if passed else "NO_TRANSFERABLE_CAPACITY_SIGNAL",
              "corpora": corpora, "rows": len(rows), "replay_byte_identical": identical,
              "selection_sha256": sha256_file(path), "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["DA015Error", "PhraseContext", "Segment", "decode", "encode", "run_preflight"]
