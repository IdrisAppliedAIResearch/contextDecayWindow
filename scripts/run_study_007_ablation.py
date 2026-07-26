"""Run the seeded 35-turn Study 007 GO/NO-GO ablation (S7-T-018).

Turns 1-35 of the real script under v7: Study 006 formation carried unmodified,
plus the information-expressed, diversity-floored LTM retrieval budget.

Turn 35 reaches the first topic transition near turn 31, so the first dream pass
fires and distilled LTM becomes non-empty. That exercises character budgeting
and the degenerate single-topic floor case. The four-topic floor, the breadth
probes, and the turn-111 flush are not reachable by turn 35 and were covered by
the replay gate and the targeted fixture.
"""

import os

from src.study.runner import StudyRunner
from src.study.script_loader import script_digest


B_LTM = 32000
K_MIN = 1

PRE_REGISTERED_SCRIPT_DIGEST = (
    "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
)


if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_005/script.json",
        study_dir="experiments/study_007/ablation/runs",
        run_id=os.environ.get(
            "CDW_STUDY_RUN_ID",
            "study_007_ablation_001",
        ),
        max_turns=35,
        memory_formation="span_dreaming",
        context_capacity=int(
            os.environ.get("CDW_CONTEXT_CAPACITY", "50000")
        ),
        strict_monitoring=True,
        expected_script_digest=PRE_REGISTERED_SCRIPT_DIGEST,
        ltm_budget=B_LTM,
        ltm_k_min=K_MIN,
    )
    runner.CONDITION_ORDER = ["iterative"]
    runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
    runner.run()
