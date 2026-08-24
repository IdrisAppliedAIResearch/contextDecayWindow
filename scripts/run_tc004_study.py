"""Repository-root entry point for the registered TC-004 stages."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "episodic" / "src")]

from analysis.tc004_study import main


if __name__ == "__main__":
    main()
