#!/usr/bin/env python
"""Run TC-002 Preflight PF4: discordant counts, with the direction withheld.

    python scripts/run_tc002_reachability.py \
        --output-dir experiments/components/tier_cost/artifacts/tc002/preflight

The artifact this writes says how many questions each registered contrast can
separate. It does not say which way any of them fall, and the module refuses to
emit a key that would. Zero model calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc002_reachability import measure  # noqa: E402

DEFAULT_OUTPUT = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts"
    / "tc002" / "preflight"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = measure(arguments.output_dir)
    print(
        f"wrote {arguments.output_dir / 'tc002_preflight_pf4_reachability.json'}"
    )
    for budget, block in sorted(result["budgets"].items()):
        print(f"--- {budget} characters ---")
        print(f"  evaluable {block['evaluable_questions']}")
        print(
            "  fill orders deliver an identical set on "
            f"{block['fill_order_delivers_identical_set']}"
        )
        for contrast, endpoints in sorted(block["contrasts"].items()):
            for endpoint, row in sorted(endpoints.items()):
                print(
                    f"  {contrast:26s} {endpoint:18s} "
                    f"discordant {row['discordant_pairs']:4d}  "
                    f"best attainable p {row['smallest_one_sided_exact_p_at_this_n']:.3g}"
                )


if __name__ == "__main__":
    main()
