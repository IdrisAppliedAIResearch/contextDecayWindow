"""Execute one registered NF-004 stage without overwriting artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "episodic" / "src"))

from analysis.nf004_measurement import (  # noqa: E402
    HOLDOUT_IDS,
    adapt_split,
    canonical_bytes,
    capture_vectors,
)
from analysis.nf004_study import (  # noqa: E402
    G6_ARTIFACT,
    G7_ARTIFACT,
    HOLDOUT_VECTOR_MANIFEST,
    PREFLIGHT_ARTIFACT,
    REPO_ROOT,
    run_g6,
    run_g7,
    run_preflight,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage", choices=("capture", "preflight", "g6", "g7")
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--holdout-cache", type=Path, required=True)
    parser.add_argument("--development-cache", type=Path)
    parser.add_argument("--embedding-model", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.stage == "capture":
        if args.embedding_model is None:
            parser.error("capture requires --embedding-model")
        output = args.output or REPO_ROOT / HOLDOUT_VECTOR_MANIFEST
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite {output}")
        records = adapt_split(args.data, HOLDOUT_IDS)
        payload = capture_vectors(
            records, args.embedding_model, args.holdout_cache
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_bytes(payload))
        print(
            json.dumps(
                {
                    "stage": "capture",
                    "entries": payload["cache"]["entries"],
                    "manifest": str(output),
                },
                sort_keys=True,
            )
        )
        return 0

    if args.stage == "preflight":
        if args.development_cache is None:
            parser.error("preflight requires --development-cache")
        output = args.output or REPO_ROOT / PREFLIGHT_ARTIFACT
        payload = run_preflight(
            args.data,
            args.holdout_cache,
            args.development_cache,
            output,
        )
        print(json.dumps({"stage": "preflight", "status": payload["status"]}))
        return 0

    if args.stage == "g6":
        output = args.output or REPO_ROOT / G6_ARTIFACT
        payload = run_g6(args.data, args.holdout_cache, output)
        print(
            json.dumps(
                {
                    "stage": "g6",
                    "status": payload["status"],
                    "primary_n": payload["population"]["primary"],
                },
                sort_keys=True,
            )
        )
        return 0

    output = args.output or REPO_ROOT / G7_ARTIFACT
    payload = run_g7(args.data, args.holdout_cache, output)
    print(
        json.dumps(
            {
                "stage": "g7",
                "status": payload["status"],
                "disposition": payload["disposition"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
