"""Restarting process supervisor for the paid HH-004 stages."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from analysis.hh002_run import _write_json
from analysis.hh004_contexts import ARM, EXPECTED, RUN
from analysis.hh004_run import stage_counts

HEALTH = RUN / "health.json"
LOG = RUN / "supervisor.log"
POLL_SECONDS = 30
STALE_SECONDS = 20 * 60
MAX_RESTARTS = 5


def _checkpoint(stage: str) -> Path:
    return RUN / ARM / ("judged_r1.json" if stage == "judge" else "predictions.json")


def _complete(stage: str, counts: dict[str, int]) -> bool:
    if stage == "pilot":
        return counts["answers"] >= 8 and counts["judgements"] >= 8
    if stage == "answers":
        return counts["answers"] == EXPECTED
    return counts["judgements"] == EXPECTED


def _health(status: str, stage: str, child_pid: int | None,
            restarts: int, error: str | None = None) -> dict[str, Any]:
    counts = stage_counts()
    checkpoint = _checkpoint(stage)
    age = time.time() - checkpoint.stat().st_mtime if checkpoint.exists() else None
    payload = {
        "schema": "hh004-health-v1", "status": status, "stage": stage,
        "supervisor_pid": os.getpid(), "child_pid": child_pid,
        "answers": counts["answers"], "judgements": counts["judgements"],
        "expected": EXPECTED, "checkpoint_age_seconds": age,
        "restarts": restarts, "last_error": error, "updated_at": time.time(),
    }
    _write_json(HEALTH, payload)
    return payload


def run() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    restarts = 0
    with LOG.open("a", encoding="utf-8", buffering=1) as log:
        for stage in ("pilot", "answers", "judge"):
            while not _complete(stage, stage_counts()):
                if restarts > MAX_RESTARTS:
                    _health("NEEDS_ATTENTION", stage, None, restarts,
                            "automatic restart budget exhausted")
                    return 2
                command = [sys.executable, "-m", "analysis.hh004_run", stage]
                process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2],
                                           stdout=log, stderr=subprocess.STDOUT,
                                           env=os.environ.copy())
                _health("RUNNING", stage, process.pid, restarts)
                last_counts = stage_counts()
                last_progress = time.time()
                failure: str | None = None
                while process.poll() is None:
                    time.sleep(POLL_SECONDS)
                    counts = stage_counts()
                    if counts != last_counts:
                        last_counts, last_progress = counts, time.time()
                    if time.time() - last_progress > STALE_SECONDS:
                        failure = f"no checkpoint progress for {STALE_SECONDS} seconds"
                        process.terminate()
                        try:
                            process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        break
                    _health("RUNNING", stage, process.pid, restarts)
                code = process.returncode
                if failure is None and code == 0 and _complete(stage, stage_counts()):
                    _health("STAGE_COMPLETE", stage, None, restarts)
                    break
                restarts += 1
                failure = failure or f"child exited {code}"
                _health("RESTARTING", stage, None, restarts, failure)
                time.sleep(min(60, 5 * restarts))
        _health("COMPLETE", "judge", None, restarts)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())


__all__ = ["HEALTH", "MAX_RESTARTS", "POLL_SECONDS", "STALE_SECONDS", "run"]
