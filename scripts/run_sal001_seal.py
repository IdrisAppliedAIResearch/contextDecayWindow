from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.sal001_seal import run
from src.analysis.sal001_shared import REPO_ROOT, STUDY_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path.home() / "Downloads" / "longmemeval_s_cleaned.json",
    )
    parser.add_argument(
        "--tier2-registration",
        type=Path,
        default=REPO_ROOT
        / "experiments"
        / "external"
        / "longmemeval"
        / "EC_001_TIER2_SUBSET.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=STUDY_ROOT / "artifacts" / "sal001_seal",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run(args.dataset, args.tier2_registration, args.output_dir)
    print(json.dumps({"status": result["status"], "counts": result["counts"]}, sort_keys=True))

