"""Posthoc identifiability audit for DA-070 signature lattices."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter, deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_analysis import _quantile
from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import ordered_tokens
from analysis.da064_analysis import _targets
from analysis.da070_lattice_descent import _hasse

DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
DA066_STREAMS_SHA256 = "821ea4b31cdeed9eea053cf81a8a4cb322f9409c92f51d0ef1c681de99c0d491"
DA066_OUTCOMES_SHA256 = "25a5dd207b54ee3d5a68dc7d0788beb5f807df88fe36a36ab7e7fc45a4a3f5ec"


class DA072Error(RuntimeError):
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


def analyze(dataset_path: Path, directory_path: Path, da066_streams_path: Path,
            da066_outcomes_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (directory_path, DIRECTORY_SHA256),
        (da066_streams_path, DA066_STREAMS_SHA256),
        (da066_outcomes_path, DA066_OUTCOMES_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA072Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    streams = {str(row["question_id"]): row for row in _read(da066_streams_path)}
    outcomes = {str(row["question_id"]): row for row in _read(da066_outcomes_path)}
    targets = _targets(dataset_path)
    rows = []
    missing_episode_count = 0
    for question_id in sorted(outcomes):
        if bool(outcomes[question_id]["complete_reachability"]):
            continue
        source = raw[question_id]
        directory = directories[question_id]
        episodes, _ = _episodes(source)
        coordinate = {
            str(item["episode_id"]): {
                "session_id": str(item["session_id"]),
                "episode_order": int(item["episode_order"]),
            }
            for item in directory["episodes"]
        }
        selected = {str(item["episode_id"]) for item in streams[question_id]["stream"]}
        missing = targets[question_id]["episodes"] - selected
        missing_episode_count += len(missing)
        target_sessions = {
            str(coordinate[episode_id]["session_id"]) for episode_id in missing
        }
        session_order = [str(item["session_id"]) for item in directory["sessions"]]
        session_position = {session_id: index for index, session_id in enumerate(session_order)}
        query_tokens = _unique(ordered_tokens(str(source["question"])))
        query_set = frozenset(query_tokens)
        session_tokens: dict[str, list[frozenset[str]]] = {session_id: [] for session_id in session_order}
        for episode in episodes:
            episode_id = str(episode["identity"])
            session_id = str(coordinate[episode_id]["session_id"])
            observed = frozenset(ordered_tokens(
                "\n".join(str(member["text"]) for member in episode["members"])
            )) & query_set
            session_tokens[session_id].append(observed)
        signatures = {
            session_id: frozenset().union(*token_sets)
            for session_id, token_sets in session_tokens.items()
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
                tuple(int(token in signature) for token in query_tokens),
            )

        roots = sorted(roots, key=node_key)
        for node in children:
            children[node].sort(key=node_key)
        parents: dict[frozenset[str], list[frozenset[str]]] = {node: [] for node in nodes}
        for parent, child_nodes in children.items():
            for child in child_nodes:
                parents[child].append(parent)
        queue = deque((root, 0) for root in roots)
        traversal: list[frozenset[str]] = []
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
        for session_id in sorted(target_sessions, key=session_position.__getitem__):
            signature = signatures[session_id]
            group = groups[signature]
            group_rank = group.index(session_id) + 1
            depth = depths[signature]
            rows.append({
                "question_id": question_id,
                "question_type": targets[question_id]["question_type"],
                "session_id": session_id,
                "classification": (
                    "EQUAL_SIGNATURE_COLLISION"
                    if len(group) > 1 else "UNIQUE_SIGNATURE_BRANCH_AMBIGUITY"
                ),
                "signature_token_count": len(signature),
                "signature_group_size": len(group),
                "signature_group_rank": group_rank,
                "lattice_depth": depth,
                "depth_width": width[depth],
                "parent_count": len(parents[signature]),
                "child_count": len(children[signature]),
                "bfs_node_position": positions[signature],
            })
    if len({row["question_id"] for row in rows}) != 27 or missing_episode_count != 35:
        raise DA072Error("Opened residual population differs")

    def distribution(field: str) -> dict[str, float | int | None]:
        values = [float(row[field]) for row in rows]
        return {
            "n": len(values),
            "p10": _quantile(values, .1),
            "p50": _quantile(values, .5),
            "p90": _quantile(values, .9),
            "max": max(values, default=None),
        }

    classes = Counter(row["classification"] for row in rows)
    question_classes: Counter[str] = Counter()
    for question_id in sorted({row["question_id"] for row in rows}):
        cell = {row["classification"] for row in rows if row["question_id"] == question_id}
        question_classes["MIXED" if len(cell) > 1 else next(iter(cell))] += 1
    types = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        cell = [row for row in rows if row["question_type"] == question_type]
        types[question_type] = {
            "sessions": len(cell),
            "classes": dict(Counter(row["classification"] for row in cell)),
        }
    result = {
        "schema": "da072-lattice-identifiability-audit-v1",
        "status": "POSTHOC_LATTICE_IDENTIFIABILITY_CHARACTERIZED",
        "questions": 27,
        "missing_episodes": missing_episode_count,
        "target_sessions": len(rows),
        "session_classes": dict(classes),
        "question_classes": dict(question_classes),
        "signature_group_size": distribution("signature_group_size"),
        "signature_group_rank": distribution("signature_group_rank"),
        "lattice_depth": distribution("lattice_depth"),
        "depth_width": distribution("depth_width"),
        "parent_count": distribution("parent_count"),
        "child_count": distribution("child_count"),
        "bfs_node_position": distribution("bfs_node_position"),
        "by_question_type": types,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc identifiability anatomy only; no selector, stopping, transfer, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(dataset_path: Path, directory_path: Path, da066_streams_path: Path,
                 da066_outcomes_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(
        dataset_path, directory_path, da066_streams_path, da066_outcomes_path
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "target_sessions.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da072-") as directory:
        replay_result, replay_rows = analyze(
            dataset_path, directory_path, da066_streams_path, da066_outcomes_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["target_sessions_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA072Error("Audit replay differs")
    return result


__all__ = ["DA072Error", "analyze", "run_analysis"]
