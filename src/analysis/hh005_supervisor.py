"""Restarting process supervisor for HH-005."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from analysis.hh005_contexts import ARMS, EXPECTED, RUN
from analysis.hh005_run import stage_counts

HEALTH = RUN / "health.json"
LOG = RUN / "supervisor.log"
POLL_SECONDS = 30
STALE_SECONDS = 20 * 60
MAX_RESTARTS = 5


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _checkpoint(arm: str, stage: str) -> Path:
    return RUN / arm / ("judged_r1.json" if stage == "judge" else "predictions.json")


def _complete(stage: str, counts: dict[str, int]) -> bool:
    return ((counts["answers"] >= 8 and counts["judgements"] >= 8) if stage == "pilot"
            else counts["answers"] == EXPECTED if stage == "answers"
            else counts["judgements"] == EXPECTED)


def _health(status: str, arm: str, stage: str, pid: int | None, restarts: int,
            error: str | None = None) -> None:
    counts = stage_counts(arm)
    checkpoint = _checkpoint(arm, stage)
    age = time.time() - checkpoint.stat().st_mtime if checkpoint.exists() else None
    all_counts = {value: stage_counts(value) for value in ARMS.values()}
    _write(HEALTH, {"schema": "hh005-health-v2", "status": status, "arm": arm,
                    "stage": stage, "all_counts": all_counts,
                    "supervisor_pid": os.getpid(), "child_pid": pid,
                    "answers": counts["answers"], "judgements": counts["judgements"],
                    "expected": EXPECTED, "checkpoint_age_seconds": age,
                    "restarts": restarts, "last_error": error, "updated_at": time.time()})


def run() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    restarts = 0
    schedule = ([(arm, "pilot") for arm in ARMS.values()] +
                [(arm, "answers") for arm in ARMS.values()] +
                [(arm, "judge") for arm in ARMS.values()])
    with LOG.open("a", encoding="utf-8", buffering=1) as log:
        for arm, stage in schedule:
            while not _complete(stage, stage_counts(arm)):
                if restarts > MAX_RESTARTS:
                    _health("NEEDS_ATTENTION", arm, stage, None, restarts, "restart budget exhausted")
                    return 2
                process = subprocess.Popen([sys.executable, "-m", "analysis.hh005_run", arm, stage],
                                           cwd=Path(__file__).resolve().parents[2], stdout=log,
                                           stderr=subprocess.STDOUT, env=os.environ.copy())
                _health("RUNNING", arm, stage, process.pid, restarts)
                prior, progress, failure = stage_counts(arm), time.time(), None
                while process.poll() is None:
                    time.sleep(POLL_SECONDS)
                    current = stage_counts(arm)
                    if current != prior:
                        prior, progress = current, time.time()
                    if time.time() - progress > STALE_SECONDS:
                        failure = f"no checkpoint progress for {STALE_SECONDS} seconds"
                        process.terminate()
                        try:
                            process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            process.kill(); process.wait()
                        break
                    _health("RUNNING", arm, stage, process.pid, restarts)
                if failure is None and process.returncode == 0 and _complete(stage, stage_counts(arm)):
                    _health("STAGE_COMPLETE", arm, stage, None, restarts)
                    break
                restarts += 1
                _health("RESTARTING", arm, stage, None, restarts,
                        failure or f"child exited {process.returncode}")
                time.sleep(min(60, 5 * restarts))
        _health("COMPLETE", list(ARMS.values())[-1], "judge", None, restarts)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
