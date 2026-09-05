"""Exact one-source-node child stream transformation for DA-095."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da023_backrefs import Backref, EncodedMember
from analysis.da032_audit import distribution
from analysis.da078_allocation import _protected_descriptors
from analysis.da078_optimal_sentinel import _append_literal
from analysis.da093_prompt_relative_stream import PromptIndex, packet_costs, parse_serialized, serialize
from analysis.da034_sentinel_backrefs import decode_members

DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
DA091_SHA256 = "f6960dfb303bf11c46c6101faa8eddc15f1f5b78d58efa1044d512a9bcd02aae"
DA093_SHA256 = "157b766f1734ab6d163a9a3359c768de6714d3793e5c16889e57b319f5779459"


class DA095Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def node_local(member: EncodedMember, history: Sequence[str]) -> tuple[EncodedMember, int]:
    totals: Counter[int] = Counter()
    for segment in member.segments:
        if isinstance(segment, Backref):
            totals[segment.member] += segment.length
    if not totals:
        raise DA095Error("DA-093 selected parse has no references")
    dominant = min(totals, key=lambda index: (-totals[index], index))
    output: list[str | Backref] = []
    for segment in member.segments:
        if not isinstance(segment, Backref) or segment.member == dominant:
            if isinstance(segment, str):
                _append_literal(output, segment)
            else:
                output.append(segment)
            continue
        source = history[segment.member]
        _append_literal(output, source[segment.start:segment.start + segment.length])
    return EncodedMember(tuple(output)), dominant


def analyze(longmem_path: Path, population_path: Path, da078_path: Path,
            da091_path: Path, da093_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (
        sha256_file(da078_path) != DA078_SHA256
        or sha256_file(da091_path) != DA091_SHA256
        or sha256_file(da093_path) != DA093_SHA256
    ):
        raise DA095Error("Sealed input differs")
    selections = {str(row["question_id"]): row for row in _read(da078_path)}
    literals = {
        (str(row["question_id"]), int(row["target_position"])): row
        for row in _read(da091_path)
    }
    source = [row for row in _read(da093_path) if row["prompt_relative_selected"]]
    wanted = {str(row["question_id"]) for row in source}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in wanted
    }
    if len(source) != 3_499 or len(records) != 455 or len(literals) != 8_055:
        raise DA095Error("Node-local population differs")

    state: dict[str, tuple[dict[str, Any], PromptIndex]] = {}
    rows: list[dict[str, Any]] = []
    savings_fractions: list[float] = []
    retention_fractions: list[float] = []
    selected_pointer_counts: list[int] = []
    selected = 0
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
        source_member = by_id[target_id].members[member_index]
        text, speaker = str(source_member["text"]), str(source_member["speaker"])
        optimal = index.encode(text)
        local, dominant = node_local(optimal, index.history)
        referenced_sources = {
            segment.member for segment in local.segments if isinstance(segment, Backref)
        }
        if referenced_sources != {dominant}:
            raise DA095Error("Node-local parse references more than one source")
        encoded = serialize(local, index.sentinel, len(index.history))
        parsed = parse_serialized(encoded, index.sentinel, len(index.history))
        if parsed != local or decode_members((parsed,), index.history, index.sentinel) != (text,):
            raise DA095Error("Node-local exact decode differs")
        costs = packet_costs(encoded, speaker)
        cumulative, peak = sum(costs), max(costs)
        literal = literals[(question_id, int(control["target_position"]))]
        literal_cumulative = int(literal["cumulative_frame_chars"])
        literal_peak = int(literal["peak_frame_chars"])
        choose = cumulative < literal_cumulative and peak <= literal_peak
        if not choose:
            rows.append({
                "question_id": question_id,
                "target_position": int(control["target_position"]),
                "selected": False,
                "literal_cumulative_chars": literal_cumulative,
            })
            continue
        selected += 1
        saving = literal_cumulative - cumulative
        da093_saving = literal_cumulative - int(control["cumulative_frame_chars"])
        pointer_count = sum(isinstance(segment, Backref) for segment in local.segments)
        selected_pointer_counts.append(pointer_count)
        savings_fractions.append(saving / literal_cumulative)
        retention_fractions.append(saving / da093_saving)
        rows.append({
            "question_id": question_id,
            "target_position": int(control["target_position"]),
            "neighbor_id": target_id,
            "member": member_index,
            "selected": True,
            "dominant_history_member": dominant,
            "pointer_count": pointer_count,
            "literal_cumulative_chars": literal_cumulative,
            "node_local_cumulative_chars": cumulative,
            "node_local_peak_chars": peak,
            "saved_cumulative_chars": saving,
            "da093_capacity_retention": saving / da093_saving,
        })

    if len(rows) != 3_499:
        raise DA095Error("Node-local row count differs")
    rate = selected / len(rows)
    median_saving = distribution(savings_fractions)["p50"] if savings_fractions else 0.0
    result = {
        "schema": "da095-exact-node-local-child-stream-v1",
        "status": (
            "NODE_LOCAL_CHILD_CAPACITY_SIGNAL"
            if rate >= 0.20 and median_saving >= 0.05
            else "NO_NODE_LOCAL_CHILD_CAPACITY_SIGNAL"
        ),
        "eligible": len(rows),
        "selected": selected,
        "selection_rate": rate,
        "selected_savings_fraction_vs_da091": distribution(savings_fractions),
        "da093_capacity_retention": distribution(retention_fractions),
        "selected_pointer_count": distribution(selected_pointer_counts),
        "max_referenced_members": 1,
        "exact_decode": True,
        "protected_mutations": {"da078": 0, "da091": 0, "da093": 0},
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "exact node-local representation only; no reader, delivery, runtime, or adoption claim",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(longmem_path: Path, population_path: Path, da078_path: Path,
                 da091_path: Path, da093_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da078_path, da091_path, da093_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "targets.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da095-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da078_path, da091_path, da093_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["targets_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA095Error("DA-095 replay differs")
    return result


__all__ = ["DA095Error", "analyze", "node_local", "run_analysis"]
