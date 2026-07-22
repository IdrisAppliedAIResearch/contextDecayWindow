"""Run the Study 004 fixture-only synthetic end-to-end verification."""

import os

from src.study.runner import StudyRunner


if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_004/tests/synthetic_study004_script.json",
        study_dir="experiments/study_004/tests/runs",
        run_id=os.environ.get("CDW_STUDY_RUN_ID", "synthetic_verification_001"),
        minimum_turns=1,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.run()
