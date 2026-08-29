"""Checkpoint-aware supervisor for the interrupted BEAM-001 continuation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from analysis.beam001_live import RUN, ROOT, file_sha256, read_jsonl, write_json


CONTINUATION_SECONDS = 14_700
EXPECTED_PREFIX_ROWS = 236
JUDGE_REPAIR_SECONDS = 1_782
JUDGE_REPAIR_PREFIX_ROWS = 238
JUDGE_REPAIR_PREFIX_SHA256 = (
    "50346c6707cd084ddc4570a8a8eec5bd6ea46882f68e3e6a161175637ee52682"
)
JUDGE_REPAIR_PENDING_ROWS = 122
JUDGE_REPAIR_PENDING_SHA256 = (
    "f9a0e6344da7afb1bf6b35612b9316803bc185c75795426469e6d3b0dd8a4902"
)
JUDGE_REPAIR_FAILED_ID = (
    "33c2b09a0f2bab25631122351fcae938a65ee2f5389a95d58a463a0972214d22"
)
STRICT_REPAIR_SECONDS = 688
STRICT_REPAIR_PREFIX_ROWS = 359
STRICT_REPAIR_PREFIX_SHA256 = (
    "578adf3c37ece497401bc6caa9afd02d1b8860c09d2f54f94c4e2a0323e4754c"
)
STRICT_REPAIR_PENDING_ID = JUDGE_REPAIR_FAILED_ID


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


def initialize_judge_repair(
    run: Path,
    *,
    now: float | None = None,
    runtime_seconds: int = JUDGE_REPAIR_SECONDS,
    expected_prefix_rows: int = JUDGE_REPAIR_PREFIX_ROWS,
    expected_prefix_sha256: str = JUDGE_REPAIR_PREFIX_SHA256,
    expected_pending_rows: int = JUDGE_REPAIR_PENDING_ROWS,
    expected_pending_sha256: str = JUDGE_REPAIR_PENDING_SHA256,
    expected_failed_id: str = JUDGE_REPAIR_FAILED_ID,
) -> dict[str, Any]:
    repair_path = run / "judge_repair_runtime.json"
    failure_path = run / "failure.json"
    archived_failure = run / "failure_001.json"
    if repair_path.exists():
        repair = json.loads(repair_path.read_text(encoding="utf-8"))
        if failure_path.exists() and not archived_failure.exists():
            failure_path.replace(archived_failure)
        elif failure_path.exists():
            raise SupervisorError("Both active and archived repair failures exist")
        return repair
    if (run / "results.json").exists() or (run / "judgments.seal.json").exists():
        raise SupervisorError("Judge repair requested after a terminal result seal")

    if not failure_path.exists():
        raise SupervisorError("Judge repair failure artifact is missing")
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    if expected_failed_id not in str(failure.get("error", "")):
        raise SupervisorError("Judge repair failure identity drift")

    checkpoint_path = run / "judgments.checkpoint.blind.jsonl"
    checkpoint = read_jsonl(checkpoint_path)
    completed_ids = [str(row["custom_id"]) for row in checkpoint]
    if (
        len(completed_ids) != expected_prefix_rows
        or len(set(completed_ids)) != expected_prefix_rows
        or file_sha256(checkpoint_path) != expected_prefix_sha256
    ):
        raise SupervisorError("Judge repair checkpoint count, identity, or hash drift")

    surface = read_jsonl(run / "judge_surface.blind.jsonl")
    pending_ids = sorted(
        str(row["custom_id"])
        for row in surface
        if str(row["custom_id"]) not in set(completed_ids)
    )
    pending_payload = ("\n".join(pending_ids) + "\n").encode("ascii")
    if (
        len(pending_ids) != expected_pending_rows
        or hashlib.sha256(pending_payload).hexdigest() != expected_pending_sha256
    ):
        raise SupervisorError("Judge repair pending-set count or hash drift")

    if archived_failure.exists():
        raise SupervisorError("Judge repair failure archive already exists")
    started = time.time() if now is None else now
    repair = {
        "checkpoint_rows_adopted": expected_prefix_rows,
        "deadline_unix": started + runtime_seconds,
        "deviations": ["DEVIATION_002", "DEVIATION_003"],
        "pending_ids_sha256": expected_pending_sha256,
        "pending_requests": expected_pending_rows,
        "runtime_seconds": runtime_seconds,
        "started_at_unix": started,
        "status": "AUTHORIZED",
    }
    write_json(repair_path, repair)
    write_json(run / "runtime_budget.json", repair)
    failure_path.replace(archived_failure)
    return repair


def initialize_strict_judge_repair(
    run: Path,
    *,
    now: float | None = None,
    runtime_seconds: int = STRICT_REPAIR_SECONDS,
    expected_prefix_rows: int = STRICT_REPAIR_PREFIX_ROWS,
    expected_prefix_sha256: str = STRICT_REPAIR_PREFIX_SHA256,
    expected_pending_id: str = STRICT_REPAIR_PENDING_ID,
) -> dict[str, Any]:
    repair_path = run / "strict_judge_repair_runtime.json"
    failure_path = run / "failure.json"
    archived_failure = run / "failure_002.json"
    if repair_path.exists():
        repair = json.loads(repair_path.read_text(encoding="utf-8"))
        if failure_path.exists() and not archived_failure.exists():
            failure_path.replace(archived_failure)
        elif failure_path.exists():
            raise SupervisorError("Both active and archived strict-repair failures exist")
        return repair
    if (run / "results.json").exists() or (run / "judgments.seal.json").exists():
        raise SupervisorError("Strict judge repair requested after a terminal result seal")
    if not failure_path.exists():
        raise SupervisorError("Strict judge repair failure artifact is missing")
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    if expected_pending_id not in str(failure.get("error", "")):
        raise SupervisorError("Strict judge repair failure identity drift")

    checkpoint_path = run / "judgments.checkpoint.blind.jsonl"
    checkpoint = read_jsonl(checkpoint_path)
    completed_ids = [str(row["custom_id"]) for row in checkpoint]
    if (
        len(completed_ids) != expected_prefix_rows
        or len(set(completed_ids)) != expected_prefix_rows
        or file_sha256(checkpoint_path) != expected_prefix_sha256
    ):
        raise SupervisorError("Strict judge checkpoint count, identity, or hash drift")
    completed = set(completed_ids)
    surface = read_jsonl(run / "judge_surface.blind.jsonl")
    pending_ids = [
        str(row["custom_id"])
        for row in surface
        if str(row["custom_id"]) not in completed
    ]
    if pending_ids != [expected_pending_id]:
        raise SupervisorError("Strict judge pending identity drift")
    if archived_failure.exists():
        raise SupervisorError("Strict judge failure archive already exists")

    started = time.time() if now is None else now
    repair = {
        "checkpoint_rows_adopted": expected_prefix_rows,
        "deadline_unix": started + runtime_seconds,
        "deviations": ["DEVIATION_002", "DEVIATION_003", "DEVIATION_004"],
        "pending_id": expected_pending_id,
        "pending_requests": 1,
        "runtime_seconds": runtime_seconds,
        "started_at_unix": started,
        "status": "AUTHORIZED",
    }
    write_json(repair_path, repair)
    write_json(run / "runtime_budget.json", repair)
    failure_path.replace(archived_failure)
    return repair


def terminal_state(run: Path, deadline_unix: float) -> str | None:
    if (run / "failure.json").exists():
        return "HANDLED_FAILURE"
    if (run / "results.json").exists():
        return "COMPLETE"
    if time.time() >= deadline_unix:
        return "RUNTIME_BUDGET_EXCEEDED"
    return None


def supervise(
    run: Path,
    command: Sequence[str],
    *,
    judge_repair: bool = False,
    strict_judge_repair: bool = False,
) -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SupervisorError("OPENAI_API_KEY is missing")
    if strict_judge_repair:
        continuation = initialize_strict_judge_repair(run)
    elif judge_repair:
        continuation = initialize_judge_repair(run)
    else:
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
    parser.add_argument("--judge-repair", action="store_true")
    parser.add_argument("--strict-judge-repair", action="store_true")
    args = parser.parse_args(argv)
    command = [sys.executable, "-u", "-m", "analysis.beam001_live", "run"]
    try:
        return supervise(
            args.run,
            command,
            judge_repair=args.judge_repair,
            strict_judge_repair=args.strict_judge_repair,
        )
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
