"""Prepare masked EC-001 scoring packets after reader answers are committed."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.analysis.ec001_longmemeval import (  # noqa: E402
    assert_repository_ready,
    load_adaptation_record,
    load_longmemeval,
    sha256_file,
    validate_subset_manifest,
)
from src.analysis.ec001_tier2 import (  # noqa: E402
    NO_ANSWER,
    build_label_prompt,
    calibration_cases,
    masked_id,
)


def _jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--subset", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--tier1-scores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = assert_repository_ready(require_clean=True)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite packets: {args.output}")

    adaptation = load_adaptation_record()
    dataset = load_longmemeval(
        args.data,
        expected_sha256=adaptation["benchmark"]["dataset_sha256"],
    )
    subset = json.loads(args.subset.read_text(encoding="utf-8"))
    selected_ids = validate_subset_manifest(subset, dataset)
    answers = {row["question_id"]: row for row in _jsonl(args.answers)}
    tier1 = {row["question_id"]: row for row in _jsonl(args.tier1_scores)}
    if set(answers) != set(selected_ids):
        raise RuntimeError("Reader answers do not exactly match the subset")
    if set(selected_ids) - set(tier1):
        raise RuntimeError("Tier 1 scores miss selected questions")

    with args.data.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    references = {row["question_id"]: row for row in raw}

    mapping: list[dict] = []
    packets: list[dict] = []
    evidence: list[dict] = []
    for question_id in selected_ids:
        source = references[question_id]
        answer_row = answers[question_id]
        tier1_row = tier1[question_id]
        anon_id = masked_id(question_id)
        abstention = question_id.endswith("_abs")
        complete = answer_row["completeness_status"] == "COMPLETE"
        no_answer = bool(answer_row["no_answer"])
        scoreable = str(answer_row["scoreable_response"])
        scoring_surface = (
            scoreable if complete and not no_answer else NO_ANSWER
        )
        mapping.append(
            {
                "anon_id": anon_id,
                "question_id": question_id,
                "question_type": source["question_type"],
                "stratum": answer_row["stratum"],
            }
        )
        packets.append(
            {
                "anon_id": anon_id,
                "question_type": source["question_type"],
                "abstention": abstention,
                "question": source["question"],
                "reference_answer": source["answer"],
                "scoreable_response": scoring_surface,
                "mechanical_zero": not complete or no_answer,
                "mechanical_zero_reason": (
                    answer_row["completeness_status"]
                    if not complete
                    else (NO_ANSWER if no_answer else None)
                ),
                "label_prompt": build_label_prompt(
                    source["question_type"],
                    source["question"],
                    source["answer"],
                    scoring_surface,
                    abstention=abstention,
                ),
            }
        )
        evidence.append(
            {
                "anon_id": anon_id,
                "marker_availability_any": tier1_row.get(
                    "marker_availability_any"
                ),
                "marker_availability_all": tier1_row.get(
                    "marker_availability_all"
                ),
                "turn_label_complete": tier1_row.get(
                    "turn_label_complete"
                ),
                "exact_gap_evaluable": tier1_row.get(
                    "exact_gap_evaluable"
                ),
                "reader_completeness_status": answer_row[
                    "completeness_status"
                ],
                "reader_no_answer": no_answer,
            }
        )

    if len({row["anon_id"] for row in mapping}) != len(mapping):
        raise RuntimeError("Masked id collision")

    args.output.mkdir(parents=True)
    mapping_path = args.output / "SEALED_MASK_MAPPING_DO_NOT_OPEN.json"
    packet_path = args.output / "rater_packets.jsonl"
    evidence_path = args.output / "mechanical_evidence.jsonl"
    calibration_path = args.output / "calibration_set.json"
    mapping_path.write_text(
        json.dumps(
            {
                "record": "EC-001 sealed scoring map",
                "mapping": mapping,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_jsonl(packet_path, packets)
    _write_jsonl(evidence_path, evidence)
    calibration_path.write_text(
        json.dumps(calibration_cases(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    header = {
        "record": "EC-001 blind scoring packet registration",
        "head": repository["head"],
        "question_count": len(packets),
        "strata": dict(
            sorted(Counter(row["stratum"] for row in mapping).items())
        ),
        "dataset_sha256": dataset.source_sha256,
        "subset_sha256": sha256_file(args.subset),
        "answers_sha256": sha256_file(args.answers),
        "tier1_scores_sha256": sha256_file(args.tier1_scores),
        "mapping_sha256": sha256_file(mapping_path),
        "packets_sha256": sha256_file(packet_path),
        "mechanical_evidence_sha256": sha256_file(evidence_path),
        "calibration_sha256": sha256_file(calibration_path),
        "arm_identity": "single external calibration arm; question ids masked",
        "status": "LOCK_BEFORE_SCORING",
    }
    (args.output / "packet_header.json").write_text(
        json.dumps(header, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(packets)} masked scoring packets at {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
