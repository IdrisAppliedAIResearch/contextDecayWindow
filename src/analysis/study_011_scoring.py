"""Study 011 section 6.1: blind scoring packets and the sealed mapping.

The registered outcome is the scored rubric, so the order in which
evidence becomes visible is part of the measurement, not housekeeping:

* Packets carry an anonymised item ID, the scoreable answer, the question
  and the locked criteria. **No arm identity, no delivery number, no
  mechanism log.**
* The arm-to-label mapping is sealed in its own file and is derived from
  the SHA-256 of the response files, so it is deterministic and not chosen
  by anyone who has seen a score.
* Every rater must first reproduce the calibration set, including a
  planted `NO_ANSWER` at 0.0. Failure revises instructions and restarts;
  it is never waived.
* Scores commit before any mechanism log is opened. Git order is the
  evidence, exactly as it was for the pre-test.

Only content outside reasoning blocks is scoreable, and an answerless item
scores 0. Both rules come from `PROTOCOL_scoring_integrity.md` and are
applied here when the packet is built, so a rater never sees a reasoning
block to be tempted by.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
PROTOCOL = (
    REPO_ROOT
    / "experiments"
    / "audits"
    / "scoring_integrity"
    / "PROTOCOL_scoring_integrity.md"
)
CALIBRATION_SET = (
    REPO_ROOT
    / "experiments"
    / "audits"
    / "scoring_integrity"
    / "calibration_set.json"
)
RUBRIC = REPO_ROOT / "experiments" / "study_002" / "rubric_filled.md"
ARMS = ("A", "B", "C", "D")
RATER_PASSES = 3

# Question -> the turn whose answer is scored. Q13 scores rule compliance
# across the late turns and is scored on the whole set, not one answer.
QUESTION_TURNS = {
    "Q1": 112,
    "Q2": 113,
    "Q3": 114,
    "Q4": 115,
    "Q5": 116,
    "Q6": 117,
    "Q7": 118,
    "Q8": 119,
    "Q9": 117,
    "Q10": 118,
    "Q11": 120,
    "Q12": 114,
}
SPANNING_QUESTIONS = {"Q13": tuple(range(112, 121))}

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_OPEN_THINK = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)


class ScoringError(RuntimeError):
    """Raised when a packet cannot be built honestly."""


def scoreable_answer(text: str) -> str:
    """Strip reasoning blocks; an unclosed one leaves no answer at all.

    `PROTOCOL_scoring_integrity.md`: only content outside reasoning blocks
    is scoreable, and an item with no final answer is `NO_ANSWER` and
    scores 0. Doing this when the packet is built means a rater is never
    shown reasoning it might credit.
    """

    without_closed = _THINK.sub("", text or "")
    without_open = _OPEN_THINK.sub("", without_closed)
    return without_open.strip()


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def answers_for(directory: Path) -> dict[int, str]:
    turns_path = directory / "logs" / "turns.jsonl"
    if not turns_path.is_file():
        raise ScoringError(f"no turn log: {turns_path}")
    answers = {}
    for row in _read_jsonl(turns_path):
        turn = int(row["turn_number"])
        if turn in set(QUESTION_TURNS.values()) | set(SPANNING_QUESTIONS["Q13"]):
            answers[turn] = str(row.get("assistant_message") or "")
    return answers


def seal_mapping(run_dirs: dict[str, Path]) -> dict:
    """Assign blind labels from response digests, never by choice."""

    digests = {}
    for arm, directory in run_dirs.items():
        responses = directory / "responses.md"
        if not responses.is_file():
            raise ScoringError(f"no responses file for arm {arm}: {responses}")
        digests[arm] = hashlib.sha256(responses.read_bytes()).hexdigest()

    order = sorted(ARMS, key=lambda arm: digests[arm])
    labels = {arm: f"arm_{chr(ord('W') + index)}" for index, arm in enumerate(order)}
    return {
        "sealed": True,
        "do_not_open": (
            "Open only after evaluation/rubric_scores.json is committed. "
            "Git history is the audit trail."
        ),
        "assignment_source": (
            "SHA-256 of each arm's responses.md, sorted; deterministic and "
            "not selected by the rater or by anyone who has seen a score"
        ),
        "mapping": {labels[arm]: arm for arm in ARMS},
        "response_sha256": digests,
        "combined_sha256": hashlib.sha256(
            "".join(digests[arm] for arm in ARMS).encode("utf-8")
        ).hexdigest(),
    }


def build_packets(run_dirs: dict[str, Path], mapping: dict) -> dict:
    label_of = {arm: label for label, arm in mapping["mapping"].items()}
    items = []
    for arm, directory in run_dirs.items():
        answers = answers_for(directory)
        for question, turn in sorted(QUESTION_TURNS.items()):
            if turn not in answers:
                raise ScoringError(f"arm {arm} has no answer at turn {turn}")
            answer = scoreable_answer(answers[turn])
            items.append(
                {
                    "item_id": hashlib.sha256(
                        f"{label_of[arm]}:{question}".encode("utf-8")
                    ).hexdigest()[:16],
                    "blind_label": label_of[arm],
                    "question": question,
                    "turn": turn,
                    "answer": answer,
                    "no_answer": not answer,
                }
            )
        compliance = {
            turn: scoreable_answer(answers[turn])
            for turn in SPANNING_QUESTIONS["Q13"]
            if turn in answers
        }
        items.append(
            {
                "item_id": hashlib.sha256(
                    f"{label_of[arm]}:Q13".encode("utf-8")
                ).hexdigest()[:16],
                "blind_label": label_of[arm],
                "question": "Q13",
                "turn": None,
                "answer": "\n\n---\n\n".join(
                    f"[turn {turn}]\n{text}" for turn, text in sorted(compliance.items())
                ),
                "no_answer": not any(compliance.values()),
            }
        )

    return {
        "study": "011",
        "section": "6.1",
        "rubric": RUBRIC.relative_to(REPO_ROOT).as_posix(),
        "protocol": PROTOCOL.relative_to(REPO_ROOT).as_posix(),
        "calibration_set": CALIBRATION_SET.relative_to(REPO_ROOT).as_posix(),
        "passes_required": RATER_PASSES,
        "rater_requirement": (
            "Three blind raters from distinct model families, none of them "
            "the reader (section 6.1). Any departure from that must be "
            "disclosed in the report, not absorbed."
        ),
        "calibration_gate": (
            "Every rater reproduces every expected score in the calibration "
            "set, including the planted NO_ANSWER at 0.0, before a single "
            "real answer is supplied. Failure restarts calibration; it is "
            "never waived."
        ),
        "withheld_from_raters": [
            "arm identity",
            "packing order",
            "delivery and availability numbers",
            "every mechanism log",
            "the plant key",
        ],
        "item_count": len(items),
        "items": sorted(items, key=lambda row: row["item_id"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arm in ARMS:
        parser.add_argument(f"--dir-{arm.lower()}", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=STUDY_ROOT / "evaluation",
    )
    args = parser.parse_args(argv)

    run_dirs = {arm: getattr(args, f"dir_{arm.lower()}") for arm in ARMS}
    try:
        mapping = seal_mapping(run_dirs)
        packets = build_packets(run_dirs, mapping)
    except ScoringError as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1

    args.output_root.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("sealed_mapping.json", mapping),
        ("blind_packets.json", packets),
    ):
        (args.output_root / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    no_answer = [row["item_id"] for row in packets["items"] if row["no_answer"]]
    print(f"items: {packets['item_count']} across {len(ARMS)} blind labels")
    print(f"NO_ANSWER items (score 0 by protocol): {len(no_answer)}")
    print("sealed mapping written; do not open until scores are committed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
