"""Blind single-retained-frame state-machine contract for DA-046."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import sha256_file

STREAM_SHA256 = "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a"
REGISTER_CAP = 2_048
GENERAL_PEAK_CAP = 4_096


class DA046Error(RuntimeError):
    pass


@dataclass
class RegisterMachine:
    current: str | None = None
    retained: str | None = None
    peak_chars: int = 0

    def _measure(self) -> None:
        current = len(self.current) if self.current is not None else 0
        retained = len(self.retained) if self.retained is not None else 0
        if current > REGISTER_CAP or retained > REGISTER_CAP:
            raise DA046Error("Register cap exceeded")
        self.peak_chars = max(self.peak_chars, current + retained)
        if self.peak_chars > GENERAL_PEAK_CAP:
            raise DA046Error("General peak cap exceeded")

    def next(self, action: Mapping[str, Any]) -> None:
        kind = str(action["kind"])
        if kind == "FRAME":
            block = action.get("block")
            if not isinstance(block, str) or len(block) != int(action["cost"]):
                raise DA046Error("Invalid current frame")
            self.current = block
        elif kind == "OVERFLOW":
            self.current = None
        else:
            raise DA046Error("Unknown stream action")
        self._measure()

    def keep(self) -> None:
        if self.current is None:
            raise DA046Error("KEEP requires a current frame")
        self.retained = self.current
        self.current = None
        self._measure()

    def answer(self) -> str | None:
        return self.retained


def _action_digest(actions: Sequence[Mapping[str, Any]]) -> str:
    encoded = json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_rows(stream_path: Path) -> list[dict[str, Any]]:
    if sha256_file(stream_path) != STREAM_SHA256:
        raise DA046Error("DA-045 stream artifact differs")
    output = []
    for row in read_gzip(stream_path):
        actions = row["treatment"]["actions"]
        transitions = [{"ordinal": int(action["ordinal"]),
                        "next": "CURRENT_FRAME" if action["kind"] == "FRAME" else "CURRENT_EMPTY",
                        "keep": "ALLOWED" if action["kind"] == "FRAME" else "REJECTED",
                        "frame_chars": int(action["cost"]),
                        "block_sha256": str(action["block_sha256"])} for action in actions]
        output.append({"question_id": str(row["question_id"]),
                       "immutable_prompt_chars": int(row["treatment"]["immutable_prompt_chars"]),
                       "immutable_order_sha256": str(row["treatment"]["immutable_order_sha256"]),
                       "stream_depth": int(row["treatment"]["stream_depth"]),
                       "frame_cap": REGISTER_CAP, "retained_cap": REGISTER_CAP,
                       "general_peak_cap": GENERAL_PEAK_CAP,
                       "stream_actions_sha256": _action_digest(actions),
                       "transitions": transitions})
    if len(output) != 465:
        raise DA046Error("DA-046 population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def _exercise(streams: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    frame = next(action for row in streams for action in row["treatment"]["actions"]
                 if action["kind"] == "FRAME")
    overflow = next(action for row in streams for action in row["treatment"]["actions"]
                    if action["kind"] == "OVERFLOW")
    another = next(action for row in streams for action in row["treatment"]["actions"]
                   if action["kind"] == "FRAME" and action["block_sha256"] != frame["block_sha256"])
    machine = RegisterMachine()
    empty_keep_rejected = False
    try:
        machine.keep()
    except DA046Error:
        empty_keep_rejected = True
    machine.next(frame)
    machine.keep()
    retained = machine.answer()
    machine.next(overflow)
    overflow_keep_rejected = False
    try:
        machine.keep()
    except DA046Error:
        overflow_keep_rejected = True
    retained_survives_overflow = machine.answer() == retained
    machine.next(another)
    retained_survives_next = machine.answer() == retained
    return {"empty_keep_rejected": empty_keep_rejected,
            "overflow_keep_rejected": overflow_keep_rejected,
            "retained_survives_overflow": retained_survives_overflow,
            "retained_survives_next": retained_survives_next,
            "general_peak_chars": machine.peak_chars}


def run_preflight(stream_path: Path, output_dir: Path) -> dict[str, Any]:
    streams = list(read_gzip(stream_path))
    rows = build_rows(stream_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_contracts.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da046-") as directory:
        replay = Path(directory) / path.name
        _write(replay, build_rows(stream_path))
        identical = path.read_bytes() == replay.read_bytes()
    exercise = _exercise(streams)
    hashes_match = all(contract["stream_actions_sha256"] == _action_digest(stream["treatment"]["actions"])
                       for contract, stream in zip(rows, streams, strict=True))
    prompt_immutable = all(contract["immutable_prompt_chars"] == stream["da038_control"]["final_chars"]
                           for contract, stream in zip(rows, streams, strict=True))
    passed = (identical and hashes_match and prompt_immutable and all(
        exercise[name] for name in ("empty_keep_rejected", "overflow_keep_rejected",
                                    "retained_survives_overflow", "retained_survives_next"))
        and exercise["general_peak_chars"] <= GENERAL_PEAK_CAP)
    result = {"schema": "da046-single-retained-frame-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "stream_hashes_match": hashes_match, "immutable_da038": prompt_immutable,
              "register_cap": REGISTER_CAP, "general_peak_cap": GENERAL_PEAK_CAP,
              "transition_exercise": exercise, "replay_byte_identical": identical,
              "contract_sha256": sha256_file(path),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise DA046Error("DA-046 blind contract failed")
    return result


__all__ = ["DA046Error", "RegisterMachine", "build_rows", "run_preflight"]
