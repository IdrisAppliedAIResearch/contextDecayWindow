"""Run the Study 005 synthetic dreaming verification fixture."""

import json
import os
from pathlib import Path

from src.memory.topic_manager import TopicManager
from src.study.runner import StudyRunner


if __name__ == "__main__":
    script_path = Path(
        "experiments/study_005/tests/synthetic_study005_script.json"
    )
    fixture = json.loads(script_path.read_text(encoding="utf-8"))
    # Make the fixture's sole consolidation pass coincide with its first probe.
    TopicManager.CONSOLIDATION_INTERVAL = int(
        fixture["consolidation_interval"]
    )
    runner = StudyRunner(
        script_path=str(script_path),
        study_dir="experiments/study_005/tests/runs",
        run_id=os.environ.get(
            "CDW_STUDY_RUN_ID",
            "synthetic_study005_001",
        ),
        minimum_turns=1,
        memory_formation="dreaming",
        context_capacity=int(
            os.environ.get("CDW_CONTEXT_CAPACITY", "50000")
        ),
        strict_monitoring=True,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.run()
