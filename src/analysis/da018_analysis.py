"""Exact evidence scoring for frozen DA-018 allocations."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.da018_allocation import ARMS
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split
from analysis.nf005_measurement import adapt_population

ALLOCATION_SHA256 = "3928700040ffe7931b5865414867b149595db67a431f32dc97a72d4e9f7ffcdb"
NF_CONTROL_SHA256 = "d69a5e1a1585f0e1988bb6599af9fd53d2d84c5d4d70e3783d96c6427839d9b8"
LONG_CONTROL_SHA256 = "aaca474da552a7273ee681686efe887e066143919bd329e56fa41ff47d6ad5d4"


class DA018AnalysisError(RuntimeError):
    pass


def paired(rows: Sequence[Mapping[str, Any]], left: str, right: str) -> dict[str, Any]:
    gains = sum(not row[left] and row[right] for row in rows)
    losses = sum(row[left] and not row[right] for row in rows)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / 2**n) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": len(rows) - n, "discordant": n, "two_sided_exact_p": p}


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA018AnalysisError("DA-018 LongMem population differs")
    return frozenset(str(row["question_id"])
                     for row in json.loads(path.read_text(encoding="utf-8"))["rows"])


def _delivered(actions: Sequence[Mapping[str, Any]], identities: Mapping[str, Sequence[str]]) -> set[str]:
    output = set()
    for action in actions:
        if action["kind"] == "PAIR":
            output.update(identities[str(action["neighbor_id"])])
        elif action["kind"] == "TURN":
            output.add(identities[str(action["neighbor_id"])][int(action["member"])])
    return output


def analyze(dataset_path: Path, longmem_path: Path, population_path: Path,
            allocation_path: Path, nf_control_path: Path,
            long_control_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((allocation_path, ALLOCATION_SHA256), (nf_control_path, NF_CONTROL_SHA256),
             (long_control_path, LONG_CONTROL_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA018AnalysisError("DA-018 sealed allocation/control differs")
    allocations = list(read_gzip(allocation_path))
    nf_alloc = {(str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
                for row in allocations if row["corpus"] == "NF004"}
    long_alloc = {str(row["question_id"]): row for row in allocations if row["corpus"] == "LONGMEM"}
    nf_controls = {(str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
                   for row in read_gzip(nf_control_path)}
    long_controls = {str(row["question_id"]): row for row in read_gzip(long_control_path)}

    nf_evidence, nf_pairs, nf_meta = {}, {}, {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            nf_pairs[source.candidate.identity] = tuple(source.dialogue_ids)
        for question in record.questions:
            key = (question.comparison_key, question.duplicate_ordinal)
            nf_evidence[key] = set(question.resolved_dialogue_ids)
            nf_meta[key] = {"sample_id": question.sample_id, "source_index": question.source_index}
    if set(nf_alloc) != set(nf_controls) or len(nf_alloc) != 1_098:
        raise DA018AnalysisError("DA-018 NF join differs")
    rows = []
    for key in sorted(nf_alloc):
        allocation = nf_alloc[key]
        direct = set().union(*(nf_pairs[value] for value in allocation["direct_ids"]))
        gold = nf_evidence[key]
        row = {"corpus": "NF004", "comparison_key": key[0], "duplicate_ordinal": key[1],
               "group": nf_meta[key]["sample_id"], "DIRECT": gold <= direct,
               "CONTROL": bool(nf_controls[key]["arms"]["PAIR_THEN_TURN"]["complete"])}
        for arm in ARMS:
            linked = _delivered(allocation["arms"][arm]["actions"], nf_pairs)
            row[arm] = gold <= direct | linked
            row[f"{arm}_carried_missing"] = sorted((gold - direct) & linked)
            if row[arm] and not row["DIRECT"] and not (gold - direct) <= linked:
                raise DA018AnalysisError("DA-018 NF gain lacks carrier accounting")
        rows.append(row)

    long_records = {record.question_id: record
                    for record in adapt_population(longmem_path, _population_ids(population_path))}
    if set(long_alloc) != set(long_records) or set(long_alloc) != set(long_controls):
        raise DA018AnalysisError("DA-018 LongMem join differs")
    for question_id in sorted(long_alloc):
        allocation, record = long_alloc[question_id], long_records[question_id]
        episode_turns = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        gold = {turn.candidate.identity for turn in record.turns if turn.is_target}
        direct = set().union(*(episode_turns[value] for value in allocation["direct_ids"]))
        row = {"corpus": "LONGMEM", "question_id": question_id, "group": record.question_type,
               "DIRECT": gold <= direct, "CONTROL": bool(long_controls[question_id]["DA016_PHRASE_LINKS"])}
        for arm in ARMS:
            linked = _delivered(allocation["arms"][arm]["actions"], episode_turns)
            row[arm] = gold <= direct | linked
            row[f"{arm}_carried_missing"] = sorted((gold - direct) & linked)
            if row[arm] and not row["DIRECT"] and not (gold - direct) <= linked:
                raise DA018AnalysisError("DA-018 LongMem gain lacks carrier accounting")
        rows.append(row)

    result_corpora = {}
    for corpus, expected in (("NF004", (935, 970)), ("LONGMEM", (164, 188))):
        subset = [row for row in rows if row["corpus"] == corpus]
        totals = {arm: sum(row[arm] for row in subset) for arm in ("DIRECT", "CONTROL", *ARMS)}
        if (totals["DIRECT"], totals["CONTROL"]) != expected:
            raise DA018AnalysisError(f"DA-018 {corpus} control reproduction differs")
        by_group = {}
        for group in sorted({row["group"] for row in subset}):
            cell = [row for row in subset if row["group"] == group]
            by_group[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell) for arm in totals},
                               "contrasts": {arm: paired(cell, "CONTROL", arm) for arm in ARMS}}
        result_corpora[corpus] = {"n": len(subset), "complete": totals,
                                  "contrasts": {arm: paired(subset, "CONTROL", arm) for arm in ARMS},
                                  "by_group": by_group, "one_hop_ceiling": 986 if corpus == "NF004" else 250}
    qualifying = []
    for arm in ARMS:
        if all(result_corpora[corpus]["contrasts"][arm]["gains"] >= 1 and
               result_corpora[corpus]["contrasts"][arm]["losses"] == 0 and
               all(cell["contrasts"][arm]["net"] >= 0
                   for cell in result_corpora[corpus]["by_group"].values())
               for corpus in result_corpora):
            qualifying.append(arm)
    result = {"schema": "da018-frozen-query-result-v1",
              "status": "CROSS_CORPUS_CARRIER_UTILITY_SIGNAL" if qualifying else "NO_CROSS_CORPUS_CARRIER_UTILITY_SIGNAL",
              "qualifying_arms": qualifying, "corpora": result_corpora,
              "calls": {"embedding": 0, "model": 0, "cache_misses": 0},
              "claim_boundary": "spent-corpus exact availability only; no reader or adoption claim"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, longmem_path: Path, population_path: Path,
                 allocation_path: Path, nf_control_path: Path,
                 long_control_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, longmem_path, population_path, allocation_path,
                           nf_control_path, long_control_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da018-result-") as directory:
        replay_result, replay_rows = analyze(dataset_path, longmem_path, population_path,
                                             allocation_path, nf_control_path, long_control_path)
        replay_path = Path(directory) / path.name
        _write(replay_path, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay_path.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA018AnalysisError("DA-018 result replay differs")
    return result


__all__ = ["DA018AnalysisError", "analyze", "paired", "run_analysis"]
