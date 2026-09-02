"""Directed provenance paths from DA-078 prompt roots to residual carriers."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter, deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.da078_allocation import _protected_descriptors

DA079_SHA256 = "08c06d6640edd6cd4579fb350033db11b7d912e7664b6659e27d603882e60ed1"
DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
DA045_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"


class DA083Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(longmem_path: Path, population_path: Path, da079_path: Path,
            da078_path: Path, da045_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = (
        (da079_path, DA079_SHA256),
        (da078_path, DA078_SHA256),
        (da045_path, DA045_SHA256),
    )
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA083Error("Sealed input differs")
    residuals = {str(row["key"]): row for row in _read(da079_path)}
    selections = {str(row["question_id"]): row for row in read_gzip(da078_path)}
    streams = {str(row["question_id"]): row for row in read_gzip(da045_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in residuals
    }
    if not (len(residuals) == len(records) == 13 and set(residuals) <= set(streams)):
        raise DA083Error("Population differs")

    rows = []
    for question_id in sorted(residuals):
        residual = residuals[question_id]
        selection = selections[question_id]
        stream = streams[question_id]
        record = records[question_id]
        by_id = {
            episode.candidate.identity: episode
            for episode in record.episodes
        }
        pair_for = lambda identity: by_id[identity].members
        da038_row = {**selection, "treatment": selection["da038_control"]}
        descriptors = _protected_descriptors(da038_row, pair_for)
        for action in selection["treatment"]["actions"]:
            if action["kind"] == "MEMBER":
                descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
        roots, root_seen = [], set()
        for identity, _members in descriptors:
            if identity not in root_seen:
                root_seen.add(identity)
                roots.append(identity)

        adjacency: dict[str, list[tuple[str, int]]] = {}
        edge_seen: set[tuple[str, str]] = set()
        for ordinal, edge in enumerate(stream["baseline_actions"], start=1):
            parent, child = str(edge["seed_id"]), str(edge["neighbor_id"])
            if (parent, child) in edge_seen:
                continue
            edge_seen.add((parent, child))
            adjacency.setdefault(parent, []).append((child, ordinal))

        distance = {root: 0 for root in roots}
        chosen_parent: dict[str, tuple[str, int]] = {}
        shortest_parents: Counter[str] = Counter()
        queue = deque(roots)
        while queue:
            parent = queue.popleft()
            for child, ordinal in adjacency.get(parent, []):
                candidate = distance[parent] + 1
                if child not in distance:
                    distance[child] = candidate
                    chosen_parent[child] = (parent, ordinal)
                    shortest_parents[child] = 1
                    queue.append(child)
                elif distance[child] == candidate:
                    shortest_parents[child] += 1

        target = str(residual["carrier"])
        if target in root_seen:
            state, depth = "ROOT_MEMBER", 0
        elif target in distance:
            state, depth = "LINKED_PATH", distance[target]
        else:
            state, depth = "ORPHAN_PARENT", None
        path_ordinals, path_degrees = [], []
        cursor = target
        while cursor in chosen_parent:
            parent, ordinal = chosen_parent[cursor]
            path_ordinals.append(ordinal)
            path_degrees.append(len(adjacency.get(parent, [])))
            cursor = parent
        path_ordinals.reverse()
        path_degrees.reverse()
        if depth is not None and len(path_ordinals) != depth:
            raise DA083Error("Chosen provenance path depth differs")
        rows.append({
            "key": question_id,
            "question_type": record.question_type,
            "blocker": str(residual["blocker"]),
            "carrier": target,
            "state": state,
            "shortest_depth": depth,
            "shortest_parent_count": int(shortest_parents[target]) if depth else 0,
            "path_edge_ordinals": path_ordinals,
            "path_child_degrees": path_degrees,
            "terminal_parent_represented": (
                target in root_seen
                or (target in chosen_parent and chosen_parent[target][0] in root_seen)
            ),
            "root_count": len(roots),
            "graph_edges": len(edge_seen),
        })

    states = Counter(row["state"] for row in rows)
    finite = [row for row in rows if row["shortest_depth"] is not None]
    path_degrees = [degree for row in finite for degree in row["path_child_degrees"]]
    result = {
        "schema": "da083-provenance-path-anatomy-v1",
        "status": "POSTHOC_PROVENANCE_PATHS_CHARACTERIZED",
        "residuals": len(rows),
        "states": dict(states),
        "shortest_depth": distribution([row["shortest_depth"] for row in finite]),
        "shortest_parent_count": distribution([
            row["shortest_parent_count"] for row in finite
        ]),
        "path_child_degree": distribution(path_degrees),
        "terminal_parent_represented": sum(row["terminal_parent_represented"] for row in rows),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc directed provenance anatomy only; no reader, stopping, transfer, delivery, or adoption",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(longmem_path: Path, population_path: Path, da079_path: Path,
                 da078_path: Path, da045_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(
        longmem_path, population_path, da079_path, da078_path, da045_path
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "paths.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da083-") as directory:
        replay_result, replay_rows = analyze(
            longmem_path, population_path, da079_path, da078_path, da045_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["paths_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA083Error("DA-083 replay differs")
    return result


__all__ = ["DA083Error", "analyze", "run_analysis"]
