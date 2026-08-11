from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.sup001_vectors import CACHE_PATH, MANIFEST_PATH, capture


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=CACHE_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    result = capture(args.model, args.cache, args.manifest)
    print(json.dumps({"status": result["status"], "requests": result["request_count"]}))
