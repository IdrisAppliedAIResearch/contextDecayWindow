#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.tc009_reachability import generate  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
