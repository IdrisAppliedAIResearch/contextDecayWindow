#!/usr/bin/env python
"""Run TC-004 Preflight Part 1 without model calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc004_exploration import (  # noqa: E402
    ARTIFACT_ROOT,
    explore,
    locomo_split_inventory,
)


if __name__ == "__main__":
    result = explore(ARTIFACT_ROOT)
    locomo = locomo_split_inventory(ARTIFACT_ROOT)
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "population": result["population"],
                "elapsed_seconds": result["elapsed_seconds"],
                "calls": result["calls"],
                "locomo": {
                    "status": locomo["status"],
                    "population": locomo["population"],
                    "treatment_vector_coverage": locomo[
                        "treatment_vector_coverage"
                    ],
                },
            },
            indent=2,
        )
    )
