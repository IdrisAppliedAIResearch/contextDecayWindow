"""Aggregate the three blind passes, then unseal, then read the band.

Two stages, and the split is the audit trail rather than a convenience:

``--stage aggregate``
    Combines three blind passes into blind scores. The mapping stays
    sealed. Commit this before running the next stage.

``--stage unseal``
    Opens the mapping, writes the per-replicate scores, and reads the band
    against the decision rule committed before any of this ran. Refuses if
    the rule's digest has moved.

Aggregation is Study 011's, imported: same calibration gate, same
majority rule, same refusal to average three disagreeing raters into a
number none of them gave, same `NO_ANSWER` guard.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.amendment_001_noise_band import (  # noqa: E402
    NOISE_BAND_ROOT,
    NoiseBandError,
    assert_decision_rule,
    build_report,
    write_report,
)
from src.analysis.study_011_score_aggregation import (  # noqa: E402
    AggregationError,
    aggregate,
    load_passes,
    unseal,
)

EVALUATION = NOISE_BAND_ROOT / "evaluation"
PACKETS = EVALUATION / "blind_packets.json"
MAPPING = EVALUATION / "sealed_mapping.json"
BLIND_SCORES = EVALUATION / "blind_scores.json"
REPLICATE_SCORES = EVALUATION / "replicate_scores.json"
BAND_VERDICT = NOISE_BAND_ROOT / "band_verdict.json"
RUN_MANIFEST = NOISE_BAND_ROOT / "run_manifest.json"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def stage_aggregate(args: argparse.Namespace) -> int:
    packets = json.loads(args.packets.read_text(encoding="utf-8"))
    aggregated = aggregate(load_passes(list(args.passes)), packets)
    _write(args.blind_scores, aggregated)
    agreement = aggregated["agreement"]
    print(
        f"blind scores written: {agreement['unanimous_items']}/"
        f"{agreement['total_items']} unanimous, "
        f"{agreement['split_items']} split"
    )
    for label, values in sorted(aggregated["blind_scores"].items()):
        print(f"  {label}: {round(sum(values.values()), 2)}/13")
    print("\nmapping still sealed. Commit these scores before unsealing.")
    return 0


def stage_unseal(args: argparse.Namespace) -> int:
    rule_digest = assert_decision_rule()
    if not args.blind_scores.is_file():
        raise NoiseBandError(
            "blind scores must be committed before the mapping is opened"
        )
    aggregated = json.loads(args.blind_scores.read_text(encoding="utf-8"))
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    unsealed = unseal(aggregated, mapping)
    _write(args.replicate_scores, unsealed)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = build_report(
        scores=unsealed["scores"],
        aggregated=aggregated,
        runs=manifest["replicates"],
        decision_rule_sha256=rule_digest,
    )
    write_report(report, args.verdict)

    print("per-replicate totals:")
    for run_id, total in sorted(unsealed["totals_out_of_13"].items()):
        print(f"  {run_id}: {total}/13")
    band = report["band"]
    print(f"\nband (max - min): {band['band']}")
    print(f"  min {band['min']}, max {band['max']}, sd {band['standard_deviation']}")
    print(f"verdict: {report['verdict']['row']} — {report['verdict']['reading']}")
    print(f"paper: {report['verdict']['paper_action']}")
    print("\nuniform application:")
    for row in report["uniform_application"]:
        marker = "survives" if row["exceeds_band"] else "NOT DEMONSTRATED"
        print(f"  {row['result']}: gap {row['gap']} — {marker}")
    variability = report["per_question_variability"]
    print(
        f"\nquestions that moved: {variability['questions_that_moved']} "
        f"({variability['concentration']})"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("aggregate", "unseal"), required=True)
    parser.add_argument("--passes", type=Path, nargs="*", default=[])
    parser.add_argument("--packets", type=Path, default=PACKETS)
    parser.add_argument("--mapping", type=Path, default=MAPPING)
    parser.add_argument("--blind-scores", type=Path, default=BLIND_SCORES)
    parser.add_argument("--replicate-scores", type=Path, default=REPLICATE_SCORES)
    parser.add_argument("--verdict", type=Path, default=BAND_VERDICT)
    parser.add_argument("--manifest", type=Path, default=RUN_MANIFEST)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.stage == "aggregate":
            if len(args.passes) < 3:
                raise NoiseBandError("§6.1 requires three blind passes")
            return stage_aggregate(args)
        return stage_unseal(args)
    except (NoiseBandError, AggregationError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
