#!/usr/bin/env python
"""Run one IC-001 phase.

    python scripts/run_ic001_internal_packing.py --phase b0 \
        --output-root experiments/internal/packing_priority/runs/ic001

Phase ``b0`` writes the recency-first arm and its binding gate. Phase
``b1`` refuses to run until that gate is committed and passing.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.ic001_internal_packing import main  # noqa: E402

if __name__ == "__main__":
    main()
