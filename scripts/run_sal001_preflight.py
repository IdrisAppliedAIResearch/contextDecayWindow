from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.sal001_preflight import run
from src.analysis.sal001_shared import DEFAULT_MODEL_PATH, STUDY_ROOT


def parse_args() -> argparse.Namespace:
    artifacts = STUDY_ROOT / "artifacts"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path.home() / "Downloads" / "longmemeval_s_cleaned.json",
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument(
        "--seal-dir", type=Path, default=artifacts / "sal001_seal"
    )
    parser.add_argument(
        "--scores", type=Path, default=artifacts / "sal001_scores" / "scores.json"
    )
    parser.add_argument(
        "--repeat-scores",
        type=Path,
        default=artifacts / "sal001_scores" / "repeat_first_three.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=artifacts / "sal001_preflight" / "preflight.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run(
        args.dataset,
        args.model,
        args.seal_dir,
        args.scores,
        args.repeat_scores,
        args.output,
    )
    print(json.dumps({"status": result["status"], "digest": result["canonical_digest"]}, sort_keys=True))
