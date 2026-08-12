"""Run the frozen DMR-001B rule on the sealed DMR-001C corpus and gate it."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.dmr001_corpus import write_json  # noqa: E402
from src.analysis.dmr001c_gates import build_gate_report  # noqa: E402

STUDY = ROOT / "experiments" / "components" / "biological_memory" / "dmr_001c"
DEFAULT_DESIGN = (
    ROOT / "experiments/components/biological_memory/dmr_001b/DMR_001B_FINAL_DESIGN.json"
)
DEFAULT_DATA = Path(r"C:\Users\muzaf\datasets\longmemeval\longmemeval_s_cleaned.json")
DEFAULT_CACHE = (
    ROOT / "experiments/external/longmemeval/runs/ec002_k_first/ec002_exact_solo_embeddings.db"
)
DEFAULT_OUTPUT = STUDY / "artifacts" / "dmr001c_gates" / "gate_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    arguments = parser.parse_args()

    report = build_gate_report(ROOT, arguments.design, arguments.data, arguments.cache)
    digest = write_json(arguments.output, report, allow_overwrite=arguments.allow_overwrite)

    s = report["summary"]
    print("DMR-001C sealed holdout")
    print(f"  streams / episodes   : {s['streams']} / {s['episodes']}")
    print(f"  seams (base rate)    : {s['seams']} ({100*s['seam_base_rate']:.1f}%)")
    print(f"  fire rate p05..p95   : {100*s['fire_rate_p05']:.2f}% .. {100*s['fire_rate_p95']:.2f}%"
          f"  ratio {s['fire_rate_p95_p05_ratio']:.2f}x")
    print(f"  macro P/R/F1         : {s['macro_precision']:.3f} / {s['macro_recall']:.3f} / {s['macro_f1']:.3f}")
    print(f"  best periodic        : {s['best_periodic']} F1={s['periodic_macro_f1'][s['best_periodic']]:.3f}")
    print(f"  C_PAIR               : F1={s['c_pair_macro_f1']:.3f} P={s['c_pair_macro_precision']:.3f}")
    print()
    for gate in report["verdict"]["gates"]:
        mark = "PASS" if gate["passed"] else "FAIL"
        if not gate["evaluated"]:
            mark = "NOT EVALUATED"
        print(f"  {gate['gate']} {gate['name']:20s} {mark}")
        for check in gate["checks"]:
            if not check["passed"]:
                print(f"      failed: {check['check']} (observed {check['observed']!r}, bar {check['bar']!r})")
    print()
    print(f"  disposition          : {report['verdict']['disposition']}")
    print(f"  artifact sha256      : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
