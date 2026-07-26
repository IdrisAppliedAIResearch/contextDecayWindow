"""S7-T-022 — prepare blinded scoring inputs.

Study 006's rater was not blind to arm identity and had already computed
formation results. Correction 2 restores the protocol. This script builds the
apparatus that makes blinding real rather than declared:

  * each arm's rubric responses are extracted into `arm_A/` and `arm_B/`;
  * which arm is which is decided by a **hash of the two response files**, so
    the assignment is deterministic, reproducible, and not chosen by anyone;
  * the mapping is written to `sealed_mapping.json` and committed **unopened**.

The rater sees only `arm_A/responses.md` and `arm_B/responses.md`. Nothing in
those files names an arm, a policy, or a parameter.

Ordering is an acceptance criterion and is verifiable from git history: this
commit, then the scores commit, and only then any mechanism log.
"""

import hashlib
import json
import re
import shutil
from pathlib import Path

TREATMENT = Path("experiments/study_007/runs/study_007_full_001/condition_c")
CONTROL = Path(
    "experiments/study_007/controls/count_budget_seeded/run_001/condition_c"
)
OUT = Path("experiments/study_007/evaluation")

# Turns the rubric scores. Q1-Q13 are the probe turns; Q14 is turn 121.
RUBRIC_TURNS = list(range(112, 122))

# Which locked-rubric questions each turn answers. Several questions share a
# turn's response (Q6/Q9 both read turn 117, Q7/Q10 both read turn 118, Q3/Q12
# both read turn 114) and Q13 is judged across turns 112-120.
#
# The `## Turn NNN — Qn: ...` labels carried in `rubric/responses.md` are stale:
# they name questions from an earlier study's set ("CRISPR Cell Line"), not the
# locked rubric. They are stripped rather than shown, so the rater is not
# primed with a wrong question. The labels are identical in both arms, so this
# is an accuracy fix, not a blinding one.
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

ARM_HEADER = re.compile(r"^## Turn (\d+)[^\n]*", re.M)


def load_rubric_responses(run_dir: Path) -> str:
    """Extract the rubric turns' responses with all arm identity removed."""
    source = run_dir / "rubric" / "responses.md"
    if not source.exists():
        source = run_dir / "responses.md"
    text = source.read_text(encoding="utf-8")

    blocks = {}
    parts = ARM_HEADER.split(text)
    # parts = [preamble, turn, body, turn, body, ...]
    for turn, body in zip(parts[1::2], parts[2::2]):
        blocks[int(turn)] = body

    lines = []
    for turn in RUBRIC_TURNS:
        if turn not in blocks:
            continue
        questions = ", ".join(TURN_QUESTIONS.get(turn, []))
        lines.append(f"## Turn {turn} — scores {questions}\n")
        lines.append(blocks[turn].strip())
        lines.append("\n---\n")
    lines.append(
        "\nQ13 (rule compliance) is judged across turns 112-120, not from a "
        "single turn.\n"
    )
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    responses = {
        "treatment_v7": load_rubric_responses(TREATMENT),
        "control_count_budget": load_rubric_responses(CONTROL),
    }

    # The assignment is derived from the content itself, so no one chooses it.
    digests = {
        name: hashlib.sha256(text.encode("utf-8")).hexdigest()
        for name, text in responses.items()
    }
    combined = hashlib.sha256(
        "".join(sorted(digests.values())).encode("utf-8")
    ).hexdigest()
    flip = int(combined[:8], 16) % 2 == 1

    order = ["treatment_v7", "control_count_budget"]
    if flip:
        order.reverse()
    mapping = {"arm_A": order[0], "arm_B": order[1]}

    for arm, name in mapping.items():
        arm_dir = OUT / arm
        if arm_dir.exists():
            shutil.rmtree(arm_dir)
        arm_dir.mkdir(parents=True)
        (arm_dir / "responses.md").write_text(
            f"# {arm} — rubric responses\n\n"
            "Arm identity is withheld until scores are committed.\n\n"
            f"{responses[name]}",
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
                    "sha256 of the two response files, so the assignment is "
                    "deterministic and chosen by no one"
                ),
                "response_sha256": digests,
                "combined_sha256": combined,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"arm_A/responses.md  {len((OUT / 'arm_A' / 'responses.md').read_text(encoding='utf-8')):,} chars")
    print(f"arm_B/responses.md  {len((OUT / 'arm_B' / 'responses.md').read_text(encoding='utf-8')):,} chars")
    print("sealed_mapping.json written — DO NOT OPEN until scores are committed")


if __name__ == "__main__":
    main()
