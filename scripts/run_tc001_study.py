#!/usr/bin/env python
"""Run one TC-001 phase.

    python scripts/run_tc001_study.py --phase g0
    python scripts/run_tc001_study.py --phase run

Phase ``g0`` reproduces the committed LoCoMo development analysis and
writes the binding gate. Phase ``run`` refuses to start until that gate
is committed and passing.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc001_study import main  # noqa: E402

if __name__ == "__main__":
    main()
