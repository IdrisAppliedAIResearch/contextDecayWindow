#!/usr/bin/env python
"""Run TC-004 PF4 without creating treatment vectors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc004_exploration import ARTIFACT_ROOT  # noqa: E402
from analysis.tc004_preflight import measure  # noqa: E402


if __name__ == "__main__":
    result = measure(ARTIFACT_ROOT)
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "budgets": result["budgets"],
            },
            indent=2,
        )
    )
