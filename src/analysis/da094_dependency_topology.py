"""Reference fragmentation and prompt-node locality audit for DA-094."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da023_backrefs import Backref
from analysis.da032_audit import distribution
from analysis.da078_allocation import _protected_descriptors
from analysis.da093_prompt_relative_stream import PromptIndex

DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
DA093_SHA256 = "157b766f1734ab6d163a9a3359c768de6714d3793e5c16889e57b319f5779459"


class DA094Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def analyze(longmem_path: Path, population_path: Path, da078_path: Path,
            da093_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da078_path) != DA078_SHA256 or sha256_file(da093_path) != DA093_SHA256:
        raise DA094Error("Sealed input differs")
    selections = {str(row["question_id"]): row for row in _read(da078_path)}
    source = [row for row in _read(da093_path) if row["prompt_relative_selected"]]
    wanted = {str(row["question_id"]) for row in source}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in wanted
    }
    if len(source) != 3_499 or len(records) != 455 or len(selections) != 465:
        raise DA094Error("Topology population differs")

    state: dict[str, tuple[dict[str, Any], PromptIndex]] = {}
    rows: list[dict[str, Any]] = []
    all_distances: list[int] = []
    for control in source:
        question_id = str(control["question_id"])
        if question_id not in state:
            record = records[question_id]
            by_id = {episode.candidate.identity: episode for episode in record.episodes}
            pair_for = lambda identity, mapping=by_id: mapping[identity].members
            selection = selections[question_id]
            da038_row = {**selection, "treatment": selection["da038_control"]}
            descriptors = _protected_descriptors(da038_row, pair_for)
            for action in selection["treatment"]["actions"]:
                if action["kind"] == "MEMBER":
                    descriptors.append((str(action["neighbor_id"]), (int(action["member"]),)))
            history = [
                str(pair_for(identity)[index]["text"])
                for identity, members in descriptors for index in members
            ]
            state[question_id] = (
                by_id,
                PromptIndex(history, str(selection["treatment"]["sentinel"])),
            )
        by_id, index = state[question_id]
        target_id = str(control["neighbor_id"])
        member_index = int(control["member"])
        text = str(by_id[target_id].members[member_index]["text"])
        encoded = index.encode(text)
        refs = [segment for segment in encoded.segments if isinstance(segment, Backref)]
        literals = [segment for segment in encoded.segments if isinstance(segment, str)]
        if not refs:
            raise DA094Error("Selected DA-093 row has no references")
        by_source: Counter[int] = Counter()
        for ref in refs:
            by_source[ref.member] += ref.length
            all_distances.append(len(index.history) - ref.member)
        referenced = sum(ref.length for ref in refs)
        literal = sum(len(value) for value in literals)
        if referenced + literal != len(text):
            raise DA094Error("Topology accounting differs from source")
        rows.append({
            "question_id": question_id,
            "target_position": int(control["target_position"]),
            "neighbor_id": target_id,
            "member": member_index,
            "fallback": str(control["fallback"]),
            "source_chars": len(text),
            "pointer_count": len(refs),
            "unique_source_members": len(by_source),
            "referenced_chars": referenced,
            "literal_chars": literal,
            "reference_coverage": referenced / len(text) if text else 0.0,
            "largest_source_share": max(by_source.values()) / referenced,
            "pointer_distance_p50": distribution([
                len(index.history) - ref.member for ref in refs
            ])["p50"],
        })

    if len(rows) != 3_499:
        raise DA094Error("Topology row count differs")

    def metrics(cell: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "rows": len(cell),
            "pointer_count": distribution([row["pointer_count"] for row in cell]),
            "unique_source_members": distribution([row["unique_source_members"] for row in cell]),
            "reference_coverage": distribution([row["reference_coverage"] for row in cell]),
            "largest_source_share": distribution([row["largest_source_share"] for row in cell]),
        }

    overall = metrics(rows)
    coherent = (
        overall["unique_source_members"]["p50"] <= 4
        and overall["unique_source_members"]["p90"] <= 8
        and overall["pointer_count"]["p50"] <= 16
        and overall["largest_source_share"]["p50"] >= 0.50
    )
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cells[str(row["fallback"])].append(row)
    result = {
        "schema": "da094-prompt-dependency-topology-v1",
        "status": (
            "COHERENT_PROMPT_DEPENDENCY_TOPOLOGY"
            if coherent else "FRAGMENTED_PROMPT_DEPENDENCY_TOPOLOGY"
        ),
        "targets": len(rows),
        "overall": overall,
        "pointer_distance": distribution(all_distances),
        "route_cells": {key: metrics(value) for key, value in sorted(cells.items())},
        "exact_accounting": True,
        "da093_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "blind exact dependency topology only; no reader, delivery, runtime, or adoption claim",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(longmem_path: Path, population_path: Path, da078_path: Path,
                 da093_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da078_path, da093_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "topology.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da094-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da078_path, da093_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["topology_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA094Error("DA-094 replay differs")
    return result


__all__ = ["DA094Error", "analyze", "run_analysis"]
