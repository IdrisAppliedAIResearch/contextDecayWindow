"""Exact NF evidence analysis for DA-034 sentinel pointers."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split

SELECTION_SHA256 = "3454fd7a148100b805a860b3a17d947eefb7c349fef721bf06e0b103b4f5d42f"
AUDIT_SHA256 = "cf7764fa9e96f5621330510704d1deb976f9a623f45047010430b69b0f250cfe"


class DA034AnalysisError(RuntimeError):
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


def _delivered(actions: Sequence[Mapping[str, Any]], identities: Mapping[str, Sequence[str]]) -> set[str]:
    output = set()
    for action in actions:
        if action["kind"] == "PAIR":
            output.update(identities[str(action["neighbor_id"])])
        elif action["kind"] == "TURN":
            output.add(identities[str(action["neighbor_id"])][int(action["member"])] )
    return output


def analyze(locomo_path: Path, selection_path: Path,
            audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA034AnalysisError("Sealed input differs")
    selections = {(str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
                  for row in read_gzip(selection_path)}
    blockers = {str(row["key"]): row["blocker"] for row in read_gzip(audit_path)
                if row["corpus"] == "NF004"}
    evidence, identities, groups = {}, {}, {}
    for record in adapt_split(locomo_path, HOLDOUT_IDS):
        for source in record.candidates:
            identities[source.candidate.identity] = tuple(source.dialogue_ids)
        for question in record.questions:
            key = (question.comparison_key, question.duplicate_ordinal)
            evidence[key] = set(question.resolved_dialogue_ids)
            groups[key] = question.sample_id
    rows = []
    for key in sorted(selections):
        selection, gold = selections[key], evidence[key]
        direct = set().union(*(identities[value] for value in selection["direct_ids"]))
        control_set = (direct | _delivered(selection["baseline_actions"], identities)
                       | _delivered(selection["da023"]["additions"], identities)
                       | _delivered(selection["control"]["actions"], identities)
                       | _delivered(selection["da031_control"]["actions"], identities))
        treatment_set = control_set | _delivered(selection["treatment"]["actions"], identities)
        control, treatment = gold <= control_set, gold <= treatment_set
        if control and not treatment:
            raise DA034AnalysisError("Protected control loss")
        item_key = f"{key[0]}:{key[1]}"
        rows.append({"key": item_key, "group": groups[key], "CONTROL": control,
                     "TREATMENT": treatment, "blocker": blockers.get(item_key),
                     "savings": selection["treatment"]["savings"],
                     "actions": selection["treatment"]["actions"]})
    complete = {arm: sum(row[arm] for row in rows) for arm in ("CONTROL", "TREATMENT")}
    if len(rows) != 1098 or complete["CONTROL"] != 983:
        raise DA034AnalysisError("Control anchor differs")
    by_group = {}
    for group in sorted({row["group"] for row in rows}):
        cell = [row for row in rows if row["group"] == group]
        by_group[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell) for arm in complete},
                           "contrast": paired(cell)}
    contrast = paired(rows)
    gains = [row for row in rows if not row["CONTROL"] and row["TREATMENT"]]
    admitted = [action for row in rows for action in row["actions"] if action["kind"] in {"PAIR", "TURN"}]
    nonnegative = all(cell["contrast"]["net"] >= 0 for cell in by_group.values())
    if contrast["gains"] >= 2 and contrast["losses"] == 0 and nonnegative:
        status = "NF_SENTINEL_VARINT_SIGNAL"
    elif contrast["gains"] == 1 and contrast["losses"] == 0 and nonnegative:
        status = "WEAK_NF_SENTINEL_VARINT_SIGNAL"
    else:
        status = "NO_NF_SENTINEL_VARINT_SIGNAL"
    result = {"schema": "da034-nf-sentinel-result-v1", "status": status,
              "population": len(rows), "complete": complete, "contrast": contrast,
              "by_conversation": by_group, "one_hop_ceiling": 986,
              "mechanism": {"savings": distribution([row["savings"] for row in rows]),
                            "admitted_actions": len(admitted),
                            "admitted_cost": distribution([action["cost"] for action in admitted]),
                            "admitted_position": distribution([action["position"] for action in admitted]),
                            "gain_blockers": {name: sum(row["blocker"] == name for row in gains)
                                              for name in sorted({row["blocker"] for row in gains if row["blocker"]})}},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent NF exact availability; reader and runtime unvalidated"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(locomo_path: Path, selection_path: Path,
                 audit_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(locomo_path, selection_path, audit_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da034-result-") as directory:
        replay_result, replay_rows = analyze(locomo_path, selection_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA034AnalysisError("Result replay differs")
    return result


__all__ = ["DA034AnalysisError", "analyze", "paired", "run_analysis"]

