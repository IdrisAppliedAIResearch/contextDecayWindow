"""Run the locked LoCoMo and LongMemEval development controls."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "episodic" / "src"))

from analysis.ranking_budget_controls import write  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locomo-data", type=Path, required=True)
    parser.add_argument("--locomo-cache", type=Path, required=True)
    parser.add_argument("--vector-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write(
        REPO,
        args.locomo_data,
        args.locomo_cache,
        args.vector_manifest,
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
