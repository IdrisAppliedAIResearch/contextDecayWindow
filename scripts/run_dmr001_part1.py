"""Execute the DMR-001 Part 1 exploration and write its committed record.

Part 1 characterizes the proposed mechanism on committed streams before any
parameter or bar is locked. The script also re-derives the decision digests in
a fresh child process so two-process determinism is executed, not asserted.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.dmr001_corpus import select_sessions, write_json  # noqa: E402
from src.analysis.dmr001_exploration import (  # noqa: E402
    ExploratoryConfig,
    decision_digest,
    normalized_stream,
    run_exploratory_former,
)
from src.analysis.dmr001_part1 import _sessions_by_split, build_part1_record  # noqa: E402

DEFAULT_OUTPUT = (
    ROOT
    / "experiments"
    / "components"
    / "biological_memory"
    / "dmr_001"
    / "exploration"
    / "DMR_001_PART1_EXPLORATION.json"
)

PROBE_CONFIGS = {
    "reference": ExploratoryConfig(
        rho=0.5, drift_threshold=0.25, min_event_size=3, max_event_size=64
    ),
    "tight": ExploratoryConfig(
        rho=0.9, drift_threshold=0.10, min_event_size=2, max_event_size=32
    ),
}


def compute_digests() -> dict[str, str]:
    sessions = select_sessions(ROOT)
    development, heldout = _sessions_by_split(sessions)
    digests: dict[str, str] = {}
    for split_name, split_sessions in (("development", development), ("holdout", heldout)):
        stream = normalized_stream(split_sessions)
        for config_name, config in PROBE_CONFIGS.items():
            digests[f"{split_name}:{config_name}"] = decision_digest(
                run_exploratory_former(stream, config)
            )
    return digests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    parser.add_argument(
        "--digests-only",
        action="store_true",
        help="print the decision digests as JSON and exit; used for the fresh-process check",
    )
    arguments = parser.parse_args()

    if arguments.digests_only:
        print(json.dumps(compute_digests(), sort_keys=True))
        return 0

    record = build_part1_record(ROOT)

    first_pass = compute_digests()
    child = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--digests-only"],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(ROOT),
    )
    second_pass = json.loads(child.stdout)

    record["determinism"]["two_process"] = {
        "configs": {
            name: {
                "rho": config.rho,
                "drift_threshold": config.drift_threshold,
                "min_event_size": config.min_event_size,
                "max_event_size": config.max_event_size,
            }
            for name, config in PROBE_CONFIGS.items()
        },
        "first_process": first_pass,
        "second_process": second_pass,
        "identical": first_pass == second_pass,
    }
    record["determinism"]["platform"] = {
        "executed_on": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "numpy": __import__("numpy").__version__,
        "second_platform_executed": False,
        "limitation": (
            "Only one platform is available in this checkout. The reduction "
            "contract removes the usual cross-platform hazard by routing every "
            "reduction through math.fsum instead of BLAS, but a second platform "
            "has not been executed and the cross-platform claim is not made."
        ),
    }

    if not record["determinism"]["two_process"]["identical"]:
        print("Two-process determinism FAILED", file=sys.stderr)
        return 1

    digest = write_json(arguments.output, record, allow_overwrite=arguments.allow_overwrite)

    counts = record["counts"]
    print("DMR-001 Part 1 exploration")
    print(
        f"  development         : {counts['development_sessions']} sessions, "
        f"{counts['development_episodes']} episodes"
    )
    print(
        f"  holdout             : {counts['holdout_sessions']} sessions, "
        f"{counts['holdout_episodes']} episodes"
    )
    print(f"  two-process identical: {record['determinism']['two_process']['identical']}")
    print(f"  artifact sha256     : {digest}")
    print(f"  artifact            : {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
