#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.tc009_exploration import explore  # noqa: E402


if __name__ == "__main__":
    result = explore()
    print(json.dumps({"status": result["status"], "trace": result["trace"], "elapsed_seconds": result["elapsed_seconds"]}, indent=2))
