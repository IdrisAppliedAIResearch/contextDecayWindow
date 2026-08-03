"""Validate the GPT-5.5 Codex-agent adjudication artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

STAGE = "C2"
DISPLAY_MODEL = "GPT-5.5"
RESUME_PHRASE = "EC001 RESUME C2 GPT-5.5 SWITCHED"
FAMILY = "gpt-5.5"
MODEL_ID = "GPT-5.5 (Codex hosted display selection)"
OUTPUT_KEYS = {
    "anon_id",
    "trigger_class",
    "stage",
    "display_model",
    "adjudicator_family",
    "adjudicator_model_id",
    "label",
    "label_response",
    "rationale",
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


def validate_adjudications(
    rows: list[dict],
    packets: list[dict],
) -> dict:
    if [row.get("anon_id") for row in rows] != [
        row.get("anon_id") for row in packets
    ]:
        raise RuntimeError("Adjudication coverage or order mismatch")
    for row, packet in zip(rows, packets, strict=True):
        if set(row) != OUTPUT_KEYS:
            raise RuntimeError(
                f"Unexpected adjudication keys: {row.get('anon_id')}"
            )
        if (
            row["stage"] != STAGE
            or row["display_model"] != DISPLAY_MODEL
            or row["adjudicator_family"] != FAMILY
            or row["adjudicator_model_id"] != MODEL_ID
        ):
            raise RuntimeError(
                f"Adjudicator metadata mismatch: {row['anon_id']}"
            )
        if row["trigger_class"] != packet["trigger_class"]:
            raise RuntimeError(
                f"Trigger class mismatch: {row['anon_id']}"
            )
        if not isinstance(row["label"], bool):
            raise RuntimeError(
                f"Non-boolean adjudication: {row['anon_id']}"
            )
        if row["label_response"] not in {"yes", "no"}:
            raise RuntimeError(
                f"Non-binary adjudication surface: {row['anon_id']}"
            )
        if row["label"] != (row["label_response"] == "yes"):
            raise RuntimeError(
                f"Adjudication label/surface mismatch: {row['anon_id']}"
            )
        if packet["mechanical_zero"] and row["label"]:
            raise RuntimeError(
                f"Mechanical zero scored positive: {row['anon_id']}"
            )
        if not str(row["rationale"]).strip():
            raise RuntimeError(
                f"Missing adjudication rationale: {row['anon_id']}"
            )
    return {
        "item_count": len(rows),
        "positive_count": sum(bool(row["label"]) for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h1-h2-packets", type=Path, required=True)
    parser.add_argument("--h5-packets", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path, required=True)
    parser.add_argument("--resume-phrase", required=True)
    parser.add_argument("--child-task", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(
            f"Refusing to overwrite validation report: {args.output}"
        )
    if args.resume_phrase != RESUME_PHRASE:
        raise RuntimeError("Manual adjudicator attestation mismatch")

    packets = _jsonl(args.h1_h2_packets) + _jsonl(args.h5_packets)
    if len({row["anon_id"] for row in packets}) != len(packets):
        raise RuntimeError("Adjudication packets contain duplicate ids")
    rows = _jsonl(args.adjudications)
    counts = validate_adjudications(rows, packets)
    report = {
        "record": "EC-001 GPT-5.5 Codex-agent adjudication validation",
        "stage": STAGE,
        "display_model": DISPLAY_MODEL,
        "adjudicator_family": FAMILY,
        "adjudicator_model_id": MODEL_ID,
        "user_attested_parent_model": DISPLAY_MODEL,
        "resume_phrase": RESUME_PHRASE,
        "child_task": args.child_task,
        "fork_turns": "none",
        "explicit_model_override": None,
        **counts,
        "h1_h2_packets_sha256": _sha256(args.h1_h2_packets),
        "h5_packets_sha256": _sha256(args.h5_packets),
        "adjudications_sha256": _sha256(args.adjudications),
        "identity_map_opened": False,
        "status": "PASS",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Adjudications PASS: {counts['item_count']} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
