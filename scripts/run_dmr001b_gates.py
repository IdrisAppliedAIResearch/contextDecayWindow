"""Run DMR-001B formation on every family and evaluate the registered gates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.dmr001_corpus import write_json  # noqa: E402
from src.analysis.dmr001b_gates import build_gate_report  # noqa: E402

STUDY = ROOT / "experiments" / "components" / "biological_memory" / "dmr_001b"
DEFAULT_DESIGN = STUDY / "DMR_001B_FINAL_DESIGN.json"
DEFAULT_PREFLIGHT = STUDY / "artifacts" / "dmr001b_preflight" / "preflight.json"
DEFAULT_OUTPUT = STUDY / "artifacts" / "dmr001b_gates" / "gate_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    arguments = parser.parse_args()

    report = build_gate_report(ROOT, arguments.design, arguments.preflight)
    digest = write_json(arguments.output, report, allow_overwrite=arguments.allow_overwrite)

    print("DMR-001B gate report")
    for name, family in report["families"].items():
        a = family["agreement_claims_only"]
        print(
            f"  {name:24s} ev={family['event_count']:4d} fire={100*family['adaptive_fire_rate']:.2f}% "
            f"capped={family['capped_closures']:2d}  P={a['precision']:.3f} R={a['recall']:.3f} F1={a['f1']:.3f}"
        )
    print()
    for gate in report["verdict"]["gates"]:
        mark = "PASS" if gate["passed"] else "FAIL"
        if not gate["evaluated"]:
            mark = "NOT EVALUATED"
        print(f"  {gate['gate']} {gate['name']:32s} {mark}")
        for check in gate["checks"]:
            if not check["passed"]:
                print(f"      failed: {check['check']} (observed {check['observed']!r}, bar {check['bar']!r})")
    print()
    print(f"  disposition          : {report['verdict']['disposition']}")
    print(f"  artifact sha256      : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
