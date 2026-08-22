#!/usr/bin/env python
"""Run TC-001B Preflight PF4: are the four bars reachable and failable?

    python scripts/run_tc001b_reachability.py \
        --output-dir experiments/components/tier_cost/artifacts/tc001b/preflight

Emits discordant-pair counts only. The direction of disagreement is not
computed, so this may be read before the bars are locked.
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

from analysis.tc001b_reachability import measure  # noqa: E402

DEFAULT_OUTPUT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts"
    / "tc001b" / "preflight"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = measure(arguments.output_dir)
    print(json.dumps(result["budgets"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
