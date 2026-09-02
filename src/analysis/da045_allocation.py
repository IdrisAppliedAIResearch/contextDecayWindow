"""Blind replaceable single-node stream over the DA-042 frontier."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da044_allocation import DA042_SHA256, parse_block, render_block

FRAME_CAP = 2_048
STREAM_DEPTH = 32


class DA045Error(RuntimeError):
    pass


def allocate(row: Mapping[str, Any], pair_for: Any) -> dict[str, Any]:
    sentinel = str(row["da038_control"]["sentinel"])
    actions = []
    for ordinal, (neighbor, member_index) in enumerate(row["treatment"]["targets"][:STREAM_DEPTH], 1):
        neighbor, member_index = str(neighbor), int(member_index)
        member = pair_for(neighbor)[member_index]
        block = render_block(sentinel, ordinal, member)
        if parse_block(block, sentinel) != (ordinal, str(member["speaker"]), str(member["text"])):
            raise DA045Error("Stream frame decode differs")
        fits = len(block) <= FRAME_CAP
        actions.append({"ordinal": ordinal, "neighbor_id": neighbor, "member": member_index,
                        "kind": "FRAME" if fits else "OVERFLOW", "cost": len(block) if fits else 0,
                        "attempt_cost": len(block), "block": block if fits else None,
                        "block_sha256": hashlib.sha256(block.encode()).hexdigest()})
    frame_costs = [action["cost"] for action in actions if action["kind"] == "FRAME"]
    return {"codec": "REPLACEABLE_NODE_STREAM", "stream_depth": STREAM_DEPTH,
            "frame_cap": FRAME_CAP, "actions": actions,
            "peak_frame_chars": max(frame_costs, default=0),
            "cumulative_exposed_chars": sum(frame_costs),
            "frontier_targets": len(row["treatment"]["targets"]),
            "depth_truncated": len(row["treatment"]["targets"]) > STREAM_DEPTH,
            "immutable_prompt_chars": int(row["da038_control"]["final_chars"]),
            "prompt_char_delta": 0,
            "immutable_order_sha256": str(row["treatment"]["immutable_order_sha256"])}


def build_rows(longmem_path: Path, population_path: Path, da042_path: Path) -> list[dict[str, Any]]:
    if sha256_file(da042_path) != DA042_SHA256:
        raise DA045Error("DA-042 blind artifact differs")
    source = list(read_gzip(da042_path))
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    output = []
    for row in source:
        by_id = {episode.candidate.identity: episode for episode in records[str(row["question_id"])].episodes}
        treatment = allocate(row, lambda identity: by_id[identity].members)
        output.append({**row, "da042_control": row["treatment"], "treatment": treatment})
    if len(output) != 465:
        raise DA045Error("DA-045 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(longmem_path: Path, population_path: Path, da042_path: Path,
                  output_dir: Path) -> dict[str, Any]:
    rows = build_rows(longmem_path, population_path, da042_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_streams.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da045-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(longmem_path, population_path, da042_path))
        identical = path.read_bytes() == replay.read_bytes()
    actions = Counter(action["kind"] for row in rows for action in row["treatment"]["actions"])
    immutable = all(row["treatment"]["immutable_prompt_chars"] == row["da038_control"]["final_chars"]
                    and row["treatment"]["prompt_char_delta"] == 0 for row in rows)
    prefix = all([action["ordinal"] for action in row["treatment"]["actions"]]
                 == list(range(1, len(row["treatment"]["actions"]) + 1)) for row in rows)
    peaks = [row["treatment"]["peak_frame_chars"] for row in rows]
    cumulative = [row["treatment"]["cumulative_exposed_chars"] for row in rows]
    frames = [sum(action["kind"] == "FRAME" for action in row["treatment"]["actions"]) for row in rows]
    passed = (identical and immutable and prefix and actions["FRAME"] > 0 and actions["OVERFLOW"] > 0
              and max(peaks) <= FRAME_CAP and all(len(row["treatment"]["actions"]) <= STREAM_DEPTH for row in rows))
    result = {"schema": "da045-replaceable-node-stream-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "actions": dict(actions), "immutable_da038": immutable, "prefix_only": prefix,
              "peak_frame_chars": {"p10": float(np.percentile(peaks, 10)),
                                   "p50": float(np.percentile(peaks, 50)),
                                   "p90": float(np.percentile(peaks, 90)), "max": max(peaks)},
              "cumulative_exposed_chars": {"p10": float(np.percentile(cumulative, 10)),
                                           "p50": float(np.percentile(cumulative, 50)),
                                           "p90": float(np.percentile(cumulative, 90))},
              "frames": {"p10": float(np.percentile(frames, 10)),
                         "p50": float(np.percentile(frames, 50)),
                         "p90": float(np.percentile(frames, 90))},
              "replay_byte_identical": identical, "allocation_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA045Error("DA-045 blind preflight failed")
    return result


__all__ = ["DA045Error", "allocate", "run_preflight"]
