"""Study 011 G6: the 35-turn ablation's GO/NO-GO.

G6 asks whether each arm "completes 35 turns and produces coherent,
scoreable output". No threshold is registered for coherence, and section 7
requires coherence reported separately from recall, so this module makes
the check mechanical and keeps the two apart:

* **Completion and scoreability decide GO.** All 35 turns present, every
  response non-empty, and no response an exact repeat of the one before
  it. Those are properties a run either has or does not.
* **Coherence is measured and reported, never thresholded.** Response
  lengths, budget-truncation counts and near-repetition rates go into the
  artifact so a degenerate arm is visible, but the decision does not rest
  on a number nobody registered.

Arm B carries the known hazard: with no recency window the model cannot
see the preceding turns, so it may be conversationally degenerate rather
than merely worse at recall. Section 3 forbids pre-empting that with a
recency floor. This gate is what catches it at 35 turns instead of 121.

No rubric turn falls inside the first 35, so nothing here reads the plant
key or scores an answer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
ABLATION_RUNS = STUDY_ROOT / "ablation_runs"
OUTPUT = STUDY_ROOT / "ablation" / "ablation_gate.json"
REQUIRED_TURNS = 35
ARMS = ("A", "B", "C", "D")


class AblationGateError(RuntimeError):
    """Raised when the ablation evidence cannot be read."""


def _repo_relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _arm_dir(arm: str, run_ids: dict[str, str]) -> Path:
    run_id = run_ids[arm]
    if arm == "D":
        # The control runs the carried Tier 6 runner unmodified, which names
        # its own output directory. Renaming it would mean editing that
        # runner, which is the thing the control exists to avoid.
        return ABLATION_RUNS / run_id / "context_matched_stm"
    return ABLATION_RUNS / run_id / f"arm_{arm.lower()}"


def assess_arm(arm: str, directory: Path) -> dict:
    turns_path = directory / "logs" / "turns.jsonl"
    if not turns_path.is_file():
        raise AblationGateError(f"no turn log for arm {arm}: {turns_path}")
    turns = _read_jsonl(turns_path)

    responses = [str(row.get("assistant_message") or "") for row in turns]
    lengths = sorted(len(text) for text in responses)
    empty = [
        int(row["turn_number"])
        for row, text in zip(turns, responses, strict=True)
        if not text.strip()
    ]
    exact_repeats = [
        int(turns[index]["turn_number"])
        for index in range(1, len(responses))
        if responses[index].strip()
        and responses[index].strip() == responses[index - 1].strip()
    ]
    truncated = [
        int(row["turn_number"])
        for row in turns
        if bool(row.get("reached_response_budget"))
        or (row.get("output_tokens") or 0) >= 2048
    ]

    completed = len(turns) >= REQUIRED_TURNS
    scoreable = not empty and not exact_repeats
    decision = "GO" if completed and scoreable else "NO_GO"
    reasons = []
    if not completed:
        reasons.append(f"completed {len(turns)} of {REQUIRED_TURNS} turns")
    if empty:
        reasons.append(f"empty responses at turns {empty}")
    if exact_repeats:
        reasons.append(f"response repeated verbatim at turns {exact_repeats}")

    return {
        "arm": arm,
        "run_directory": _repo_relative(directory),
        "decision": decision,
        "reasons": reasons,
        "completion": {
            "turns_completed": len(turns),
            "turns_required": REQUIRED_TURNS,
            "complete": completed,
        },
        "scoreability": {
            "empty_response_turns": empty,
            "verbatim_repeat_turns": exact_repeats,
            "budget_truncated_turns": truncated,
        },
        "coherence_reported_not_thresholded": {
            "note": (
                "Reported for reading, not for deciding. Section 7 requires "
                "coherence separate from recall, and no coherence threshold "
                "is registered."
            ),
            "response_chars_min": lengths[0] if lengths else 0,
            "response_chars_median": (
                lengths[len(lengths) // 2] if lengths else 0
            ),
            "response_chars_max": lengths[-1] if lengths else 0,
            "budget_truncated_count": len(truncated),
            "verbatim_repeat_count": len(exact_repeats),
        },
    }


def build(run_ids: dict[str, str]) -> dict:
    arms = {
        arm: assess_arm(arm, _arm_dir(arm, run_ids))
        for arm in ARMS
        if arm in run_ids
    }
    missing = [arm for arm in ARMS if arm not in arms]
    no_go = [arm for arm, row in arms.items() if row["decision"] != "GO"]
    return {
        "study": "011",
        "gate": "G6",
        "requirement": (
            "each arm completes 35 turns and produces coherent, scoreable "
            "output"
        ),
        "arms": arms,
        "arms_missing": missing,
        "arms_not_go": no_go,
        "decision": "GO" if not missing and not no_go else "NO_GO",
        "consequence": (
            "A NO_GO arm does not run at 121 turns. Section 9 registers the "
            "case where Arm B fails and the study runs three arms: record it, "
            "do not add a recency floor, which would make Arm B not an "
            "isolation."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arm in ARMS:
        parser.add_argument(f"--run-{arm.lower()}", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    run_ids = {arm: getattr(args, f"run_{arm.lower()}") for arm in ARMS}
    try:
        gate = build(run_ids)
    except AblationGateError as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for arm, row in gate["arms"].items():
        detail = "; ".join(row["reasons"]) if row["reasons"] else "clean"
        print(f"arm {arm}: {row['decision']} ({detail})")
    print(f"G6: {gate['decision']}")
    return 0 if gate["decision"] == "GO" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
