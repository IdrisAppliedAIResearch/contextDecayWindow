"""One-time source binding with exact local span pointers for DA-096."""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da023_backrefs import Backref, EncodedMember
from analysis.da031_varint_backrefs import decode_uint, encode_uint
from analysis.da032_audit import distribution
from analysis.da034_sentinel_backrefs import decode_members
from analysis.da078_allocation import _protected_descriptors
from analysis.da078_optimal_sentinel import _append_literal
from analysis.da093_prompt_relative_stream import PromptIndex, packet_costs
from analysis.da095_node_local_stream import node_local

DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
DA093_SHA256 = "157b766f1734ab6d163a9a3359c768de6714d3793e5c16889e57b319f5779459"
DA095_SHA256 = "50c719e4d776262b852f0a778a5a0de81aa8517c54206371c3c62b622a0cceda"


class DA096Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def render_bound(member: EncodedMember, dominant: int, sentinel: str,
                 history_size: int) -> str:
    distance = history_size - dominant
    if not 1 <= distance <= history_size:
        raise DA096Error("Bound source is not strictly prior")
    chunks = [f"{sentinel}B{encode_uint(distance)}{sentinel}"]
    for segment in member.segments:
        if isinstance(segment, str):
            if sentinel in segment:
                raise DA096Error("Sentinel occurs in bound literal")
            chunks.append(segment)
            continue
        if segment.member != dominant:
            raise DA096Error("Bound stream references another source")
        chunks.append(
            f"{sentinel}{encode_uint(segment.start)}{encode_uint(segment.length)}{sentinel}"
        )
    return "".join(chunks)


def parse_bound(value: str, sentinel: str, history_size: int) -> tuple[EncodedMember, int]:
    opening = sentinel + "B"
    if not value.startswith(opening):
        raise DA096Error("Bound header missing")
    header_end = value.find(sentinel, len(opening))
    if header_end < 0:
        raise DA096Error("Bound header unterminated")
    distance, cursor = decode_uint(value[len(opening):header_end], 0)
    if cursor != header_end - len(opening) or not 1 <= distance <= history_size:
        raise DA096Error("Bound source header invalid")
    dominant = history_size - distance
    segments: list[str | Backref] = []
    position = header_end + len(sentinel)
    while position < len(value):
        start = value.find(sentinel, position)
        if start < 0:
            _append_literal(segments, value[position:])
            break
        if start > position:
            _append_literal(segments, value[position:start])
        end = value.find(sentinel, start + len(sentinel))
        if end < 0:
            raise DA096Error("Bound span unterminated")
        body = value[start + len(sentinel):end]
        offset, cursor = decode_uint(body, 0)
        length, cursor = decode_uint(body, cursor)
        if cursor != len(body) or length <= 0:
            raise DA096Error("Bound span invalid")
        segments.append(Backref(dominant, offset, length))
        position = end + len(sentinel)
    member = EncodedMember(tuple(segments))
    if render_bound(member, dominant, sentinel, history_size) != value:
        raise DA096Error("Bound wire form is noncanonical")
    return member, dominant


def analyze(longmem_path: Path, population_path: Path, da078_path: Path,
            da093_path: Path, da095_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (
        sha256_file(da078_path) != DA078_SHA256
        or sha256_file(da093_path) != DA093_SHA256
        or sha256_file(da095_path) != DA095_SHA256
    ):
        raise DA096Error("Sealed input differs")
    selections = {str(row["question_id"]): row for row in _read(da078_path)}
    source = [row for row in _read(da093_path) if row["prompt_relative_selected"]]
    controls = {
        (str(row["question_id"]), int(row["target_position"])): row
        for row in _read(da095_path)
    }
    wanted = {str(row["question_id"]) for row in source}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in wanted
    }
    if len(source) != 3_499 or len(controls) != 3_499 or len(records) != 455:
        raise DA096Error("Bound-node population differs")

    state: dict[str, tuple[dict[str, Any], PromptIndex]] = {}
    rows: list[dict[str, Any]] = []
    incremental_fractions: list[float] = []
    absolute_fractions: list[float] = []
    pointer_counts: list[int] = []
    selected = 0
    for source_row in source:
        question_id = str(source_row["question_id"])
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
        target_id = str(source_row["neighbor_id"])
        member_index = int(source_row["member"])
        source_member = by_id[target_id].members[member_index]
        text, speaker = str(source_member["text"]), str(source_member["speaker"])
        optimal = index.encode(text)
        local, dominant = node_local(optimal, index.history)
        wire = render_bound(local, dominant, index.sentinel, len(index.history))
        parsed, parsed_dominant = parse_bound(wire, index.sentinel, len(index.history))
        if (
            parsed != local
            or parsed_dominant != dominant
            or decode_members((parsed,), index.history, index.sentinel) != (text,)
        ):
            raise DA096Error("Bound-node exact decode differs")
        costs = packet_costs(wire, speaker)
        cumulative, peak = sum(costs), max(costs)
        key = (question_id, int(source_row["target_position"]))
        control = controls[key]
        if not control["selected"]:
            raise DA096Error("DA-095 control is not selected")
        control_cumulative = int(control["node_local_cumulative_chars"])
        control_peak = int(control["node_local_peak_chars"])
        choose = cumulative < control_cumulative and peak <= control_peak
        if not choose:
            rows.append({**control, "bound_selected": False})
            continue
        selected += 1
        incremental = control_cumulative - cumulative
        literal_cumulative = int(control["literal_cumulative_chars"])
        pointer_count = sum(isinstance(segment, Backref) for segment in local.segments)
        pointer_counts.append(pointer_count)
        incremental_fractions.append(incremental / control_cumulative)
        absolute_fractions.append((literal_cumulative - cumulative) / literal_cumulative)
        rows.append({
            **control,
            "bound_selected": True,
            "bound_source_member": dominant,
            "bound_pointer_count": pointer_count,
            "bound_cumulative_chars": cumulative,
            "bound_peak_chars": peak,
            "incremental_saved_chars": incremental,
        })

    if len(rows) != 3_499:
        raise DA096Error("Bound-node row count differs")
    rate = selected / len(rows)
    median_incremental = distribution(incremental_fractions)["p50"] if incremental_fractions else 0.0
    result = {
        "schema": "da096-bound-node-local-span-stream-v1",
        "status": (
            "BOUND_NODE_SPAN_CAPACITY_SIGNAL"
            if rate >= 0.90 and median_incremental >= 0.01
            else "NO_BOUND_NODE_SPAN_CAPACITY_SIGNAL"
        ),
        "eligible": len(rows),
        "selected": selected,
        "selection_rate": rate,
        "incremental_savings_fraction_vs_da095": distribution(incremental_fractions),
        "absolute_savings_fraction_vs_da091": distribution(absolute_fractions),
        "bound_pointer_count": distribution(pointer_counts),
        "bound_sources_per_child": 1,
        "exact_decode": True,
        "protected_mutations": {"da078": 0, "da091": 0, "da093": 0, "da095": 0},
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "exact bound-node span representation only; no reader, delivery, runtime, or adoption claim",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(longmem_path: Path, population_path: Path, da078_path: Path,
                 da093_path: Path, da095_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da078_path, da093_path, da095_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "targets.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da096-") as directory:
        replay_result, replay_rows = analyze(
            longmem_path, population_path, da078_path, da093_path, da095_path
        )
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["targets_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA096Error("DA-096 replay differs")
    return result


__all__ = ["DA096Error", "analyze", "parse_bound", "render_bound", "run_analysis"]
