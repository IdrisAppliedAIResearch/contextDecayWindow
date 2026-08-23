#!/usr/bin/env python
"""Run TC-005 G0 or the registered two-process offline outcome phase."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

REPO_ROOT = Path(__file__).resolve().parents[1]
for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from analysis.tc005_study import (  # noqa: E402
    G0_ROOT,
    OUTCOME_ROOT,
    TC005Error,
    analyze_worker,
    compute_worker,
    run_g0,
    run_precondition,
    write_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("g0", "run", "worker"), required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _suite() -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", "-q"]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": "src"},
        check=False,
    )
    if result.returncode:
        raise TC005Error(result.stdout + result.stderr)
    last = next(
        (line for line in reversed(result.stdout.splitlines()) if " passed" in line),
        "",
    )
    return {
        "status": "PASS",
        "command": ".venv\\Scripts\\python.exe -m pytest -q",
        "summary": last,
    }


def _worker_process(output: Path) -> None:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--phase",
        "worker",
        "--output",
        str(output),
    ]
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": "src"},
        check=True,
    )


def main() -> int:
    args = parse_args()
    if args.phase == "worker":
        if args.output is None:
            raise TC005Error("Worker requires --output")
        print(json.dumps(compute_worker(args.output), indent=2))
        return 0
    if args.phase == "g0":
        result = run_g0(args.output or G0_ROOT, _suite())
        print(json.dumps({"status": result["status"], "calls": result["calls"]}, indent=2))
        return 0

    precondition = run_precondition()
    output = args.output or OUTCOME_ROOT
    if output.exists() and any(output.iterdir()):
        raise TC005Error("Registered run output directory is not empty")
    with tempfile.TemporaryDirectory(prefix="tc005-run-") as directory:
        root = Path(directory)
        first = root / "first"
        second = root / "second"
        _worker_process(first)
        _worker_process(second)
        one = json.loads((first / "worker_digest.json").read_text(encoding="utf-8"))
        two = json.loads((second / "worker_digest.json").read_text(encoding="utf-8"))
        if one != two:
            raise TC005Error("Fresh-process deterministic replay differed")
        result = analyze_worker(first, output)
    (output / "run_precondition.json").write_text(
        json.dumps(precondition, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "determinism.json").write_text(
        json.dumps(
            {"status": "PASS", "fresh_processes": 2, "worker_digest": one},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "run_header.json").write_text(
        json.dumps(
            {
                "schema": "tc005-run-header-v1",
                "command": ".venv\\Scripts\\python.exe scripts\\run_tc005_study.py --phase run",
                "parallel": 1,
                "speculative_decoding": False,
                "threading": {
                    key: os.environ.get(key)
                    for key in (
                        "OMP_NUM_THREADS",
                        "OPENBLAS_NUM_THREADS",
                        "MKL_NUM_THREADS",
                        "NUMEXPR_NUM_THREADS",
                    )
                },
                "precondition": precondition,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_manifest(output)
    print(json.dumps({"status": result["status"], "selection": result["selection"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
