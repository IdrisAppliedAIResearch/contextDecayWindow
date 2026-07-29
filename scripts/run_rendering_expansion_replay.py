from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.rendering_expansion_replay import generate_pre_fix_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run DR-001 pre-fix replay and expansion measurement."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for deterministic CSV, JSON, and Markdown artifacts.",
    )
    args = parser.parse_args()
    summary = generate_pre_fix_artifacts(args.output_dir)
    print(f"G-R1 {summary['g_r1']['status']}")
    if summary["g_r1"]["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

