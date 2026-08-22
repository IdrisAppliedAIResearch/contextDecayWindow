#!/usr/bin/env python
"""Run TC-001's post-run K-tier order diagnostic.

    python scripts/run_tc001_k_tier_order.py

DESCRIPTIVE. Written after TC-001's verdict existed; carries no bar.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc001_k_tier_order import main  # noqa: E402

if __name__ == "__main__":
    main()
