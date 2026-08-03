"""Unseal EC-001 identities and finalize Codex-substituted integrity scores."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.analysis.ec001_longmemeval import (  # noqa: E402
    assert_repository_ready,
    sha256_file,
)
from src.analysis.ec001_tier2 import aggregate_labels  # noqa: E402


AUTHORIZED_RESULT_NAME = "Codex-substituted integrity score"


def _jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _by_id(path: Path) -> dict[str, dict]:
    rows = _jsonl(path)
    result = {row["anon_id"]: row for row in rows}
    if len(result) != len(rows):
        raise RuntimeError(f"Duplicate anonymous id in {path}")
    return result


def _gap(rows: list[dict]) -> dict:
    eligible = [
        row
        for row in rows
        if row["exact_gap_evaluable"]
        and isinstance(row["marker_availability_all"], bool)
    ]
    if not eligible:
        return {"status": "NOT_EVALUABLE", "denominator": 0}
    availability = sum(
        row["marker_availability_all"] for row in eligible
    ) / len(eligible)
    correctness = sum(row["integrity_label"] for row in eligible) / len(
        eligible
    )
    return {
        "status": "EVALUABLE",
        "denominator": len(eligible),
        "marker_availability_rate": availability,
        "correctness_rate": correctness,
        "tier1_minus_tier2": availability - correctness,
        "excluded_not_evaluable_count": sum(
            not row["exact_gap_evaluable"] for row in rows
        ),
        "excluded_incomplete_turn_label_count": sum(
            row["turn_label_complete"] is False for row in rows
        ),
        "excluded_abstention_count": sum(
            row["turn_label_complete"] is None for row in rows
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--mechanical-evidence", type=Path, required=True)
    parser.add_argument("--subset", type=Path, required=True)
    parser.add_argument("--runtime-record", type=Path, required=True)
    parser.add_argument(
        "--rater-output",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--trigger-summary", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = assert_repository_ready(require_clean=True)
    if len(args.rater_output) != 3:
        raise RuntimeError("Exactly three rater outputs are required")
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite scores: {args.output}")

    runtime = json.loads(args.runtime_record.read_text(encoding="utf-8"))
    boundary = runtime.get("reporting_boundary", {})
    if boundary.get("authorized_result_name") != AUTHORIZED_RESULT_NAME:
        raise RuntimeError("Runtime record does not authorize Codex scoring")
    if boundary.get("benchmark_protocol_score_authorized") is not False:
        raise RuntimeError("Benchmark-protocol score must remain unauthorized")

    sealed = json.loads(args.mapping.read_text(encoding="utf-8"))
    mapping_rows = sealed["mapping"]
    mapping = {row["anon_id"]: row for row in mapping_rows}
    packets = _by_id(args.packets)
    evidence = _by_id(args.mechanical_evidence)
    adjudications = _by_id(args.adjudications)
    triggers = json.loads(args.trigger_summary.read_text(encoding="utf-8"))
    membership = triggers["trigger_membership"]
    triggered = set().union(*(set(values) for values in membership.values()))
    if set(adjudications) != triggered:
        raise RuntimeError("Adjudication coverage differs from trigger set")

    rater_by_family: dict[str, dict[str, dict]] = {}
    for path in args.rater_output:
        rows = _by_id(path)
        families = {row["family_id"] for row in rows.values()}
        if len(families) != 1:
            raise RuntimeError(f"Mixed-family output: {path}")
        family = next(iter(families))
        if family in rater_by_family:
            raise RuntimeError(f"Duplicate family output: {family}")
        rater_by_family[family] = rows
    if set(mapping) != set(packets) or set(mapping) != set(evidence):
        raise RuntimeError("Scoring artifacts have different item coverage")
    if any(set(rows) != set(mapping) for rows in rater_by_family.values()):
        raise RuntimeError("Rater output has incomplete item coverage")

    rows: list[dict] = []
    for anon_id, identity in mapping.items():
        family_rows = [
            rater_by_family[family][anon_id]
            for family in sorted(rater_by_family)
        ]
        labels = {bool(row["label"]) for row in family_rows}
        if packets[anon_id]["mechanical_zero"] and any(labels):
            raise RuntimeError(f"Positive score on mechanical zero: {anon_id}")
        if anon_id in triggered:
            integrity_label = bool(adjudications[anon_id]["label"])
            integrity_rationale = adjudications[anon_id]["rationale"]
            basis = "independent_ai_adjudication"
        else:
            if len(labels) != 1:
                raise RuntimeError(
                    f"Unadjudicated disagreement: {anon_id}"
                )
            integrity_label = next(iter(labels))
            integrity_rationale = [
                {
                    "family_id": row["family_id"],
                    "rationale": row["rationale"],
                }
                for row in family_rows
            ]
            basis = "three_family_unanimous"
        row = {
            "question_id": identity["question_id"],
            "anon_id": anon_id,
            "question_type": identity["question_type"],
            "stratum": identity["stratum"],
            "integrity_label": integrity_label,
            "integrity_rationale": integrity_rationale,
            "integrity_basis": basis,
            "family_labels": {
                family_row["family_id"]: bool(family_row["label"])
                for family_row in family_rows
            },
            "triggers": [
                trigger
                for trigger, values in membership.items()
                if anon_id in values
            ],
            **evidence[anon_id],
        }
        rows.append(row)

    subset = json.loads(args.subset.read_text(encoding="utf-8"))
    integrity_rows = [
        {"stratum": row["stratum"], "label": row["integrity_label"]}
        for row in rows
    ]
    summary = {
        "record": "EC-001 finalized Codex-substituted integrity scores",
        "head": repository["head"],
        "question_count": len(rows),
        "authorized_result_name": AUTHORIZED_RESULT_NAME,
        "codex_substituted_integrity": aggregate_labels(
            integrity_rows,
            subset["benchmark_population_counts"],
        ),
        "availability_to_correctness_gap": {
            "codex_substituted_integrity": _gap(rows),
        },
        "trigger_counts": triggers["trigger_counts"],
        "adjudication_limitation": "AI adjudication; not human adjudication",
        "benchmark_protocol_score_authorized": False,
        "published_longmemeval_comparison_authorized": False,
        "identity_mapping_unsealed_after_scoring": True,
        "source_hashes": {
            "mapping": sha256_file(args.mapping),
            "packets": sha256_file(args.packets),
            "mechanical_evidence": sha256_file(args.mechanical_evidence),
            "subset": sha256_file(args.subset),
            "runtime_record": sha256_file(args.runtime_record),
            "trigger_summary": sha256_file(args.trigger_summary),
            "adjudications": sha256_file(args.adjudications),
            "rater_outputs": {
                path.name: sha256_file(path) for path in args.rater_output
            },
        },
    }

    args.output.mkdir(parents=True)
    ledger = args.output / "codex_integrity_score_ledger.jsonl"
    with ledger.open("w", encoding="utf-8") as handle:
        for row in sorted(rows, key=lambda item: item["question_id"]):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary["score_ledger_sha256"] = sha256_file(ledger)
    (args.output / "codex_integrity_score_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Finalized {len(rows)} Codex-substituted scores at {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
