#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.tc009_convex_protected_probe import run_preflight, run_probe  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=("preflight", "run"))
    args = parser.parse_args()
    result = run_preflight() if args.phase == "preflight" else run_probe()
    print(json.dumps({"status": result["status"]}, indent=2))
