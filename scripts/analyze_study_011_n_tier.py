"""Write the N-tier characterization artifact for Study 011.

Offline. No model call, no embedding call, no mechanism change. Reads the
four committed run directories and writes a single JSON artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.study_011_n_tier import STUDY_ROOT, analyze

DEFAULT_OUTPUT = STUDY_ROOT / "analysis" / "n_tier_characterization.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = analyze()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {args.output}")
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
