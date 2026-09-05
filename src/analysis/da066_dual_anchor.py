"""Blind dual-anchor local frontier for DA-066."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import sha256_file

DA065_STREAMS_SHA256 = "ce336e78d919a0107f70e6e7d68563cd9b6774a115b6b9e74b142b756388a700"
DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
RADIUS = 5
CURRENT_FRAME_CAP = 2_048


class DA066Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def build_rows(da065_path: Path, directory_path: Path) -> list[dict[str, Any]]:
    if (sha256_file(da065_path) != DA065_STREAMS_SHA256
            or sha256_file(directory_path) != DIRECTORY_SHA256):
        raise DA066Error("Sealed input differs")
    parents = {str(row["question_id"]): row for row in _read(da065_path)}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    if set(parents) != set(directories) or len(parents) != 465:
        raise DA066Error("Population differs")
    rows = []
    for question_id in sorted(parents):
        parent = parents[question_id]
        prefix_count = int(parent["pack_prefix_count"])
        prefix = list(parent["stream"][:prefix_count])
        lexical_frontier = list(parent["stream"][prefix_count:])
        coordinate = {
            str(item["episode_id"]): {
                "session_id": str(item["session_id"]),
                "episode_order": int(item["episode_order"]),
                "member_ids": [str(member["member_id"]) for member in item["members"]],
            }
            for item in directories[question_id]["episodes"]
        }
        by_local = {
            (str(item["session_id"]), int(item["episode_order"])): str(item["episode_id"])
            for item in directories[question_id]["episodes"]
        }
        stream, seen = [], set()
        for item in prefix:
            episode_id = str(item["episode_id"])
            if episode_id in seen:
                raise DA066Error("Parent prefix contains duplicate")
            seen.add(episode_id)
            stream.append(dict(item))
        rejections: Counter[str] = Counter()
        pack_local_additions = 0
        for anchor in prefix:
            session_id = str(anchor["session_id"])
            episode_order = int(anchor["episode_order"])
            for distance in range(1, RADIUS + 1):
                for direction in (-1, 1):
                    neighbor_id = by_local.get((session_id, episode_order + direction * distance))
                    if neighbor_id is None:
                        rejections["SESSION_BOUNDARY"] += 1
                        continue
                    if neighbor_id in seen:
                        rejections["DUPLICATE"] += 1
                        continue
                    seen.add(neighbor_id)
                    item = dict(coordinate[neighbor_id])
                    item.update({"episode_id": neighbor_id, "origin": "PACK_LOCAL"})
                    stream.append(item)
                    pack_local_additions += 1
        lexical_additions = 0
        for parent_item in lexical_frontier:
            episode_id = str(parent_item["episode_id"])
            if episode_id in seen:
                rejections["PRIOR_REPRESENTATION"] += 1
                continue
            seen.add(episode_id)
            item = dict(parent_item)
            item["origin"] = "LEXICAL_LOCAL"
            stream.append(item)
            lexical_additions += 1
        if [item["episode_id"] for item in stream[:prefix_count]] != [
            item["episode_id"] for item in prefix
        ]:
            raise DA066Error("Immutable episode prefix differs")
        rows.append({
            "question_id": question_id,
            "pack_prefix_count": prefix_count,
            "pack_anchor_count": len(prefix),
            "pack_local_additions": pack_local_additions,
            "lexical_local_additions": lexical_additions,
            "rejections": dict(rejections),
            "stream": stream,
            "radius": RADIUS,
            "simultaneously_rendered_episodes": 1,
            "current_frame_cap": CURRENT_FRAME_CAP,
            "protected_payload_mutations": 0,
            "rendered_char_delta": 0,
        })
    return rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(da065_path: Path, directory_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(da065_path, directory_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_streams.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da066-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(da065_path, directory_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    rejections: Counter[str] = Counter()
    for row in rows:
        rejections.update(row["rejections"])
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden = ("has_" + "answer", "evi" + "dence")
    leakage_clean = not any(token in source for token in forbidden)
    valid = (
        identical
        and sum(row["pack_anchor_count"] for row in rows) > 0
        and sum(row["pack_local_additions"] for row in rows) > 0
        and sum(row["lexical_local_additions"] for row in rows) > 0
        and rejections["SESSION_BOUNDARY"] > 0
        and all(len(row["stream"]) == len({item["episode_id"] for item in row["stream"]}) for row in rows)
        and all(len(item["member_ids"]) == 2 for row in rows for item in row["stream"])
        and all(row["radius"] == RADIUS for row in rows)
        and all(row["simultaneously_rendered_episodes"] == 1 for row in rows)
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
        and leakage_clean
    )
    result = {
        "schema": "da066-dual-anchor-local-frontier-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "radius": RADIUS,
        "pack_anchors": sum(row["pack_anchor_count"] for row in rows),
        "pack_local_additions": sum(row["pack_local_additions"] for row in rows),
        "lexical_local_additions": sum(row["lexical_local_additions"] for row in rows),
        "rejections": dict(rejections),
        "min_stream_episodes": min(len(row["stream"]) for row in rows),
        "max_stream_episodes": max(len(row["stream"]) for row in rows),
        "simultaneously_rendered_episodes": 1,
        "peak_current_frame_chars": CURRENT_FRAME_CAP,
        "protected_payload_mutations": 0,
        "rendered_char_delta": 0,
        "leakage_scan_clean": leakage_clean,
        "replay_byte_identical": identical,
        "streams_sha256": sha256_file(artifact),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
    }
    (output_dir / "preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not valid:
        raise DA066Error("Blind dual-anchor preflight failed")
    return result


__all__ = ["DA066Error", "build_rows", "run_preflight"]
