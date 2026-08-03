"""Validate a blind Codex-agent calibration attempt without exposing answers."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CALIBRATION = (
    REPO
    / "experiments"
    / "external"
    / "longmemeval"
    / "runs"
    / "scoring_001"
    / "calibration_set.json"
)
BLIND_CALIBRATION = (
    REPO
    / "experiments"
    / "external"
    / "longmemeval"
    / "EC_001_CODEX_AGENT_CALIBRATION_BLIND.jsonl"
)
STAGES = {"C1": "GPT-5.4"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_calibration(
    observations: dict,
    expected: list[dict],
    *,
    stage: str,
    display_model: str,
) -> dict:
    if STAGES.get(stage) != display_model:
        raise RuntimeError("Stage/display-model mismatch")
    if observations.get("stage") != stage:
        raise RuntimeError("Calibration stage mismatch")
    if observations.get("display_model") != display_model:
        raise RuntimeError("Calibration display-model mismatch")
    rows = observations.get("calibration")
    if not isinstance(rows, list):
        raise RuntimeError("Calibration observations must be a list")
    expected_by_id = {
        str(row["calibration_id"]): bool(row["expected_label"])
        for row in expected
    }
    if [str(row.get("calibration_id")) for row in rows] != list(
        expected_by_id
    ):
        raise RuntimeError("Calibration ids or order mismatch")

    failures: list[str] = []
    for row in rows:
        if set(row) != {
            "calibration_id",
            "label",
            "label_response",
        }:
            raise RuntimeError("Unexpected calibration observation keys")
        label = row["label"]
        if not isinstance(label, bool):
            raise RuntimeError("Calibration label must be boolean")
        surface = row["label_response"]
        if surface not in {"yes", "no"}:
            raise RuntimeError("Calibration surface must be exact yes/no")
        if label != (surface == "yes"):
            raise RuntimeError("Calibration label/surface mismatch")
        calibration_id = str(row["calibration_id"])
        if label != expected_by_id[calibration_id]:
            failures.append(calibration_id)
    return {
        "status": "PASS" if not failures else "FAIL",
        "failed_calibration_ids": failures,
        "calibration_count": len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--display-model", required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite gate: {args.output}")

    observations = json.loads(
        args.observations.read_text(encoding="utf-8")
    )
    expected = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    result = validate_calibration(
        observations,
        expected,
        stage=args.stage,
        display_model=args.display_model,
    )
    gate = {
        "record": "EC-001 Codex-agent calibration gate",
        "stage": args.stage,
        "display_model": args.display_model,
        **result,
        "observations_sha256": _sha256(args.observations),
        "blind_calibration_sha256": _sha256(BLIND_CALIBRATION),
        "expected_labels_exposed_to_child_before_attempt": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(gate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if result["status"] != "PASS":
        print(
            "Calibration failed: "
            + ", ".join(result["failed_calibration_ids"])
        )
        return 1
    print(f"Calibration PASS: {args.stage}/{args.display_model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
