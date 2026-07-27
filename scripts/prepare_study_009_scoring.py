"""Prepare Study 009's blinded scoring inputs.

The accepted Study 007 condition-C run is Arm L. The new Study 009 run is
Arm S. This script extracts only the rubric responses, removes architecture
labels, assigns anonymous arm names from response hashes, and writes a sealed
mapping that must not be opened until scores are committed.
"""

import hashlib
import json
import re
import shutil
from pathlib import Path

ARM_L = Path(
    "experiments/study_007/runs/study_007_full_001/condition_c"
)
ARM_S = Path(
    "experiments/study_009/runs/study_009_full_001/arm_s"
)
OUT = Path("experiments/study_009/evaluation")

RUBRIC_TURNS = list(range(112, 122))
TURN_QUESTIONS = {
    112: ["Q1"],
    113: ["Q2"],
    114: ["Q3", "Q12"],
    115: ["Q4"],
    116: ["Q5"],
    117: ["Q6", "Q9"],
    118: ["Q7", "Q10"],
    119: ["Q8"],
    120: ["Q11"],
    121: ["Q14"],
}
TURN_HEADER = re.compile(r"^## Turn (\d+)[^\n]*", re.M)


def load_rubric_responses(run_dir: Path) -> str:
    """Return rubric-turn responses with identifying headers replaced."""
    source = run_dir / "rubric" / "responses.md"
    if not source.exists():
        source = run_dir / "responses.md"
    text = source.read_text(encoding="utf-8")

    parts = TURN_HEADER.split(text)
    blocks = {
        int(turn): body
        for turn, body in zip(parts[1::2], parts[2::2])
    }
    missing = [turn for turn in RUBRIC_TURNS if turn not in blocks]
    if missing:
        raise ValueError(f"missing rubric turns in {source}: {missing}")

    lines = []
    for turn in RUBRIC_TURNS:
        questions = ", ".join(TURN_QUESTIONS[turn])
        lines.extend(
            [
                f"## Turn {turn} - scores {questions}\n",
                blocks[turn].strip(),
                "\n---\n",
            ]
        )
    lines.append(
        "\nQ13 (rule compliance) is judged across turns 112-120, not from "
        "a single turn.\n"
    )
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    responses = {
        "arm_l_study_007_accepted": load_rubric_responses(ARM_L),
        "arm_s_study_009": load_rubric_responses(ARM_S),
    }
    digests = {
        name: hashlib.sha256(text.encode("utf-8")).hexdigest()
        for name, text in responses.items()
    }
    combined = hashlib.sha256(
        "".join(sorted(digests.values())).encode("utf-8")
    ).hexdigest()

    order = ["arm_l_study_007_accepted", "arm_s_study_009"]
    if int(combined[:8], 16) % 2:
        order.reverse()
    mapping = {"arm_A": order[0], "arm_B": order[1]}

    for anonymous_arm, source_arm in mapping.items():
        arm_dir = OUT / anonymous_arm
        if arm_dir.exists():
            shutil.rmtree(arm_dir)
        arm_dir.mkdir(parents=True)
        (arm_dir / "responses.md").write_text(
            f"# {anonymous_arm} - rubric responses\n\n"
            "Arm identity is withheld until scores are committed.\n\n"
            f"{responses[source_arm]}",
            encoding="utf-8",
        )

    (OUT / "sealed_mapping.json").write_text(
        json.dumps(
            {
                "sealed": True,
                "do_not_open": (
                    "Open only after evaluation/rubric_scores.json is "
                    "committed. Git history is the audit trail."
                ),
                "mapping": mapping,
                "assignment_source": (
                    "SHA-256 of both response files; deterministic and "
                    "not selected by the rater"
                ),
                "response_sha256": digests,
                "combined_sha256": combined,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    for anonymous_arm in ("arm_A", "arm_B"):
        path = OUT / anonymous_arm / "responses.md"
        print(f"{path}: {len(path.read_text(encoding='utf-8')):,} chars")
    print("sealed_mapping.json written; do not open before score commit")


if __name__ == "__main__":
    main()
