from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from src.inference.provider import RESPONSE_BUDGET
from src.study.retrieval_bakeoff_tier6_runner import (
    RetrievalBakeoffTier6Runner,
)
from src.study.script_loader import script_digest


REPO_ROOT = Path(__file__).resolve().parents[1]
SURVEY_ROOT = (
    REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff"
)
SETTINGS_PATH = (
    SURVEY_ROOT / "settings" / "tier6_context_match_settings.json"
)
SCRIPT_PATH = REPO_ROOT / "experiments" / "study_005" / "script.json"
SCRIPT_DIGEST = (
    "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
)
REGISTRATION_ANCHOR = "b60b7084741eb5d30298261076b4bca78abe713a"
CORPUS_ORDER_ANCHOR = "96cdb776"
CALIBRATION_PROTOCOL_ANCHOR = "032af39d"
CORRECTED_PROTOCOL_ANCHOR = "39ba9175"
ENGINE_PATH = (
    REPO_ROOT / "src" / "memory" / "context_matched_stm.py"
)
CORRECTED_SETTINGS_LOCK = (
    SURVEY_ROOT / "settings" / "tier6_corrected_121_settings_lock.json"
)
EQUIVALENCE_GATE = (
    SURVEY_ROOT / "tier6" / "equivalence_gate_corrected"
    / "equivalence_gate.json"
)
ABLATION_GATE = SURVEY_ROOT / "tier6" / "corrected_ablation_gate.json"
CORRECTED_RUN_IDS = {
    "ablation": {
        "tier6_ablation_corrected_a",
        "tier6_ablation_corrected_b",
    },
    "live": {"tier6_live_121_corrected_001"},
}
FORBIDDEN_FRAGMENTS = (
    "answer_key",
    "overlap_matrix",
    "rubric",
    "q_facts_key",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("ablation", "live"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--checkpoint-interval", type=int)
    parser.add_argument("--resume-checkpoint", type=Path)
    return parser.parse_args()


def assert_server(server_props: dict) -> None:
    generation = server_props["default_generation_settings"]
    settings = generation["params"]
    failures = []
    if int(settings["seed"]) != 5005:
        failures.append(f"seed={settings['seed']}")
    if int(server_props["total_slots"]) != 1:
        failures.append(f"total_slots={server_props['total_slots']}")
    if int(generation["n_ctx"]) < 50000:
        failures.append(f"n_ctx={generation['n_ctx']}")
    if settings.get("speculative.types") != "none":
        failures.append(
            f"speculative.types={settings.get('speculative.types')}"
        )
    if not server_props.get("build_info"):
        failures.append("build_info=missing")
    if RESPONSE_BUDGET != 2048:
        failures.append(f"response_budget={RESPONSE_BUDGET}")
    if failures:
        raise RuntimeError(
            "Registered Tier 6 runtime guard failed: " + ", ".join(failures)
        )


def main() -> int:
    args = parse_args()
    settings = _assert_ready(args)
    server_url = os.environ.get(
        "CDW_INFERENCE_SERVER_URL",
        "http://127.0.0.1:8080",
    ).rstrip("/")
    os.environ["CDW_INFERENCE_SERVER_URL"] = server_url
    with urlopen(f"{server_url}/props", timeout=30) as response:
        server_props = json.loads(response.read().decode("utf-8"))
    assert_server(server_props)

    server_pid = _server_pid()
    server_binary = Path(
        os.environ["CDW_INFERENCE_SERVER_BINARY"]
    ).resolve()
    server_command = os.environ["CDW_INFERENCE_SERVER_COMMAND"]
    model_path = Path(server_props["model_path"]).resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"Server model does not exist: {model_path}")
    generation_model_sha256 = _sha256(model_path)
    selected = settings["selected"]
    output_root = (
        SURVEY_ROOT
        / "tier6"
        / ("ablations" if args.phase == "ablation" else "runs")
    )
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / f"{args.run_id}_launch_manifest.json"
    if manifest_path.exists() and args.resume_checkpoint is None:
        raise RuntimeError(f"Launch manifest already exists: {manifest_path}")

    manifest = {
        "status": "STARTED",
        "phase": args.phase,
        "run_id": args.run_id,
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "registration_anchor": REGISTRATION_ANCHOR,
        "corpus_order_anchor": CORPUS_ORDER_ANCHOR,
        "calibration_protocol_anchor": CALIBRATION_PROTOCOL_ANCHOR,
        "corrected_protocol_anchor": CORRECTED_PROTOCOL_ANCHOR,
        "code_commit": _git("rev-parse", "HEAD"),
        "command": [sys.executable, *sys.argv],
        "launcher_pid": os.getpid(),
        "server_pid": server_pid,
        "server_binary": str(server_binary),
        "server_binary_sha256": _sha256(server_binary),
        "server_command": server_command,
        "server_url": server_url,
        "server_build_hash": server_props["build_info"],
        "server_props": server_props,
        "generation_model_path": str(model_path),
        "generation_model_sha256": generation_model_sha256,
        "settings_path": str(SETTINGS_PATH.relative_to(REPO_ROOT)),
        "settings_sha256": _sha256(SETTINGS_PATH),
        "settings_code_commit": settings["code_commit"],
        "corrected_settings_lock": str(
            CORRECTED_SETTINGS_LOCK.relative_to(REPO_ROOT)
        ),
        "corrected_settings_lock_sha256": _sha256(
            CORRECTED_SETTINGS_LOCK
        ),
        "equivalence_gate": str(
            EQUIVALENCE_GATE.relative_to(REPO_ROOT)
        ),
        "equivalence_gate_sha256": _sha256(EQUIVALENCE_GATE),
        "selected_settings": {
            "n_cap": int(selected["n_cap"]),
            "k_threshold": float(selected["k_threshold"]),
            "payload_budget": int(settings["payload_budget"]),
            "calibration_match_gate": selected["match_gate_status"],
            "calibration_median_absolute_percentage_error": selected[
                "median_absolute_percentage_error"
            ],
        },
        "script_path": str(SCRIPT_PATH.relative_to(REPO_ROOT)),
        "script_sha256_post_decode_lf": SCRIPT_DIGEST,
        "seed": 5005,
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
        "context_capacity": int(
            os.environ.get("CDW_CONTEXT_CAPACITY", "50000")
        ),
        "embedding_model_path": os.environ["CDW_EMBEDDING_MODEL_PATH"],
        "embedding_model_sha256": _sha256(
            Path(os.environ["CDW_EMBEDDING_MODEL_PATH"])
        ),
        "source_hashes_verified": settings["source_hashes_before"],
        "static_leakage_audit": _static_leakage_gate(),
        "ablation_gate_sha256": (
            _sha256(ABLATION_GATE) if args.phase == "live" else None
        ),
    }
    _write_json(manifest_path, manifest)

    runner = RetrievalBakeoffTier6Runner(
        script_path=str(SCRIPT_PATH),
        study_dir=str(output_root),
        run_id=args.run_id,
        n_cap=int(selected["n_cap"]),
        k_threshold=float(selected["k_threshold"]),
        payload_budget=int(settings["payload_budget"]),
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
    manifest["runtime_audit_sha256"] = _sha256(
        output_dir / "runtime_audit.json"
    )
    manifest["mechanism_seal_sha256"] = _sha256(
        output_dir / "mechanism_seal.json"
    )
    _write_json(manifest_path, manifest)
    return 0


def _assert_ready(args: argparse.Namespace) -> dict:
    if sys.flags.utf8_mode != 1:
        raise RuntimeError("Tier 6 requires Python UTF-8 mode")
    if _git("branch", "--show-current") != "retrieval-bakeoff":
        raise RuntimeError("Tier 6 requires retrieval-bakeoff")
    if args.run_id not in CORRECTED_RUN_IDS[args.phase]:
        raise RuntimeError(
            f"Corrected Tier 6 {args.phase} run ID must be one of "
            f"{sorted(CORRECTED_RUN_IDS[args.phase])}"
        )
    preloaded_forbidden = [
        name
        for name in sys.modules
        if name.startswith("src.")
        and any(
            token in name
            for token in ("ltm", "digest", "dream", "promotion")
        )
    ]
    if preloaded_forbidden:
        raise RuntimeError(
            "Tier 6 launcher imported forbidden memory-tier modules: "
            + ", ".join(sorted(preloaded_forbidden))
        )
    if args.resume_checkpoint is None and _git("status", "--porcelain"):
        raise RuntimeError("Tier 6 requires a clean worktree")
    for anchor in (
        REGISTRATION_ANCHOR,
        CORPUS_ORDER_ANCHOR,
        CALIBRATION_PROTOCOL_ANCHOR,
        CORRECTED_PROTOCOL_ANCHOR,
    ):
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", anchor, "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    if not SETTINGS_PATH.is_file():
        raise FileNotFoundError("Tier 6 calibrated settings are not committed")
    if not _is_tracked(SETTINGS_PATH):
        raise RuntimeError("Tier 6 calibrated settings are not tracked")
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    if settings["status"] != "LOCKED_BEFORE_T6_INFERENCE":
        raise RuntimeError("Tier 6 settings are not locked")
    if settings["selected"]["match_gate_status"] != "PASS":
        raise RuntimeError("Tier 6 calibration match gate did not pass")
    for path in (CORRECTED_SETTINGS_LOCK, EQUIVALENCE_GATE):
        if not path.is_file() or not _is_tracked(path):
            raise RuntimeError(
                f"Committed corrected Tier 6 gate is required: {path}"
            )
    corrected_lock = json.loads(
        CORRECTED_SETTINGS_LOCK.read_text(encoding="utf-8")
    )
    if (
        corrected_lock.get("status")
        != "LOCKED_BEFORE_CORRECTED_T6_ABLATION"
    ):
        raise RuntimeError("Corrected Tier 6 settings are not locked")
    if (
        corrected_lock.get("original_settings_sha256")
        != _sha256(SETTINGS_PATH)
    ):
        raise RuntimeError("Corrected lock does not match original settings")
    frozen = corrected_lock.get("selected_settings", {})
    if (
        int(frozen.get("n_cap", -1))
        != int(settings["selected"]["n_cap"])
        or float(frozen.get("k_threshold", -1))
        != float(settings["selected"]["k_threshold"])
        or int(frozen.get("payload_budget", -1))
        != int(settings["payload_budget"])
    ):
        raise RuntimeError("Corrected settings changed the calibrated values")
    equivalence = json.loads(
        EQUIVALENCE_GATE.read_text(encoding="utf-8")
    )
    if equivalence.get("status") != "PASS":
        raise RuntimeError("Corrected offline/live equivalence gate failed")
    if (
        equivalence.get("corrected_settings_lock_sha256")
        != _sha256(CORRECTED_SETTINGS_LOCK)
    ):
        raise RuntimeError("Equivalence gate used another settings lock")
    if script_digest(SCRIPT_PATH.read_text(encoding="utf-8")) != SCRIPT_DIGEST:
        raise RuntimeError("Post-decode Study 009 script hash changed")
    _verify_source_hashes(settings["source_hashes_before"])

    embedding_path = os.environ.get("CDW_EMBEDDING_MODEL_PATH")
    if not embedding_path:
        raise EnvironmentError("CDW_EMBEDDING_MODEL_PATH is required")
    if _sha256(Path(embedding_path)) != settings["embedding_model_sha256"]:
        raise RuntimeError("Embedding model differs from calibration")
    server_binary = os.environ.get("CDW_INFERENCE_SERVER_BINARY")
    server_command = os.environ.get("CDW_INFERENCE_SERVER_COMMAND")
    if not server_binary or not Path(server_binary).is_file():
        raise EnvironmentError(
            "CDW_INFERENCE_SERVER_BINARY must name the live server binary"
        )
    if not server_command:
        raise EnvironmentError(
            "CDW_INFERENCE_SERVER_COMMAND is required in every run header"
        )
    if args.phase == "live":
        if not ABLATION_GATE.is_file() or not _is_tracked(ABLATION_GATE):
            raise RuntimeError("Committed Tier 6 ablation gate is required")
        gate = json.loads(ABLATION_GATE.read_text(encoding="utf-8"))
        if gate.get("status") != "PASS":
            raise RuntimeError("Tier 6 ablation gate did not pass")
        current_server_pid = int(os.environ["CDW_INFERENCE_SERVER_PID"])
        if current_server_pid in {
            int(pid) for pid in gate.get("server_pids", [])
        }:
            raise RuntimeError(
                "Tier 6 live inference requires a fresh server PID"
            )
    elif args.checkpoint_interval is not None:
        raise RuntimeError("Ablation runs may not change checkpoint cadence")
    return settings


def _static_leakage_gate() -> dict:
    violations = _scan_source(ENGINE_PATH)
    planted = (
        "from src.retrieval_bakeoff.answer_key_reader import load\n"
    )
    planted_violations = _scan_text(planted, Path("planted_mechanism.py"))
    if violations:
        raise RuntimeError(
            "Tier 6 mechanism contains forbidden references: "
            + "; ".join(violations)
        )
    if not planted_violations:
        raise AssertionError("Tier 6 planted leakage violation was not rejected")
    return {
        "status": "PASS",
        "engine": str(ENGINE_PATH.relative_to(REPO_ROOT)),
        "planted_violation_rejected": True,
    }


def _scan_source(path: Path) -> list[str]:
    return _scan_text(path.read_text(encoding="utf-8"), path)


def _scan_text(source: str, path: Path) -> list[str]:
    tree = ast.parse(source, filename=str(path))
    violations = set()
    for node in ast.walk(tree):
        values = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
        elif isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                values.append(node.module)
            values.extend(alias.name for alias in node.names)
        for value in values:
            lowered = value.casefold()
            for fragment in FORBIDDEN_FRAGMENTS:
                if fragment in lowered:
                    violations.add(
                        f"{path}:{getattr(node, 'lineno', 0)}:{fragment}"
                    )
    return sorted(violations)


def _verify_source_hashes(expected: dict[str, str]) -> None:
    changed = []
    for relative, digest in expected.items():
        path = REPO_ROOT / relative
        if not path.is_file() or _sha256(path) != digest:
            changed.append(relative)
    if changed:
        raise RuntimeError(
            f"Tier 6 calibration sources changed: {sorted(changed)}"
        )


def _server_pid() -> int:
    value = os.environ.get("CDW_INFERENCE_SERVER_PID")
    if not value or not value.isdigit():
        raise EnvironmentError("CDW_INFERENCE_SERVER_PID is required")
    pid = int(value)
    if os.name == "nt":
        kernel32 = __import__("ctypes").windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            raise RuntimeError(f"Inference server PID is not alive: {pid}")
        kernel32.CloseHandle(handle)
    else:
        try:
            os.kill(pid, 0)
        except OSError as exc:
            raise RuntimeError(
                f"Inference server PID is not alive: {pid}"
            ) from exc
    return pid


def _is_tracked(path: Path) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
