"""Launch Study 011 Arm D, the control, on the deployed configuration.

Arm D is not served by ``run_study_011_arm.py``. Section 5 requires the
control on the deployed configuration as committed, from checked-out
prior architecture in a separate worktree, never a flag that disables
K-first. This launcher therefore:

* imports the carried ``RetrievalBakeoffTier6Runner`` and
  ``ContextMatchedStmRetrievalEngine`` unmodified, and nothing of Study
  011's own mechanism;
* **asserts** that no Study 011 mechanism module is resident, so the
  absence is a property of the run rather than a claim about it;
* refuses to run outside a worktree checked out at the pre-Study-011
  commit.

Nothing here disables anything. The deployed packer walks recency first
by construction; there is no K-first switch to turn off.

The one registered departure from the deployed run is the budget. Section
5 fixes 32,000 characters for all four arms; the corrected Tier 6 run used
60,595. Arm D is the deployed *order* at the registered budget, and
section 3.1 records that it reproduces no committed live run.
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
    ENGINE_PATH,
    SCRIPT_DIGEST,
    SCRIPT_PATH,
    _git,
    _scan_source,
    _server_pid,
    _sha256,
    _write_json,
    assert_server,
)
from src.inference.provider import RESPONSE_BUDGET  # noqa: E402
from src.study.retrieval_bakeoff_tier6_runner import (  # noqa: E402
    RetrievalBakeoffTier6Runner,
)

BUDGET_CHARS = 32_000
SEED = 5005
ARM = "D"
FORBIDDEN_MODULE_TOKENS = ("tier_isolation", "study_011")
CONTROL_WORKTREE_MARKER = "STUDY_011_CONTROL_WORKTREE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("ablation", "live"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--control-commit",
        required=True,
        help="the pre-Study-011 commit this worktree must be checked out at",
    )
    parser.add_argument("--ablation-gate", type=Path)
    return parser.parse_args()


def assert_control_isolation(control_commit: str) -> dict:
    """Make current-study leakage impossible, not merely unlikely."""

    failures: list[str] = []

    resident = sorted(
        name
        for name in sys.modules
        if any(token in name for token in FORBIDDEN_MODULE_TOKENS)
    )
    if resident:
        failures.append(f"Study 011 mechanism modules are resident: {resident}")

    head = _git("rev-parse", "HEAD")
    if not head.startswith(control_commit):
        failures.append(
            f"control worktree is at {head[:12]}, not {control_commit[:12]}"
        )
    if os.environ.get(CONTROL_WORKTREE_MARKER) != "1":
        failures.append(
            f"{CONTROL_WORKTREE_MARKER}=1 is required; the control must not be "
            "launched from the study worktree"
        )
    if _git("status", "--porcelain", "--untracked-files=no"):
        failures.append("control worktree is dirty")

    # The carried engine must be the committed one, byte for byte.
    # `_git` strips its output, and git may hand back CRLF on Windows, so
    # both sides are normalised the same way before comparing. The check is
    # that the engine is the committed one, not that trailing whitespace
    # survived a checkout.
    tracked = _git("show", f"{control_commit}:src/memory/context_matched_stm.py")
    on_disk = ENGINE_PATH.read_text(encoding="utf-8")
    if tracked.replace("\r\n", "\n").strip() != on_disk.replace(
        "\r\n", "\n"
    ).strip():
        failures.append("deployed engine differs from the control commit")

    leakage = _scan_source(ENGINE_PATH)
    if leakage:
        failures.append(f"rubric artifacts reachable from mechanism: {leakage}")

    if failures:
        raise RuntimeError("Arm D control isolation failed: " + "; ".join(failures))
    return {
        "status": "PASS",
        "control_commit": head,
        "resident_study_011_modules": [],
        "deployed_engine_matches_control_commit": True,
        "engine_sha256": _sha256(ENGINE_PATH),
    }


def main() -> int:
    args = parse_args()
    isolation = assert_control_isolation(args.control_commit)

    if args.phase == "live":
        if args.ablation_gate is None or not args.ablation_gate.is_file():
            raise RuntimeError(
                "a committed 35-turn ablation gate is required before a "
                "121-turn control run"
            )
        gate = json.loads(args.ablation_gate.read_text(encoding="utf-8"))
        if gate.get("decision") != "GO" or (
            gate.get("arms", {}).get(ARM, {}).get("decision") != "GO"
        ):
            raise RuntimeError(f"ablation decision for arm {ARM} is not GO")

    server_url = os.environ.get(
        "CDW_INFERENCE_SERVER_URL",
        "http://127.0.0.1:8080",
    ).rstrip("/")
    os.environ["CDW_INFERENCE_SERVER_URL"] = server_url
    with urlopen(f"{server_url}/props", timeout=30) as response:
        server_props = json.loads(response.read().decode("utf-8"))
    assert_server(server_props)

    lock = json.loads(CORRECTED_SETTINGS_LOCK.read_text(encoding="utf-8"))
    selected = lock["selected_settings"]
    model_path = Path(server_props["model_path"]).resolve()

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / f"{args.run_id}_launch_manifest.json"
    if manifest_path.exists():
        raise RuntimeError(f"Launch manifest already exists: {manifest_path}")

    manifest = {
        "status": "STARTED",
        "study": "011",
        "arm": ARM,
        "arm_configuration": {
            "arm": "D",
            "label": "both, recency-first (deployed)",
            "recency_enabled": True,
            "k_enabled": True,
            "packing_order": "recency -> K",
            "served_by": "deployed code in a separate worktree",
        },
        "phase": args.phase,
        "run_id": args.run_id,
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "control_isolation": isolation,
        "code_commit": _git("rev-parse", "HEAD"),
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
        "engine_path": "src/memory/context_matched_stm.py",
        "engine_sha256": isolation["engine_sha256"],
        "runner": "src/study/retrieval_bakeoff_tier6_runner.py, unmodified",
        "selected_settings": {
            "n_cap": int(selected["n_cap"]),
            "k_threshold": float(selected["k_threshold"]),
            "payload_budget": BUDGET_CHARS,
            "payload_budget_note": (
                "Section 5 registers 32,000 characters for every arm. The "
                "corrected Tier 6 run used 60,595, so Arm D is the deployed "
                "order at the registered budget and reproduces no committed "
                "live run (section 3.1)."
            ),
        },
        "script_path": "experiments/study_005/script.json",
        "script_sha256_post_decode_lf": SCRIPT_DIGEST,
        "seed": SEED,
        "response_budget": RESPONSE_BUDGET,
        "parallel_slots": 1,
        "speculative_decoding": "none",
        "max_turns": 35 if args.phase == "ablation" else 121,
        "python": sys.executable,
        "python_version": platform.python_version(),
        "python_utf8_mode": sys.flags.utf8_mode,
        "context_capacity": int(os.environ.get("CDW_CONTEXT_CAPACITY", "50000")),
        "embedding_model_path": os.environ["CDW_EMBEDDING_MODEL_PATH"],
        "embedding_model_sha256": _sha256(
            Path(os.environ["CDW_EMBEDDING_MODEL_PATH"])
        ),
    }
    _write_json(manifest_path, manifest)

    runner = RetrievalBakeoffTier6Runner(
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
    manifest["output_dir"] = str(output_dir)
    manifest["scoring_surface_sha256"] = _sha256(
        output_dir / "scoring_surface.json"
    )
    manifest["runtime_audit_sha256"] = _sha256(output_dir / "runtime_audit.json")
    manifest["mechanism_seal_sha256"] = _sha256(output_dir / "mechanism_seal.json")
    _write_json(manifest_path, manifest)
    print(f"arm D {args.phase} complete: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
