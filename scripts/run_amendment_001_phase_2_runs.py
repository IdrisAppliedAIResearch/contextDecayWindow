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
    completed = subprocess.run(
        command,
        cwd=str(CONTROL_WORKTREE),
        env=replicate_env(server),
        capture_output=True,
        text=True,
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(
            f"replicate {run_id} failed with exit {completed.returncode}"
        )
    manifest_path = RUNS_ROOT / f"{run_id}_launch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETE":
        raise RuntimeError(f"replicate {run_id} did not complete")
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

    completed = []
    log_dir = NOISE_BAND_ROOT / "server_logs"
    with Server("1", log_dir, "phase_2") as server:
        header = {
            "server_pid": server.process.pid,
            "server_build_hash": server.props["build_info"],
            "server_command": " ".join(server.command),
            "one_process_for_all_replicates": True,
            "why": (
                "Study 011's four arms ran back to back on one server "
                "process. The band is measured against those differences, so "
                "the replicates are produced the same way. Across-process "
                "reproducibility is Phase 1's question, not a confound to "
                "smuggle in here."
            ),
        }
        for index in range(1, args.replicates + 1):
            completed.append(launch_replicate(index, server))

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
        "replicates": completed,
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
    for row in completed:
        print(f"  {row['run_id']}: {row['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
