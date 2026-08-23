#!/usr/bin/env python
"""Run TC-005 PF4 after Part 1."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc005_exploration import ARTIFACT_ROOT  # noqa: E402
from analysis.tc005_reachability import measure  # noqa: E402


if __name__ == "__main__":
    result = measure(ARTIFACT_ROOT / "preflight")
    print(json.dumps({"schema": result["schema"], "status": result["status"]}, indent=2))
