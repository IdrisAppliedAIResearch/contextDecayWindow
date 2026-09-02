"""Exact episode-sequence separability for DA-075 residual collisions."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import bigrams, ordered_tokens
from analysis.da073_ordered_lattice import _features, _typed_features, _unique

DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
DA075_TARGETS_SHA256 = "1673943685b8d75f1815b314eac68cd4f0edfa50095cf51290cb246c0c540b54"


class DA076Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                handle.write(payload.encode())


def analyze(dataset_path: Path, directory_path: Path,
            da075_targets_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (directory_path, DIRECTORY_SHA256),
        (da075_targets_path, DA075_TARGETS_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA076Error("Sealed input differs")

    raw = {
        str(row["question_id"]): row
        for row in json.loads(dataset_path.read_text(encoding="utf-8"))
    }
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    collision_rows = [
        row for row in _read(da075_targets_path)
        if row["role_state"] == "ROLE_SIGNATURE_COLLISION"
    ]
    if len(collision_rows) != 5:
        raise DA076Error("Residual-collision population differs")

    targets: dict[str, list[dict[str, Any]]] = {}
    for row in collision_rows:
        targets.setdefault(str(row["question_id"]), []).append(row)

    rows = []
    for question_id in sorted(targets):
        question = raw[question_id]
        directory = directories[question_id]
        episodes, _ = _episodes(question)
        coordinate = {
            str(item["episode_id"]): str(item["session_id"])
            for item in directory["episodes"]
        }
        session_order = [str(item["session_id"]) for item in directory["sessions"]]
        query_sequence = ordered_tokens(str(question["question"]))
        query_unigrams = _unique(query_sequence)
        query_bigrams = _unique(bigrams(query_sequence))
        episode_features: dict[str, list[frozenset[str]]] = {
            session_id: [] for session_id in session_order
        }
        for episode in episodes:
            features = set(_features(
                "\n".join(str(member["text"]) for member in episode["members"]),
                query_unigrams,
                query_bigrams,
            ))
            for member in episode["members"]:
                features.update(_typed_features(
                    str(member["text"]),
                    str(member["speaker"]).upper(),
                    query_unigrams,
                    query_bigrams,
                ))
            episode_features[coordinate[str(episode["identity"])]].append(frozenset(features))

        unions = {
            session_id: frozenset().union(*sequence)
            for session_id, sequence in episode_features.items()
        }
        sequences = {
            session_id: tuple(tuple(sorted(features)) for features in sequence)
            for session_id, sequence in episode_features.items()
        }
        union_groups: dict[frozenset[str], list[str]] = {}
        for session_id in session_order:
            if unions[session_id]:
                union_groups.setdefault(unions[session_id], []).append(session_id)

        for target in targets[question_id]:
            session_id = str(target["session_id"])
            union_group = union_groups[unions[session_id]]
            sequence_group = [
                peer for peer in union_group
                if sequences[peer] == sequences[session_id]
            ]
            same_length = [
                peer for peer in union_group
                if len(sequences[peer]) == len(sequences[session_id])
            ]
            rows.append({
                "question_id": question_id,
                "question_type": str(target["question_type"]),
                "session_id": session_id,
                "union_group_size": len(union_group),
                "union_group_rank": union_group.index(session_id) + 1,
                "sequence_group_size": len(sequence_group),
                "sequence_group_rank": sequence_group.index(session_id) + 1,
                "sequence_length": len(sequences[session_id]),
                "same_length_group_size": len(same_length),
                "length_alone_unique": len(same_length) == 1,
                "classification": (
                    "SEQUENCE_SPLIT" if len(sequence_group) == 1
                    else "SEQUENCE_COLLISION"
                ),
            })

    rows.sort(key=lambda row: (row["question_id"], row["union_group_rank"], row["session_id"]))
    states = Counter(row["classification"] for row in rows)
    result = {
        "schema": "da076-sequence-separability-v1",
        "status": "POSTHOC_SEQUENCE_SEPARABILITY_CHARACTERIZED",
        "target_sessions": len(rows),
        "classifications": dict(states),
        "length_alone_unique": sum(row["length_alone_unique"] for row in rows),
        "union_group_sizes": sorted(row["union_group_size"] for row in rows),
        "sequence_group_sizes": sorted(row["sequence_group_size"] for row in rows),
        "sequence_lengths": sorted(row["sequence_length"] for row in rows),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc exact sequence separability only; no graph, selector, stopping, transfer, or adoption",
    }
    return result, rows


def run_analysis(dataset_path: Path, directory_path: Path,
                 da075_targets_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, directory_path, da075_targets_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "target_sessions.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da076-") as directory:
        replay_result, replay_rows = analyze(dataset_path, directory_path, da075_targets_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["target_sessions_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA076Error("Sequence audit replay differs")
    return result


__all__ = ["DA076Error", "analyze", "run_analysis"]
