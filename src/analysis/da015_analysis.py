"""DA-014 oracle capacity accounting for the sealed DA-015 codec."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.nf005_measurement import adapt_population

PHRASE_SHA256 = "7ccc9908c04acc951d90cdb118bb0ca1d974f141e1f623b9670167e774231fe4"
TRACE_SHA256 = "8c9ea6565d127ef3d1d6cef8ad969fce689236d40acaaee9e333eb52e074856a"


class DA015AnalysisError(RuntimeError):
    pass


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA015AnalysisError("NF-003 population differs")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(row["question_id"]) for row in payload["rows"])


def run_analysis(dataset_path: Path, population_path: Path, phrase_path: Path,
                 trace_path: Path, output_dir: Path) -> dict[str, Any]:
    if sha256_file(phrase_path) != PHRASE_SHA256 or sha256_file(trace_path) != TRACE_SHA256:
        raise DA015AnalysisError("DA-015 sealed input differs")
    savings = {row["key"]: int(row["incremental_savings"]) for row in read_gzip(phrase_path) if row["corpus"] == "DA013"}
    records = {record.question_id: record for record in adapt_population(dataset_path, _population_ids(population_path))}
    traces = [row for row in read_gzip(trace_path) if row["class"] == "INITIAL_PAYLOAD_TOO_LARGE"]
    rows = []
    for trace in traces:
        record = records[trace["question_id"]]
        episode_turns = {episode.candidate.identity: episode.turn_identities for episode in record.episodes}
        missing = set(trace["missing_targets"])
        options = []
        for carrier in trace["carriers"]:
            identity = carrier["neighbor_id"]
            carried = set(carrier["carried"])
            if not missing <= carried:
                continue
            members = episode_turns[identity]
            required = [index for index, turn_id in enumerate(members) if turn_id in missing]
            cost = int(carrier["initial"]["full_cost"] if len(required) > 1 else carrier["initial"]["turn_costs"][required[0]])
            options.append((cost, identity))
        if not options:
            raise DA015AnalysisError("Initial-size item lacks a sufficient carrier")
        required_cost, carrier_id = min(options)
        initial_slack = int(trace["carriers"][0]["initial"]["initial_slack"])
        added = savings[trace["question_id"]]
        rows.append({"question_id": trace["question_id"], "question_type": trace["question_type"],
                     "initial_slack": initial_slack, "phrase_savings": added,
                     "new_slack": initial_slack + added, "required_cost": required_cost,
                     "carrier_id": carrier_id, "capacity_cleared": required_cost <= initial_slack + added})
    if len(rows) != 49:
        raise DA015AnalysisError("DA-015 capacity population differs")
    cleared = sum(row["capacity_cleared"] for row in rows)
    result = {"schema": "da015-capacity-oracle-v1", "population": 49, "capacity_cleared": cleared,
              "still_too_large": 49 - cleared,
              "by_question_type": {kind: {"n": len(cell := [row for row in rows if row["question_type"] == kind]),
                                           "cleared": sum(row["capacity_cleared"] for row in cell)}
                                   for kind in sorted({row["question_type"] for row in rows})},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "opened-label oracle capacity only; no allocation or reader claim"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rows.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["DA015AnalysisError", "run_analysis"]
