"""Write the metadata-only inventory for the locked LoCoMo holdout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from analysis.locomo_holdout_inventory import write  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write(args.data, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
