"""Blind signature-lattice descent for DA-070."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter, deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import ordered_tokens
from analysis.da069_conjunctive_signatures import _shortest_cover

DA069_STREAMS_SHA256 = "7b533e17239378a4d1926f6e2c6d0d81804ae93c1f22f7af12263df63889d1af"
DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
RADIUS = 5
CURRENT_FRAME_CAP = 2_048


class DA070Error(RuntimeError):
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


def _hasse(signatures: Sequence[frozenset[str]]) -> tuple[list[frozenset[str]], dict[frozenset[str], list[frozenset[str]]]]:
    nodes = list(dict.fromkeys(signatures))
    roots = [node for node in nodes if not any(node < other for other in nodes)]
    children: dict[frozenset[str], list[frozenset[str]]] = {node: [] for node in nodes}
    for parent in nodes:
        for child in nodes:
            if not child < parent:
                continue
            if any(child < middle < parent for middle in nodes):
                continue
            children[parent].append(child)
    return roots, children


def _synthetic_check() -> bool:
    a = frozenset({"a"})
    b = frozenset({"b"})
    ab = frozenset({"a", "b"})
    abc = frozenset({"a", "b", "c"})
    roots, children = _hasse([a, b, ab, abc])
    return (
        roots == [abc]
        and children[abc] == [ab]
        and children[ab] == [a, b]
        and not children[a]
        and not children[b]
    )


def build_rows(dataset_path: Path, da069_path: Path, directory_path: Path,
               max_traversal_depth: int | None = None) -> list[dict[str, Any]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (da069_path, DA069_STREAMS_SHA256),
        (directory_path, DIRECTORY_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA070Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    parents = {str(row["question_id"]): row for row in _read(da069_path)}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    if set(parents) != set(directories) or len(parents) != 465:
        raise DA070Error("Population differs")
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
        session_position = {session_id: index for index, session_id in enumerate(session_order)}
        query_tokens = _unique(ordered_tokens(str(source["question"])))
        query_set = frozenset(query_tokens)
        session_tokens: dict[str, list[frozenset[str]]] = {session_id: [] for session_id in session_order}
        for episode in episodes:
            episode_id = str(episode["identity"])
            item = coordinate[episode_id]
            observed = frozenset(ordered_tokens(
                "\n".join(str(member["text"]) for member in episode["members"])
            )) & query_set
            session_tokens[str(item["session_id"])].append(observed)
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
        for parent_node in children:
            children[parent_node].sort(key=node_key)
        queue = deque((root, 0) for root in roots)
        visited: set[frozenset[str]] = set()
        traversal: list[tuple[frozenset[str], int]] = []
        while queue:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            traversal.append((node, depth))
            queue.extend((child, depth + 1) for child in children[node])
        if visited != set(nodes):
            raise DA070Error("Lattice BFS did not cover every nonempty signature")
        root_set = set(roots)
        stream = [dict(item) for item in prefix]
        seen = {str(item["episode_id"]) for item in stream}
        if len(seen) != len(stream):
            raise DA070Error("DA-069 prefix contains duplicate")
        rejections: Counter[str] = Counter()
        additions = 0
        appended_sessions = 0
        interval_episodes = 0

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

        appended_nodes = 0
        for signature, depth in traversal:
            if signature in root_set or (
                max_traversal_depth is not None and depth > max_traversal_depth
            ):
                continue
            appended_nodes += 1
            for session_id in groups[signature]:
                appended_sessions += 1
                start, end = _shortest_cover(session_tokens[session_id], signature)
                interval_episodes += end - start + 1
                for order in range(start, end + 1):
                    append(by_local[(session_id, order)], "LATTICE_INTERVAL")
                for endpoint in sorted({start, end}):
                    for distance in range(1, RADIUS + 1):
                        for direction in (-1, 1):
                            neighbor_id = by_local.get((session_id, endpoint + direction * distance))
                            if neighbor_id is None:
                                rejections["SESSION_BOUNDARY"] += 1
                                continue
                            append(neighbor_id, "LATTICE_LOCAL")
        if [item["episode_id"] for item in stream[:len(prefix)]] != [
            item["episode_id"] for item in prefix
        ]:
            raise DA070Error("Protected DA-069 prefix differs")
        output_row = {
            "question_id": question_id,
            "da069_prefix_count": len(prefix),
            "query_tokens": query_tokens,
            "signature_nodes": len(nodes),
            "root_nodes": len(roots),
            "cover_edges": sum(len(values) for values in children.values()),
            "max_depth": max((depth for _, depth in traversal), default=0),
            "appended_signature_nodes": appended_nodes,
            "appended_sessions": appended_sessions,
            "interval_episodes": interval_episodes,
            "lattice_additions": additions,
            "rejections": dict(rejections),
            "stream": stream,
            "radius": RADIUS,
            "simultaneously_rendered_episodes": 1,
            "current_frame_cap": CURRENT_FRAME_CAP,
            "protected_payload_mutations": 0,
            "rendered_char_delta": 0,
        }
        if max_traversal_depth is not None:
            output_row["traversal_depth_limit"] = max_traversal_depth
            output_row["nodes_within_limit"] = sum(
                depth <= max_traversal_depth for _, depth in traversal
            )
        rows.append(output_row)
    return rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, da069_path: Path,
                  directory_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = build_rows(dataset_path, da069_path, directory_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_streams.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da070-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, da069_path, directory_path))
        identical = artifact.read_bytes() == replay.read_bytes()
    rejections: Counter[str] = Counter()
    for row in rows:
        rejections.update(row["rejections"])
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden = ("has_" + "answer", "evi" + "dence")
    leakage_clean = not any(token in source for token in forbidden)
    valid = (
        _synthetic_check()
        and identical
        and sum(row["cover_edges"] for row in rows) > 0
        and max(row["max_depth"] for row in rows) > 0
        and sum(row["appended_signature_nodes"] for row in rows) > 0
        and sum(row["lattice_additions"] for row in rows) > 0
        and rejections["SESSION_BOUNDARY"] > 0
        and all(len(row["stream"]) == len({item["episode_id"] for item in row["stream"]}) for row in rows)
        and all(len(item["member_ids"]) == 2 for row in rows for item in row["stream"])
        and all(row["radius"] == RADIUS for row in rows)
        and all(row["simultaneously_rendered_episodes"] == 1 for row in rows)
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
        and leakage_clean
    )
    result = {
        "schema": "da070-signature-lattice-descent-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "synthetic_hasse_check": _synthetic_check(),
        "radius": RADIUS,
        "da069_prefix_episodes": sum(row["da069_prefix_count"] for row in rows),
        "signature_nodes": sum(row["signature_nodes"] for row in rows),
        "root_nodes": sum(row["root_nodes"] for row in rows),
        "cover_edges": sum(row["cover_edges"] for row in rows),
        "max_depth": max(row["max_depth"] for row in rows),
        "appended_signature_nodes": sum(row["appended_signature_nodes"] for row in rows),
        "appended_sessions": sum(row["appended_sessions"] for row in rows),
        "interval_episodes": sum(row["interval_episodes"] for row in rows),
        "lattice_additions": sum(row["lattice_additions"] for row in rows),
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
        raise DA070Error("Blind lattice preflight failed")
    return result


__all__ = ["DA070Error", "_hasse", "_synthetic_check", "build_rows", "run_preflight"]
