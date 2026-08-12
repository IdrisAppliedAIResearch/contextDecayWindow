"""Characterize the DMR-001 stop. Descriptive only; changes no bar or verdict."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.dmr001_corpus import write_json  # noqa: E402
from src.analysis.dmr001_poststop import build_poststop  # noqa: E402

STUDY = ROOT / "experiments" / "components" / "biological_memory" / "dmr_001"
DEFAULT_DESIGN = STUDY / "DMR_001_FINAL_DESIGN.json"
DEFAULT_GATES = STUDY / "artifacts" / "dmr001_gates" / "gate_report.json"
DEFAULT_OUTPUT = STUDY / "artifacts" / "dmr001_gates" / "post_stop_characterization.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--gates", type=Path, default=DEFAULT_GATES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    arguments = parser.parse_args()

    report = build_poststop(ROOT, arguments.design, arguments.gates)
    digest = write_json(arguments.output, report, allow_overwrite=arguments.allow_overwrite)

    print("DMR-001 post-stop characterization (descriptive only)")
    for split, value in report["splits"].items():
        matches = value["matches"]
        drift = value["drift"]
        print(f"  {split}")
        print(f"    predicted by reason      : {matches['predicted_by_reason']}")
        print(f"    matched by reason        : {matches['matched_by_reason']}")
        print(
            "    precision by reason      : "
            + ", ".join(f"{k}={v:.3f}" for k, v in matches["precision_by_reason"].items())
        )
        print(
            f"    boundaries from forced   : {matches['share_of_boundaries_from_forced']:.3f}"
        )
        print(
            f"    eligible episodes over the threshold: "
            f"{drift['eligible_above_threshold']}/{drift['eligible_for_drift_predicate']} "
            f"({drift['eligible_above_threshold_fraction']:.4f})"
        )
        print(
            f"    near-zero drift vs prototype: {drift['near_zero_drift_against_prototype']} "
            f"({drift['near_zero_drift_fraction']:.3f})"
        )
    print(f"  artifact sha256            : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
