"""Run the Study 005 synthetic dreaming verification fixture."""

import os

from src.study.runner import StudyRunner


if __name__ == "__main__":
    runner = StudyRunner(
        script_path=(
            "experiments/study_005/tests/"
            "synthetic_study005_script.json"
        ),
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
