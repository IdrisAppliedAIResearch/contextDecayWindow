from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.sup001_benchmark import ARTIFACT_ROOT, run


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path, default=ARTIFACT_ROOT / "sup001_corpus"
    )
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), sort_keys=True))
