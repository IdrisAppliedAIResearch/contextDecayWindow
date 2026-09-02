"""Exact LongMem availability analysis for DA-078."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.da033_analysis import _delivered, distribution, paired
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
AUDIT_SHA256 = "b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727"


class DA078AnalysisError(RuntimeError):
    pass


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA078AnalysisError("Population differs")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in data["rows"])


def analyze(longmem_path: Path, population_path: Path, selection_path: Path,
            audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA078AnalysisError("Sealed input differs")
    selections = {str(row["question_id"]): row for row in read_gzip(selection_path)}
    blockers = {str(row["key"]): str(row["blocker"]) for row in read_gzip(audit_path)}
    records = {
        record.question_id: record
        for record in adapt_population(longmem_path, _ids(population_path))
    }
    rows = []
    for question_id in sorted(records):
        selection, record = selections[question_id], records[question_id]
        identities = {
            episode.candidate.identity: tuple(episode.turn_identities)
            for episode in record.episodes
        }
        gold = {turn.candidate.identity for turn in record.turns if turn.is_target}
        direct = set().union(*(identities[value] for value in selection["direct_ids"]))
        base = (
            direct
            | _delivered(selection["baseline_actions"], identities)
            | _delivered(selection["da023"]["additions"], identities)
            | _delivered(selection["control"]["actions"], identities)
            | _delivered(selection["da031_control"]["actions"], identities)
            | _delivered(selection["da033_control"]["actions"], identities)
        )
        control_set = base | _delivered(selection["da038_control"]["actions"], identities)
        treatment_set = control_set | _delivered(selection["treatment"]["actions"], identities)
        control, treatment = gold <= control_set, gold <= treatment_set
        if control and not treatment:
            raise DA078AnalysisError("Protected DA-038 loss")
        rows.append({
            "question_id": question_id,
            "question_type": record.question_type,
            "CONTROL": control,
            "TREATMENT": treatment,
            "blocker": blockers.get(question_id),
            "actions": selection["treatment"]["actions"],
        })
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    if len(rows) != 465 or complete["CONTROL"] != 232:
        raise DA078AnalysisError("DA-038 control anchor differs")
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {
            "n": len(cell),
            "complete": {arm: sum(row[arm] for row in cell) for arm in complete},
            "contrast": paired(cell),
        }
    contrast = paired(rows)
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    admitted = [
        action for row in rows for action in row["actions"]
        if action["kind"] == "MEMBER"
    ]
    nonnegative = all(cell["contrast"]["net"] >= 0 for cell in groups.values())
    if contrast["gains"] >= 5 and contrast["losses"] == 0 and nonnegative:
        status = "PROTECTED_OPTIMAL_PARSE_SIGNAL"
    elif contrast["gains"] >= 2 and contrast["losses"] == 0 and nonnegative:
        status = "WEAK_PROTECTED_OPTIMAL_PARSE_SIGNAL"
    else:
        status = "NO_PROTECTED_OPTIMAL_PARSE_SIGNAL"
    result = {
        "schema": "da078-protected-optimal-sentinel-result-v1",
        "status": status,
        "population": len(rows),
        "complete": complete,
        "contrast": contrast,
        "by_question_type": groups,
        "one_hop_ceiling": 250,
        "mechanism": {
            "admitted_members": len(admitted),
            "member_cost": distribution([action["cost"] for action in admitted]),
            "member_position": distribution([action["position"] for action in admitted]),
            "gain_blockers": {
                name: sum(row["blocker"] == name for row in gains)
                for name in sorted({row["blocker"] for row in gains if row["blocker"]})
            },
        },
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "spent LongMem exact availability; reader, production runtime, and transfer unvalidated",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(longmem_path: Path, population_path: Path, selection_path: Path,
                 audit_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, selection_path, audit_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "outcomes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da078-result-") as directory:
        replay_result, replay_rows = analyze(
            longmem_path, population_path, selection_path, audit_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["outcomes_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA078AnalysisError("DA-078 outcome replay differs")
    return result


__all__ = ["DA078AnalysisError", "analyze", "run_analysis"]
