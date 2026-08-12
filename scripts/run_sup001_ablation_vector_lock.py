from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))
sys.path.insert(0, str(REPO_ROOT))

from src.analysis.sup001_ablation_vectors import capture


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    result = capture(args.model)
    print(json.dumps({"status": result["status"], "texts": result["text_count"]}))
