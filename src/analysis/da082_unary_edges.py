"""Structural sibling and unary-seed anatomy for DA-079 residuals."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da032_audit import distribution
from analysis.da078_allocation import _protected_descriptors

DA079_SHA256 = "08c06d6640edd6cd4579fb350033db11b7d912e7664b6659e27d603882e60ed1"
DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
DA045_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"


class DA082Error(RuntimeError):
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
        raise DA082Error("Sealed input differs")
    residuals = {str(row["key"]): row for row in _read(da079_path)}
    selections = {str(row["question_id"]): row for row in read_gzip(da078_path)}
    streams = {str(row["question_id"]): row for row in read_gzip(da045_path)}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in residuals
    }
    if not (len(residuals) == len(records) == 13 and set(residuals) <= set(streams)):
        raise DA082Error("Population differs")

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
        prompt_members = {
            (identity, index)
            for identity, members in descriptors
            for index in members
        }
        prompt_episodes = {identity for identity, _ in prompt_members}
        required_key = (str(residual["carrier"]), int(residual["required_member"]))
        sibling_present = (required_key[0], 1 - required_key[1]) in prompt_members

        frontier = {
            (str(action["neighbor_id"]), int(action["member"]))
            for action in stream["treatment"]["actions"]
        }
        seed_targets: dict[str, set[tuple[str, int]]] = {}
        matching_seeds: set[str] = set()
        for edge in stream["baseline_actions"]:
            neighbor = str(edge["neighbor_id"])
            seed = str(edge["seed_id"])
            edge_targets = {
                key for key in frontier
                if key[0] == neighbor
            }
            seed_targets.setdefault(seed, set()).update(edge_targets)
            if required_key in edge_targets:
                matching_seeds.add(seed)
        if not matching_seeds:
            raise DA082Error("Required target has no frozen baseline edge")
        represented = sorted(seed for seed in matching_seeds if seed in prompt_episodes)
        represented_degrees = [len(seed_targets[seed]) for seed in represented]
        unary = [seed for seed in represented if len(seed_targets[seed]) == 1]
        if sibling_present:
            state = "PRESENT_SIBLING"
        elif unary:
            state = "UNARY_PRESENT_SEED"
        else:
            state = "BRANCH_AMBIGUOUS"
        rows.append({
            "key": question_id,
            "question_type": record.question_type,
            "blocker": str(residual["blocker"]),
            "carrier": required_key[0],
            "required_member": required_key[1],
            "state": state,
            "sibling_present": sibling_present,
            "matching_seed_count": len(matching_seeds),
            "represented_matching_seed_count": len(represented),
            "unary_represented_seed_count": len(unary),
            "min_represented_branch_degree": min(represented_degrees) if represented_degrees else None,
            "max_represented_branch_degree": max(represented_degrees) if represented_degrees else None,
        })

    states = Counter(row["state"] for row in rows)
    represented_degrees = [
        row["min_represented_branch_degree"] for row in rows
        if row["min_represented_branch_degree"] is not None
    ]
    result = {
        "schema": "da082-unary-dependency-edge-anatomy-v1",
        "status": "POSTHOC_UNARY_DEPENDENCY_EDGES_CHARACTERIZED",
        "residuals": len(rows),
        "states": dict(states),
        "matching_seed_count": distribution([row["matching_seed_count"] for row in rows]),
        "represented_matching_seed_count": distribution([
            row["represented_matching_seed_count"] for row in rows
        ]),
        "min_represented_branch_degree": distribution(represented_degrees),
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "posthoc sibling/unary-edge anatomy only; no reader, stopping, transfer, delivery, or adoption",
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
    artifact = output_dir / "edges.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da082-") as directory:
        replay_result, replay_rows = analyze(
            longmem_path, population_path, da079_path, da078_path, da045_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["edges_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA082Error("DA-082 replay differs")
    return result


__all__ = ["DA082Error", "analyze", "run_analysis"]
