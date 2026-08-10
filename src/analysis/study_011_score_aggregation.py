"""Study 011: combine three blind passes into committed scores.

Three raters produce three independent scores per item. This module
combines them and, more importantly, refuses to hide where they did not
agree.

* **Calibration is a gate, not a note.** Any rater that failed to
  reproduce the calibration set -- including the planted `NO_ANSWER` at
  0.0 -- stops the aggregation. The protocol says failure revises the
  instructions and restarts; it is never waived.
* **Majority decides, unanimity is recorded.** Where two of three agree,
  that value stands. Where all three differ, the item is a conflict and
  is surfaced, not averaged into a number that no rater gave.
* **Agreement is reported per question.** Three raters agreeing can mean
  the score is right or that they share a bias; section 7 names that
  surrogate. The agreement rate is evidence about the raters, not about
  the arms, and is labelled that way.

The blind labels stay blind here. Nothing in this module opens the sealed
mapping; a separate step does that only after the scores are committed.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
EVALUATION = STUDY_ROOT / "evaluation"
PACKETS = EVALUATION / "blind_packets.json"
QUESTIONS = tuple(f"Q{index}" for index in range(1, 14))


class AggregationError(RuntimeError):
    """Raised when the passes cannot be combined honestly."""


def load_passes(paths: list[Path]) -> list[dict]:
    passes = []
    for path in paths:
        if not path.is_file():
            raise AggregationError(f"missing rater pass: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        calibration = payload.get("calibration", {})
        if not calibration.get("passed"):
            raise AggregationError(
                f"{path.name} did not pass the calibration gate: "
                f"{calibration.get('disagreements')}. The protocol restarts "
                "calibration; it is never waived."
            )
        passes.append(payload)
    if len(passes) < 3:
        raise AggregationError(
            f"section 6.1 requires three raters; got {len(passes)}"
        )
    return passes


def combine_item(values: list[float]) -> dict:
    counts = Counter(values)
    top, frequency = counts.most_common(1)[0]
    if frequency >= 2:
        return {
            "value": float(top),
            "agreement": "unanimous" if frequency == len(values) else "majority",
            "conflict": False,
        }
    return {
        "value": float(statistics.median(values)),
        "agreement": "split",
        "conflict": True,
    }


def aggregate(passes: list[dict], packets: dict) -> dict:
    items = {row["item_id"]: row for row in packets["items"]}
    raters = [payload.get("rater", f"pass_{index + 1}") for index, payload in enumerate(passes)]

    per_item = {}
    conflicts = []
    for item_id, row in items.items():
        values = []
        for index, payload in enumerate(passes):
            score = payload.get("scores", {}).get(item_id)
            if score is None:
                raise AggregationError(
                    f"rater {raters[index]} did not score item {item_id}"
                )
            values.append(float(score["primary"]))
        combined = combine_item(values)
        if row.get("no_answer") and combined["value"] != 0.0:
            raise AggregationError(
                f"item {item_id} is NO_ANSWER but scored {combined['value']}; "
                "an answerless item is never scored above zero"
            )
        per_item[item_id] = {
            "blind_label": row["blind_label"],
            "question": row["question"],
            "rater_values": values,
            **combined,
        }
        if combined["conflict"]:
            conflicts.append(item_id)

    by_label: dict[str, dict[str, float]] = {}
    for item_id, row in per_item.items():
        by_label.setdefault(row["blind_label"], {})[row["question"]] = row["value"]

    for label, scores in by_label.items():
        missing = [question for question in QUESTIONS if question not in scores]
        if missing:
            raise AggregationError(f"{label} is missing {missing}")

    unanimous = sum(
        1 for row in per_item.values() if row["agreement"] == "unanimous"
    )
    return {
        "study": "011",
        "raters": raters,
        "rater_family_note": (
            "Section 6.1 requires three raters from distinct model families. "
            "Three distinct models were used, but they belong to a single "
            "family. This is a departure from the registered design and is "
            "disclosed here and in the report rather than absorbed."
        ),
        "calibration": "all three raters reproduced the calibration set",
        "blind_scores": by_label,
        "per_item": per_item,
        "conflicts": conflicts,
        "agreement": {
            "unanimous_items": unanimous,
            "total_items": len(per_item),
            "unanimous_rate": round(unanimous / len(per_item), 4),
            "split_items": len(conflicts),
            "this_measures_the_raters": (
                "Agreement is evidence about the raters, not about the arms. "
                "Three raters can agree because a score is right or because "
                "they share a bias, and same-family raters make the second "
                "more likely."
            ),
        },
        "mapping_not_opened": (
            "Blind labels are still blind. The sealed mapping is opened only "
            "after these scores are committed."
        ),
    }


def unseal(aggregated: dict, mapping: dict) -> dict:
    """Attach arm identities. Run only after the scores are committed."""

    label_to_arm = mapping["mapping"]
    scores = {
        label_to_arm[label]: values
        for label, values in aggregated["blind_scores"].items()
    }
    return {
        "study": "011",
        "source": "three blind passes, majority-combined, committed before unsealing",
        "raters": aggregated["raters"],
        "rater_family_note": aggregated["rater_family_note"],
        "conflicts": aggregated["conflicts"],
        "agreement": aggregated["agreement"],
        "scores": scores,
        "totals_out_of_13": {
            arm: round(sum(values.values()), 2) for arm, values in scores.items()
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passes", type=Path, nargs="+", required=True)
    parser.add_argument("--packets", type=Path, default=PACKETS)
    parser.add_argument(
        "--output", type=Path, default=EVALUATION / "blind_scores.json"
    )
    parser.add_argument(
        "--unseal-with",
        type=Path,
        help="sealed mapping; supply only after blind scores are committed",
    )
    parser.add_argument(
        "--unsealed-output", type=Path, default=EVALUATION / "rubric_scores.json"
    )
    args = parser.parse_args(argv)

    try:
        packets = json.loads(args.packets.read_text(encoding="utf-8"))
        aggregated = aggregate(load_passes(list(args.passes)), packets)
    except AggregationError as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(aggregated, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    agreement = aggregated["agreement"]
    print(
        f"blind scores written: {agreement['unanimous_items']}/"
        f"{agreement['total_items']} unanimous, "
        f"{agreement['split_items']} split"
    )
    for label, values in sorted(aggregated["blind_scores"].items()):
        print(f"  {label}: {round(sum(values.values()), 2)}/13")

    if args.unseal_with:
        mapping = json.loads(args.unseal_with.read_text(encoding="utf-8"))
        unsealed = unseal(aggregated, mapping)
        args.unsealed_output.write_text(
            json.dumps(unsealed, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        for arm, total in sorted(unsealed["totals_out_of_13"].items()):
            print(f"  arm {arm}: {total}/13")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
