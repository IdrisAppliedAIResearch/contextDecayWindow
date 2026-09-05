"""Evidence-aware protected retained-set oracle for DA-052."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _delivered, _paired, _quantile, _records
from analysis.da048_continuation import sha256_file
from analysis.da052_contract import RetainedSetMachine

ENVELOPE_SHA256 = "e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc"
DA045_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"
DA048_SHA256 = "8ea82cc737b65bf457e05bf921043907d70f0f82f0e878b340ab6c7f04c41bd3"
DA050_SHA256 = "40c8b768e80c8b0c80e1b310f7abe3e2f3cc6066362f6b59a8aa436bfcfae490"
DA050_OUTCOMES_SHA256 = "32d93e6c3653ace8c3933eeb421b907937fcef2f168e584b5dc61e15dac14f6a"
CONTRACT_SHA256 = "c72d9468b4789945f549f7ef3cd40efbfc344db3fc5428069fefc2b20fcfd666"


class DA052AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(dataset_path: Path, envelope_path: Path, da045_path: Path, da048_path: Path,
            da050_path: Path, da050_outcomes_path: Path,
            contract_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((envelope_path, ENVELOPE_SHA256), (da045_path, DA045_SHA256),
             (da048_path, DA048_SHA256), (da050_path, DA050_SHA256),
             (da050_outcomes_path, DA050_OUTCOMES_SHA256), (contract_path, CONTRACT_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA052AnalysisError("Sealed input differs")
    records = _records(dataset_path)
    envelopes = {str(row["question_id"]): row for row in _read(envelope_path)}
    one_hop = {str(row["question_id"]): row["treatment"]["actions"] for row in _read(da045_path)}
    distance_2 = {str(row["question_id"]): row["actions"] for row in _read(da048_path)}
    distance_3_5 = {str(row["question_id"]): row["actions"] for row in _read(da050_path)}
    prior = {str(row["question_id"]): row for row in _read(da050_outcomes_path)}
    rows = []
    for question_id in sorted(envelopes):
        envelope, record = envelopes[question_id], records[question_id]
        episodes, gold = record["episodes"], record["gold"]
        direct = set().union(*(episodes[value] for value in envelope["direct_ids"]))
        base = (direct | _delivered(envelope["baseline_actions"], episodes)
                | _delivered(envelope["da023"]["additions"], episodes)
                | _delivered(envelope["control"]["actions"], episodes)
                | _delivered(envelope["da031_control"]["actions"], episodes)
                | _delivered(envelope["da033_control"]["actions"], episodes)
                | _delivered(envelope["da038_control"]["actions"], episodes))
        control = bool(prior[question_id]["TREATMENT"])
        missing = gold - base
        machine = RetainedSetMachine()
        retained_ids: set[str] = set()
        cumulative = 0
        source_counts: Counter[str] = Counter()
        actions_visited = 0
        if not control:
            stop = False
            for source, actions in (("ONE_HOP", one_hop[question_id]),
                                    ("DISTANCE_2", distance_2[question_id]),
                                    ("DISTANCE_3_5", distance_3_5[question_id])):
                for action in actions:
                    machine.next(action)
                    actions_visited += 1
                    cumulative += int(action["cost"])
                    if action["kind"] == "FRAME":
                        member_id = episodes[str(action["neighbor_id"])][int(action["member"])]
                        if member_id in missing and member_id not in retained_ids:
                            if not machine.keep():
                                raise DA052AnalysisError("Oracle required frame was rejected")
                            retained_ids.add(member_id)
                            source_counts[source] += 1
                    if missing <= retained_ids:
                        stop = True
                        break
                if stop:
                    break
        treatment = control or missing <= retained_ids
        rows.append({"question_id": question_id, "question_type": record["question_type"],
                     "CONTROL": control, "TREATMENT": treatment,
                     "missing_members": len(missing), "retained_members": len(retained_ids),
                     "retained_chars": sum(map(len, machine.retained)),
                     "peak_auxiliary_chars": machine.peak_chars,
                     "actions_visited": actions_visited, "cumulative_chars": cumulative,
                     "source_counts": dict(source_counts)})
    if len(rows) != 465 or sum(row["CONTROL"] for row in rows) != 332:
        raise DA052AnalysisError("DA-050 anchor differs")
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    contrast = _paired(rows)
    groups = {}
    for group in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == group]
        groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell)
                                                       for arm in complete},
                         "contrast": _paired(cell)}
    nonnegative = all(cell["contrast"]["losses"] == 0 for cell in groups.values())
    status = ("RETAINED_SET_CAPACITY_SIGNAL" if contrast["gains"] >= 10
              and contrast["losses"] == 0 and nonnegative else "NO_RETAINED_SET_CAPACITY_SIGNAL")
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    def dist(field: str) -> dict[str, float | None]:
        values = [int(row[field]) for row in gains]
        return {"p10": _quantile(values, .1), "p50": _quantile(values, .5),
                "p90": _quantile(values, .9), "max": max(values, default=None)}
    result = {"schema": "da052-protected-retained-set-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "by_question_type": groups,
              "oracle_gains": {"n": len(gains),
                               "retained_members": dict(sorted(Counter(
                                   int(row["retained_members"]) for row in gains).items())),
                               "retained_chars": dist("retained_chars"),
                               "peak_auxiliary_chars": dist("peak_auxiliary_chars"),
                               "actions_visited": dist("actions_visited"),
                               "cumulative_chars": dist("cumulative_chars"),
                               "source_frames": dict(sum((Counter(row["source_counts"])
                                                          for row in gains), Counter()))},
              "protected_payload_mutations": 0,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "evidence-aware minimum retained-frame-set oracle only"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, envelope_path: Path, da045_path: Path, da048_path: Path,
                 da050_path: Path, da050_outcomes_path: Path, contract_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    args = (dataset_path, envelope_path, da045_path, da048_path, da050_path,
            da050_outcomes_path, contract_path)
    result, rows = analyze(*args)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "outcomes.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da052-result-") as directory:
        replay_result, replay_rows = analyze(*args)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(artifact)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    if not identical:
        raise DA052AnalysisError("Analysis replay differs")
    return result


__all__ = ["DA052AnalysisError", "analyze", "run_analysis"]
