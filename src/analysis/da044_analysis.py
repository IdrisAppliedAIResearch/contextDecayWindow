"""Exact evidence-delivery analysis for DA-044 auxiliary pages."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.da032_audit import distribution
from analysis.da033_analysis import _delivered, paired
from analysis.da044_allocation import parse_page
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "24e58f888d0f262a86af6c2a97e219175628c4d88aa0c56f3e2236c2ee848730"
AUDIT_SHA256 = "b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727"


class DA044AnalysisError(RuntimeError):
    pass


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA044AnalysisError("Population differs")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in data["rows"])


def analyze(longmem_path: Path, population_path: Path, selection_path: Path,
            audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA044AnalysisError("Sealed input differs")
    selections = {str(row["question_id"]): row for row in read_gzip(selection_path)}
    blockers = {str(row["key"]): str(row["blocker"]) for row in read_gzip(audit_path)}
    records = {record.question_id: record for record in adapt_population(longmem_path, _ids(population_path))}
    rows = []
    for question_id in sorted(records):
        selection, record = selections[question_id], records[question_id]
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        gold = {turn.candidate.identity for turn in record.turns if turn.is_target}
        direct = set().union(*(identities[value] for value in selection["direct_ids"]))
        control_set = (direct | _delivered(selection["baseline_actions"], identities)
                       | _delivered(selection["da023"]["additions"], identities)
                       | _delivered(selection["control"]["actions"], identities)
                       | _delivered(selection["da031_control"]["actions"], identities)
                       | _delivered(selection["da033_control"]["actions"], identities)
                       | _delivered(selection["da038_control"]["actions"], identities))
        decoded = parse_page(str(selection["treatment"]["page"]),
                             str(selection["da038_control"]["sentinel"]))
        if [ordinal for ordinal, _, _ in decoded] != [node["ordinal"] for node in selection["treatment"]["nodes"]]:
            raise DA044AnalysisError("Page node decode differs")
        page_set = {identities[str(node["neighbor_id"])][int(node["member"])]
                    for node in selection["treatment"]["nodes"]}
        treatment_set = control_set | page_set
        control, treatment = gold <= control_set, gold <= treatment_set
        if control and not treatment:
            raise DA044AnalysisError("Protected DA-038 loss")
        rows.append({"question_id": question_id, "question_type": record.question_type,
                     "CONTROL": control, "TREATMENT": treatment,
                     "blocker": blockers.get(question_id),
                     "page_chars": int(selection["treatment"]["page_chars"]),
                     "page_nodes": len(selection["treatment"]["nodes"])})
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    if len(rows) != 465 or complete["CONTROL"] != 232:
        raise DA044AnalysisError("Control anchor differs")
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell),
                         "complete": {arm: sum(row[arm] for row in cell) for arm in complete},
                         "contrast": paired(cell)}
    contrast = paired(rows)
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    nonnegative = all(cell["contrast"]["net"] >= 0 for cell in groups.values())
    if contrast["gains"] >= 12 and contrast["losses"] == 0 and nonnegative:
        status = "AUXILIARY_FRONTIER_PAGE_SIGNAL"
    elif contrast["gains"] >= 5 and contrast["losses"] == 0 and nonnegative:
        status = "WEAK_AUXILIARY_FRONTIER_PAGE_SIGNAL"
    else:
        status = "NO_AUXILIARY_FRONTIER_PAGE_SIGNAL"
    total_chars = sum(row["page_chars"] for row in rows)
    result = {"schema": "da044-auxiliary-frontier-page-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "by_question_type": groups, "one_hop_ceiling": 250,
              "capacity_attribution": {"total_auxiliary_chars": total_chars,
                                       "chars_per_gain_population": (total_chars / contrast["gains"]
                                                                      if contrast["gains"] else None),
                                       "page_chars": distribution([row["page_chars"] for row in rows]),
                                       "page_nodes": distribution([row["page_nodes"] for row in rows]),
                                       "gain_row_page_chars": distribution([row["page_chars"] for row in gains])},
              "gain_blockers": {name: sum(row["blocker"] == name for row in gains)
                                for name in sorted({row["blocker"] for row in gains if row["blocker"]})},
              "protected_da038_losses": contrast["losses"],
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent exact availability with added auxiliary capacity; no reader/runtime claim"}
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
    with tempfile.TemporaryDirectory(prefix="da044-result-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, selection_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA044AnalysisError("Result replay differs")
    return result


__all__ = ["DA044AnalysisError", "analyze", "run_analysis"]
