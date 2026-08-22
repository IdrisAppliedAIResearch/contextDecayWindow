#!/usr/bin/env python
"""Run one TC-001B phase.

    python scripts/run_tc001b_study.py --phase g0
    python scripts/run_tc001b_study.py --phase run

``g0`` must be committed before ``run`` will open any arm's availability;
the precondition is enforced in code, not by convention.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc001b_study import main  # noqa: E402

if __name__ == "__main__":
    main()
