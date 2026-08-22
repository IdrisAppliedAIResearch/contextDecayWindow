#!/usr/bin/env python
"""Run TC-001B Preflight Part 1.

    python scripts/run_tc001b_preflight.py \
        --output-dir experiments/components/tier_cost/artifacts/tc001b/preflight

Zero model calls: the LoCoMo development embedding cache is opened
read-only with its digests asserted, and a miss raises.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc001b_exploration import explore  # noqa: E402

DEFAULT_OUTPUT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts"
    / "tc001b" / "preflight"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = explore(arguments.output_dir)
    print(f"wrote {arguments.output_dir / 'tc001b_preflight_part1.json'}")
    print(json.dumps(result["identity"], indent=2, sort_keys=True))
    print(json.dumps(result["behaviour"]["ordering"], indent=2, sort_keys=True))
    print(json.dumps(result["behaviour"]["degenerate_states"], indent=2, sort_keys=True))
    print(f"null band max_abs_net {result['null_band']['max_abs_net']}")
    print(f"elapsed {result['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
