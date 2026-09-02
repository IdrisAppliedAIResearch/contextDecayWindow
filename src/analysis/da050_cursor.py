"""Blind distance-three-through-five directional cursor for DA-050."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import (
    DATASET_SHA256,
    DA042_SHA256,
    FRAME_CAP,
    _episodes,
    _read_gzip,
    render_block,
    sha256_file,
)

DISTANCES = (3, 4, 5)


class DA050Error(RuntimeError):
    pass


def build_rows(dataset_path: Path, envelope_path: Path) -> list[dict[str, Any]]:
    if sha256_file(dataset_path) != DATASET_SHA256 or sha256_file(envelope_path) != DA042_SHA256:
        raise DA050Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    output = []
    for envelope in _read_gzip(envelope_path):
        question_id = str(envelope["question_id"])
        episodes, by_id = _episodes(raw[question_id])
        direct = set(map(str, envelope["direct_ids"]))
        one_hop = {str(target[0]) for target in envelope["treatment"]["targets"]}
        seen: set[str] = set()
        candidates = []
        rejections: Counter[str] = Counter()
        for edge_position, edge in enumerate(envelope["baseline_actions"]):
            direction = int(edge["direction"])
            if direction not in {-1, 1}:
                raise DA050Error("Unexpected direction")
            seed_id = str(edge["seed_id"])
            seed_index = by_id[seed_id]
            seed = episodes[seed_index]
            for distance in DISTANCES:
                target_index = seed_index + direction * distance
                if not 0 <= target_index < len(episodes):
                    rejections["CORPUS_BOUNDARY"] += 1
                    continue
                target = episodes[target_index]
                if target["session"] != seed["session"]:
                    rejections["SESSION_BOUNDARY"] += 1
                    continue
                target_id = str(target["identity"])
                if target_id in direct or target_id in one_hop:
                    rejections["PRIOR_REPRESENTATION"] += 1
                    continue
                if target_id in seen:
                    rejections["DUPLICATE"] += 1
                    continue
                seen.add(target_id)
                candidates.append({"edge_position": edge_position, "seed_id": seed_id,
                                   "direction": direction, "distance": distance,
                                   "neighbor_id": target_id, "members": target["members"]})
        sentinel = str(envelope["da038_control"]["sentinel"])
        actions = []
        for ordinal, (candidate, member_index, member) in enumerate(
            ((candidate, member_index, member) for candidate in candidates
             for member_index, member in enumerate(candidate["members"])), 1
        ):
            block = render_block(sentinel, ordinal, member)
            fits = len(block) <= FRAME_CAP
            actions.append({"ordinal": ordinal, "edge_position": candidate["edge_position"],
                            "seed_id": candidate["seed_id"], "direction": candidate["direction"],
                            "distance": candidate["distance"], "neighbor_id": candidate["neighbor_id"],
                            "member": member_index, "kind": "FRAME" if fits else "OVERFLOW",
                            "cost": len(block) if fits else 0, "attempt_cost": len(block),
                            "block": block if fits else None,
                            "block_sha256": hashlib.sha256(block.encode()).hexdigest()})
        output.append({"question_id": question_id,
                       "immutable_prompt_chars": int(envelope["da038_control"]["final_chars"]),
                       "immutable_order_sha256": str(envelope["treatment"]["immutable_order_sha256"]),
                       "continuation_episodes": len(candidates), "actions": actions,
                       "rejections": dict(rejections)})
    if len(output) != 465:
        raise DA050Error("Population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, envelope_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, envelope_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_cursor.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da050-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, envelope_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    actions = [action for row in rows for action in row["actions"]]
    kinds = Counter(action["kind"] for action in actions)
    distances = Counter(int(action["distance"]) for action in actions)
    rejections = Counter()
    for row in rows:
        rejections.update(row["rejections"])
    passed = (identical and kinds["FRAME"] > 0 and sum(rejections.values()) > 0
              and set(distances) == set(DISTANCES)
              and max((int(action["cost"]) for action in actions), default=0) <= FRAME_CAP)
    result = {"schema": "da050-directional-cursor-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "continuation_episodes": sum(row["continuation_episodes"] for row in rows),
              "actions": dict(kinds), "actions_by_distance": dict(distances),
              "rejections": dict(rejections),
              "peak_frame_chars": max((int(action["cost"]) for action in actions), default=0),
              "cumulative_frame_chars": sum(int(action["cost"]) for action in actions),
              "immutable_prompt_mutations": 0, "replay_byte_identical": identical,
              "artifact_sha256": sha256_file(artifact),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    if not passed:
        raise DA050Error("Blind preflight failed")
    return result


__all__ = ["DA050Error", "build_rows", "run_preflight"]
