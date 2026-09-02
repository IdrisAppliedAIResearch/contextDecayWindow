"""Checkpointed HH-005 execution using the unchanged HH-004 harness."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Sequence

from analysis.da013_preflight import sha256_file
from analysis.hh002_run import _read_json, _write_json
from analysis.hh005_contexts import ARMS, EXPECTED, PREFLIGHT, REPO, RUN, HH005Error
import analysis.hh004_run as harness


def assert_paid_preconditions(arm: str) -> dict:
    gate = _read_json(PREFLIGHT / "g0_g3.json") or {}
    contexts = RUN / arm / "contexts.json"
    expected_hash = gate.get("arms", {}).get(arm, {}).get("contexts_sha256")
    if gate.get("status") != "PASS" or expected_hash != sha256_file(contexts):
        raise HH005Error("committed HH-005 context gate differs")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                               cwd=REPO, text=True).strip():
        raise HH005Error("tracked worktree is dirty before paid submission")
    if not subprocess.check_output(["git", "ls-files", str((PREFLIGHT / "g0_g3.json").relative_to(REPO))],
                                   cwd=REPO, text=True).strip():
        raise HH005Error("HH-005 preflight is not committed")
    return gate


def _configure(arm: str) -> None:
    harness.RUN = RUN
    harness.PREFLIGHT = PREFLIGHT
    harness.ARM = arm
    harness.EXPECTED = EXPECTED
    harness.assert_paid_preconditions = lambda: assert_paid_preconditions(arm)


def stage_counts(arm: str) -> dict[str, int]:
    _configure(arm)
    return harness.stage_counts()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HH-005 paid runner")
    parser.add_argument("arm", choices=tuple(ARMS.values()))
    parser.add_argument("stage", choices=("pilot", "answers", "judge"))
    args = parser.parse_args(argv)
    _configure(args.arm)
    if args.stage == "pilot":
        answer = harness.run_answers(pilot=True)
        judge = harness.run_judging(pilot=True)
        result = {"answers": answer, "judge": judge}
        if answer["completed"] < 8 or judge["completed"] < 8:
            raise HH005Error("HH-005 pilot is incomplete")
        _write_json(PREFLIGHT / f"g4_paid_pilot_{args.arm}.json", result)
    elif args.stage == "answers":
        result = harness.run_answers(pilot=False)
    else:
        result = harness.run_judging(pilot=False)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
