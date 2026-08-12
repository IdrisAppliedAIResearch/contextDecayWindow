from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.sal001_analyze import run
from src.analysis.sal001_shared import STUDY_ROOT


def parse_args() -> argparse.Namespace:
    root = STUDY_ROOT / "artifacts"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scores",
        type=Path,
        default=root / "sal001_scores" / "scores.json",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=root / "sal001_seal" / "SEALED_LABELS_DO_NOT_OPEN.json",
    )
    parser.add_argument(
        "--preflight",
        type=Path,
        default=root / "sal001_preflight" / "preflight.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "sal001_analysis" / "analysis.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run(args.scores, args.labels, args.preflight, args.output)
    print(json.dumps(result["verdict"], sort_keys=True))

