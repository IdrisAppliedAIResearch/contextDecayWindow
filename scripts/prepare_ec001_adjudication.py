"""Compute EC-001 H1–H5 triggers after three rater passes are committed."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.analysis.ec001_longmemeval import (  # noqa: E402
    assert_repository_ready,
    sha256_file,
)
from src.analysis.ec001_tier2 import select_h5  # noqa: E402


def _jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument(
        "--rater-output",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = assert_repository_ready(require_clean=True)
    if len(args.rater_output) != 3:
        raise RuntimeError("Exactly three rater outputs are required")
    if args.output.exists():
        raise FileExistsError(
            f"Refusing to overwrite adjudication packets: {args.output}"
        )

    packets = {row["anon_id"]: row for row in _jsonl(args.packets)}
    by_item: dict[str, list[dict]] = {key: [] for key in packets}
    family_ids: set[str] = set()
    for path in args.rater_output:
        rows = _jsonl(path)
        if set(row["anon_id"] for row in rows) != set(packets):
            raise RuntimeError(f"Rater output coverage mismatch: {path}")
        observed_families = {str(row["family_id"]) for row in rows}
        if len(observed_families) != 1:
            raise RuntimeError(f"Rater output mixes families: {path}")
        family_id = next(iter(observed_families))
        if family_id in family_ids:
            raise RuntimeError(f"Duplicate rater family: {family_id}")
        family_ids.add(family_id)
        for row in rows:
            if not str(row.get("rationale", "")).strip():
                raise RuntimeError(
                    f"Missing rationale for {row['anon_id']}/{family_id}"
                )
            by_item[row["anon_id"]].append(row)

    h1: list[str] = []
    h2: list[str] = []
    unanimous: list[str] = []
    for anon_id, rows in by_item.items():
        packet = packets[anon_id]
        if packet["mechanical_zero"] and any(row["label"] for row in rows):
            h1.append(anon_id)
        labels = {bool(row["label"]) for row in rows}
        if len(labels) > 1:
            h2.append(anon_id)
        elif anon_id not in h1:
            unanimous.append(anon_id)

    h5 = list(select_h5(unanimous))
    triggered = sorted(set(h1) | set(h2) | set(h5))
    h2_packets: list[dict] = []
    h5_packets: list[dict] = []
    for anon_id in sorted(set(h1) | set(h2)):
        rows = sorted(
            by_item[anon_id],
            key=lambda row: hashlib.sha256(
                f"{anon_id}\0{row['family_id']}".encode("utf-8")
            ).hexdigest(),
        )
        h2_packets.append(
            {
                **packets[anon_id],
                "trigger_class": sorted(
                    trigger
                    for trigger, population in (("H1", h1), ("H2", h2))
                    if anon_id in population
                ),
                "blinded_judgments": [
                    {
                        "pass": f"pass-{index}",
                        "label": bool(row["label"]),
                        "rationale": row["rationale"],
                    }
                    for index, row in enumerate(rows, 1)
                ],
            }
        )
    for anon_id in sorted(h5):
        h5_packets.append(
            {
                **packets[anon_id],
                "trigger_class": ["H5"],
            }
        )

    args.output.mkdir(parents=True)
    h2_path = args.output / "h1_h2_conflict_packets.jsonl"
    h5_path = args.output / "h5_blind_packets.jsonl"
    _write_jsonl(h2_path, h2_packets)
    _write_jsonl(h5_path, h5_packets)
    summary = {
        "record": "EC-001 H1-H5 trigger computation",
        "head": repository["head"],
        "family_ids": sorted(family_ids),
        "question_count": len(packets),
        "trigger_counts": {
            "H1": len(h1),
            "H2": len(h2),
            "H3": 0,
            "H4": 0,
            "H5": len(h5),
        },
        "trigger_membership": {
            "H1": sorted(h1),
            "H2": sorted(h2),
            "H3": [],
            "H4": [],
            "H5": sorted(h5),
        },
        "triggered_item_count": len(triggered),
        "unanimous_non_h1_count": len(unanimous),
        "h5_population_rule": (
            "ceil(10% of unanimous non-H1 items), minimum one"
        ),
        "h5_family_labels_revealed_to_packet": False,
        "packets_sha256": sha256_file(args.packets),
        "rater_output_sha256": {
            path.name: sha256_file(path) for path in args.rater_output
        },
        "h1_h2_packets_sha256": sha256_file(h2_path),
        "h5_packets_sha256": sha256_file(h5_path),
    }
    (args.output / "trigger_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Prepared {len(h2_packets)} conflict and {len(h5_packets)} "
        f"blind-control adjudication packets at {args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
