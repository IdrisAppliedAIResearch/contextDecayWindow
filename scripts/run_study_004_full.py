"""Run the GO-authorized 121-turn Study 004 Condition C v4."""

import os

from src.study.runner import StudyRunner


if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_004/script.json",
        study_dir="experiments/study_004/runs",
        run_id=os.environ.get("CDW_STUDY_RUN_ID", "run_001"),
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
    runner.run()
