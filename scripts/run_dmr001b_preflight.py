"""Execute DMR-001B PF1-PF10 and write the committed preflight artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.dmr001_corpus import write_json  # noqa: E402
from src.analysis.dmr001b_preflight import build_preflight  # noqa: E402

STUDY = ROOT / "experiments" / "components" / "biological_memory" / "dmr_001b"
DEFAULT_DESIGN = STUDY / "DMR_001B_FINAL_DESIGN.json"
DEFAULT_OUTPUT = STUDY / "artifacts" / "dmr001b_preflight" / "preflight.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    arguments = parser.parse_args()

    report = build_preflight(ROOT, arguments.design)
    digest = write_json(arguments.output, report, allow_overwrite=arguments.allow_overwrite)

    print("DMR-001B preflight")
    for key, value in report.items():
        if key.startswith("PF") and isinstance(value, dict) and "checks" in value:
            checks = value["checks"]
            passed = sum(1 for check in checks if check["passed"])
            print(f"  {key:22s} {passed}/{len(checks)}")
    print(f"  status               : {report['status']}")
    for failure in report["failed_checks"]:
        print(f"    FAILED {failure['section']}: {failure['check']}")
    print(f"  artifact sha256      : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
