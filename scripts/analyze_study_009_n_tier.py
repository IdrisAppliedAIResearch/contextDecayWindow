"""Write the Study 009 N-tier characterization artifact.

Offline. Reads the committed runs, writes one JSON file, changes no
mechanism code.

    .venv/Scripts/python.exe scripts/analyze_study_009_n_tier.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analysis.study_009_n_tier import REPO_ROOT, write_report

DEFAULT_OUTPUT = (
    REPO_ROOT / "experiments/study_009/analysis/n_tier_characterization.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = write_report(args.output)
    print(json.dumps(report["shared_key_probe"], indent=2))
    for run in report["runs"]:
        replay = run["replay"]
        print(
            f"{run['run']}: replay {replay['turns_matched']}"
            f"/{replay['turns_testable']} identical={replay['identical']}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
