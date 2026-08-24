#!/usr/bin/env python
"""Run TC-001 Preflight Part 1.

    python scripts/run_tc001_preflight.py \
        --output-dir experiments/components/tier_cost/artifacts/tc001/preflight

Zero model calls: the LoCoMo development embedding cache is opened
read-only with its digests asserted, and a miss raises.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc001_exploration import explore  # noqa: E402

DEFAULT_OUTPUT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts"
    / "tc001" / "preflight"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = explore(arguments.output_dir)
    print(f"wrote {arguments.output_dir / 'tc001_preflight_part1.json'}")
    print(f"elapsed {result['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
