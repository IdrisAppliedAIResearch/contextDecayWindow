"""Prompt-relative exact child packet streams for DA-093."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da013_preflight import load_blind_population, sha256_file
from analysis.da023_backrefs import Backref, EncodedMember
from analysis.da031_varint_backrefs import encode_uint
from analysis.da032_audit import distribution
from analysis.da034_sentinel_backrefs import decode_members, parse_reference, reference_code
from analysis.da078_allocation import _protected_descriptors
from analysis.da078_optimal_sentinel import _RangeMinimum, _append_literal, _span_buckets

DA078_SHA256 = "e1e0aa2674dc103e2e6b03d7ddf81b4daf2f600cb5eb9950809b6d7a2e7e96cd"
DA091_SHA256 = "f6960dfb303bf11c46c6101faa8eddc15f1f5b78d58efa1044d512a9bcd02aae"
ELIGIBLE = {"CHILD_PACKET_STREAM", "TYPED_EDGE_CHILD_PACKET_STREAM"}
FRAME_CAP = 2_048
CHUNK_CHARS = 1_800
_INF = (10**18, 0)


class DA093Error(RuntimeError):
    pass


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


class PromptIndex:
    """Reusable immutable-history index with DA-078's exact DP and tie order."""

    def __init__(self, history: Sequence[str], sentinel: str) -> None:
        if any(sentinel in text for text in history):
            raise DA093Error("Sentinel occurs in immutable history")
        self.history = tuple(history)
        self.sentinel = sentinel
        self.index: dict[str, list[tuple[int, int]]] = {}
        for member_index, source in enumerate(history):
            for start in range(max(0, len(source) - 3)):
                self.index.setdefault(source[start:start + 4], []).append((member_index, start))

    def encode(self, text: str) -> EncodedMember:
        if self.sentinel in text:
            raise DA093Error("Sentinel occurs in child")
        size = len(text)
        costs = [0] * (size + 1)
        choices: list[tuple[str, Backref | None, int] | None] = [None] * size
        ranges = _RangeMinimum(size + 1)
        ranges.update(size, (0, -size))
        history_size = len(self.history)
        for position in range(size - 1, -1, -1):
            best_cost = 1 + costs[position + 1]
            best_key = (0, 0, 0, 0)
            best_choice: tuple[str, Backref | None, int] = ("LITERAL", None, 1)
            candidates = self.index.get(text[position:position + 4], ()) if position + 4 <= size else ()
            for member_index, start in candidates:
                source = self.history[member_index]
                limit = min(size - position, len(source) - start)
                length = 4
                while length < limit and text[position + length] == source[start + length]:
                    length += 1
                for lower, upper in _span_buckets(length):
                    downstream, negative_endpoint = ranges.query(position + lower, position + upper + 1)
                    span = -negative_endpoint - position
                    ref = Backref(member_index, start, span)
                    candidate_cost = len(reference_code(self.sentinel, ref, history_size)) + downstream
                    key = (1, member_index, start, -span)
                    if candidate_cost < best_cost or (candidate_cost == best_cost and key < best_key):
                        best_cost = candidate_cost
                        best_key = key
                        best_choice = ("REFERENCE", ref, span)
            costs[position] = best_cost
            choices[position] = best_choice
            ranges.update(position, (best_cost, -position))
        segments: list[str | Backref] = []
        position = 0
        while position < size:
            choice = choices[position]
            if choice is None:
                raise DA093Error("Optimal child parse is incomplete")
            kind, ref, width = choice
            if kind == "LITERAL":
                _append_literal(segments, text[position])
            else:
                if ref is None:
                    raise DA093Error("Reference choice is missing")
                segments.append(ref)
            position += width
        return EncodedMember(tuple(segments))


def serialize(member: EncodedMember, sentinel: str, history_size: int) -> str:
    return "".join(
        segment if isinstance(segment, str) else reference_code(sentinel, segment, history_size)
        for segment in member.segments
    )


def parse_serialized(value: str, sentinel: str, history_size: int) -> EncodedMember:
    segments: list[str | Backref] = []
    position = 0
    while position < len(value):
        opening = value.find(sentinel, position)
        if opening < 0:
            _append_literal(segments, value[position:])
            break
        if opening > position:
            _append_literal(segments, value[position:opening])
        closing = value.find(sentinel, opening + len(sentinel))
        if closing < 0:
            raise DA093Error("Unterminated serialized reference")
        code = value[opening:closing + len(sentinel)]
        segments.append(parse_reference(code, sentinel, history_size))
        position = closing + len(sentinel)
    return EncodedMember(tuple(segments))


def packet_costs(encoded: str, speaker: str) -> list[int]:
    delimiter = "^"
    while delimiter in encoded:
        delimiter += "^"
    chunks = [encoded[start:start + CHUNK_CHARS] for start in range(0, len(encoded), CHUNK_CHARS)] or [""]
    costs = []
    decoded = []
    for index, chunk in enumerate(chunks, start=1):
        block = f"{delimiter}E{encode_uint(index)}{encode_uint(len(chunks))}{delimiter}{speaker}: {chunk}"
        if len(block) > FRAME_CAP:
            raise DA093Error("Encoded packet exceeds frame cap")
        end = block.find(delimiter, len(delimiter) + 1)
        body = block[end + len(delimiter):]
        parsed_speaker, parsed_chunk = body.split(": ", 1)
        if parsed_speaker != speaker:
            raise DA093Error("Encoded packet speaker differs")
        decoded.append(parsed_chunk)
        costs.append(len(block))
    if "".join(decoded) != encoded:
        raise DA093Error("Encoded packet reassembly differs")
    return costs


def analyze(longmem_path: Path, population_path: Path, da078_path: Path,
            da091_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(da078_path) != DA078_SHA256 or sha256_file(da091_path) != DA091_SHA256:
        raise DA093Error("Sealed input differs")
    selections = {str(row["question_id"]): row for row in _read(da078_path)}
    controls = _read(da091_path)
    wanted = {str(row["question_id"]) for row in controls}
    records = {
        record.question_id: record
        for record in load_blind_population(longmem_path, population_path)
        if record.question_id in wanted
    }
    if len(selections) != 465 or len(controls) != 8_055 or len(records) != 461:
        raise DA093Error("Prompt-relative population differs")

    state: dict[str, tuple[dict[str, Any], PromptIndex, dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    selected_savings: list[int] = []
    eligible = selected = 0
    for control in controls:
        route = str(control["route"])
        if route not in ELIGIBLE:
            rows.append({**control, "prompt_relative_selected": False})
            continue
        eligible += 1
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
            index = PromptIndex(history, str(selection["treatment"]["sentinel"]))
            state[question_id] = (by_id, index, selection)
        by_id, index, _ = state[question_id]
        target_id = str(control["neighbor_id"])
        member_index = int(control["member"])
        source = by_id[target_id].members[member_index]
        text, speaker = str(source["text"]), str(source["speaker"])
        encoded_member = index.encode(text)
        encoded = serialize(encoded_member, index.sentinel, len(index.history))
        parsed = parse_serialized(encoded, index.sentinel, len(index.history))
        if parsed != encoded_member or decode_members((parsed,), index.history, index.sentinel) != (text,):
            raise DA093Error("Prompt-relative exact decode differs")
        costs = packet_costs(encoded, speaker)
        cumulative, peak = sum(costs), max(costs)
        control_cumulative = int(control["cumulative_frame_chars"])
        control_peak = int(control["peak_frame_chars"])
        choose = cumulative < control_cumulative and peak <= control_peak
        if not choose:
            rows.append({**control, "prompt_relative_selected": False})
            continue
        selected += 1
        saving = control_cumulative - cumulative
        selected_savings.append(saving / control_cumulative)
        rows.append({
            **control,
            "route": "PROMPT_RELATIVE_EXACT_CHILD_STREAM",
            "frames": len(costs),
            "peak_frame_chars": peak,
            "cumulative_frame_chars": cumulative,
            "prompt_relative_selected": True,
            "encoded_chars": len(encoded),
            "saved_cumulative_chars": saving,
        })
    if eligible != 3_499 or len(rows) != len(controls):
        raise DA093Error("Eligible child-stream count differs")
    selection_rate = selected / eligible
    median_fraction = distribution(selected_savings)["p50"] if selected_savings else 0.0
    result = {
        "schema": "da093-prompt-relative-exact-child-stream-v1",
        "status": (
            "PROMPT_RELATIVE_CHILD_CAPACITY_SIGNAL"
            if selection_rate >= 0.20 and median_fraction >= 0.10
            else "NO_PROMPT_RELATIVE_CHILD_CAPACITY_SIGNAL"
        ),
        "targets": len(rows),
        "eligible": eligible,
        "selected": selected,
        "selection_rate": selection_rate,
        "selected_savings_fraction": distribution(selected_savings),
        "selected_frames": distribution([row["frames"] for row in rows if row["prompt_relative_selected"]]),
        "selected_peak_frame_chars": distribution([row["peak_frame_chars"] for row in rows if row["prompt_relative_selected"]]),
        "selected_cumulative_frame_chars": distribution([row["cumulative_frame_chars"] for row in rows if row["prompt_relative_selected"]]),
        "preserved_noneligible": len(rows) - eligible,
        "protected_da078_mutations": 0,
        "calls": {"embedding": 0, "model": 0, "cache_access": 0},
        "claim_boundary": "reversible prompt-relative representation only; reader use and delivery untested",
    }
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(longmem_path: Path, population_path: Path, da078_path: Path,
                 da091_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(longmem_path, population_path, da078_path, da091_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "targets.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da093-") as directory:
        replay_result, replay_rows = analyze(longmem_path, population_path, da078_path, da091_path)
        replay = Path(directory) / artifact.name
        _write(replay, replay_rows)
        identical = result == replay_result and artifact.read_bytes() == replay.read_bytes()
    result["replay_byte_identical"] = identical
    result["targets_sha256"] = sha256_file(artifact)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA093Error("DA-093 replay differs")
    return result


__all__ = ["DA093Error", "PromptIndex", "analyze", "parse_serialized", "run_analysis", "serialize"]
