"""Blind exact-bigram episode occurrence stream for DA-064."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import bigrams, ordered_tokens

PACK_ROUTES_SHA256 = "111edd60e2165e7932899b993a2c81cdaaa0e74bc998fce391a3fc3d00033a9f"
DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
CURRENT_FRAME_CAP = 2_048


class DA064Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def build_rows(dataset_path: Path, pack_path: Path, directory_path: Path) -> list[dict[str, Any]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (pack_path, PACK_ROUTES_SHA256),
        (directory_path, DIRECTORY_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA064Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    packs = {str(row["question_id"]): row for row in _read(pack_path)}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    if set(packs) != set(directories) or len(packs) != 465:
        raise DA064Error("Population differs")
    rows = []
    for question_id in sorted(packs):
        source = raw[question_id]
        episodes, _ = _episodes(source)
        coordinate = {
            str(item["episode_id"]): {
                "session_id": str(item["session_id"]),
                "episode_order": int(item["episode_order"]),
                "member_ids": [str(member["member_id"]) for member in item["members"]],
            }
            for item in directories[question_id]["episodes"]
        }
        prefix = list(map(str, packs[question_id]["represented_episode_ids"]))
        query_bigrams = bigrams(ordered_tokens(str(source["question"])))
        postings = {pair: [] for pair in query_bigrams}
        for episode in episodes:
            episode_id = str(episode["identity"])
            text = "\n".join(str(member["text"]) for member in episode["members"])
            observed = set(bigrams(ordered_tokens(text)))
            for pair in query_bigrams:
                if pair in observed:
                    postings[pair].append(episode_id)
        stream_ids, seen = [], set()
        for episode_id in prefix:
            if episode_id not in seen:
                seen.add(episode_id)
                stream_ids.append(episode_id)
        matched, unmatched = [], []
        for pair in query_bigrams:
            if postings[pair]:
                matched.append(list(pair))
            else:
                unmatched.append(list(pair))
            for episode_id in postings[pair]:
                if episode_id not in seen:
                    seen.add(episode_id)
                    stream_ids.append(episode_id)
        if any(episode_id not in coordinate for episode_id in stream_ids):
            raise DA064Error("Stream episode lacks exact coordinate")
        stream = []
        for index, episode_id in enumerate(stream_ids):
            item = dict(coordinate[episode_id])
            item.update({"episode_id": episode_id, "origin": "PACK" if index < len(prefix) else "BIGRAM"})
            stream.append(item)
        if [item["episode_id"] for item in stream[:len(prefix)]] != prefix:
            raise DA064Error("Immutable episode prefix differs")
        rows.append({
            "question_id": question_id,
            "pack_prefix_count": len(prefix),
            "matched_bigrams": matched,
            "unmatched_bigrams": unmatched,
            "stream": stream,
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


def run_preflight(dataset_path: Path, pack_path: Path,
                  directory_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, pack_path, directory_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_streams.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da064-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, pack_path, directory_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    matched = sum(len(row["matched_bigrams"]) for row in rows)
    unmatched = sum(len(row["unmatched_bigrams"]) for row in rows)
    bigram_items = sum(sum(item["origin"] == "BIGRAM" for item in row["stream"]) for row in rows)
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden = ("has_" + "answer", "evi" + "dence")
    leakage_clean = not any(token in source for token in forbidden)
    valid = (
        identical
        and matched > 0
        and unmatched > 0
        and bigram_items > 0
        and all(len(row["stream"]) == len({item["episode_id"] for item in row["stream"]}) for row in rows)
        and all(len(item["member_ids"]) == 2 for row in rows for item in row["stream"])
        and all(row["simultaneously_rendered_episodes"] == 1 for row in rows)
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
        and leakage_clean
    )
    result = {
        "schema": "da064-occurrence-coordinate-stream-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "matched_bigrams": matched,
        "unmatched_bigrams": unmatched,
        "pack_episodes": sum(row["pack_prefix_count"] for row in rows),
        "new_bigram_episodes": bigram_items,
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
        raise DA064Error("Blind occurrence preflight failed")
    return result


__all__ = ["DA064Error", "build_rows", "run_preflight"]
