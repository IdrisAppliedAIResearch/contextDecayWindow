"""Minimum exact sequence-prefix witnesses for DA-076 residual carriers."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import bigrams, ordered_tokens
from analysis.da073_ordered_lattice import _features, _typed_features, _unique

DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
DA076_TARGETS_SHA256 = "85315ec92eb1cd5382707eb1c2a272b9d54cb720b36b2fe0b21068d09948dbeb"


class DA077Error(RuntimeError):
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


def _canonical(sequence: tuple[tuple[str, ...], ...]) -> str:
    return json.dumps(sequence, ensure_ascii=True, separators=(",", ":"))


def analyze(dataset_path: Path, directory_path: Path,
            da076_targets_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (directory_path, DIRECTORY_SHA256),
        (da076_targets_path, DA076_TARGETS_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA077Error("Sealed input differs")

    raw = {
        str(row["question_id"]): row
        for row in json.loads(dataset_path.read_text(encoding="utf-8"))
    }
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    target_rows = _read(da076_targets_path)
    if len(target_rows) != 5 or any(row["classification"] != "SEQUENCE_SPLIT" for row in target_rows):
        raise DA077Error("DA-076 target population differs")

    rows = []
    for target in target_rows:
        question_id = str(target["question_id"])
        session_id = str(target["session_id"])
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
            peer: [] for peer in session_order
        }
        for episode in episodes:
            features = set(_features(
                "\n".join(str(member["text"]) for member in episode["members"]),
                query_unigrams,
                query_bigrams,
            ))
            for member in episode["members"]:
                features.update(_typed_features(
                    str(member["text"]), str(member["speaker"]).upper(),
                    query_unigrams, query_bigrams,
                ))
            episode_features[coordinate[str(episode["identity"])]].append(frozenset(features))

        unions = {
            peer: frozenset().union(*sequence)
            for peer, sequence in episode_features.items()
        }
        union_group = [peer for peer in session_order if unions[peer] == unions[session_id]]
        sequences = {
            peer: tuple(tuple(sorted(features)) for features in episode_features[peer])
            for peer in union_group
        }
        target_sequence = sequences[session_id]
        trajectory = []
        witness_depth = None
        for depth in range(1, len(target_sequence) + 1):
            prefix = target_sequence[:depth]
            group = [peer for peer in union_group if sequences[peer][:depth] == prefix]
            trajectory.append({"depth": depth, "group_size": len(group)})
            if len(group) == 1 and witness_depth is None:
                witness_depth = depth
        if witness_depth is None:
            raise DA077Error("Full sequence does not identify sealed target")
        witness = target_sequence[:witness_depth]
        rows.append({
            "question_id": question_id,
            "question_type": str(target["question_type"]),
            "session_id": session_id,
            "union_group_size": len(union_group),
            "full_sequence_length": len(target_sequence),
            "length_alone_unique": bool(target["length_alone_unique"]),
            "witness_depth": witness_depth,
            "witness_fraction": witness_depth / len(target_sequence),
            "witness_canonical_chars": len(_canonical(witness)),
            "full_sequence_canonical_chars": len(_canonical(target_sequence)),
            "peer_group_trajectory": trajectory,
        })

    rows.sort(key=lambda row: (row["question_id"], row["session_id"]))

    def distribution(field: str) -> dict[str, float | int]:
        values = [float(row[field]) for row in rows]
        return {
            "n": len(values),
            "p50": _quantile(values, .5),
            "p90": _quantile(values, .9),
            "min": min(values),
            "max": max(values),
        }

    result = {
        "schema": "da077-sequence-prefix-witness-v1",
        "status": "POSTHOC_SEQUENCE_PREFIX_WITNESS_CHARACTERIZED",
        "target_sessions": len(rows),
        "witness_depth": distribution("witness_depth"),
        "full_sequence_length": distribution("full_sequence_length"),
        "witness_fraction": distribution("witness_fraction"),
        "witness_canonical_chars": distribution("witness_canonical_chars"),
        "full_sequence_canonical_chars": distribution("full_sequence_canonical_chars"),
        "length_alone_unique": sum(row["length_alone_unique"] for row in rows),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc exact-prefix compactness only; no address, selector, reader, transfer, delivery, or adoption",
    }
    return result, rows


def run_analysis(dataset_path: Path, directory_path: Path,
                 da076_targets_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, directory_path, da076_targets_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "target_sessions.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da077-") as directory:
        replay_result, replay_rows = analyze(dataset_path, directory_path, da076_targets_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["target_sessions_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA077Error("Prefix witness replay differs")
    return result


__all__ = ["DA077Error", "analyze", "run_analysis"]
