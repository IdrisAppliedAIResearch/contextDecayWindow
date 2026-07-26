"""Study 007 determinism spot-check (S7-T-005).

Carried from `scripts/verify_study_005_determinism.py` with two additions:

1. The script digest is asserted post-decode (Correction 1), so a mis-decoded
   prefix aborts instead of producing self-consistent corruption.
2. The comparison phase additionally checks the prefix against **Study 006's
   recorded hashes**. The ten-turn prefix runs with an empty distilled LTM, so
   it exercises no Study 007 retrieval code at all. If Study 007's runtime is
   the same runtime, the prefix must reproduce Study 006's prompts and
   responses byte for byte. A divergence here means something changed upstream
   of LTM retrieval — which is out of scope and would invalidate the study.

Phases (each of a and b must run against a **fresh server process**):

    CDW_DETERMINISM_PHASE=a  CDW_SERVER_PID=<pid> CDW_INFERENCE_SERVER_URL=... python scripts/verify_study_007_determinism.py
    CDW_DETERMINISM_PHASE=b  ...
    CDW_DETERMINISM_PHASE=compare ...
"""

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from urllib.request import urlopen

from src.study.runner import StudyRunner
from src.study.script_loader import script_digest


PREFIX_TURNS = 10
SEED = 5005
SCRIPT_PATH = "experiments/study_005/script.json"

# Recorded by Study 005, re-verified by Study 006, carried into Study 007.
PRE_REGISTERED_SCRIPT_DIGEST = (
    "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
)

STUDY_006_MANIFEST = Path(
    "experiments/study_006/runtime/determinism_prefix_001/prefix_a_manifest.json"
)


def _turn_rows(path: Path) -> list[dict]:
    turns_path = path / "condition_c" / "logs" / "turns.jsonl"
    return [
        json.loads(line)
        for line in turns_path.read_text(encoding="utf-8").splitlines()
    ]


def _responses(path: Path) -> list[str]:
    return [row["assistant_message"] for row in _turn_rows(path)]


def _prompts(path: Path) -> list[str]:
    condition_path = path / "condition_c"
    return [
        (condition_path / row["constructed_prompt_path"]).read_text(
            encoding="utf-8"
        )
        for row in _turn_rows(path)
    ]


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _run_phase(phase: str, output_root: Path) -> None:
    run_id = f"prefix_{phase}"
    run_path = output_root / run_id
    if run_path.exists():
        raise FileExistsError(f"Refusing to reuse prefix directory: {run_path}")

    server_url = os.environ["CDW_INFERENCE_SERVER_URL"].rstrip("/")
    with urlopen(f"{server_url}/props", timeout=30) as response:
        server_props = json.loads(response.read().decode("utf-8"))

    runner = StudyRunner(
        script_path=SCRIPT_PATH,
        study_dir=str(output_root),
        run_id=run_id,
        max_turns=PREFIX_TURNS,
        memory_formation="span_dreaming",
        context_capacity=50000,
        strict_monitoring=True,
        expected_script_digest=PRE_REGISTERED_SCRIPT_DIGEST,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
    runner.run()

    with sqlite3.connect(run_path / "condition_c" / "study.db") as conn:
        dream_event_count = conn.execute(
            "SELECT COUNT(*) FROM dream_events"
        ).fetchone()[0]
        distilled_count = conn.execute(
            "SELECT COUNT(*) FROM distilled_ltm"
        ).fetchone()[0]
    if dream_event_count or distilled_count:
        raise AssertionError(
            "The ten-turn prefix must retain an empty distilled LTM. A "
            "non-empty store would mean the prefix exercises Study 007 "
            "retrieval, and it would no longer be comparable to Study 006's."
        )

    manifest = {
        "phase": phase,
        "study": "007",
        "seed": SEED,
        "prefix_turns": PREFIX_TURNS,
        "single_slot": True,
        "speculative_decoding": False,
        "server_pid": int(os.environ["CDW_SERVER_PID"]),
        "server_props": server_props,
        "script_digest_post_decode": script_digest(
            Path(SCRIPT_PATH).read_text(encoding="utf-8")
        ),
        "dream_event_count": dream_event_count,
        "distilled_count": distilled_count,
        "prompt_sha256": [_hash_text(p) for p in _prompts(run_path)],
        "response_sha256": [_hash_text(r) for r in _responses(run_path)],
    }
    (output_root / f"{run_id}_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"PASS: completed seeded prefix phase {phase}")


def _compare(output_root: Path) -> None:
    first = _responses(output_root / "prefix_a")
    second = _responses(output_root / "prefix_b")
    first_prompts = _prompts(output_root / "prefix_a")
    second_prompts = _prompts(output_root / "prefix_b")

    manifests = {
        name: json.loads(
            (output_root / f"prefix_{name}_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        for name in ("a", "b")
    }
    if manifests["a"]["server_pid"] == manifests["b"]["server_pid"]:
        raise AssertionError(
            "Determinism phases must use fresh server processes"
        )

    response_matches = [x == y for x, y in zip(first, second, strict=True)]
    prompt_matches = [
        x == y for x, y in zip(first_prompts, second_prompts, strict=True)
    ]

    # Cross-study: the prefix uses no Study 007 code, so it must reproduce
    # Study 006's recorded hashes exactly.
    prior = json.loads(STUDY_006_MANIFEST.read_text(encoding="utf-8"))
    current_prompts = manifests["a"]["prompt_sha256"]
    current_responses = manifests["a"]["response_sha256"]
    cross_prompt_matches = [
        x == y
        for x, y in zip(prior["prompt_sha256"], current_prompts, strict=True)
    ]
    cross_response_matches = [
        x == y
        for x, y in zip(prior["response_sha256"], current_responses, strict=True)
    ]

    report = {
        "study": "007",
        "seed": SEED,
        "prefix_turns": PREFIX_TURNS,
        "single_slot": True,
        "speculative_decoding": False,
        "fresh_server_per_phase": True,
        "script_digest_post_decode": manifests["a"][
            "script_digest_post_decode"
        ],
        "all_prompts_identical": all(prompt_matches),
        "all_turns_identical": all(response_matches),
        "prompt_matches": prompt_matches,
        "response_matches": response_matches,
        "cross_study_source": str(STUDY_006_MANIFEST),
        "cross_study_prompts_identical": all(cross_prompt_matches),
        "cross_study_responses_identical": all(cross_response_matches),
        "cross_study_prompt_matches": cross_prompt_matches,
        "cross_study_response_matches": cross_response_matches,
    }
    (output_root / "determinism_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print(f"within-study prompts identical : {all(prompt_matches)}")
    print(f"within-study turns identical   : {all(response_matches)}")
    print(
        f"cross-study (006) prompts      : "
        f"{sum(cross_prompt_matches)}/{len(cross_prompt_matches)}"
    )
    print(
        f"cross-study (006) responses    : "
        f"{sum(cross_response_matches)}/{len(cross_response_matches)}"
    )
    if not (all(prompt_matches) and all(response_matches)):
        raise AssertionError("Within-study determinism spot-check FAILED")
    if not (all(cross_prompt_matches) and all(cross_response_matches)):
        raise AssertionError(
            "Prefix diverged from Study 006. The prefix exercises no Study 007 "
            "code, so a divergence means something changed upstream of LTM "
            "retrieval. Diagnose before running."
        )
    print("PASS: determinism verified within study and against Study 006")


def main() -> None:
    phase = os.environ.get("CDW_DETERMINISM_PHASE", "").casefold()
    if phase not in {"a", "b", "compare"}:
        raise ValueError("Set CDW_DETERMINISM_PHASE to a, b, or compare")
    output_root = Path(
        os.environ.get(
            "CDW_RUNTIME_VERIFY_DIR",
            "experiments/study_007/runtime/determinism_prefix_001",
        )
    )
    output_root.mkdir(parents=True, exist_ok=True)

    if phase in {"a", "b"}:
        _run_phase(phase, output_root)
    else:
        _compare(output_root)


if __name__ == "__main__":
    main()
