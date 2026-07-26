"""S6-T-017 — the GO-authorized 121-turn Study 006 treatment run.

All log handles are opened by the runner before turn 1. Dream passes fire at the
topic transitions and the turn-111 end-of-session flush; Q14 is asked at turn 121.
Carried monitoring rules apply: three consecutive empty or truncated responses
stop the run.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.memory.span_dream_engine import SpanDreamEngine  # noqa: E402
from src.memory.span_segmenter import (  # noqa: E402
    MAX_SPAN_WORDS,
    MIN_SPAN_WORDS,
    extractor_name,
    segmenter_name,
)
from src.study.runner import StudyRunner  # noqa: E402

OUTPUT_ROOT = REPO / "experiments/study_006/runs"
RUN_ID = os.environ.get("CDW_STUDY_RUN_ID", "study_006_full_001")


def main() -> None:
    server_url = os.environ.get("CDW_INFERENCE_SERVER_URL", "").rstrip("/")
    if not server_url:
        raise SystemExit("CDW_INFERENCE_SERVER_URL is not set")
    with urlopen(f"{server_url}/props", timeout=30) as response:
        server_props = json.loads(response.read().decode("utf-8"))

    script_path = REPO / "experiments/study_005/script.json"
    import hashlib

    script_sha = hashlib.sha256(
        script_path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    expected = "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
    if script_sha != expected:
        raise SystemExit(
            f"script hash {script_sha} does not match the Study 005 script {expected}"
        )

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "arm": "treatment_span_selection_v6",
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "pre_registration_sha": "5def302",
        "amendment": "AMENDMENT_001_selection_scale.md",
        "script_sha256_lf": script_sha,
        "seed": server_props["default_generation_settings"]["params"]["seed"],
        "segmenter": segmenter_name(),
        "extractor": extractor_name(),
        "policy": {
            "selection_unit": "sentence_span",
            "word_window": [MIN_SPAN_WORDS, MAX_SPAN_WORDS],
            "numeric_weight": 2,
            "source_weights": {"user": 1.5, "assistant": 1.0},
            "per_topic_cap": SpanDreamEngine.PER_TOPIC_CAP,
            "salience_floor": SpanDreamEngine.SALIENCE_FLOOR,
            "dedup_threshold": SpanDreamEngine.DEDUP_THRESHOLD,
        },
        "module_paths": {
            "src.study.runner": str(Path(StudyRunner.__module__ and
                                          sys.modules["src.study.runner"].__file__).resolve()),
            "src.memory.span_dream_engine": str(
                Path(sys.modules["src.memory.span_dream_engine"].__file__).resolve()
            ),
        },
        "pid": os.getpid(),
        "python": sys.executable,
        "pythonutf8": os.environ.get("PYTHONUTF8"),
        "context_capacity": os.environ.get("CDW_CONTEXT_CAPACITY", "50000"),
        "server_props": server_props,
    }
    manifest_path = OUTPUT_ROOT / f"{RUN_ID}_launch_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"arm          : {manifest['arm']}")
    print(f"seed         : {manifest['seed']}")
    print(f"segmenter    : {manifest['segmenter']}")
    print(f"extractor    : {manifest['extractor']}")
    print(f"cap / floor  : {manifest['policy']['per_topic_cap']} / "
          f"{manifest['policy']['salience_floor']}")
    print(f"script sha   : {script_sha}")
    print(f"manifest     : {manifest_path}")
    print()

    runner = StudyRunner(
        script_path=str(script_path),
        study_dir=str(OUTPUT_ROOT),
        run_id=RUN_ID,
        memory_formation="span_dreaming",
        context_capacity=int(os.environ.get("CDW_CONTEXT_CAPACITY", "50000")),
        strict_monitoring=True,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
    runner.run()


if __name__ == "__main__":
    main()
