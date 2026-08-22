#!/usr/bin/env python
"""Run one registered TC-003 phase.

    python scripts/run_tc003_study.py --phase g0
    python scripts/run_tc003_study.py --phase run

The run phase refuses to open evidence labels until a passing, committed G0
artifact exists.  Zero model calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc003_study import main  # noqa: E402

if __name__ == "__main__":
    main()
