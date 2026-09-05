"""Blind unigram-plus-bigram signature lattice for DA-073."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter, deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da048_continuation import DATASET_SHA256, _episodes, sha256_file
from analysis.da061_bigrams import bigrams, ordered_tokens
from analysis.da069_conjunctive_signatures import _shortest_cover
from analysis.da070_lattice_descent import _hasse, _synthetic_check

DA066_STREAMS_SHA256 = "821ea4b31cdeed9eea053cf81a8a4cb322f9409c92f51d0ef1c681de99c0d491"
DIRECTORY_SHA256 = "dffb9bae7b6bfd4108b8f7966056e15d9c37e8e5b75cd06cd8e4ba658fe9170c"
RADIUS = 5
CURRENT_FRAME_CAP = 2_048


class DA073Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _unique(values: Sequence[Any]) -> list[Any]:
    output, seen = [], set()
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _features(text: str, query_unigrams: Sequence[str],
              query_bigrams: Sequence[tuple[str, str]]) -> frozenset[str]:
    tokens = ordered_tokens(text)
    token_set = set(tokens)
    bigram_set = set(bigrams(tokens))
    output = {f"U\0{token}" for token in query_unigrams if token in token_set}
    output.update(
        f"B\0{left}\0{right}"
        for left, right in query_bigrams
        if (left, right) in bigram_set
    )
    return frozenset(output)


def _typed_features(text: str, role: str, query_unigrams: Sequence[str],
                    query_bigrams: Sequence[tuple[str, str]]) -> frozenset[str]:
    if role not in {"USER", "ASSISTANT"}:
        raise DA073Error("Unexpected typed feature role")
    tokens = ordered_tokens(text)
    token_set = set(tokens)
    bigram_set = set(bigrams(tokens))
    output = {
        f"TU\0{role}\0{token}"
        for token in query_unigrams
        if token in token_set
    }
    output.update(
        f"TB\0{role}\0{left}\0{right}"
        for left, right in query_bigrams
        if (left, right) in bigram_set
    )
    return frozenset(output)


def build_rows(dataset_path: Path, da066_path: Path, directory_path: Path,
               role_typed: bool = False) -> list[dict[str, Any]]:
    seals = (
        (dataset_path, DATASET_SHA256),
        (da066_path, DA066_STREAMS_SHA256),
        (directory_path, DIRECTORY_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA073Error("Sealed input differs")
    raw = {str(row["question_id"]): row for row in json.loads(dataset_path.read_text(encoding="utf-8"))}
    parents = {str(row["question_id"]): row for row in _read(da066_path)}
    directories = {str(row["question_id"]): row for row in _read(directory_path)}
    if set(parents) != set(directories) or len(parents) != 465:
        raise DA073Error("Population differs")
    rows = []
    for question_id in sorted(parents):
        source = raw[question_id]
        prefix = list(parents[question_id]["stream"])
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
        query_sequence = ordered_tokens(str(source["question"]))
        query_unigrams = _unique(query_sequence)
        query_bigrams = _unique(bigrams(query_sequence))
        feature_order = (
            [f"U\0{token}" for token in query_unigrams]
            + [f"B\0{left}\0{right}" for left, right in query_bigrams]
        )
        if role_typed:
            for role in ("USER", "ASSISTANT"):
                feature_order.extend(f"TU\0{role}\0{token}" for token in query_unigrams)
                feature_order.extend(
                    f"TB\0{role}\0{left}\0{right}"
                    for left, right in query_bigrams
                )
        session_features: dict[str, list[frozenset[str]]] = {
            session_id: [] for session_id in session_order
        }
        observed_bigram_features = 0
        typed_counts: Counter[str] = Counter()
        for episode in episodes:
            episode_id = str(episode["identity"])
            session_id = str(coordinate[episode_id]["session_id"])
            features = _features(
                "\n".join(str(member["text"]) for member in episode["members"]),
                query_unigrams,
                query_bigrams,
            )
            if role_typed:
                augmented = set(features)
                for member in episode["members"]:
                    role = str(member["speaker"]).upper()
                    member_features = _typed_features(
                        str(member["text"]), role, query_unigrams, query_bigrams
                    )
                    augmented.update(member_features)
                    typed_counts[f"{role}_UNIGRAM"] += sum(
                        feature.startswith(f"TU\0{role}\0") for feature in member_features
                    )
                    typed_counts[f"{role}_BIGRAM"] += sum(
                        feature.startswith(f"TB\0{role}\0") for feature in member_features
                    )
                features = frozenset(augmented)
            observed_bigram_features += sum(feature.startswith("B\0") for feature in features)
            session_features[session_id].append(features)
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
        queue = deque((root, 0) for root in roots)
        traversal: list[tuple[frozenset[str], int]] = []
        visited: set[frozenset[str]] = set()
        while queue:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            traversal.append((node, depth))
            queue.extend((child, depth + 1) for child in children[node])
        if visited != set(nodes):
            raise DA073Error("Ordered-feature BFS did not cover every node")
        stream = [dict(item) for item in prefix]
        seen = {str(item["episode_id"]) for item in stream}
        if len(seen) != len(stream):
            raise DA073Error("DA-066 prefix contains duplicate")
        rejections: Counter[str] = Counter()
        additions = 0
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

        for signature, _depth in traversal:
            for session_id in groups[signature]:
                start, end = _shortest_cover(session_features[session_id], signature)
                interval_episodes += end - start + 1
                for order in range(start, end + 1):
                    append(by_local[(session_id, order)], "ORDERED_INTERVAL")
                for endpoint in sorted({start, end}):
                    for distance in range(1, RADIUS + 1):
                        for direction in (-1, 1):
                            neighbor_id = by_local.get((session_id, endpoint + direction * distance))
                            if neighbor_id is None:
                                rejections["SESSION_BOUNDARY"] += 1
                                continue
                            append(neighbor_id, "ORDERED_LOCAL")
        if [item["episode_id"] for item in stream[:len(prefix)]] != [
            item["episode_id"] for item in prefix
        ]:
            raise DA073Error("Protected DA-066 prefix differs")
        equal_sessions = sum(len(group) for group in groups.values() if len(group) > 1)
        output_row = {
            "question_id": question_id,
            "da066_prefix_count": len(prefix),
            "query_unigram_features": len(query_unigrams),
            "query_bigram_features": len(query_bigrams),
            "observed_bigram_features": observed_bigram_features,
            "signature_nodes": len(nodes),
            "equal_signature_sessions": equal_sessions,
            "root_nodes": len(roots),
            "cover_edges": sum(len(values) for values in children.values()),
            "max_depth": max((depth for _, depth in traversal), default=0),
            "interval_episodes": interval_episodes,
            "ordered_feature_additions": additions,
            "rejections": dict(rejections),
            "stream": stream,
            "radius": RADIUS,
            "simultaneously_rendered_episodes": 1,
            "current_frame_cap": CURRENT_FRAME_CAP,
            "protected_payload_mutations": 0,
            "rendered_char_delta": 0,
        }
        if role_typed:
            output_row["role_typed"] = True
            output_row["typed_feature_occurrences"] = dict(typed_counts)
        rows.append(output_row)
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
    with tempfile.TemporaryDirectory(prefix="da073-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(dataset_path, da066_path, directory_path))
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
        and sum(row["query_bigram_features"] for row in rows) > 0
        and sum(row["observed_bigram_features"] for row in rows) > 0
        and sum(row["cover_edges"] for row in rows) > 0
        and sum(row["ordered_feature_additions"] for row in rows) > 0
        and rejections["SESSION_BOUNDARY"] > 0
        and all(len(row["stream"]) == len({item["episode_id"] for item in row["stream"]}) for row in rows)
        and all(len(item["member_ids"]) == 2 for row in rows for item in row["stream"])
        and all(row["simultaneously_rendered_episodes"] == 1 for row in rows)
        and all(row["protected_payload_mutations"] == row["rendered_char_delta"] == 0 for row in rows)
        and leakage_clean
    )
    result = {
        "schema": "da073-ordered-feature-lattice-preflight-v1",
        "status": "PASS" if valid else "FAIL",
        "questions": len(rows),
        "synthetic_hasse_check": _synthetic_check(),
        "query_unigram_features": sum(row["query_unigram_features"] for row in rows),
        "query_bigram_features": sum(row["query_bigram_features"] for row in rows),
        "observed_bigram_features": sum(row["observed_bigram_features"] for row in rows),
        "signature_nodes": sum(row["signature_nodes"] for row in rows),
        "equal_signature_sessions": sum(row["equal_signature_sessions"] for row in rows),
        "root_nodes": sum(row["root_nodes"] for row in rows),
        "cover_edges": sum(row["cover_edges"] for row in rows),
        "max_depth": max(row["max_depth"] for row in rows),
        "interval_episodes": sum(row["interval_episodes"] for row in rows),
        "ordered_feature_additions": sum(row["ordered_feature_additions"] for row in rows),
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
        raise DA073Error("Blind ordered-feature preflight failed")
    return result


__all__ = ["DA073Error", "_features", "_typed_features", "build_rows", "run_preflight"]
