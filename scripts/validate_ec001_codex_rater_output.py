"""Validate the GPT-5.4 Codex-agent rater artifact before committing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACKETS = (
    REPO
    / "experiments"
    / "external"
    / "longmemeval"
    / "runs"
    / "scoring_001"
    / "rater_packets.jsonl"
)
AMENDMENT_010_SHA = "b80bd8b32a86771dbaa4ba1f2fb8faa0eaae074d"
STAGE = "C1"
DISPLAY_MODEL = "GPT-5.4"
RESUME_PHRASE = "EC001 RESUME C1 GPT-5.4 SWITCHED"
FAMILY_ID = "codex-gpt54"
MODEL_FAMILY = "gpt-5.4"
MODEL_ID = "GPT-5.4 (Codex hosted display selection)"
OUTPUT_KEYS = {
    "anon_id",
    "stage",
    "display_model",
    "family_id",
    "model_family",
    "model_id",
    "label",
    "label_response",
    "rationale",
    "rater_called",
    "mechanical_zero",
}


def _jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_rater_rows(rows: list[dict], packets: list[dict]) -> dict:
    if [row.get("anon_id") for row in rows] != [
        row.get("anon_id") for row in packets
    ]:
        raise RuntimeError("Rater output coverage or order mismatch")
    for row, packet in zip(rows, packets, strict=True):
        if set(row) != OUTPUT_KEYS:
            raise RuntimeError(f"Unexpected output keys: {row.get('anon_id')}")
        if (
            row["stage"] != STAGE
            or row["display_model"] != DISPLAY_MODEL
            or row["family_id"] != FAMILY_ID
            or row["model_family"] != MODEL_FAMILY
            or row["model_id"] != MODEL_ID
        ):
            raise RuntimeError(f"Model metadata mismatch: {row['anon_id']}")
        if not isinstance(row["label"], bool):
            raise RuntimeError(f"Non-boolean label: {row['anon_id']}")
        if not str(row["rationale"]).strip():
            raise RuntimeError(f"Missing rationale: {row['anon_id']}")
        mechanical = bool(packet["mechanical_zero"])
        if bool(row["mechanical_zero"]) != mechanical:
            raise RuntimeError(f"Mechanical flag mismatch: {row['anon_id']}")
        if mechanical:
            if (
                row["label"]
                or row["label_response"] != "MECHANICAL_ZERO"
                or row["rater_called"]
            ):
                raise RuntimeError(
                    f"Invalid mechanical zero: {row['anon_id']}"
                )
        else:
            if row["label_response"] not in {"yes", "no"}:
                raise RuntimeError(
                    f"Non-binary surface: {row['anon_id']}"
                )
            if row["label"] != (row["label_response"] == "yes"):
                raise RuntimeError(
                    f"Label/surface mismatch: {row['anon_id']}"
                )
            if row["rater_called"] is not True:
                raise RuntimeError(f"Missing rater call: {row['anon_id']}")
    return {
        "question_count": len(rows),
        "mechanical_zero_count": sum(
            bool(row["mechanical_zero"]) for row in rows
        ),
        "positive_count": sum(bool(row["label"]) for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--display-model", required=True)
    parser.add_argument("--resume-phrase", required=True)
    parser.add_argument("--child-task", required=True)
    parser.add_argument("--calibration-gate", type=Path, required=True)
    parser.add_argument("--rater-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(
            f"Refusing to overwrite validation report: {args.output}"
        )
    if (
        args.stage != STAGE
        or args.display_model != DISPLAY_MODEL
        or args.resume_phrase != RESUME_PHRASE
    ):
        raise RuntimeError("Manual stage attestation mismatch")
    gate = json.loads(
        args.calibration_gate.read_text(encoding="utf-8")
    )
    if (
        gate.get("status") != "PASS"
        or gate.get("stage") != STAGE
        or gate.get("display_model") != DISPLAY_MODEL
    ):
        raise RuntimeError("Calibration gate is not a matching PASS")

    packets = _jsonl(PACKETS)
    rows = _jsonl(args.rater_output)
    counts = validate_rater_rows(rows, packets)
    report = {
        "record": "EC-001 GPT-5.4 Codex-agent rater validation",
        "stage": STAGE,
        "display_model": DISPLAY_MODEL,
        "family_id": FAMILY_ID,
        "model_family": MODEL_FAMILY,
        "model_id": MODEL_ID,
        "user_attested_parent_model": DISPLAY_MODEL,
        "resume_phrase": RESUME_PHRASE,
        "child_task": args.child_task,
        "fork_turns": "none",
        "explicit_model_override": None,
        "amendment_010_sha": AMENDMENT_010_SHA,
        **counts,
        "packets_sha256": _sha256(PACKETS),
        "calibration_gate_sha256": _sha256(args.calibration_gate),
        "rater_output_sha256": _sha256(args.rater_output),
        "identity_map_opened": False,
        "status": "PASS",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Rater output PASS: {counts['question_count']} rows, "
        f"{counts['mechanical_zero_count']} mechanical zeros"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
