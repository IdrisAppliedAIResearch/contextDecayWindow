"""Blind out-of-band dependency head over immutable DA-038."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da040_allocation import BUDGET, DA038_SHA256, _protected_descriptors
from analysis.da041_allocation import _targets


class DA042Error(RuntimeError):
    pass


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    descriptors = _protected_descriptors(row, pair_for)
    order = "\0".join(f"{identity}:{','.join(map(str, members))}" for identity, members in descriptors)
    digest = hashlib.sha256(order.encode()).hexdigest()
    present = {(identity, member) for identity, members in descriptors for member in members}
    targets = _targets(row, present, pair_for)
    rendered_chars = int(row["treatment"]["final_chars"])
    return {"codec": "CONTROL_PLANE_HEAD", "rendered_final_chars": rendered_chars,
            "immutable_final_chars": rendered_chars, "immutable_order_sha256": digest,
            "rendered_char_delta": 0,
            "dependency_head": ({"type": "dependency_head",
                                  "resolver": "baseline_absent_members_v1"}
                                 if targets else None),
            "targets": [[identity, member] for identity, member in targets]}


def build_rows(longmem_path: Path, population_path: Path, da038_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da038_path) != DA038_SHA256:
        raise DA042Error("DA-038 blind artifact differs")
    source = list(read_gzip(da038_path))
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        by_id = {episode.candidate.identity: episode for episode in records[str(row["question_id"])].episodes}
        treatment = allocate(row, lambda identity: by_id[identity].members)
        output.append({**row, "da038_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA042Error("DA-042 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, da038_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da038_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_envelopes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da042-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da038_path))
        identical = path.read_bytes() == replay.read_bytes()
    immutable = all(row["treatment"]["immutable_final_chars"] == row["da038_control"]["final_chars"]
                    and row["treatment"]["rendered_char_delta"] == 0 for row in rows)
    nonempty = [row for row in rows if row["treatment"]["targets"]]
    heads_complete = all(row["treatment"]["dependency_head"] == {
        "type": "dependency_head", "resolver": "baseline_absent_members_v1"} for row in nonempty)
    passed = (identical and immutable and heads_complete and nonempty
              and max(row["treatment"]["rendered_final_chars"] for row in rows) <= BUDGET)
    result = {"schema": "da042-control-plane-head-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "heads": len(nonempty), "resolved_targets": sum(len(row["treatment"]["targets"]) for row in rows),
              "immutable_da038": immutable, "rendered_char_delta": 0,
              "max_rendered_chars": max(row["treatment"]["rendered_final_chars"] for row in rows),
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA042Error("DA-042 blind preflight failed")
    return result


__all__ = ["DA042Error", "allocate", "run_preflight"]
