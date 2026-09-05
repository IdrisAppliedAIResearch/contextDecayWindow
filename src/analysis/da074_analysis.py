"""Reachability, burden, and collision analysis for DA-074."""

from __future__ import annotations

import gzip
import json
import statistics
from pathlib import Path
from typing import Any

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import bigrams, ordered_tokens
from analysis.da064_analysis import _targets
from analysis.da073_ordered_lattice import _features, _typed_features, _unique

STREAMS_SHA256 = "1c99679e481b7a3ef3d91d184d5df047f9aebab460805480895cfa8618c1a5d1"
DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
DA066_OUTCOMES_SHA256 = "25a5dd207b54ee3d5a68dc7d0788beb5f807df88fe36a36ab7e7fc45a4a3f5ec"
DA072_TARGETS_SHA256 = "b6e2bc8db8773a0659ede9c8eb11342b007be57241f728110298622631bbaa06"
WORK_REFERENCE = 37
COLLISION_REFERENCE = 13


class DA074AnalysisError(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _role_signature_groups(question: dict[str, Any], directory: dict[str, Any]) -> dict[str, int]:
    episodes, _ = _episodes(question)
    coordinate = {
        str(item["episode_id"]): str(item["session_id"])
        for item in directory["episodes"]
    }
    query_sequence = ordered_tokens(str(question["question"]))
    query_unigrams = _unique(query_sequence)
    query_bigrams = _unique(bigrams(query_sequence))
    session_features: dict[str, list[frozenset[str]]] = {
        str(item["session_id"]): [] for item in directory["sessions"]
    }
    for episode in episodes:
        episode_id = str(episode["identity"])
        session_id = coordinate[episode_id]
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
        session_features[session_id].append(frozenset(features))
    signatures = {
        session_id: frozenset().union(*features)
        for session_id, features in session_features.items()
    }
    counts: dict[frozenset[str], int] = {}
    for signature in signatures.values():
        if signature:
            counts[signature] = counts.get(signature, 0) + 1
    return {
        session_id: counts[signature]
        for session_id, signature in signatures.items()
        if signature
    }


def analyze(dataset_path: Path, directory_path: Path, streams_path: Path,
            da066_outcomes_path: Path,
            da072_targets_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (directory_path, DIRECTORY_SHA256),
        (streams_path, STREAMS_SHA256),
        (da066_outcomes_path, DA066_OUTCOMES_SHA256),
        (da072_targets_path, DA072_TARGETS_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA074AnalysisError("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    baseline = {str(row["question_id"]): row for row in _read(da066_outcomes_path)}
    target_sessions: dict[str, set[str]] = {}
    for row in _read(da072_targets_path):
        target_sessions.setdefault(str(row["question_id"]), set()).add(str(row["session_id"]))
    targets = _targets(dataset_path)
    rows = []
    target_group_sizes = []
    for source in _read(streams_path):
        question_id = str(source["question_id"])
        required = targets[question_id]["episodes"]
        stream = list(source["stream"])
        positions = {str(item["episode_id"]): index + 1 for index, item in enumerate(stream)}
        ranks = [positions[episode_id] for episode_id in required if episode_id in positions]
        complete = len(ranks) == len(required)
        last = max(ranks) if complete else None
        da066_count = int(baseline[question_id]["stream_episodes"])
        rows.append({
            "question_id": question_id,
            "question_type": targets[question_id]["question_type"],
            "complete_reachability": complete,
            "any_reachability": bool(ranks),
            "da066_complete": bool(baseline[question_id]["complete_reachability"]),
            "first_required_position": min(ranks) if ranks else None,
            "last_required_position": last,
            "additional_episodes_beyond_da066": max(0, last - da066_count) if last is not None else None,
            "stream_episodes": len(stream),
            "protected_payload_mutations": int(source["protected_payload_mutations"]),
        })
        if question_id in target_sessions:
            sizes = _role_signature_groups(raw[question_id], directories[question_id])
            target_group_sizes.extend(sizes[session_id] for session_id in target_sessions[question_id])
    if len(rows) != 465 or len(target_group_sizes) != 31:
        raise DA074AnalysisError("Outcome population differs")

    def distribution(field: str, population: list[dict[str, Any]] = rows) -> dict[str, float | int | None]:
        values = [float(row[field]) for row in population if row[field] is not None]
        return {
            "n": len(values),
            "p10": _quantile(values, .1),
            "p50": _quantile(values, .5),
            "p90": _quantile(values, .9),
            "max": max(values, default=None),
        }

    complete = sum(row["complete_reachability"] for row in rows)
    complete_rate = complete / len(rows)
    mutations = sum(row["protected_payload_mutations"] for row in rows)
    gains = [row for row in rows if row["complete_reachability"] and not row["da066_complete"]]
    gain_values = [int(row["additional_episodes_beyond_da066"]) for row in gains]
    gain_median = statistics.median(gain_values) if gain_values else None
    collision_sessions = sum(size > 1 for size in target_group_sizes)
    status = (
        "ROLE_TYPED_FEATURE_LATTICE_SIGNAL"
        if complete_rate >= .98 and mutations == 0
        and gain_median is not None and gain_median < WORK_REFERENCE
        and collision_sessions < COLLISION_REFERENCE
        else "NO_ROLE_TYPED_FEATURE_LATTICE_SIGNAL"
    )
    result = {
        "schema": "da074-role-typed-feature-lattice-result-v1",
        "status": status,
        "questions": len(rows),
        "complete_reachability": complete,
        "complete_reachability_rate": complete_rate,
        "any_reachability": sum(row["any_reachability"] for row in rows),
        "first_required_position": distribution("first_required_position"),
        "last_required_position": distribution("last_required_position"),
        "stream_episodes": distribution("stream_episodes"),
        "gain_only": {
            "questions": len(gains),
            "additional_episodes_beyond_da066": distribution(
                "additional_episodes_beyond_da066", gains
            ),
            "reference_median": WORK_REFERENCE,
        },
        "target_collisions": {
            "sessions": collision_sessions,
            "reference_sessions": COLLISION_REFERENCE,
            "group_size": {
                "n": len(target_group_sizes),
                "p50": _quantile([float(value) for value in target_group_sizes], .5),
                "p90": _quantile([float(value) for value in target_group_sizes], .9),
                "max": max(target_group_sizes),
            },
        },
        "simultaneously_rendered_episodes": 1,
        "peak_current_frame_chars": 2_048,
        "protected_payload_mutations": mutations,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "role-typed reachability, burden, and collision anatomy only; no reader or delivery",
    }
    return result, rows


def run_analysis(dataset_path: Path, directory_path: Path, streams_path: Path,
                 da066_outcomes_path: Path, da072_targets_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(
        dataset_path, directory_path, streams_path,
        da066_outcomes_path, da072_targets_path,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "reachability.jsonl.gz"
    with artifact.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    result["reachability_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


__all__ = ["DA074AnalysisError", "analyze", "run_analysis"]
