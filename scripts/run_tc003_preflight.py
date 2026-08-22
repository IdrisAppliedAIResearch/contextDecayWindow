#!/usr/bin/env python
"""Run TC-003 Preflight Part 1.

    python scripts/run_tc003_preflight.py

Writes ``experiments/components/tier_cost/artifacts/tc003/preflight/``.
Zero model calls: the LoCoMo development embedding cache is opened read-only
and a miss raises.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc003_exploration import ARTIFACT_ROOT, explore  # noqa: E402

if __name__ == "__main__":
    result = explore(ARTIFACT_ROOT / "preflight")
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "elapsed_seconds": result["elapsed_seconds"],
                "sham_band_max_abs_net": result["sham_band"]["max_abs_net"],
            },
            indent=2,
        )
    )
