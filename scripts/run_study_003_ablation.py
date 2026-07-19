"""Run the mandatory Study 003 35-turn iterative pre-run ablation."""

import os

from src.study.runner import StudyRunner


if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_003/script.json",
        study_dir="experiments/study_003/runs",
        run_id=os.environ.get("CDW_STUDY_RUN_ID", "ablation_35_server"),
        max_turns=35,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.run()
