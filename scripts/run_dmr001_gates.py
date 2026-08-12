"""Run every DMR-001 arm on both splits and evaluate the registered gates.

Refuses to run unless a passing PF1-PF10 artifact already exists on disk. The
bars come from the committed pre-registration; nothing here chooses one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.dmr001_corpus import write_json  # noqa: E402
from src.analysis.dmr001_formation import build_study_report  # noqa: E402

STUDY = ROOT / "experiments" / "components" / "biological_memory" / "dmr_001"
DEFAULT_DESIGN = STUDY / "DMR_001_FINAL_DESIGN.json"
DEFAULT_PREFLIGHT = STUDY / "artifacts" / "dmr001_preflight" / "preflight.json"
DEFAULT_OUTPUT = STUDY / "artifacts" / "dmr001_gates" / "gate_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    arguments = parser.parse_args()

    report = build_study_report(ROOT, arguments.design, arguments.preflight)
    digest = write_json(arguments.output, report, allow_overwrite=arguments.allow_overwrite)

    print("DMR-001 gate report")
    for split, value in report["splits"].items():
        treatment = value["arms"]["T_EVENT"]
        agreement = treatment["agreement"]["1"]
        print(
            f"  {split:12s} {value['episodes']:5d} episodes  "
            f"{treatment['sizes']['event_count']:4d} events  "
            f"P={agreement['precision']:.3f} R={agreement['recall']:.3f} F1={agreement['f1']:.3f}"
        )
    print()
    for gate in report["verdict"]["gates"]:
        mark = "PASS" if gate["passed"] else "FAIL"
        if not gate["evaluated"]:
            mark = "NOT EVALUATED"
        print(f"  {gate['gate']} {gate['name']:20s} {mark}")
        for check in gate["checks"]:
            if not check["passed"]:
                print(
                    f"      failed: {check['check']} "
                    f"(observed {check['observed']!r}, bar {check['bar']!r})"
                )
    print()
    print(f"  disposition          : {report['verdict']['disposition']}")
    print(f"  stopped at           : {report['verdict']['stopped_at'] or '(none)'}")
    print(f"  artifact sha256      : {digest}")
    print(f"  artifact             : {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
