"""Blind protected retained-set contract for DA-052."""

from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

STREAM_SEALS = {
    "ONE_HOP": "ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a",
    "DISTANCE_2": "8ea82cc737b65bf457e05bf921043907d70f0f82f0e878b340ab6c7f04c41bd3",
    "DISTANCE_3_5": "40c8b768e80c8b0c80e1b310f7abe3e2f3cc6066362f6b59a8aa436bfcfae490",
}
FRAME_CAP = 2_048
RETAINED_SLOTS = 5
RETAINED_CAP = FRAME_CAP * RETAINED_SLOTS
GENERAL_CAP = RETAINED_CAP + FRAME_CAP


class DA052Error(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame(action: Mapping[str, Any]) -> str | None:
    if str(action.get("kind")) == "OVERFLOW":
        return None
    if str(action.get("kind")) != "FRAME":
        raise DA052Error("Unknown stream action")
    block = action.get("block")
    if not isinstance(block, str) or len(block) != int(action.get("cost", -1)):
        raise DA052Error("Malformed frame")
    if len(block) > FRAME_CAP or hashlib.sha256(block.encode()).hexdigest() != action.get("block_sha256"):
        raise DA052Error("Frame integrity differs")
    return block


@dataclass
class RetainedSetMachine:
    current: str | None = None
    retained: list[str] = field(default_factory=list)
    peak_chars: int = 0

    def _measure(self) -> None:
        retained_chars = sum(map(len, self.retained))
        current_chars = len(self.current) if self.current is not None else 0
        if len(self.retained) > RETAINED_SLOTS or retained_chars > RETAINED_CAP:
            raise DA052Error("Retained-set cap exceeded")
        self.peak_chars = max(self.peak_chars, retained_chars + current_chars)
        if self.peak_chars > GENERAL_CAP:
            raise DA052Error("General auxiliary cap exceeded")

    def next(self, action: Mapping[str, Any]) -> None:
        self.current = _frame(action)
        self._measure()

    def keep(self) -> bool:
        if self.current is None or self.current in self.retained or len(self.retained) >= RETAINED_SLOTS:
            return False
        previous = list(self.retained)
        try:
            self.retained.append(self.current)
            self.current = None
            self._measure()
        except DA052Error:
            self.retained = previous
            raise
        return True


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _digest(actions: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_rows(paths: Mapping[str, Path]) -> list[dict[str, Any]]:
    if set(paths) != set(STREAM_SEALS) or any(sha256_file(paths[name]) != seal
                                               for name, seal in STREAM_SEALS.items()):
        raise DA052Error("Sealed stream differs")
    streams = {name: {str(row["question_id"]): row for row in _read(path)}
               for name, path in paths.items()}
    question_ids = sorted(streams["ONE_HOP"])
    if len(question_ids) != 465 or any(set(stream) != set(question_ids) for stream in streams.values()):
        raise DA052Error("Combined stream join differs")
    output = []
    for question_id in question_ids:
        actions = {
            "ONE_HOP": streams["ONE_HOP"][question_id]["treatment"]["actions"],
            "DISTANCE_2": streams["DISTANCE_2"][question_id]["actions"],
            "DISTANCE_3_5": streams["DISTANCE_3_5"][question_id]["actions"],
        }
        output.append({"question_id": question_id, "stream_order": list(STREAM_SEALS),
                       "stream_action_sha256": {name: _digest(actions[name]) for name in STREAM_SEALS},
                       "stream_action_count": {name: len(actions[name]) for name in STREAM_SEALS},
                       "frame_cap": FRAME_CAP, "retained_slots": RETAINED_SLOTS,
                       "retained_cap": RETAINED_CAP, "general_cap": GENERAL_CAP})
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
            for row in rows:
                handle.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def _exercise(paths: Mapping[str, Path]) -> dict[str, Any]:
    all_actions = [action for row in _read(paths["DISTANCE_2"]) for action in row["actions"]]
    frames = [action for action in all_actions if action["kind"] == "FRAME"]
    overflow = next(action for action in all_actions if action["kind"] == "OVERFLOW")
    machine = RetainedSetMachine()
    empty_rejected = not machine.keep()
    for action in frames[:5]:
        machine.next(action)
        if not machine.keep():
            raise DA052Error("Valid retained slot rejected")
    retained = list(machine.retained)
    machine.next(frames[0])
    duplicate_rejected = not machine.keep() and machine.retained == retained
    machine.next(frames[5])
    full_rejected = not machine.keep() and machine.retained == retained
    machine.next(overflow)
    overflow_rejected = not machine.keep() and machine.retained == retained
    return {"empty_rejected": empty_rejected, "duplicate_rejected": duplicate_rejected,
            "full_rejected": full_rejected, "overflow_rejected": overflow_rejected,
            "retained_survives_later_actions": machine.retained == retained,
            "retained_slots": len(machine.retained), "peak_chars": machine.peak_chars}


def run_preflight(paths: Mapping[str, Path], output_dir: Path) -> dict[str, Any]:
    rows = build_rows(paths)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "blind_contracts.jsonl.gz"
    _write(artifact, rows)
    with tempfile.TemporaryDirectory(prefix="da052-") as directory:
        replay = Path(directory) / artifact.name
        _write(replay, build_rows(paths))
        identical = artifact.read_bytes() == replay.read_bytes()
    exercise = _exercise(paths)
    passed = (identical and all(exercise[name] for name in
              ("empty_rejected", "duplicate_rejected", "full_rejected", "overflow_rejected",
               "retained_survives_later_actions")) and exercise["peak_chars"] <= GENERAL_CAP)
    result = {"schema": "da052-protected-retained-set-preflight-v1",
              "status": "PASS" if passed else "FAIL", "questions": len(rows),
              "stream_order": list(STREAM_SEALS), "retained_slots": RETAINED_SLOTS,
              "frame_cap": FRAME_CAP, "retained_cap": RETAINED_CAP,
              "general_cap": GENERAL_CAP, "transition_exercise": exercise,
              "immutable_payload_mutations": 0, "replay_byte_identical": identical,
              "contract_sha256": sha256_file(artifact),
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                                encoding="utf-8")
    if not passed:
        raise DA052Error("Blind contract failed")
    return result


__all__ = ["DA052Error", "RetainedSetMachine", "build_rows", "run_preflight"]
