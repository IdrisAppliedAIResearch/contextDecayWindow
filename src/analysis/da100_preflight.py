"""Registered full-population runtime gate for DA-100."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.da013_preflight import sha256_file
from analysis.da098_budget_replay import DA098Error, run_preflight

DA098_ALLOCATION_SHA256 = "f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9"


def run_da100(dataset_path: Path, cache_path: Path, manifest_path: Path,
              da035_path: Path, output_dir: Path) -> dict[str, Any]:
    base = run_preflight(dataset_path, cache_path, manifest_path, da035_path, output_dir)
    artifact = output_dir / "blind_allocations.jsonl.gz"
    if sha256_file(artifact) != DA098_ALLOCATION_SHA256:
        raise DA098Error("DA-100 allocation differs from sealed DA-098")
    runs = [base["runtime"]["allocation_ms"], base["runtime"]["replay_allocation_ms"]]
    production = (all(run["p50"] <= 25 and run["p95"] <= 100
                      and run["max"] <= 200 for run in runs))
    runtime = (all(run["p95"] <= 200 and run["max"] <= 500 for run in runs)
               and base["runtime"]["total_wall_ms"] <= 8 * 60 * 1000)
    if production:
        disposition = "FUSED_SINGLETON_PRODUCTION_SIGNAL"
    elif runtime:
        disposition = "FUSED_SINGLETON_RUNTIME_SIGNAL"
    else:
        disposition = "NO_FUSED_SINGLETON_RUNTIME_SIGNAL"
    result = {
        "schema": "da100-fused-singleton-runtime-v1",
        "status": "PASS" if production or runtime else "FAIL",
        "disposition": disposition,
        "allocation_sha256": sha256_file(artifact),
        "equivalence": {
            "rows": base["rows"],
            "byte_identical_replay": base["replay_byte_identical"],
            "cache_misses": base["cache"]["misses"],
            "calls": base["calls"],
        },
        "runtime": base["runtime"],
    }
    (output_dir / "da100_preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


__all__ = ["run_da100"]
