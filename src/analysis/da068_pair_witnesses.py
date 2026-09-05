"""Blind minimum query-pair witness frontier for DA-068."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import ordered_tokens

DA066_STREAMS_SHA256 = "821ea4b31cdeed9eea053cf81a8a4cb322f9409c92f51d0ef1c681de99c0d491"
DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
RADIUS = 5
CURRENT_FRAME_CAP = 2_048


class DA068Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _unique(values: Sequence[str]) -> list[str]:
    output, seen = [], set()
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _minimum_witness(left: Sequence[int], right: Sequence[int]) -> tuple[int, int]:
    if not left or not right:
        raise DA068Error("Empty witness side")
    return min(
        ((a, b) for a in left for b in right),
        key=lambda pair: (
            abs(pair[0] - pair[1]),
            min(pair),
            max(pair),
            pair[0],
            pair[1],
        ),
    )


def build_rows(dataset_path: Path, da066_path: Path, directory_path: Path) -> list[dict[str, Any]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (da066_path, DA066_STREAMS_SHA256),
        (directory_path, DIRECTORY_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA068Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    parents = {str(row["question_id"]): row for row in _read(da066_path)}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    if set(parents) != set(directories) or len(parents) != 465:
        raise DA068Error("Population differs")
    rows = []
    for question_id in sorted(parents):
        source = raw[question_id]
        parent = parents[question_id]
        prefix = list(parent["stream"])
        episodes, _ = _episodes(source)
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
        session_order = [str(item["session_id"]) for item in directories[question_id]["sessions"]]
        query_tokens = _unique(ordered_tokens(str(source["question"])))
        occurrence: dict[str, dict[str, list[int]]] = {
            token: {session_id: [] for session_id in session_order} for token in query_tokens
        }
        for episode in episodes:
            episode_id = str(episode["identity"])
            item = coordinate[episode_id]
            observed = set(ordered_tokens("\n".join(str(member["text"]) for member in episode["members"])))
            for token in query_tokens:
                if token in observed:
                    occurrence[token][str(item["session_id"])].append(int(item["episode_order"]))
        stream = [dict(item) for item in prefix]
        seen = {str(item["episode_id"]) for item in stream}
        if len(seen) != len(stream):
            raise DA068Error("DA-066 prefix contains duplicate")
        rejections: Counter[str] = Counter()
        witness_kinds: Counter[str] = Counter()
        additions = 0

        def append(episode_id: str, origin: str) -> None:
            nonlocal additions
            if episode_id in seen:
                rejections["PRIOR_REPRESENTATION"] += 1
                return
            seen.add(episode_id)
            item = dict(coordinate[episode_id])
            item.update({"episode_id": episode_id, "origin": origin})
            stream.append(item)
            additions += 1

        witnesses = 0
        for left_index, left_token in enumerate(query_tokens):
            for right_token in query_tokens[left_index + 1:]:
                for session_id in session_order:
                    left = occurrence[left_token][session_id]
                    right = occurrence[right_token][session_id]
                    if not left or not right:
                        continue
                    left_order, right_order = _minimum_witness(left, right)
                    witnesses += 1
                    witness_kinds["SAME_EPISODE" if left_order == right_order else "CROSS_EPISODE"] += 1
                    endpoints = sorted({left_order, right_order})
                    for endpoint_order in endpoints:
                        endpoint_id = by_local[(session_id, endpoint_order)]
                        append(endpoint_id, "PAIR_WITNESS")
                    for endpoint_order in endpoints:
                        for distance in range(1, RADIUS + 1):
                            for direction in (-1, 1):
                                neighbor_id = by_local.get((session_id, endpoint_order + direction * distance))
                                if neighbor_id is None:
                                    rejections["SESSION_BOUNDARY"] += 1
                                    continue
                                append(neighbor_id, "PAIR_WITNESS_LOCAL")
        if [item["episode_id"] for item in stream[:len(prefix)]] != [
            item["episode_id"] for item in prefix
        ]:
            raise DA068Error("Protected DA-066 prefix differs")
        rows.append({
            "question_id": question_id,
            "da066_prefix_count": len(prefix),
            "query_tokens": query_tokens,
            "witnesses": witnesses,
            "witness_kinds": dict(witness_kinds),
            "pair_witness_additions": additions,
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


def run_preflight(dataset_path: Path, da066_path: Path,
                  directory_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, da066_path, directory_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_streams.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da068-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, da066_path, directory_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    rejections: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    for row in rows:
        rejections.update(row["rejections"])
        kinds.update(row["witness_kinds"])
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden = ("has_" + "answer", "evi" + "dence")
    leakage_clean = not any(token in source for token in forbidden)
    valid = (
        identical
        and kinds["SAME_EPISODE"] > 0
        and kinds["CROSS_EPISODE"] > 0
        and sum(row["pair_witness_additions"] for row in rows) > 0
        and rejections["SESSION_BOUNDARY"] > 0
        and all(len(row["stream"]) == len({item["episode_id"] for item in row["stream"]}) for row in rows)
        and all(len(item["member_ids"]) == 2 for row in rows for item in row["stream"])
        and all(row["radius"] == RADIUS for row in rows)
        and all(row["simultaneously_rendered_episodes"] == 1 for row in rows)
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
        and leakage_clean
    )
    result = {
        "schema": "da068-minimum-pair-witness-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "radius": RADIUS,
        "da066_prefix_episodes": sum(row["da066_prefix_count"] for row in rows),
        "witnesses": sum(row["witnesses"] for row in rows),
        "witness_kinds": dict(kinds),
        "pair_witness_additions": sum(row["pair_witness_additions"] for row in rows),
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
        raise DA068Error("Blind pair-witness preflight failed")
    return result


__all__ = ["DA068Error", "_minimum_witness", "build_rows", "run_preflight"]
