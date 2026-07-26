"""S7-T-020 — same-seed Study 006 control, launched from a checked-out worktree.

The pre-registration is binding: the control runs on **checked-out Study 006
code in a separate worktree, never the Study 007 runner with the budget disabled
by flag**. A flag would leave the arms sharing a code path and make "the arms
differ only in the retrieval budget" an assertion rather than a fact.

This launcher refuses to start on a missing or dirty worktree, an unexpected
HEAD, a diff against the accepted implementation, a wrong post-decode script
digest, an import that escapes the worktree, or any trace of the Study 007
retrieval budget. Module paths, server properties, the command and the process
id are recorded *before* the first inference call.

## How Correction 1 is inherited

The pre-registration grants the control exactly one deviation from pure Study
006 code: it inherits Correction 1 (explicit UTF-8 and post-decode hash
assertion), because a control that silently receives mojibake is not a valid
baseline.

That deviation is honoured **without modifying the worktree**. Patching Study
006's `script_loader.py` would make the worktree dirty and forfeit the zero-diff
guarantee that is the whole point of running from a checkout. Instead:

  * the launcher asserts the post-decode digest itself, before exec, so a
    mis-decode aborts before any inference is spent — the guarantee Correction 1
    exists to provide; and
  * the run executes under `PYTHONUTF8=1`, which is *proven* to yield the
    pre-registered digest (`tests/test_script_loader_encoding.py` loads the same
    script under a cp1252 default and obtains `d8ba73fd…`, while the unencoded
    read yields `5eb93a82…`).

So the control gets Correction 1's protection and Study 006's exact bytes. The
assertion moved out of the worktree rather than into it, which is stricter than
the pre-registration asked for and is recorded in the launch manifest.
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
        r"C:\Users\muzaf\PycharmProjects\cdw-study006-control",
    )
)
# The accepted Study 006 implementation as merged to main. Its only src/ delta
# from the commit at which the runtime was frozen for the Study 006 run
# (`0102536`) is `src/analysis/study_006_evaluation.py`, an analysis module the
# runner never imports. Asserted below.
EXPECTED_SHA = "a2fb66a61d8e1e7fca03ccad65844c15bb0748eb"
FROZEN_RUNTIME_SHA = "0102536"
EXPECTED_SCRIPT_SHA = (
    "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
)
OUTPUT_ROOT = REPO / "experiments/study_007/controls/count_budget_seeded"
RUN_ID = os.environ.get("CDW_STUDY_RUN_ID", "run_001")
FORBIDDEN = ["src/memory/retrieval_budget.py"]


def fail(message: str) -> None:
    raise SystemExit(f"CONTROL LAUNCH REFUSED: {message}")


def git(*args: str, cwd: Path = WORKTREE) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def script_digest(text: str) -> str:
    """Post-decode digest, LF-normalized. Mirrors Correction 1 exactly."""
    return hashlib.sha256(
        text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    ).hexdigest()


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

    # The runtime code must be identical to the state the Study 006 run used.
    runtime_diff = git(
        "diff", "--name-only", FROZEN_RUNTIME_SHA, EXPECTED_SHA,
        "--", "src/", "migrations/", cwd=REPO,
    )
    unexpected = [
        path for path in runtime_diff.splitlines()
        if path and path != "src/analysis/study_006_evaluation.py"
    ]
    if unexpected:
        fail(
            "runtime code changed between the frozen Study 006 runtime and the "
            f"control checkout: {unexpected}"
        )

    script = WORKTREE / "experiments/study_005/script.json"
    if not script.exists():
        fail("study script missing from the control worktree")

    # Correction 1, applied from outside the worktree: decode explicitly as
    # UTF-8 and assert the post-decode digest before any inference is spent.
    try:
        text = script.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        fail(f"control script is not valid UTF-8: {error}")
    digest = script_digest(text)
    if digest != EXPECTED_SCRIPT_SHA:
        fail(
            f"post-decode script digest is {digest}, expected "
            f"{EXPECTED_SCRIPT_SHA}. The control would have received a script "
            "that is not the pre-registered one."
        )

    for relative in FORBIDDEN:
        if (WORKTREE / relative).exists():
            fail(
                f"Study 007 retrieval budget present in control worktree: "
                f"{relative}"
            )

    return {"head": head, "script_sha256": digest}


RUNNER = r'''
import json, os, sys
from pathlib import Path

worktree = Path(sys.argv[1]).resolve()
output_root = sys.argv[2]
run_id = sys.argv[3]
manifest_path = sys.argv[4]

import src.study.runner as runner_module
import src.memory.span_dream_engine as span_module
import src.memory.retrieval_engine as retrieval_module
import src.memory.arbitration as arbitration_module

# Import escape guard: every study module must resolve inside the worktree.
for module in (runner_module, span_module, retrieval_module, arbitration_module):
    resolved = Path(module.__file__).resolve()
    if worktree not in resolved.parents:
        raise SystemExit(
            f"CONTROL LAUNCH REFUSED: {module.__name__} resolved to {resolved}, "
            f"outside the control worktree"
        )

# The Study 007 budget must not be importable from this interpreter at all.
try:
    import src.memory.retrieval_budget  # noqa: F401
except ImportError:
    pass
else:
    raise SystemExit(
        "CONTROL LAUNCH REFUSED: src.memory.retrieval_budget is importable "
        "in the control interpreter"
    )

# The control must be running the count-based policy.
if not hasattr(retrieval_module.RetrievalEngine, "LTM_TOP_M"):
    raise SystemExit("CONTROL LAUNCH REFUSED: LTM_TOP_M missing")
if hasattr(arbitration_module, "arbitrate_budgeted"):
    raise SystemExit(
        "CONTROL LAUNCH REFUSED: tier-budgeted arbitration present in control"
    )

manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
manifest["module_paths"] = {
    m.__name__: str(Path(m.__file__).resolve())
    for m in (runner_module, span_module, retrieval_module, arbitration_module)
}
manifest["ltm_top_m"] = retrieval_module.RetrievalEngine.LTM_TOP_M
manifest["span_engine_cap"] = span_module.SpanDreamEngine.PER_TOPIC_CAP
manifest["span_engine_floor"] = span_module.SpanDreamEngine.SALIENCE_FLOOR
manifest["span_engine_dedup"] = span_module.SpanDreamEngine.DEDUP_THRESHOLD
manifest["runner_pid"] = os.getpid()
Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("control guards passed; module paths recorded", flush=True)
for name, path in manifest["module_paths"].items():
    print(f"  {name} -> {path}", flush=True)
print(
    f"  RetrievalEngine: LTM_TOP_M={manifest['ltm_top_m']} (count-based)",
    flush=True,
)
print(
    f"  SpanDreamEngine: cap={manifest['span_engine_cap']} "
    f"floor={manifest['span_engine_floor']} "
    f"dedup={manifest['span_engine_dedup']}",
    flush=True,
)

runner = runner_module.StudyRunner(
    script_path=str(worktree / "experiments/study_005/script.json"),
    study_dir=output_root,
    run_id=run_id,
    memory_formation="span_dreaming",
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

    if os.environ.get("PYTHONUTF8") != "1":
        fail(
            "PYTHONUTF8=1 is required for the control. Study 006 code has no "
            "explicit encoding on the script open; the launcher's digest "
            "assertion checks the file, but the runner must decode it the same "
            "way."
        )

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
        "arm": "control_count_budget_study_006",
        "study": "007",
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "worktree": str(WORKTREE),
        "worktree_head": verified["head"],
        "frozen_runtime_sha": FROZEN_RUNTIME_SHA,
        "script_sha256_post_decode_lf": verified["script_sha256"],
        "seed": server_props["default_generation_settings"]["params"]["seed"],
        "server_props": server_props,
        "command": command[:2] + ["<runner>"] + command[3:],
        "python": sys.executable,
        "pythonutf8": os.environ.get("PYTHONUTF8"),
        "context_capacity": os.environ.get("CDW_CONTEXT_CAPACITY", "50000"),
        "permitted_deviation": (
            "Correction 1 (explicit UTF-8 + post-decode digest assertion) is "
            "applied by this launcher rather than by patching the worktree, so "
            "the zero-diff guarantee is preserved. The run executes under "
            "PYTHONUTF8=1, which is proven to yield the pre-registered digest."
        ),
        "guards": [
            "worktree_exists",
            "head_matches_accepted_sha",
            "worktree_clean",
            "no_diff_against_accepted_sha",
            "runtime_code_matches_frozen_study_006_runtime",
            "script_decodes_as_utf8",
            "post_decode_script_digest_matches",
            "no_study_007_budget_on_disk",
            "no_import_escape",
            "study_007_budget_not_importable",
            "count_based_policy_confirmed",
            "pythonutf8_set",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"control launch verified; manifest at {manifest_path}", flush=True)
    subprocess.run(command, cwd=str(WORKTREE), check=True)


if __name__ == "__main__":
    main()
