"""Run the approved 120-turn Study 003 iterative condition."""

import os

from src.study.runner import StudyRunner


if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_003/script.json",
        study_dir="experiments/study_003/runs",
        run_id=os.environ.get("CDW_STUDY_RUN_ID", "study_003_full_001"),
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.run()
