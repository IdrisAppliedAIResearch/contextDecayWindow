from __future__ import annotations

import argparse
import json

from analysis.tc010_study import run_preflight, run_study


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "run"))
    args = parser.parse_args()
    result = run_preflight() if args.phase == "preflight" else run_study()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
