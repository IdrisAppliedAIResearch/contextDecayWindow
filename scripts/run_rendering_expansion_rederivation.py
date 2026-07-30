from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.rendering_expansion_rederivation import (
    generate_rederivation,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the mandatory DR-001 downstream re-derivation."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = generate_rederivation(args.output_dir)
    print(f"DR-001 re-derivation {result['status']}")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

