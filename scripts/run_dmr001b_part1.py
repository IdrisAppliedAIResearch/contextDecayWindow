"""DMR-001B Part 1: sweep adaptive drift rules against DMR-001's fixed rule.

Diagnostic. Both corpora were read by DMR-001, so no confirmatory claim is
available; the question is only whether a rule form exists that is not
cap-dominated on both conversation families.
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
from src.analysis.dmr001b_exploration import (  # noqa: E402
    EXPLORATION_SCHEMA,
    AdaptiveConfig,
    annotated_boundary_indices,
    decision_digest,
    family_streams,
    normalized_stream,
    run_adaptive_former,
    summarize,
)

DEFAULT_OUTPUT = (
    ROOT
    / "experiments"
    / "components"
    / "biological_memory"
    / "dmr_001b"
    / "exploration"
    / "DMR_001B_PART1_EXPLORATION.json"
)

TOLERANCE = 1
MIN_EVENT_SIZE = 5
WINDOWS = (16, 32, 64)
WARMUP = 16
CAPS = (32, None)

PARAMS = {
    "fixed": (0.55, 0.60, 0.65, 0.70, 0.75),
    "percentile": (0.80, 0.85, 0.90, 0.95, 0.975),
    "robust_z": (1.0, 1.5, 2.0, 2.5, 3.0),
    "ratio": (1.10, 1.20, 1.30, 1.40, 1.50),
}


def candidate_configs() -> list[AdaptiveConfig]:
    configs: list[AdaptiveConfig] = []
    for cap in CAPS:
        for param in PARAMS["fixed"]:
            configs.append(
                AdaptiveConfig(
                    rule="fixed",
                    param=param,
                    window=WINDOWS[0],
                    warmup=0,
                    min_event_size=MIN_EVENT_SIZE,
                    max_event_size=cap,
                )
            )
        for rule in ("percentile", "robust_z", "ratio"):
            for param in PARAMS[rule]:
                for window in WINDOWS:
                    configs.append(
                        AdaptiveConfig(
                            rule=rule,
                            param=param,
                            window=window,
                            warmup=WARMUP,
                            min_event_size=MIN_EVENT_SIZE,
                            max_event_size=cap,
                        )
                    )
    return configs


def build_record() -> dict:
    sessions = select_sessions(ROOT)
    families = family_streams(sessions)
    prepared = {
        name: (
            normalized_stream(members),
            annotated_boundary_indices(members),
            sum(session.episode_count for session in members),
        )
        for name, members in families.items()
    }

    rows = []
    for config in candidate_configs():
        row = {
            "label": config.label(),
            "rule": config.rule,
            "param": config.param,
            "window": config.window,
            "warmup": config.warmup,
            "max_event_size": config.max_event_size,
            "families": {},
        }
        for name, (stream, annotated, length) in prepared.items():
            decisions = run_adaptive_former(stream, config)
            row["families"][name] = summarize(
                decisions, annotated, tolerance=TOLERANCE, stream_length=length
            )
        claims = [
            value["agreement_claims_only"]["f1"] for value in row["families"].values()
        ]
        capped = [value["capped_fraction_of_events"] for value in row["families"].values()]
        row["worst_family_f1"] = min(claims)
        row["mean_family_f1"] = sum(claims) / len(claims)
        row["worst_family_capped_fraction"] = max(capped)
        rows.append(row)

    return {
        "schema": EXPLORATION_SCHEMA,
        "study": "DMR-001B",
        "status": "PART1_DIAGNOSTIC_NO_CONFIRMATORY_CLAIM",
        "predecessor": "DMR-001, stopped at G3, DEGENERATE_FORMATION",
        "scope": (
            "Both corpora were read by DMR-001, so under the arc's invariant 7 they are "
            "development sets. This sweep can show whether a rule form exists that is "
            "not cap-dominated on both families; it cannot confirm one."
        ),
        "grid": {
            "tolerance": TOLERANCE,
            "min_event_size": MIN_EVENT_SIZE,
            "windows": list(WINDOWS),
            "warmup": WARMUP,
            "caps": ["32", "none"],
            "params": {rule: list(values) for rule, values in PARAMS.items()},
            "configs": len(candidate_configs()),
        },
        "families": {
            name: {
                "sessions": len(members),
                "episodes": sum(session.episode_count for session in members),
                "annotated_boundaries": len(annotated_boundary_indices(members)),
            }
            for name, members in families.items()
        },
        "rows": rows,
    }


def digests() -> dict[str, str]:
    sessions = select_sessions(ROOT)
    out = {}
    for name, members in family_streams(sessions).items():
        stream = normalized_stream(members)
        config = AdaptiveConfig(
            rule="percentile",
            param=0.90,
            window=32,
            warmup=WARMUP,
            min_event_size=MIN_EVENT_SIZE,
            max_event_size=32,
        )
        out[name] = decision_digest(run_adaptive_former(stream, config))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    parser.add_argument("--digests-only", action="store_true")
    arguments = parser.parse_args()

    if arguments.digests_only:
        print(json.dumps(digests(), sort_keys=True))
        return 0

    record = build_record()
    first = digests()
    child = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--digests-only"],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(ROOT),
    )
    second = json.loads(child.stdout)
    record["determinism"] = {
        "first_process": first,
        "second_process": second,
        "identical": first == second,
        "platform": platform.platform(),
        "second_platform_executed": False,
    }
    if not record["determinism"]["identical"]:
        print("Two-process determinism FAILED", file=sys.stderr)
        return 1

    digest = write_json(arguments.output, record, allow_overwrite=arguments.allow_overwrite)

    print("DMR-001B Part 1 (diagnostic)")
    for name, value in record["families"].items():
        print(
            f"  {name}: {value['sessions']} sessions, {value['episodes']} episodes, "
            f"{value['annotated_boundaries']} annotated boundaries"
        )
    print(f"  configs swept        : {record['grid']['configs']}")
    print(f"  two-process identical: {record['determinism']['identical']}")
    print(f"  artifact sha256      : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
