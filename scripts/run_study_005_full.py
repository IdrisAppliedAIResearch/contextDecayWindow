"""Run the GO-authorized 121-turn Study 005 treatment."""

import os

from src.study.runner import StudyRunner


if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_005/script.json",
        study_dir="experiments/study_005/runs",
        run_id=os.environ.get(
            "CDW_STUDY_RUN_ID",
            "study_005_full_001",
        ),
        memory_formation="dreaming",
        context_capacity=int(
            os.environ.get("CDW_CONTEXT_CAPACITY", "50000")
        ),
        strict_monitoring=True,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
    runner.run()
