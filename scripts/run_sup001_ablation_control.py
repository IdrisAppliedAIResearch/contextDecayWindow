from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))
sys.path.insert(0, str(REPO_ROOT))

from src.analysis.sup001_ablation_control import run


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--server-url", default="http://127.0.0.1:8080")
    parser.add_argument("--server-binary", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output, args.expected_commit, args.server_url, args.server_binary)
    print(json.dumps({"status": result["status"], "probes": result["probe_count"]}))
