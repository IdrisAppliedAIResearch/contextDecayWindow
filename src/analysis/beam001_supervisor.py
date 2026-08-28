"""Checkpoint-aware supervisor for the interrupted BEAM-001 continuation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from analysis.beam001_live import RUN, ROOT, read_jsonl, write_json


CONTINUATION_SECONDS = 14_700
EXPECTED_PREFIX_ROWS = 236


class SupervisorError(RuntimeError):
    pass


def initialize_continuation(
    run: Path,
    *,
    now: float | None = None,
    runtime_seconds: int = CONTINUATION_SECONDS,
    expected_prefix_rows: int = EXPECTED_PREFIX_ROWS,
) -> dict[str, Any]:
    continuation_path = run / "interruption_continuation.json"
    if continuation_path.exists():
        return json.loads(continuation_path.read_text(encoding="utf-8"))

    checkpoint = read_jsonl(run / "answers.checkpoint.jsonl")
    ids = [str(row["custom_id"]) for row in checkpoint]
    if len(ids) != expected_prefix_rows or len(set(ids)) != expected_prefix_rows:
        raise SupervisorError(
            f"Expected {expected_prefix_rows} unique checkpoint rows, found "
            f"{len(ids)} rows and {len(set(ids))} ids"
        )
    runtime_path = run / "runtime_budget.json"
    if not runtime_path.exists():
        raise SupervisorError("Original runtime budget is missing")
    prior = json.loads(runtime_path.read_text(encoding="utf-8"))
    started = time.time() if now is None else now
    continuation = {
        "checkpoint_rows_adopted": expected_prefix_rows,
        "deadline_unix": started + runtime_seconds,
        "deviation": "DEVIATION_002",
        "original_deadline_unix": float(prior["deadline_unix"]),
        "original_started_at_unix": float(prior["started_at_unix"]),
        "runtime_seconds": runtime_seconds,
        "started_at_unix": started,
        "status": "AUTHORIZED",
    }
    write_json(continuation_path, continuation)
    write_json(runtime_path, continuation)
    return continuation


def terminal_state(run: Path, deadline_unix: float) -> str | None:
    if (run / "failure.json").exists():
        return "HANDLED_FAILURE"
    if (run / "results.json").exists():
        return "COMPLETE"
    if time.time() >= deadline_unix:
        return "RUNTIME_BUDGET_EXCEEDED"
    return None


def supervise(run: Path, command: Sequence[str]) -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SupervisorError("OPENAI_API_KEY is missing")
    continuation = initialize_continuation(run)
    deadline = float(continuation["deadline_unix"])
    attempts = 0
    log_path = run / "background.log"
    supervisor_pid = os.getpid()
    write_json(
        run / "background_launch.json",
        {
            "command": list(command),
            "log": log_path.name,
            "pid": supervisor_pid,
            "role": "checkpoint_supervisor",
            "started_at_unix": time.time(),
        },
    )

    while True:
        terminal = terminal_state(run, deadline)
        if terminal is not None:
            write_json(
                run / "supervisor.json",
                {
                    "attempts": attempts,
                    "status": terminal,
                    "supervisor_pid": supervisor_pid,
                    "updated_at_unix": time.time(),
                },
            )
            return 0 if terminal == "COMPLETE" else 1

        attempts += 1
        with log_path.open("a", encoding="utf-8", newline="\n") as log:
            child = subprocess.Popen(
                list(command),
                cwd=ROOT,
                env=os.environ.copy(),
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            write_json(
                run / "supervisor.json",
                {
                    "attempts": attempts,
                    "child_pid": child.pid,
                    "status": "RUNNING",
                    "supervisor_pid": supervisor_pid,
                    "updated_at_unix": time.time(),
                },
            )
            return_code = child.wait()

        terminal = terminal_state(run, deadline)
        if terminal is not None:
            continue
        write_json(
            run / "supervisor.json",
            {
                "attempts": attempts,
                "last_child_exit_code": return_code,
                "status": "RESTARTING_AFTER_HARD_EXIT",
                "supervisor_pid": supervisor_pid,
                "updated_at_unix": time.time(),
            },
        )
        time.sleep(2)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=RUN)
    args = parser.parse_args(argv)
    command = [sys.executable, "-u", "-m", "analysis.beam001_live", "run"]
    try:
        return supervise(args.run, command)
    except Exception as error:  # noqa: BLE001
        write_json(
            args.run / "supervisor.json",
            {
                "error": str(error),
                "error_type": type(error).__name__,
                "status": "SUPERVISOR_FAILED",
                "updated_at_unix": time.time(),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
