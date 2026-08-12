from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.sup001_part1 import reconstruction_digest, run_part1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest-only", action="store_true")
    args = parser.parse_args()
    result = reconstruction_digest() if args.digest_only else run_part1()
    print(json.dumps(result if args.digest_only else {"status": result["status"]}, sort_keys=True))
