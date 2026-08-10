"""Run Amendment 001 Phase 2: five replicates of Arm D.

§4.1 registers Arm D, the deployed configuration, repeated N = 5 with an
identical corpus, identical settings, identical seed and the standing
runtime at temp 1. Nothing here is a new arm; the launcher is Study 011's
own ``run_study_011_arm_d.py``, invoked from a control worktree checked
out at the pre-Study-011 commit, exactly as the committed Arm D run was.

**One server process for all five.** Study 011's four arms ran back to
back on server PID 13088, so the differences the band is measured against
are within-process differences. Replicating on five fresh processes would
measure a different quantity and report it as the same one. Phase 1
measures across-process reproducibility separately, where it is the
question rather than a confound.

The script does not score anything and does not touch the evaluation
directory. Scoring is a separate step whose commit must follow the
decision rule's.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_amendment_001_phase_1 import (  # noqa: E402
    MODEL_PATH,
    SEED,
    SERVER_BINARY,
    SERVER_URL,
    Server,
)

STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
NOISE_BAND_ROOT = STUDY_ROOT / "noise_band"
RUNS_ROOT = NOISE_BAND_ROOT / "runs"
RUN_LOGS = NOISE_BAND_ROOT / "run_logs"
CONTROL_WORKTREE = Path(r"C:\Users\muzaf\PycharmProjects\cdw-study011-control")
CONTROL_COMMIT = "4db83229"
ABLATION_GATE = STUDY_ROOT / "ablation" / "ablation_gate.json"
EMBEDDING_MODEL = Path(
    os.environ.get(
        "CDW_EMBEDDING_MODEL_PATH",
        r"C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF"
        r"\Qwen3-Embedding-0.6B-Q8_0.gguf",
    )
)
REPLICATES = 5
RUN_ID = "study_011_noise_band_d_{index:02d}"


def replicate_env(server: Server) -> dict[str, str]:
    """The environment Study 011's launcher requires, and nothing extra."""

    environment = dict(os.environ)
    environment.update(
        {
            "STUDY_011_CONTROL_WORKTREE": "1",
            "CDW_INFERENCE_SERVER_URL": SERVER_URL,
            "CDW_INFERENCE_SERVER_BINARY": str(SERVER_BINARY),
            "CDW_INFERENCE_SERVER_COMMAND": " ".join(server.command),
            "CDW_INFERENCE_SERVER_PID": str(server.process.pid),
            "CDW_EMBEDDING_MODEL_PATH": str(EMBEDDING_MODEL),
            "CDW_CONTEXT_CAPACITY": "50000",
            "PYTHONUTF8": "1",
        }
    )
    environment.pop("CDW_INFERENCE_MODEL_PATH", None)
    return environment


def completed_replicate(index: int) -> dict | None:
    """A replicate that already finished is reused, not re-run.

    A 121-turn run is forty minutes of inference. If the driver falls over
    after one — as it did on the first attempt, decoding the child's
    output — re-running the completed replicate would throw that away and
    would also change what is being measured, since the replicates share
    one server process by design and a re-run would sit in a different
    one.
    """
    run_id = RUN_ID.format(index=index)
    manifest_path = RUNS_ROOT / f"{run_id}_launch_manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETE":
        raise RuntimeError(
            f"{run_id} has a manifest but did not complete; remove it "
            "deliberately before re-running, so a partial run is never "
            "silently overwritten"
        )
    return _summarize(index, run_id, manifest, manifest["launched_at"])


def _summarize(index: int, run_id: str, manifest: dict, started: str) -> dict:
    return {
        "index": index,
        "run_id": run_id,
        "started_at": started,
        "finished_at": manifest["finished_at"],
        "output_dir": manifest["output_dir"],
        "server_pid": manifest["server_pid"],
        "engine_sha256": manifest["engine_sha256"],
        "scoring_surface_sha256": manifest["scoring_surface_sha256"],
        "control_isolation": manifest["control_isolation"]["status"],
    }


def launch_replicate(index: int, server: Server) -> dict:
    run_id = RUN_ID.format(index=index)
    command = [
        sys.executable,
        str(CONTROL_WORKTREE / "scripts" / "run_study_011_arm_d.py"),
        "--phase", "live",
        "--run-id", run_id,
        "--output-root", str(RUNS_ROOT),
        "--control-commit", CONTROL_COMMIT,
        "--ablation-gate", str(ABLATION_GATE),
    ]
    started = datetime.now(timezone.utc).isoformat()
    print(f"\n=== replicate {index}/{REPLICATES}: {run_id} ===", flush=True)
    # The child's output goes to a file opened in UTF-8, never through this
    # process's stdout. Twice now a forty-minute run finished and the
    # driver died moving those bytes -- once decoding them in the console
    # codepage, once encoding them back out to a redirected stream. A pipe
    # the text never has to cross cannot fail that way.
    RUN_LOGS.mkdir(parents=True, exist_ok=True)
    log_path = RUN_LOGS / f"{run_id}.log"
    with log_path.open("w", encoding="utf-8", errors="replace") as handle:
        completed = subprocess.run(
            command,
            cwd=str(CONTROL_WORKTREE),
            env=replicate_env(server),
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
    print(f"    child exit {completed.returncode}; output in {log_path.name}", flush=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"replicate {run_id} failed with exit {completed.returncode}; "
            f"see {log_path}"
        )
    manifest_path = RUNS_ROOT / f"{run_id}_launch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETE":
        raise RuntimeError(f"replicate {run_id} did not complete")
    return _summarize(index, run_id, manifest, started)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=REPLICATES)
    parser.add_argument(
        "--output",
        type=Path,
        default=NOISE_BAND_ROOT / "run_manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.replicates != REPLICATES:
        raise SystemExit(
            f"§4.1 registers N = {REPLICATES}; the decision rule's last row "
            "says report and stop rather than estimate from fewer"
        )
    if not CONTROL_WORKTREE.is_dir():
        raise SystemExit(f"control worktree missing: {CONTROL_WORKTREE}")
    if not ABLATION_GATE.is_file():
        raise SystemExit(f"committed ablation gate missing: {ABLATION_GATE}")
    if not EMBEDDING_MODEL.is_file():
        raise SystemExit(f"embedding model missing: {EMBEDDING_MODEL}")
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)

    reused = {
        index: summary
        for index in range(1, args.replicates + 1)
        if (summary := completed_replicate(index)) is not None
    }
    outstanding = [
        index for index in range(1, args.replicates + 1) if index not in reused
    ]
    for index, summary in sorted(reused.items()):
        print(f"reusing completed replicate {index}: {summary['run_id']}")

    header: dict = {}
    completed = dict(reused)
    if outstanding:
        log_dir = NOISE_BAND_ROOT / "server_logs"
        with Server("1", log_dir, "phase_2") as server:
            header = {
                "server_pid": server.process.pid,
                "server_build_hash": server.props["build_info"],
                "server_command": " ".join(server.command),
                "replicates_in_this_process": outstanding,
                "why_one_process": (
                    "Study 011's four arms ran back to back on one server "
                    "process. The band is measured against those differences, "
                    "so the replicates are produced the same way. "
                    "Across-process reproducibility is Phase 1's question, "
                    "not a confound to smuggle in here."
                ),
            }
            for index in outstanding:
                completed[index] = launch_replicate(index, server)

    ordered = [completed[index] for index in sorted(completed)]
    # A resumed replicate ran in a process that is gone. That is a real
    # deviation from the design above and the artifact says so rather than
    # letting "one process" stand unqualified.
    process_continuity = "INTACT" if not reused else "BROKEN"
    if process_continuity == "BROKEN":
        print(
            "\nWARNING: replicates "
            f"{sorted(reused)} were reused from earlier server processes. "
            "The band now mixes across-process variation; this is recorded "
            "in the manifest.",
            file=sys.stderr,
        )

    manifest = {
        "study": "011",
        "amendment": (
            "experiments/study_011/amendments/"
            "AMENDMENT_001_determinism_and_noise_band.md"
        ),
        "phase": "2",
        "design": (
            f"Arm D, the deployed configuration, repeated N = {args.replicates}"
        ),
        "control_commit": CONTROL_COMMIT,
        "control_worktree": str(CONTROL_WORKTREE),
        "seed": SEED,
        "temperature": 1.0,
        "model": str(MODEL_PATH),
        "server": header,
        "process_continuity": process_continuity,
        "process_continuity_note": (
            "INTACT means every replicate ran back to back in the one server "
            "process named above, as Study 011's four arms did. BROKEN means "
            "at least one replicate was reused from an earlier process, so "
            "the band mixes across-process variation with run-to-run "
            "variation and must be read with that stated."
        ),
        "reused_replicates": sorted(reused),
        "replicates": ordered,
        "scored": False,
        "note": (
            "No score exists at this commit. The decision rule committed "
            "before this run is DECISION_RULE.md; scoring follows."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nwrote {args.output}")
    print(f"  process continuity: {process_continuity}")
    for row in ordered:
        print(f"  {row['run_id']}: {row['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
