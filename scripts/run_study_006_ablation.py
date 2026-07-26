"""Run the seeded 35-turn Study 006 GO/NO-GO ablation (S6-T-014).

Turns 1-35 of the real script under the v6 span-selection policy. Reaches the
first topic transition near turn 31, so the first dream pass fires with span
selection live.
"""

import os

from src.study.runner import StudyRunner


if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_005/script.json",
        study_dir="experiments/study_006/ablation/runs",
        run_id=os.environ.get(
            "CDW_STUDY_RUN_ID",
            "study_006_ablation_001",
        ),
        max_turns=35,
        memory_formation="span_dreaming",
        context_capacity=int(
            os.environ.get("CDW_CONTEXT_CAPACITY", "50000")
        ),
        strict_monitoring=True,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
    runner.run()
