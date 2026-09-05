"""Exact content-addressed node reuse audit for DA-092."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da032_audit import distribution

DA091_SHA256 = "f6960dfb303bf11c46c6101faa8eddc15f1f5b78d58efa1044d512a9bcd02aae"


class DA092Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def node_key(speaker: str, text: str) -> str:
    return hashlib.sha256(speaker.encode() + b"\0" + text.encode()).hexdigest()


def analyze(longmem_path: Path, population_path: Path,
            da091_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da091_path) != DA091_SHA256:
        raise DA092Error("Sealed DA-091 targets differ")
    controls = _read(da091_path)
    wanted = {str(row["question_id"]) for row in controls}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in wanted
    }
    if len(controls) != 8_055 or len(records) != 461:
        raise DA092Error("Content-node population differs")

    canonical: dict[str, tuple[str, str]] = {}
    references: Counter[str] = Counter()
    questions: dict[str, set[str]] = defaultdict(set)
    route_refs: Counter[str] = Counter()
    route_nodes: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    repeated_chars = 0
    for control in controls:
        question_id = str(control["question_id"])
        episodes = {
            episode.candidate.identity: episode
            for episode in records[question_id].episodes
        }
        target_id = str(control["neighbor_id"])
        member_index = int(control["member"])
        member = episodes[target_id].members[member_index]
        speaker, text = str(member["speaker"]), str(member["text"])
        key = node_key(speaker, text)
        value = (speaker, text)
        if key in canonical and canonical[key] != value:
            raise DA092Error("Content-address collision")
        canonical[key] = value
        references[key] += 1
        questions[key].add(question_id)
        route = str(control["route"])
        route_refs[route] += 1
        route_nodes[route].add(key)
        repeated_chars += len(text)
        rows.append({
            "question_id": question_id,
            "target_position": int(control["target_position"]),
            "neighbor_id": target_id,
            "member": member_index,
            "parent_id": str(control["parent_id"]),
            "direction": int(control["direction"]),
            "route": route,
            "node_key": key,
            "speaker": speaker,
            "source_chars": len(text),
        })

    unique_chars = sum(len(text) for _, text in canonical.values())
    unique_nodes = len(canonical)
    reuse = len(rows) - unique_nodes
    if any(node_key(*canonical[key]) != key for key in canonical):
        raise DA092Error("Exact node resolution differs")
    route_summary = {
        route: {
            "references": route_refs[route],
            "unique_nodes_within_route": len(route_nodes[route]),
            "reused_references_within_route": route_refs[route] - len(route_nodes[route]),
        }
        for route in sorted(route_refs)
    }
    result = {
        "schema": "da092-content-addressed-node-reuse-v1",
        "status": (
            "CONTENT_ADDRESSED_NODE_REUSE_SIGNAL"
            if reuse / len(rows) >= 0.10 else "NO_CONTENT_ADDRESSED_NODE_REUSE_SIGNAL"
        ),
        "references": len(rows),
        "unique_nodes": unique_nodes,
        "reused_references": reuse,
        "reuse_fraction": reuse / len(rows),
        "repeated_source_chars": repeated_chars,
        "unique_source_chars": unique_chars,
        "avoidable_duplicate_store_chars": repeated_chars - unique_chars,
        "store_char_reduction_fraction": (repeated_chars - unique_chars) / repeated_chars,
        "references_per_node": distribution(list(references.values())),
        "questions_per_node": distribution([len(value) for value in questions.values()]),
        "max_references_per_node": max(references.values()),
        "route_reuse": route_summary,
        "exact_collision_count": 0,
        "da091_row_mutations": 0,
        "per_question_exposure_change": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "shared exact-node storage only; no prompt, reader, runtime, delivery, or adoption claim",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                output.write(payload.encode())


def run_analysis(longmem_path: Path, population_path: Path,
                 da091_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da091_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "references.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da092-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da091_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["references_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not identical:
        raise DA092Error("DA-092 replay differs")
    return result


__all__ = ["DA092Error", "analyze", "node_key", "run_analysis"]
