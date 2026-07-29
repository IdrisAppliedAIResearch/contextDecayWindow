from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.rendering_expansion_replay import (
    generate_post_fix_artifacts,
    generate_pre_fix_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run DR-001 pre-fix replay and expansion measurement."
    )
    parser.add_argument(
        "--phase",
        choices=("pre", "post"),
        required=True,
        help="Replay phase. Pre must run before renderer implementation.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for deterministic CSV, JSON, and Markdown artifacts.",
    )
    args = parser.parse_args()
    if args.phase == "pre":
        summary = generate_pre_fix_artifacts(args.output_dir)
        gate = "g_r1"
        label = "G-R1"
    else:
        summary = generate_post_fix_artifacts(args.output_dir)
        gate = "g_r2"
        label = "G-R2"
    print(f"{label} {summary[gate]['status']}")
    if summary[gate]["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
