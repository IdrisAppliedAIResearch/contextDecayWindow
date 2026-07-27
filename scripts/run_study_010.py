"""Launch a guarded Study 010 endurance arm."""

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from src.inference.provider import RESPONSE_BUDGET
from src.study.runner import StudyRunner
from src.study.script_loader import script_digest
from src.study.study_009_runner import Study009Runner

SCRIPT = Path("experiments/study_010/script_1000.json")
SCRIPT_DIGEST = "2d186e1b7f4c89d7095d01d7ac267d981abb0996c60c922a35f78cf2c6d38521"
OUTPUT = Path("experiments/study_010/runs")
AMENDMENTS = [
    "AMENDMENT_004_authorized_exploratory_restart.md",
    "AMENDMENT_005_disable_inapplicable_rule_extraction.md",
    "AMENDMENT_006_parse_but_do_not_persist_rules.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("L", "S"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--phase", choices=("rehearsal", "full"), default="full"
    )
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--resume-checkpoint")
    return parser.parse_args()


def assert_server(props: dict) -> None:
    generation = props["default_generation_settings"]
    params = generation["params"]
    failures = []
    if int(params["seed"]) != 5005:
        failures.append(f"seed={params['seed']}")
    if int(props["total_slots"]) != 1:
        failures.append(f"total_slots={props['total_slots']}")
    if int(generation["n_ctx"]) < 50000:
        failures.append(f"n_ctx={generation['n_ctx']}")
    if params.get("speculative.types") != "none":
        failures.append(f"speculative.types={params.get('speculative.types')}")
    if RESPONSE_BUDGET != 2048:
        failures.append(f"response_budget={RESPONSE_BUDGET}")
    if failures:
        raise RuntimeError("runtime guard failed: " + ", ".join(failures))


def main() -> None:
    args = parse_args()
    if args.phase == "rehearsal" and args.max_turns != 200:
        raise RuntimeError("Study 010 rehearsal must use --max-turns 200")
    if args.phase == "full" and args.max_turns not in (None, 1000):
        raise RuntimeError("Study 010 full runs must execute all 1,000 turns")

    actual = script_digest(SCRIPT.read_text(encoding="utf-8"))
    if actual != SCRIPT_DIGEST:
        raise RuntimeError(f"script digest mismatch: {actual}")

    server_url = os.environ.get(
        "CDW_INFERENCE_SERVER_URL", "http://127.0.0.1:8080"
    ).rstrip("/")
    os.environ["CDW_INFERENCE_SERVER_URL"] = server_url
    with urlopen(f"{server_url}/props", timeout=30) as response:
        props = json.loads(response.read().decode("utf-8"))
    assert_server(props)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = {
        "study": "010",
        "evidence_status": "post_stop_exploratory",
        "governing_amendments": [
            f"experiments/study_010/amendments/{name}"
            for name in AMENDMENTS
        ],
        "phase": args.phase,
        "arm": args.arm,
        "run_id": args.run_id,
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "registration_anchor": "52f05e7",
        "execution_commit": git_sha,
        "script": str(SCRIPT),
        "script_sha256_post_decode_lf": SCRIPT_DIGEST,
        "seed": 5005,
        "response_budget": RESPONSE_BUDGET,
        "max_turns": args.max_turns,
        "resume_checkpoint": args.resume_checkpoint,
        "rule_handling": "parse_tag_but_do_not_persist",
        "checkpoint_interval": 100,
        "server_props": props,
        "python": os.sys.executable,
        "context_capacity": int(os.environ.get("CDW_CONTEXT_CAPACITY", "50000")),
        "policy": (
            {
                "composition": "pure_stm_n_plus_k",
                "ltm": False,
                "digest": False,
            }
            if args.arm == "S"
            else {
                "composition": "accepted_study_007",
                "memory_formation": "span_dreaming",
                "ltm_budget_chars": 32000,
                "ltm_k_min": 1,
                "digest": False,
            }
        ),
    }
    (OUTPUT / f"{args.run_id}_{args.arm.lower()}_launch_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    common = {
        "script_path": str(SCRIPT),
        "study_dir": str(OUTPUT),
        "run_id": args.run_id,
        "max_turns": args.max_turns,
        "context_capacity": manifest["context_capacity"],
        "strict_monitoring": True,
        "expected_script_digest": SCRIPT_DIGEST,
        "checkpoint_interval": 100,
        "resume_checkpoint": args.resume_checkpoint,
        "suppress_rule_detection": False,
        "ignore_rule_detection_result": True,
    }
    if args.arm == "S":
        Study009Runner(composition="S", **common).run()
    else:
        runner = StudyRunner(
            memory_formation="span_dreaming",
            ltm_budget=32000,
            ltm_k_min=1,
            minimum_turns=1000,
            **common,
        )
        runner.CONDITION_ORDER = ["iterative"]
        runner.CONDITION_OUTPUT_NAMES = {"iterative": "arm_l"}
        runner.run()


if __name__ == "__main__":
    main()
