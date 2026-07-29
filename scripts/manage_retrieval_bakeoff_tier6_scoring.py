from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.retrieval_bakeoff_tier6_scoring import (
    analyze_passes,
    finalize_scores,
    prepare_scoring,
    unseal_scores,
    validate_calibration_result,
    validate_rating_file,
    write_preflight,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    subparsers.add_parser("prepare")
    subparsers.add_parser("analyze")
    subparsers.add_parser("finalize")
    subparsers.add_parser("unseal")

    calibration = subparsers.add_parser("validate-calibration")
    calibration.add_argument("--result", type=Path, required=True)

    rating = subparsers.add_parser("validate-rating")
    rating.add_argument("--result", type=Path, required=True)
    rating.add_argument("--packet", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "preflight":
        result = write_preflight()
    elif args.command == "prepare":
        result = prepare_scoring()
    elif args.command == "analyze":
        result = analyze_passes()
    elif args.command == "finalize":
        result = finalize_scores()
    elif args.command == "unseal":
        result = unseal_scores()
    elif args.command == "validate-calibration":
        result = validate_calibration_result(args.result)
    elif args.command == "validate-rating":
        rows = validate_rating_file(args.result, args.packet)
        result = {"status": "PASS", "item_count": len(rows)}
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
