from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis.dx002_context_growth import analyse, write_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the DX-002 context growth diagnostic over the committed "
            "Study 010 serialized prompts. Offline; makes no inference call."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result = analyse()
    write_artifacts(result, args.output_dir)
    decision = result["decision"]
    print(f"DX-002 {result['status']}")
    print(f"Branch {decision['branch']} - {decision['label']}")
    for entry in decision.get("climbing_parts", []):
        print(f"  still climbing: {entry}")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
