"""Exact LongMem evidence analysis for DA-025 atomic additions."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "2ce54a9c4bec30046eaa583eb543af6e4050c0c790258878aa797f691292aa14"
AUDIT_SHA256 = "22225c9563bf82b12a9a9804d75e227722242148f9f7454420afc0619046d771"


class DA025AnalysisError(RuntimeError):
    pass


def paired(rows: Sequence[Mapping[str, Any]], left: str, right: str) -> dict[str, Any]:
    gains = sum(not row[left] and row[right] for row in rows)
    losses = sum(row[left] and not row[right] for row in rows)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / 2**n) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": len(rows) - n, "discordant": n, "two_sided_exact_p": p}


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA025AnalysisError("Population differs")
    return frozenset(str(row["question_id"])
                     for row in json.loads(path.read_text(encoding="utf-8"))["rows"])


def _delivered(actions: Sequence[Mapping[str, Any]], identities: Mapping[str, Sequence[str]], atomic: bool = False) -> set[str]:
    output = set()
    for action in actions:
        if action["kind"] == "PAIR":
            output.update(identities[str(action["neighbor_id"])])
        elif action["kind"] in ({"MEMBER"} if atomic else {"TURN"}):
            output.add(identities[str(action["neighbor_id"])][int(action["member"])])
    return output


def analyze(longmem_path: Path, population_path: Path, selection_path: Path,
            audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA025AnalysisError("Sealed input differs")
    selections = {str(row["question_id"]): row for row in read_gzip(selection_path)}
    wrong = {str(row["key"]) for row in read_gzip(audit_path)
             if row["corpus"] == "LONGMEM" and row["blocker"] == "WRONG_FROZEN_MEMBER"}
    records = {record.question_id: record for record in adapt_population(longmem_path, _ids(population_path))}
    rows = []
    for question_id in sorted(records):
        record, selection = records[question_id], selections[question_id]
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        gold = {turn.candidate.identity for turn in record.turns if turn.is_target}
        direct = set().union(*(identities[value] for value in selection["direct_ids"]))
        baseline = _delivered(selection["baseline_actions"], identities)
        da023 = baseline | _delivered(selection["da023_additions"], identities)
        treatment = baseline | _delivered(selection["treatment"]["actions"], identities, True)
        row = {"question_id": question_id, "question_type": record.question_type,
               "wrong_member_residual": question_id in wrong,
               "DIRECT": gold <= direct, "DA016": gold <= direct | baseline,
               "DA023": gold <= direct | da023, "DA025": gold <= direct | treatment}
        if row["DA016"] and not row["DA025"]:
            raise DA025AnalysisError("Immutable baseline loss")
        rows.append(row)
    totals = {arm: sum(row[arm] for row in rows) for arm in ("DIRECT", "DA016", "DA023", "DA025")}
    if (totals["DIRECT"], totals["DA016"], totals["DA023"]) != (164, 188, 202):
        raise DA025AnalysisError("Control anchors differ")
    contrast = paired(rows, "DA023", "DA025")
    by_type = {}
    for kind in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == kind]
        by_type[kind] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell) for arm in totals},
                         "contrast": paired(cell, "DA023", "DA025")}
    wrong_rows = [row for row in rows if row["wrong_member_residual"]]
    wrong_contrast = paired(wrong_rows, "DA023", "DA025")
    signal = contrast["gains"] >= 5 and contrast["losses"] == 0 and all(
        cell["contrast"]["net"] >= 0 for cell in by_type.values())
    result = {"schema": "da025-atomic-result-v1",
              "status": "LONGMEM_ATOMIC_ADDITION_SIGNAL" if signal else "NO_LONGMEM_ATOMIC_ADDITION_SIGNAL",
              "population": len(rows), "complete": totals, "contrast_vs_da023": contrast,
              "contrast_vs_da016": paired(rows, "DA016", "DA025"), "by_question_type": by_type,
              "wrong_member_residuals": {"n": len(wrong_rows), "contrast": wrong_contrast},
              "one_hop_ceiling": 250, "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent LongMem availability; runtime and reader unvalidated"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(longmem_path: Path, population_path: Path, selection_path: Path,
                 audit_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, selection_path, audit_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da025-result-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, selection_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA025AnalysisError("Result replay differs")
    return result


__all__ = ["DA025AnalysisError", "analyze", "paired", "run_analysis"]

