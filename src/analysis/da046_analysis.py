"""Oracle single-register mechanical sufficiency analysis for DA-046."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.da032_audit import distribution
from analysis.da033_analysis import _delivered, paired
from analysis.da046_contract import RegisterMachine, _action_digest
from analysis.nf005_measurement import adapt_population

STREAM_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"
CONTRACT_SHA256 = "83290a8bbeacdbc8b6a436dcadb314976c1daee09aa56c570b95096b87879089"
AUDIT_SHA256 = "b12532da99fe17d713a1918dc64fc553ab0872cf980425bd1763bf3893cd4727"


class DA046AnalysisError(RuntimeError):
    pass


def _ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA046AnalysisError("Population differs")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in data["rows"])


def analyze(longmem_path: Path, population_path: Path, stream_path: Path,
            contract_path: Path, audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((stream_path, STREAM_SHA256), (contract_path, CONTRACT_SHA256),
             (audit_path, AUDIT_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA046AnalysisError("Sealed input differs")
    streams = {str(row["question_id"]): row for row in read_gzip(stream_path)}
    contracts = {str(row["question_id"]): row for row in read_gzip(contract_path)}
    residuals = {str(row["key"]): row for row in read_gzip(audit_path)}
    records = {record.question_id: record for record in adapt_population(longmem_path, _ids(population_path))}
    rows = []
    for question_id in sorted(records):
        stream, contract, record = streams[question_id], contracts[question_id], records[question_id]
        actions = stream["treatment"]["actions"]
        if contract["stream_actions_sha256"] != _action_digest(actions):
            raise DA046AnalysisError("Contract stream hash differs")
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        gold = {turn.candidate.identity for turn in record.turns if turn.is_target}
        direct = set().union(*(identities[value] for value in stream["direct_ids"]))
        control_set = (direct | _delivered(stream["baseline_actions"], identities)
                       | _delivered(stream["da023"]["additions"], identities)
                       | _delivered(stream["control"]["actions"], identities)
                       | _delivered(stream["da031_control"]["actions"], identities)
                       | _delivered(stream["da033_control"]["actions"], identities)
                       | _delivered(stream["da038_control"]["actions"], identities))
        retained_ids: set[str] = set()
        path = None
        blocker = None
        if question_id in residuals:
            residual = residuals[question_id]
            blocker = str(residual["blocker"])
            required = set(map(str, residual["remaining_missing"]))
            matching = [action for action in actions
                        if identities[str(action["neighbor_id"])][int(action["member"])] in required]
            if len(matching) != 1 or matching[0]["kind"] != "FRAME":
                raise DA046AnalysisError("Oracle requirement is not one retainable frame")
            target = matching[0]
            machine = RegisterMachine()
            cumulative = 0
            visited = 0
            for action in actions:
                machine.next(action)
                visited += 1
                cumulative += int(action["cost"])
                if action is target:
                    machine.keep()
                    break
            retained = machine.answer()
            if retained is None or hashlib.sha256(retained.encode()).hexdigest() != target["block_sha256"]:
                raise DA046AnalysisError("Oracle retained frame differs")
            retained_ids.add(identities[str(target["neighbor_id"])][int(target["member"])])
            if not required <= retained_ids:
                raise DA046AnalysisError("Oracle retained frame lacks required identity")
            path = {"target_ordinal": int(target["ordinal"]), "actions_visited": visited,
                    "cumulative_chars": cumulative, "retained_chars": len(retained),
                    "peak_auxiliary_chars": machine.peak_chars}
        treatment_set = control_set | retained_ids
        control, treatment = gold <= control_set, gold <= treatment_set
        if control and not treatment:
            raise DA046AnalysisError("Protected DA-038 loss")
        rows.append({"question_id": question_id, "question_type": record.question_type,
                     "CONTROL": control, "TREATMENT": treatment, "blocker": blocker,
                     "oracle_path": path})
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    contrast = paired(rows)
    oracle_rows = [row for row in rows if row["oracle_path"] is not None]
    if len(rows) != 465 or len(oracle_rows) != 18 or complete["CONTROL"] != 232:
        raise DA046AnalysisError("Population or control anchor differs")
    paths = [row["oracle_path"] for row in oracle_rows]
    sufficient = (complete["TREATMENT"] == 250 and contrast["gains"] == 18
                  and contrast["losses"] == 0
                  and max(path["peak_auxiliary_chars"] for path in paths) <= 2_048)
    status = "ORACLE_SINGLE_REGISTER_SUFFICIENT" if sufficient else "ORACLE_SINGLE_REGISTER_INSUFFICIENT"
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell),
                         "complete": {arm: sum(row[arm] for row in cell) for arm in complete},
                         "contrast": paired(cell)}
    result = {"schema": "da046-oracle-single-register-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "one_hop_ceiling": 250, "by_question_type": groups,
              "oracle_paths": {"n": len(paths),
                               "target_ordinal": distribution([path["target_ordinal"] for path in paths]),
                               "actions_visited": distribution([path["actions_visited"] for path in paths]),
                               "cumulative_chars": distribution([path["cumulative_chars"] for path in paths]),
                               "retained_chars": distribution([path["retained_chars"] for path in paths]),
                               "peak_auxiliary_chars": distribution([path["peak_auxiliary_chars"] for path in paths]),
                               "max_peak_auxiliary_chars": max(path["peak_auxiliary_chars"] for path in paths)},
              "protected_da038_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware oracle retention sufficiency only; recognition/stopping untested"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(longmem_path: Path, population_path: Path, stream_path: Path,
                 contract_path: Path, audit_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, stream_path, contract_path, audit_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "oracle_paths.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da046-result-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, stream_path,
                                             contract_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "oracle_paths_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA046AnalysisError("Result replay differs")
    return result


__all__ = ["DA046AnalysisError", "analyze", "run_analysis"]
