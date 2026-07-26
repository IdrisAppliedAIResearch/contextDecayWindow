"""S7-T-021 — full 121-turn Study 007 v7 run.

Study 006 formation carried unmodified, plus the information-expressed,
diversity-floored LTM retrieval budget at the locked parameters.

Dream passes fire at 31/61/91 and the turn-111 flush completes before 112.
Q11 is turn 120 and Q14 is turn 121. All log handles, including
`retrieval_budget.csv`, open before turn 1.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from src.study.runner import StudyRunner
from src.study.script_loader import script_digest


B_LTM = 32000
K_MIN = 1

SCRIPT_PATH = "experiments/study_005/script.json"
PRE_REGISTERED_SCRIPT_DIGEST = (
    "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
)
OUTPUT_ROOT = Path("experiments/study_007/runs")
RUN_ID = os.environ.get("CDW_STUDY_RUN_ID", "study_007_full_001")


if __name__ == "__main__":
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    server_url = os.environ["CDW_INFERENCE_SERVER_URL"].rstrip("/")
    with urlopen(f"{server_url}/props", timeout=30) as response:
        server_props = json.loads(response.read().decode("utf-8"))

    manifest = {
        "arm": "treatment_information_budget_v7",
        "study": "007",
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "pre_registration": "experiments/study_007/pre_registration.md",
        "amendments": [
            "AMENDMENT_001_delivered_information.md",
            "AMENDMENT_002_floor_cost_criterion.md",
        ],
        "script_sha256_post_decode_lf": script_digest(
            Path(SCRIPT_PATH).read_text(encoding="utf-8")
        ),
        "seed": server_props["default_generation_settings"]["params"]["seed"],
        "server_props": server_props,
        "policy": {
            "formation": "study_006_span_selection_unmodified",
            "ltm_budget_chars": B_LTM,
            "ltm_k_min": K_MIN,
            "budget_charged_at": "rendered_cost_after_identifier_dedup",
            "fill_rule": "pure_global_similarity_no_topic_cap",
            "floor_protection": True,
            "containment_dedup": "drop_ltm_entry_keep_stm_episode",
        },
        "pid": os.getpid(),
        "python": os.sys.executable,
        "pythonutf8": os.environ.get("PYTHONUTF8"),
        "context_capacity": os.environ.get("CDW_CONTEXT_CAPACITY", "50000"),
    }
    (OUTPUT_ROOT / f"{RUN_ID}_launch_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    runner = StudyRunner(
        script_path=SCRIPT_PATH,
        study_dir=str(OUTPUT_ROOT),
        run_id=RUN_ID,
        memory_formation="span_dreaming",
        context_capacity=int(
            os.environ.get("CDW_CONTEXT_CAPACITY", "50000")
        ),
        strict_monitoring=True,
        expected_script_digest=PRE_REGISTERED_SCRIPT_DIGEST,
        ltm_budget=B_LTM,
        ltm_k_min=K_MIN,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
    runner.run()
