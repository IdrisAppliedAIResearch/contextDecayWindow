"""Run the Study 003 synthetic promotion-trigger mechanism test."""

from src.study.runner import StudyRunner


if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_003/tests/synthetic_trigger_script.json",
        study_dir="experiments/study_003/runs",
        run_id="synthetic_trigger_003",
        minimum_turns=1,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.run()
