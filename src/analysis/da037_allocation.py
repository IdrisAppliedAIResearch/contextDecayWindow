"""Blind LongMem sentinel-capacity atomic allocation for DA-037."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da034_allocation import DA031_SHA256
from analysis.da035_allocation import BUDGET, allocate


class DA037Error(RuntimeError):
    pass


def build_rows(longmem_path: Path, population_path: Path, da031_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da031_path) != DA031_SHA256:
        raise DA037Error("DA-031 blind artifact differs")
    source = [row for row in read_gzip(da031_path) if row["corpus"] == "LONGMEM"]
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        record = records[str(row["question_id"])]
        by_id = {episode.candidate.identity: episode for episode in record.episodes}
        treatment = allocate(row, lambda identity: by_id[identity].members)
        output.append({**row, "da031_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA037Error("DA-037 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, da031_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da031_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_allocations.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da037-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da031_path))
        identical = path.read_bytes() == replay.read_bytes()
    codecs = Counter(row["treatment"]["codec"] for row in rows)
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["actions"])
    savings = [int(row["treatment"]["savings"]) for row in rows]
    immutable = all(row["treatment"]["selected_chars"] <= row["da031_control"]["final_chars"]
                    for row in rows)
    passed = (identical and immutable and codecs["SENTINEL"] > 0 and actions["MEMBER"] > 0
              and actions["SKIP_MEMBER"] > 0
              and max(row["treatment"]["final_chars"] for row in rows) <= BUDGET)
    result = {"schema": "da037-longmem-sentinel-atomic-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "codecs": dict(codecs), "actions": dict(actions), "immutable_da031": immutable,
              "median_selected_savings": float(np.median(savings)),
              "p10_selected_savings": float(np.percentile(savings, 10)),
              "p90_selected_savings": float(np.percentile(savings, 90)),
              "max_final_chars": max(row["treatment"]["final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA037Error("DA-037 blind preflight failed")
    return result


__all__ = ["DA037Error", "build_rows", "run_preflight"]
