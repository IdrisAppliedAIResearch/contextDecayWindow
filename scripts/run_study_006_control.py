"""S6-T-016 — same-seed Study 005 control, launched from a checked-out worktree.

The pre-registration is binding here: the control runs on **checked-out Study 005
code in a separate worktree, never the Study 006 runner with span selection
disabled by flag**. A flag would leave the two arms sharing a code path and make
"the arms differ only in selection policy" an assertion rather than a fact.

This launcher refuses to start on a dirty worktree, an unexpected HEAD, a diff
against the accepted implementation, a wrong script hash, an import that escapes
the worktree, or any trace of the Study 006 selection engine. Module paths,
server properties, the command and the process id are all recorded *before* the
first inference call.

Run it with the repository root as cwd; it execs the runner with the worktree as
cwd and sys.path root.
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

REPO = Path(__file__).resolve().parents[1]
WORKTREE = Path(
    os.environ.get(
        "CDW_CONTROL_WORKTREE",
        r"C:\Users\muzaf\PycharmProjects\cdw-study005-control",
    )
)
EXPECTED_SHA = "f8796fd541125dd39164bb2bd815e9afe52484ab"
EXPECTED_SCRIPT_SHA = (
    "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
)
OUTPUT_ROOT = REPO / "experiments/study_006/controls/whole_turn_seeded"
RUN_ID = os.environ.get("CDW_STUDY_RUN_ID", "run_001")
FORBIDDEN = ["src/memory/span_dream_engine.py", "src/memory/span_segmenter.py"]


def fail(message: str) -> None:
    raise SystemExit(f"CONTROL LAUNCH REFUSED: {message}")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(WORKTREE), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def verify() -> dict:
    if not WORKTREE.is_dir():
        fail(f"control worktree does not exist: {WORKTREE}")

    head = git("rev-parse", "HEAD")
    if head != EXPECTED_SHA:
        fail(f"worktree HEAD is {head}, expected {EXPECTED_SHA}")

    dirty = git("status", "--porcelain")
    if dirty:
        fail(f"worktree is dirty:\n{dirty}")

    diff = git("diff", "--stat", EXPECTED_SHA)
    if diff:
        fail(f"worktree differs from the accepted implementation:\n{diff}")

    script = WORKTREE / "experiments/study_005/script.json"
    if not script.exists():
        fail("study script missing from the control worktree")
    # LF-normalized: core.autocrlf rewrites line endings on checkout, so raw
    # working-tree bytes do not match the recorded hash on Windows.
    raw = script.read_bytes().replace(b"\r\n", b"\n")
    script_sha = hashlib.sha256(raw).hexdigest()
    if script_sha != EXPECTED_SCRIPT_SHA:
        fail(f"script hash is {script_sha}, expected {EXPECTED_SCRIPT_SHA}")

    for relative in FORBIDDEN:
        if (WORKTREE / relative).exists():
            fail(f"Study 006 selection engine present in control worktree: {relative}")

    return {"head": head, "script_sha256": script_sha}


RUNNER = r'''
import json, os, sys
from pathlib import Path

worktree = Path(sys.argv[1]).resolve()
output_root = sys.argv[2]
run_id = sys.argv[3]
manifest_path = sys.argv[4]

import src.study.runner as runner_module
import src.memory.dream_engine as dream_module
import src.memory.distilled_ltm_store as store_module

# Import escape guard: every study module must resolve inside the worktree.
for module in (runner_module, dream_module, store_module):
    resolved = Path(module.__file__).resolve()
    if worktree not in resolved.parents:
        raise SystemExit(
            f"CONTROL LAUNCH REFUSED: {module.__name__} resolved to {resolved}, "
            f"outside the control worktree"
        )

# The Study 006 engine must not be importable from this interpreter at all.
try:
    import src.memory.span_dream_engine  # noqa: F401
except ImportError:
    pass
else:
    raise SystemExit(
        "CONTROL LAUNCH REFUSED: src.memory.span_dream_engine is importable "
        "in the control interpreter"
    )

manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
manifest["module_paths"] = {
    m.__name__: str(Path(m.__file__).resolve())
    for m in (runner_module, dream_module, store_module)
}
manifest["dream_engine_extractor"] = dream_module.DreamEngine.EXTRACTOR
manifest["dream_engine_cap"] = dream_module.DreamEngine.PER_TOPIC_CAP
manifest["dream_engine_floor"] = dream_module.DreamEngine.SALIENCE_FLOOR
manifest["runner_pid"] = os.getpid()
Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("control guards passed; module paths recorded", flush=True)
for name, path in manifest["module_paths"].items():
    print(f"  {name} -> {path}", flush=True)
print(
    f"  DreamEngine: extractor={manifest['dream_engine_extractor']} "
    f"cap={manifest['dream_engine_cap']} floor={manifest['dream_engine_floor']}",
    flush=True,
)

runner = runner_module.StudyRunner(
    script_path=str(worktree / "experiments/study_005/script.json"),
    study_dir=output_root,
    run_id=run_id,
    memory_formation="dreaming",
    context_capacity=int(os.environ.get("CDW_CONTEXT_CAPACITY", "50000")),
    strict_monitoring=True,
)
runner.CONDITION_ORDER = ["iterative"]
runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
runner.run()
'''


def main() -> None:
    verified = verify()

    server_url = os.environ.get("CDW_INFERENCE_SERVER_URL", "").rstrip("/")
    if not server_url:
        fail("CDW_INFERENCE_SERVER_URL is not set")
    with urlopen(f"{server_url}/props", timeout=30) as response:
        server_props = json.loads(response.read().decode("utf-8"))

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_ROOT / f"{RUN_ID}_launch_manifest.json"

    command = [
        sys.executable,
        "-c",
        RUNNER,
        str(WORKTREE),
        str(OUTPUT_ROOT),
        RUN_ID,
        str(manifest_path),
    ]

    manifest = {
        "arm": "control_whole_turn_study_005",
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "worktree": str(WORKTREE),
        "worktree_head": verified["head"],
        "script_sha256_lf": verified["script_sha256"],
        "seed": server_props["default_generation_settings"]["params"]["seed"],
        "server_props": server_props,
        "command": command[:2] + ["<runner>"] + command[3:],
        "python": sys.executable,
        "pythonutf8": os.environ.get("PYTHONUTF8"),
        "context_capacity": os.environ.get("CDW_CONTEXT_CAPACITY", "50000"),
        "guards": [
            "worktree_exists",
            "head_matches_accepted_sha",
            "worktree_clean",
            "no_diff_against_accepted_sha",
            "script_hash_matches",
            "no_study_006_engine_on_disk",
            "no_import_escape",
            "study_006_engine_not_importable",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"control worktree : {WORKTREE}")
    print(f"HEAD             : {verified['head']}")
    print(f"script sha256    : {verified['script_sha256']}")
    print(f"seed             : {manifest['seed']}")
    print(f"output           : {OUTPUT_ROOT / RUN_ID}")
    print(f"manifest         : {manifest_path}")
    print()

    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(WORKTREE)
    completed = subprocess.run(command, cwd=str(WORKTREE), env=environment)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
