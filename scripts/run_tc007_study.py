#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.tc007_study import (  # noqa: E402
    G0_ROOT, OUTCOME_ROOT, TC007Error, analyze_worker, compute_worker,
    run_g0, run_precondition, write_manifest,
)


def _suite():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True,
        capture_output=True, env={**os.environ, "PYTHONPATH": "src"}, check=False,
    )
    if result.returncode:
        raise TC007Error(result.stdout + result.stderr)
    summary = next((line for line in reversed(result.stdout.splitlines()) if " passed" in line), "")
    return {"status": "PASS", "command": ".venv\\Scripts\\python.exe -m pytest -q", "summary": summary}


def _worker(output: Path):
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--phase", "worker", "--output", str(output)],
        cwd=ROOT, env={**os.environ, "PYTHONPATH": "src"}, check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("g0", "run", "worker"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.phase == "worker":
        if not args.output:
            raise TC007Error("Worker requires --output")
        print(json.dumps(compute_worker(args.output), indent=2))
        return 0
    if args.phase == "g0":
        result = run_g0(args.output or G0_ROOT, _suite())
        print(json.dumps({"status": result["status"], "calls": result["calls"]}, indent=2))
        return 0

    precondition = run_precondition()
    output = args.output or OUTCOME_ROOT
    if output.exists() and any(output.iterdir()):
        raise TC007Error("Registered run output is not empty")
    with tempfile.TemporaryDirectory(prefix="tc007-run-") as directory:
        first, second = Path(directory) / "first", Path(directory) / "second"
        _worker(first)
        _worker(second)
        one = json.loads((first / "worker_digest.json").read_text(encoding="utf-8"))
        two = json.loads((second / "worker_digest.json").read_text(encoding="utf-8"))
        if one != two:
            raise TC007Error("Fresh-process deterministic replay differed")
        result = analyze_worker(first, output)
    (output / "run_precondition.json").write_text(json.dumps(precondition, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "determinism.json").write_text(json.dumps({"status": "PASS", "fresh_processes": 2, "worker_digest": one}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "run_header.json").write_text(json.dumps({
        "schema": "tc007-run-header-v1",
        "command": ".venv\\Scripts\\python.exe scripts\\run_tc007_study.py --phase run",
        "parallel": 1,
        "speculative_decoding": False,
        "precondition": precondition,
        "threading": {key: os.environ.get(key) for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(output)
    print(json.dumps({"status": result["status"], "selection": result["selection"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
