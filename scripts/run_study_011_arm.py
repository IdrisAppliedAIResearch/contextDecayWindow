"""Launch one Study 011 arm, ablation or live.

Serves arms A, B and C. Arm D is the control and runs from checked-out
deployed code in a separate worktree (section 5), so this script refuses
it rather than approximating it with a flag.

Readiness is gated, not assumed. Nothing runs until the section 4
pre-test is committed and PASS, and no live run starts until the 35-turn
ablation's GO is committed.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_retrieval_bakeoff_tier6 import (  # noqa: E402
    CORRECTED_SETTINGS_LOCK,
    SCRIPT_DIGEST,
    SCRIPT_PATH,
    _git,
    _is_tracked,
    _scan_source,
    _server_pid,
    _sha256,
    _write_json,
    assert_server,
)
from src.inference.provider import RESPONSE_BUDGET  # noqa: E402
from src.study.study_011_runner import Study011Runner  # noqa: E402
from src.tier_isolation.study011 import SERVED_ARMS, arm_accounting  # noqa: E402

STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
PRE_REGISTRATION = STUDY_ROOT / "pre_registration.md"
PRE_TEST = STUDY_ROOT / "gates" / "pre_test" / "pre_test_summary.json"
T_DECISION = STUDY_ROOT / "decisions" / "DECISION_T_threshold.md"
ABLATION_GATE = STUDY_ROOT / "ablation" / "ablation_gate.json"
ENGINE_PATH = REPO_ROOT / "src" / "tier_isolation" / "study011.py"
RUNNER_PATH = REPO_ROOT / "src" / "study" / "study_011_runner.py"
BUDGET_CHARS = 32_000
SEED = 5005


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=SERVED_ARMS, required=True)
    parser.add_argument("--phase", choices=("ablation", "live"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--checkpoint-interval", type=int)
    parser.add_argument("--resume-checkpoint", type=Path)
    return parser.parse_args()


def _assert_ready(args: argparse.Namespace) -> dict:
    """Refuse to run until the registered order of evidence holds."""

    failures: list[str] = []

    if not _is_tracked(PRE_REGISTRATION):
        failures.append("pre-registration is not committed")
    for path in (PRE_TEST, T_DECISION):
        if not path.exists() or not _is_tracked(path):
            failures.append(f"not committed: {path.relative_to(REPO_ROOT)}")

    pre_test = {}
    if PRE_TEST.exists():
        pre_test = json.loads(PRE_TEST.read_text(encoding="utf-8"))
        if pre_test.get("status") != "PASS":
            failures.append(f"pre-test status is {pre_test.get('status')}")
        if pre_test.get("failed_gates"):
            failures.append(f"pre-test failures: {pre_test['failed_gates']}")

    ablation = {}
    if args.phase == "live":
        if not ABLATION_GATE.exists() or not _is_tracked(ABLATION_GATE):
            failures.append(
                "no committed 35-turn ablation gate; a 121-turn run may not "
                "start without one"
            )
        else:
            ablation = json.loads(ABLATION_GATE.read_text(encoding="utf-8"))
            if ablation.get("decision") != "GO":
                failures.append(f"ablation decision is {ablation.get('decision')}")
            if args.arm not in ablation.get("arms", {}):
                failures.append(f"ablation carries no verdict for arm {args.arm}")
            elif ablation["arms"][args.arm].get("decision") != "GO":
                failures.append(f"ablation decision for arm {args.arm} is not GO")

    # Scanned on the mechanism, matching the carried launcher's scope. The
    # runner is measurement: it collects the model's answers at the rubric
    # turns, exactly as the carried Tier 6 runner does, and reads no plant
    # key. Scanning it would flag `rubric_responses` and stop every run on
    # a variable name.
    leakage = _scan_source(ENGINE_PATH)
    if leakage:
        failures.append(f"rubric artifacts reachable from mechanism: {leakage}")

    if failures:
        raise RuntimeError("Study 011 readiness failed: " + "; ".join(failures))

    lock = json.loads(CORRECTED_SETTINGS_LOCK.read_text(encoding="utf-8"))
    return {
        "pre_test": pre_test,
        "ablation_gate": ablation,
        "selected": lock["selected_settings"],
    }


def main() -> int:
    args = parse_args()
    ready = _assert_ready(args)
    selected = ready["selected"]

    server_url = os.environ.get(
        "CDW_INFERENCE_SERVER_URL",
        "http://127.0.0.1:8080",
    ).rstrip("/")
    os.environ["CDW_INFERENCE_SERVER_URL"] = server_url
    with urlopen(f"{server_url}/props", timeout=30) as response:
        server_props = json.loads(response.read().decode("utf-8"))
    assert_server(server_props)

    model_path = Path(server_props["model_path"]).resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"Server model does not exist: {model_path}")

    output_root = STUDY_ROOT / (
        "ablation_runs" if args.phase == "ablation" else "runs"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / f"{args.run_id}_launch_manifest.json"
    if manifest_path.exists() and args.resume_checkpoint is None:
        raise RuntimeError(f"Launch manifest already exists: {manifest_path}")

    declared = arm_accounting(args.arm)
    manifest = {
        "status": "STARTED",
        "study": "011",
        "arm": args.arm,
        "arm_configuration": declared,
        "phase": args.phase,
        "run_id": args.run_id,
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "pre_registration_sha256": _sha256(PRE_REGISTRATION),
        "design_commit": _git("rev-list", "-1", "HEAD", "--", str(PRE_REGISTRATION)),
        "code_commit": _git("rev-parse", "HEAD"),
        "pre_test_sha256": _sha256(PRE_TEST),
        "t_decision_sha256": _sha256(T_DECISION),
        "ablation_gate_sha256": (
            _sha256(ABLATION_GATE) if args.phase == "live" else None
        ),
        "command": [sys.executable, *sys.argv],
        "launcher_pid": os.getpid(),
        "server_pid": _server_pid(),
        "server_binary": os.environ.get("CDW_INFERENCE_SERVER_BINARY"),
        "server_command": os.environ.get("CDW_INFERENCE_SERVER_COMMAND"),
        "server_url": server_url,
        "server_build_hash": server_props["build_info"],
        "server_props": server_props,
        "generation_model_path": str(model_path),
        "generation_model_sha256": _sha256(model_path),
        "engine_path": str(ENGINE_PATH.relative_to(REPO_ROOT)),
        "engine_sha256": _sha256(ENGINE_PATH),
        "runner_path": str(RUNNER_PATH.relative_to(REPO_ROOT)),
        "runner_sha256": _sha256(RUNNER_PATH),
        "settings_source": str(CORRECTED_SETTINGS_LOCK.relative_to(REPO_ROOT)),
        "selected_settings": {
            "n_cap": int(selected["n_cap"]) if declared["recency_enabled"] else 0,
            "k_threshold": (
                float(selected["k_threshold"]) if declared["k_enabled"] else None
            ),
            "payload_budget": BUDGET_CHARS,
            "payload_budget_note": (
                "Section 5 registers 32,000 characters for every arm. The "
                "corrected Tier 6 run used 60,595; Study 011 is not a "
                "reproduction of it (section 3.1)."
            ),
        },
        "script_path": str(SCRIPT_PATH.relative_to(REPO_ROOT)),
        "script_sha256_post_decode_lf": SCRIPT_DIGEST,
        "seed": SEED,
        "response_budget": RESPONSE_BUDGET,
        "parallel_slots": 1,
        "speculative_decoding": "none",
        "max_turns": 35 if args.phase == "ablation" else 121,
        "checkpoint_interval": args.checkpoint_interval,
        "resume_checkpoint": (
            str(args.resume_checkpoint) if args.resume_checkpoint else None
        ),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "python_utf8_mode": sys.flags.utf8_mode,
        "context_capacity": int(os.environ.get("CDW_CONTEXT_CAPACITY", "50000")),
        "embedding_model_path": os.environ["CDW_EMBEDDING_MODEL_PATH"],
        "embedding_model_sha256": _sha256(
            Path(os.environ["CDW_EMBEDDING_MODEL_PATH"])
        ),
        "static_leakage_audit": {
            "status": "PASS",
            "engines": [
                str(ENGINE_PATH.relative_to(REPO_ROOT)),
                str(RUNNER_PATH.relative_to(REPO_ROOT)),
            ],
        },
    }
    _write_json(manifest_path, manifest)

    runner = Study011Runner(
        arm=args.arm,
        script_path=str(SCRIPT_PATH),
        study_dir=str(output_root),
        run_id=args.run_id,
        n_cap=int(selected["n_cap"]),
        k_threshold=float(selected["k_threshold"]),
        payload_budget=BUDGET_CHARS,
        max_turns=35 if args.phase == "ablation" else None,
        context_capacity=manifest["context_capacity"],
        strict_monitoring=True,
        expected_script_digest=SCRIPT_DIGEST,
        checkpoint_interval=args.checkpoint_interval,
        resume_checkpoint=(
            str(args.resume_checkpoint) if args.resume_checkpoint else None
        ),
    )
    try:
        output_dir = runner.run()
    except BaseException as exc:
        manifest["status"] = "FAILED"
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        _write_json(manifest_path, manifest)
        raise

    manifest["status"] = "COMPLETE"
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    manifest["output_dir"] = str(output_dir.relative_to(REPO_ROOT))
    manifest["scoring_surface_sha256"] = _sha256(
        output_dir / "scoring_surface.json"
    )
    manifest["runtime_audit_sha256"] = _sha256(output_dir / "runtime_audit.json")
    manifest["mechanism_seal_sha256"] = _sha256(output_dir / "mechanism_seal.json")
    _write_json(manifest_path, manifest)
    print(f"arm {args.arm} {args.phase} complete: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
