"""Study 011 section 6.3 and 6.4: the one binding bar and the contrasts.

B1 is the only bar: **Arm C must not score below Arm D.** If correcting
the packing order makes the live result worse, the correction is not
adopted regardless of any availability gain. LV-001 is why -- a mechanism
that improves delivery and degrades answers has not improved anything.

Everything else here is descriptive. No materiality threshold is
registered, matching EC-002 and IC-001, and the program holds no variance
estimate anywhere, so none of these numbers supports a significance claim
and the module says so in its own output rather than leaving it to a
reader.

Aggregates are reported beside per-question rows and never instead of
them. IC-001's two arms delivered exactly the same episode total in
different compositions; only the paired rows showed the change.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
ARMS = ("A", "B", "C", "D")
QUESTIONS = tuple(f"Q{index}" for index in range(1, 14))
CONTRASTS = (("C", "D"), ("C", "A"), ("C", "B"), ("A", "B"))
STUDY_009_REFERENCE = {
    "arm_S": 9.0,
    "arm_L": 12.0,
    "caveat": (
        "Study 009 ran under recency-first packing and pre-DR-001 "
        "accounting, and its Arm L is the preserved Study 007 condition-C "
        "run. It is a reference point, not a comparison arm."
    ),
}


class VerdictError(RuntimeError):
    """Raised when the verdict cannot be computed from committed scores."""


def load_scores(path: Path) -> dict[str, dict[str, float]]:
    """Committed per-arm, per-question scores. Nothing is inferred."""

    if not path.is_file():
        raise VerdictError(f"no committed scores: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise VerdictError("scores file has no `scores` object")
    for arm in ARMS:
        if arm not in scores:
            raise VerdictError(f"no committed score for arm {arm}")
        missing = [question for question in QUESTIONS if question not in scores[arm]]
        if missing:
            raise VerdictError(f"arm {arm} is missing scores for {missing}")
    return {
        arm: {question: float(scores[arm][question]) for question in QUESTIONS}
        for arm in ARMS
    }


def totals(scores: dict[str, dict[str, float]]) -> dict[str, float]:
    return {arm: round(sum(scores[arm].values()), 2) for arm in ARMS}


def paired(scores: dict[str, dict[str, float]], left: str, right: str) -> dict:
    gains, losses, level = [], [], []
    for question in QUESTIONS:
        delta = scores[left][question] - scores[right][question]
        row = {
            "question": question,
            left: scores[left][question],
            right: scores[right][question],
            "delta": round(delta, 2),
        }
        if delta > 0:
            gains.append(row)
        elif delta < 0:
            losses.append(row)
        else:
            level.append(row)
    return {
        "contrast": f"{left} - {right}",
        "total_delta": round(
            sum(scores[left].values()) - sum(scores[right].values()), 2
        ),
        "gains": gains,
        "losses": losses,
        "unchanged_count": len(level),
        "per_question": [
            {
                "question": question,
                left: scores[left][question],
                right: scores[right][question],
                "delta": round(scores[left][question] - scores[right][question], 2),
            }
            for question in QUESTIONS
        ],
    }


def b1_verdict(scores: dict[str, dict[str, float]]) -> dict:
    arm_c = sum(scores["C"].values())
    arm_d = sum(scores["D"].values())
    passed = arm_c >= arm_d
    return {
        "bar": "B1",
        "statement": "Arm C must not score below Arm D",
        "arm_c": round(arm_c, 2),
        "arm_d": round(arm_d, 2),
        "delta": round(arm_c - arm_d, 2),
        "status": "PASS" if passed else "FAIL",
        "consequence": (
            "The packing correction is adopted."
            if passed
            else "The packing correction is NOT adopted, regardless of any "
            "availability gain. A mechanism that improves delivery and "
            "degrades answers has not improved anything (LV-001)."
        ),
    }


def build(scores: dict[str, dict[str, float]]) -> dict:
    return {
        "study": "011",
        "sections": ["6.3", "6.4"],
        "treatment_scores": {
            "per_question": scores,
            "totals_out_of_13": totals(scores),
        },
        "b1": b1_verdict(scores),
        "registered_contrasts": {
            f"{left}-{right}": paired(scores, left, right)
            for left, right in CONTRASTS
        },
        "study_009_reference": STUDY_009_REFERENCE,
        "no_significance_claim": (
            "No materiality threshold is registered and the program holds no "
            "variance estimate anywhere. One corpus, one seed, one runtime, "
            "a single run per arm: Study 011 cannot establish that any "
            "difference here would replicate."
        ),
        "aggregates_conceal_composition": (
            "Totals are reported beside the per-question rows, never instead "
            "of them. IC-001's arms delivered identical episode totals in "
            "different compositions."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scores",
        type=Path,
        default=STUDY_ROOT / "evaluation" / "rubric_scores.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=STUDY_ROOT / "evaluation" / "verdict.json",
    )
    args = parser.parse_args(argv)

    try:
        result = build(load_scores(args.scores))
    except VerdictError as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for arm, total in result["treatment_scores"]["totals_out_of_13"].items():
        print(f"arm {arm}: {total}/13")
    b1 = result["b1"]
    print(f"B1: {b1['status']} (C {b1['arm_c']} - D {b1['arm_d']} = {b1['delta']})")
    for name, contrast in result["registered_contrasts"].items():
        print(
            f"{name}: {contrast['total_delta']:+} "
            f"({len(contrast['gains'])} gains, {len(contrast['losses'])} losses)"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
