"""Exact LongMem evidence analysis for DA-033."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "22b918036e5ecbd00c0cc032eef61f587b02c1c347505d458b310cd34a961d8e"
AUDIT_SHA256 = "cf7764fa9e96f5621330510704d1deb976f9a623f45047010430b69b0f250cfe"


class DA033AnalysisError(RuntimeError):
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


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA033AnalysisError("Population differs")
    return frozenset(str(row["question_id"])
                     for row in json.loads(path.read_text(encoding="utf-8"))["rows"])


def _delivered(actions: Sequence[Mapping[str, Any]], identities: Mapping[str, Sequence[str]]) -> set[str]:
    output = set()
    for action in actions:
        if action["kind"] == "PAIR":
            output.update(identities[str(action["neighbor_id"])])
        elif action["kind"] in {"TURN", "MEMBER"}:
            output.add(identities[str(action["neighbor_id"])][int(action["member"])])
    return output


def analyze(longmem_path: Path, population_path: Path, selection_path: Path,
            audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA033AnalysisError("Sealed input differs")
    selections = {str(row["question_id"]): row for row in read_gzip(selection_path)}
    blockers = {str(row["key"]): row["blocker"] for row in read_gzip(audit_path)
                if row["corpus"] == "LONGMEM"}
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
                       | _delivered(selection["da031_control"]["actions"], identities))
        treatment_set = control_set | _delivered(selection["treatment"]["actions"], identities)
        control, treatment = gold <= control_set, gold <= treatment_set
        if control and not treatment:
            raise DA033AnalysisError("Protected control loss")
        rows.append({"question_id": question_id, "question_type": record.question_type,
                     "CONTROL": control, "TREATMENT": treatment,
                     "blocker": blockers.get(question_id),
                     "actions": selection["treatment"]["actions"]})
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    if len(rows) != 465 or complete["CONTROL"] != 211:
        raise DA033AnalysisError("Control anchor differs")
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell) for arm in complete},
                         "contrast": paired(cell)}
    contrast = paired(rows)
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    admitted = [action for row in rows for action in row["actions"] if action["kind"] == "MEMBER"]
    nonnegative = all(cell["contrast"]["net"] >= 0 for cell in groups.values())
    if contrast["gains"] >= 5 and contrast["losses"] == 0 and nonnegative:
        status = "LONGMEM_VARINT_ATOMIC_SIGNAL"
    elif contrast["gains"] >= 2 and contrast["losses"] == 0 and nonnegative:
        status = "WEAK_LONGMEM_VARINT_ATOMIC_SIGNAL"
    else:
        status = "NO_LONGMEM_VARINT_ATOMIC_SIGNAL"
    result = {"schema": "da033-longmem-varint-atomic-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "by_question_type": groups, "one_hop_ceiling": 250,
              "mechanism": {"admitted_members": len(admitted),
                            "member_cost": distribution([action["cost"] for action in admitted]),
                            "member_position": distribution([action["position"] for action in admitted]),
                            "gain_blockers": {name: sum(row["blocker"] == name for row in gains)
                                              for name in sorted({row["blocker"] for row in gains if row["blocker"]})}},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent LongMem exact availability; reader and runtime unvalidated"}
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
    with tempfile.TemporaryDirectory(prefix="da033-result-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, selection_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA033AnalysisError("Result replay differs")
    return result


__all__ = ["DA033AnalysisError", "analyze", "paired", "run_analysis"]

