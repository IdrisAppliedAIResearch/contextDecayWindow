#!/usr/bin/env python
"""Run TC-005 Preflight Part 1."""

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

from analysis.tc005_exploration import ARTIFACT_ROOT, explore  # noqa: E402


if __name__ == "__main__":
    result = explore(ARTIFACT_ROOT / "preflight")
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "elapsed_seconds": result["elapsed_seconds"],
                "bakeoff_rows": result["identity"]["retrieval_bakeoff_reproduction"]["rows_checked"],
                "embedding_calls": result["embedding_audit"]["bakeoff_embedding_calls"],
            },
            indent=2,
        )
    )
