"""Exact evidence analysis for frozen DA-020 boundary substitutions."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f"


class DA020AnalysisError(RuntimeError):
    pass


def paired(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    gains = sum(not row["CONTROL"] and row["TREATMENT"] for row in rows)
    losses = sum(row["CONTROL"] and not row["TREATMENT"] for row in rows)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / 2**n) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": len(rows) - n, "discordant": n, "two_sided_exact_p": p}


def distribution(values: Sequence[int | float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA020AnalysisError("DA-020 LongMem population differs")
    return frozenset(str(row["question_id"])
                     for row in json.loads(path.read_text(encoding="utf-8"))["rows"])


def _delivered(actions: Sequence[Mapping[str, Any]], identities: Mapping[str, Sequence[str]]) -> set[str]:
    delivered = set()
    for action in actions:
        if action["kind"] == "PAIR":
            delivered.update(identities[str(action["neighbor_id"])])
        elif action["kind"] == "TURN":
            delivered.add(identities[str(action["neighbor_id"])][int(action["member"])])
    return delivered


def analyze(dataset_path: Path, longmem_path: Path, population_path: Path,
            selection_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256:
        raise DA020AnalysisError("DA-020 frozen selection differs")
    selections = list(read_gzip(selection_path))
    nf = {(str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
          for row in selections if row["corpus"] == "NF004"}
    long = {str(row["question_id"]): row for row in selections if row["corpus"] == "LONGMEM"}

    nf_evidence, nf_pairs, nf_meta = {}, {}, {}
    for record in adapt_split(dataset_path, HOLDOUT_IDS):
        for source in record.candidates:
            nf_pairs[source.candidate.identity] = tuple(source.dialogue_ids)
        for question in record.questions:
            key = (question.comparison_key, question.duplicate_ordinal)
            nf_evidence[key] = set(question.resolved_dialogue_ids)
            nf_meta[key] = (question.sample_id, question.source_index)
    if len(nf) != 1_098:
        raise DA020AnalysisError("DA-020 NF population differs")
    rows = []
    for key in sorted(nf):
        selection = nf[key]
        direct = set().union(*(nf_pairs[value] for value in selection["direct_ids"]))
        control_links = _delivered(selection["baseline_actions"], nf_pairs)
        treatment_links = _delivered(selection["treatment"]["actions"], nf_pairs)
        gold = nf_evidence[key]
        row = {"corpus": "NF004", "comparison_key": key[0], "duplicate_ordinal": key[1],
               "group": nf_meta[key][0], "source_index": nf_meta[key][1],
               "executed": bool(selection["treatment"]["executed"]),
               "DIRECT": gold <= direct, "CONTROL": gold <= direct | control_links,
               "TREATMENT": gold <= direct | treatment_links,
               "removed_evidence": sorted((gold & control_links) - (direct | treatment_links)),
               "added_evidence": sorted((gold & treatment_links) - (direct | control_links))}
        if row["TREATMENT"] and not row["DIRECT"] and not (gold - direct) <= treatment_links:
            raise DA020AnalysisError("DA-020 NF gain lacks carrier accounting")
        rows.append(row)

    records = {record.question_id: record
               for record in adapt_population(longmem_path, _population_ids(population_path))}
    if set(long) != set(records):
        raise DA020AnalysisError("DA-020 LongMem population join differs")
    for question_id in sorted(long):
        selection, record = long[question_id], records[question_id]
        episode_turns = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        direct = set().union(*(episode_turns[value] for value in selection["direct_ids"]))
        control_links = _delivered(selection["baseline_actions"], episode_turns)
        treatment_links = _delivered(selection["treatment"]["actions"], episode_turns)
        gold = {turn.candidate.identity for turn in record.turns if turn.is_target}
        row = {"corpus": "LONGMEM", "question_id": question_id, "group": record.question_type,
               "executed": bool(selection["treatment"]["executed"]),
               "DIRECT": gold <= direct, "CONTROL": gold <= direct | control_links,
               "TREATMENT": gold <= direct | treatment_links,
               "removed_evidence": sorted((gold & control_links) - (direct | treatment_links)),
               "added_evidence": sorted((gold & treatment_links) - (direct | control_links))}
        if row["TREATMENT"] and not row["DIRECT"] and not (gold - direct) <= treatment_links:
            raise DA020AnalysisError("DA-020 LongMem gain lacks carrier accounting")
        rows.append(row)

    corpora = {}
    expected = {"NF004": (935, 970, 571), "LONGMEM": (164, 188, 188)}
    for corpus, anchors in expected.items():
        subset = [row for row in rows if row["corpus"] == corpus]
        complete = {arm: sum(row[arm] for row in subset) for arm in ("DIRECT", "CONTROL", "TREATMENT")}
        executed = sum(row["executed"] for row in subset)
        if (complete["DIRECT"], complete["CONTROL"], executed) != anchors:
            raise DA020AnalysisError(f"DA-020 {corpus} control/activity reproduction differs")
        groups = {}
        for group in sorted({row["group"] for row in subset}):
            cell = [row for row in subset if row["group"] == group]
            groups[group] = {"n": len(cell), "executed": sum(row["executed"] for row in cell),
                             "complete": {arm: sum(row[arm] for row in cell) for arm in complete},
                             "contrast": paired(cell)}
        selection_subset = [row for row in selections if row["corpus"] == corpus and row["treatment"]["executed"]]
        mechanism = {
            "incumbent_cost": distribution([row["treatment"]["incumbent"]["cost"] for row in selection_subset]),
            "replacement_cost": distribution([row["treatment"]["replacement"]["cost"] for row in selection_subset]),
            "incumbent_cosine": distribution([row["treatment"]["incumbent"]["payload_cosine"] for row in selection_subset]),
            "replacement_cosine": distribution([row["treatment"]["replacement"]["payload_cosine"] for row in selection_subset]),
            "incumbent_kind": dict(Counter(row["treatment"]["incumbent"]["kind"] for row in selection_subset)),
            "replacement_kind": dict(Counter(row["treatment"]["replacement"]["kind"] for row in selection_subset)),
            "removed_target_identities": sum(len(row["removed_evidence"]) for row in subset),
            "added_target_identities": sum(len(row["added_evidence"]) for row in subset),
        }
        corpora[corpus] = {"n": len(subset), "complete": complete, "contrast": paired(subset),
                           "by_group": groups, "mechanism": mechanism,
                           "one_hop_ceiling": 986 if corpus == "NF004" else 250}
    signal = all(cell["contrast"]["gains"] >= 1 and cell["contrast"]["losses"] == 0 and
                 all(group["contrast"]["net"] >= 0 for group in cell["by_group"].values())
                 for cell in corpora.values())
    result = {"schema": "da020-boundary-substitution-result-v1",
              "status": "PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL" if signal else "NO_PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL",
              "corpora": corpora, "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent-corpus exact availability only; no reader or adoption claim"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, longmem_path: Path, population_path: Path,
                 selection_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, longmem_path, population_path, selection_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da020-result-") as directory:
        replay_result, replay_rows = analyze(dataset_path, longmem_path, population_path, selection_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA020AnalysisError("DA-020 result replay differs")
    return result


__all__ = ["DA020AnalysisError", "analyze", "paired", "run_analysis"]

