#!/usr/bin/env python
"""Run one TC-002 phase.

    python scripts/run_tc002_study.py --phase g0
    python scripts/run_tc002_study.py --phase run

The run phase refuses to open an arm until G0's artifact exists, is
git-tracked, and reports PASS. Zero model calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc002_study import main  # noqa: E402

if __name__ == "__main__":
    main()
