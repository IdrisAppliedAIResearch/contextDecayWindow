from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.sal001_score import run
from src.analysis.sal001_shared import DEFAULT_MODEL_PATH, STUDY_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=STUDY_ROOT / "artifacts" / "sal001_seal" / "scorer_manifest.json",
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--session-limit", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run(
        args.manifest,
        args.model,
        args.output,
        session_limit=args.session_limit,
    )
    print(
        json.dumps(
            {
                "deterministic_digest": result["deterministic_digest"],
                "records": len(result["records"]),
                "sessions": len(result["sessions"]),
            },
            sort_keys=True,
        )
    )
