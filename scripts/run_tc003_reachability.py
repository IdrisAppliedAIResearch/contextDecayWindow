#!/usr/bin/env python
"""Run TC-003 Preflight PF4 reachability.

    python scripts/run_tc003_reachability.py

Writes ``experiments/components/tier_cost/artifacts/tc003/preflight/``.
Discordant counts and instrument reachability only: the artifact carries no
directional key and the writer refuses to emit one. Zero model calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc003_exploration import ARTIFACT_ROOT  # noqa: E402
from analysis.tc003_reachability import measure  # noqa: E402

if __name__ == "__main__":
    result = measure(ARTIFACT_ROOT / "preflight")
    print(json.dumps({key: result[key] for key in ("schema", "status")}, indent=2))
