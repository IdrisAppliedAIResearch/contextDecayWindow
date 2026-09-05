"""Posthoc role-lattice anatomy for the fixed DA-072 target sessions."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter, deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import bigrams, ordered_tokens
from analysis.da070_lattice_descent import _hasse
from analysis.da073_ordered_lattice import _features, _typed_features, _unique

DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
DA072_TARGETS_SHA256 = "b6e2bc8db8773a0659ede9c8eb11342b007be57241f728110298622631bbaa06"


class DA075Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(dataset_path: Path, directory_path: Path,
            da072_targets_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (directory_path, DIRECTORY_SHA256),
        (da072_targets_path, DA072_TARGETS_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA075Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    prior_rows = _read(da072_targets_path)
    prior = {
        (str(row["question_id"]), str(row["session_id"])): row
        for row in prior_rows
    }
    targets: dict[str, list[str]] = {}
    for question_id, session_id in prior:
        targets.setdefault(question_id, []).append(session_id)
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
        session_position = {session_id: index for index, session_id in enumerate(session_order)}
        query_sequence = ordered_tokens(str(question["question"]))
        query_unigrams = _unique(query_sequence)
        query_bigrams = _unique(bigrams(query_sequence))
        feature_order = (
            [f"U\0{token}" for token in query_unigrams]
            + [f"B\0{left}\0{right}" for left, right in query_bigrams]
        )
        for role in ("USER", "ASSISTANT"):
            feature_order.extend(f"TU\0{role}\0{token}" for token in query_unigrams)
            feature_order.extend(
                f"TB\0{role}\0{left}\0{right}"
                for left, right in query_bigrams
            )
        session_features: dict[str, list[frozenset[str]]] = {
            session_id: [] for session_id in session_order
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
        groups: dict[frozenset[str], list[str]] = {}
        for session_id in session_order:
            signature = signatures[session_id]
            if signature:
                groups.setdefault(signature, []).append(session_id)
        nodes = list(groups)
        roots, children = _hasse(nodes)

        def node_key(signature: frozenset[str]) -> tuple[int, tuple[int, ...]]:
            return (
                min(session_position[session_id] for session_id in groups[signature]),
                tuple(int(feature in signature) for feature in feature_order),
            )

        roots = sorted(roots, key=node_key)
        for node in children:
            children[node].sort(key=node_key)
        parents: dict[frozenset[str], list[frozenset[str]]] = {node: [] for node in nodes}
        for parent, child_nodes in children.items():
            for child in child_nodes:
                parents[child].append(parent)
        queue = deque((root, 0) for root in roots)
        traversal = []
        depths: dict[frozenset[str], int] = {}
        while queue:
            node, depth = queue.popleft()
            if node in depths:
                continue
            depths[node] = depth
            traversal.append(node)
            queue.extend((child, depth + 1) for child in children[node])
        positions = {node: index + 1 for index, node in enumerate(traversal)}
        width = Counter(depths.values())
        for session_id in sorted(targets[question_id], key=session_position.__getitem__):
            signature = signatures[session_id]
            group = groups[signature]
            old = prior[(question_id, session_id)]
            role_position = positions[signature]
            rows.append({
                "question_id": question_id,
                "question_type": str(old["question_type"]),
                "session_id": session_id,
                "prior_classification": str(old["classification"]),
                "role_state": (
                    "ROLE_SIGNATURE_COLLISION" if len(group) > 1 else "ROLE_SIGNATURE_UNIQUE"
                ),
                "role_signature_group_size": len(group),
                "role_signature_group_rank": group.index(session_id) + 1,
                "role_lattice_depth": depths[signature],
                "role_depth_width": width[depths[signature]],
                "role_parent_count": len(parents[signature]),
                "role_child_count": len(children[signature]),
                "prior_bfs_node_position": int(old["bfs_node_position"]),
                "role_bfs_node_position": role_position,
                "bfs_position_change": role_position - int(old["bfs_node_position"]),
            })
    if len(rows) != 31:
        raise DA075Error("Target-session population differs")

    def distribution(field: str) -> dict[str, float | int | None]:
        values = [float(row[field]) for row in rows]
        return {
            "n": len(values),
            "p10": _quantile(values, .1),
            "p50": _quantile(values, .5),
            "p90": _quantile(values, .9),
            "min": min(values, default=None),
            "max": max(values, default=None),
        }

    transitions = Counter(
        f"{row['prior_classification']}->{row['role_state']}" for row in rows
    )
    result = {
        "schema": "da075-role-lattice-anatomy-v1",
        "status": "POSTHOC_ROLE_LATTICE_ANATOMY_CHARACTERIZED",
        "target_sessions": len(rows),
        "role_states": dict(Counter(row["role_state"] for row in rows)),
        "transitions": dict(transitions),
        "role_signature_group_size": distribution("role_signature_group_size"),
        "role_signature_group_rank": distribution("role_signature_group_rank"),
        "role_lattice_depth": distribution("role_lattice_depth"),
        "role_depth_width": distribution("role_depth_width"),
        "role_parent_count": distribution("role_parent_count"),
        "role_child_count": distribution("role_child_count"),
        "role_bfs_node_position": distribution("role_bfs_node_position"),
        "bfs_position_change": distribution("bfs_position_change"),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc role-lattice anatomy only; no selector, stopping, transfer, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, directory_path: Path,
                 da072_targets_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(dataset_path, directory_path, da072_targets_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "target_sessions.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da075-") as directory:
        replay_result, replay_rows = analyze(dataset_path, directory_path, da072_targets_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["target_sessions_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA075Error("Role anatomy replay differs")
    return result


__all__ = ["DA075Error", "analyze", "run_analysis"]
