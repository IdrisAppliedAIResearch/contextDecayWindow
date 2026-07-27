"""Launch Study 009 Arm S or S+D with registered runtime guards."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from src.inference.provider import RESPONSE_BUDGET
from src.study.script_loader import script_digest
from src.study.study_009_runner import Study009Runner


SCRIPT_PATH = Path("experiments/study_005/script.json")
SCRIPT_DIGEST = "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
OUTPUT_ROOT = Path("experiments/study_009/runs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("S", "S+D"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-turns", type=int)
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
    if RESPONSE_BUDGET != 2048:
        failures.append(f"response_budget={RESPONSE_BUDGET}")
    if failures:
        raise RuntimeError(
            "Registered runtime guard failed: " + ", ".join(failures)
        )


def main() -> None:
    args = parse_args()
    if script_digest(SCRIPT_PATH.read_text(encoding="utf-8")) != SCRIPT_DIGEST:
        raise RuntimeError("Post-decode script hash does not match registration")
    server_url = os.environ.get(
        "CDW_INFERENCE_SERVER_URL", "http://127.0.0.1:8080"
    ).rstrip("/")
    os.environ["CDW_INFERENCE_SERVER_URL"] = server_url
    with urlopen(f"{server_url}/props", timeout=30) as response:
        server_props = json.loads(response.read().decode("utf-8"))
    assert_server(server_props)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "study": "009",
        "arm": args.arm,
        "run_id": args.run_id,
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "registration_anchor": "37fff74",
        "script": str(SCRIPT_PATH),
        "script_sha256_post_decode_lf": SCRIPT_DIGEST,
        "seed": 5005,
        "response_budget": RESPONSE_BUDGET,
        "max_turns": args.max_turns,
        "digest": (
            {"d": 2, "budget": 2500, "rebuild_turns": [31, 61, 91, 111]}
            if args.arm == "S+D"
            else None
        ),
        "server_props": server_props,
        "python": os.sys.executable,
        "pythonutf8": os.environ.get("PYTHONUTF8"),
        "context_capacity": int(
            os.environ.get("CDW_CONTEXT_CAPACITY", "50000")
        ),
    }
    (OUTPUT_ROOT / f"{args.run_id}_launch_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    Study009Runner(
        script_path=str(SCRIPT_PATH),
        study_dir=str(OUTPUT_ROOT),
        run_id=args.run_id,
        composition=args.arm,
        max_turns=args.max_turns,
        context_capacity=manifest["context_capacity"],
        strict_monitoring=True,
        expected_script_digest=SCRIPT_DIGEST,
        digest_d=2,
        digest_budget=2500,
    ).run()


if __name__ == "__main__":
    main()
