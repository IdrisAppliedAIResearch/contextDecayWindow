"""Finalize blinded Study 010 scores without opening the arm mapping."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "experiments/study_010/evaluation"


def normalize(payload: dict, pass_number: int) -> dict[tuple[str, str], dict]:
    result: dict[tuple[str, str], dict] = {}
    if pass_number in (1, 2):
        for arm, arm_data in payload["arms"].items():
            for item in arm_data["items"]:
                label = item.get("item", item.get("label"))
                result[(arm, label)] = {
                    "primary": item.get("primary_score", item.get("primary")),
                    "strict": item.get("strict_score", item.get("strict")),
                    "rationale": item["rationale"],
                    "expected_items_found": item["expected_items_found"],
                }
    else:
        for arm, items in payload["items"].items():
            for label, item in items.items():
                result[(arm, label)] = item
    return result


def main() -> None:
    payloads = [
        json.loads((EVAL / f"rater_pass_{number}.json").read_text(encoding="utf-8"))
        for number in (1, 2, 3)
    ]
    if not all(payload["calibration"]["passed"] for payload in payloads):
        raise RuntimeError("A rater failed calibration")
    passes = [normalize(payload, number) for number, payload in enumerate(payloads, 1)]
    if any(set(scored) != set(passes[0]) for scored in passes[1:]):
        raise RuntimeError("Rater item sets differ")
    if len(passes[0]) != 46:
        raise RuntimeError("Expected 46 arm-question scores")

    adjudication = json.loads(
        (EVAL / "conflict_adjudication.json").read_text(encoding="utf-8")
    )
    adjudicated = {
        (item["arm"], item.get("item", item.get("label"))): item
        for item in adjudication.get("items", adjudication.get("adjudications", []))
    }
    arms: dict[str, dict] = {}
    conflicts = []
    for key in sorted(passes[0]):
        score_pairs = [(scored[key]["primary"], scored[key]["strict"]) for scored in passes]
        counts = Counter(score_pairs)
        final_pair, votes = counts.most_common(1)[0]
        if len(counts) > 1:
            conflicts.append(
                {
                    "arm": key[0],
                    "item": key[1],
                    "pass_scores": score_pairs,
                    "majority": list(final_pair),
                }
            )
            if key not in adjudicated:
                raise RuntimeError(f"Missing adjudication for {key}")
            final_pair = (
                adjudicated[key]["final_primary_score"],
                adjudicated[key]["final_strict_score"],
            )
        exemplar = passes[1][key]
        arms.setdefault(key[0], {"items": {}})["items"][key[1]] = {
            "primary": final_pair[0],
            "strict": final_pair[1],
            "rationale": exemplar["rationale"],
            "expected_items_found": exemplar["expected_items_found"],
            "agreement": f"{votes}/3 before adjudication",
        }

    for arm_data in arms.values():
        items = arm_data["items"]
        interim = [item for label, item in items.items() if label.startswith("I")]
        terminal = [item for label, item in items.items() if label.startswith("Q")]
        arm_data["summary"] = {
            "interim_primary": sum(item["primary"] for item in interim),
            "interim_strict": sum(item["strict"] for item in interim),
            "terminal_primary": sum(item["primary"] for item in terminal),
            "terminal_strict": sum(item["strict"] for item in terminal),
            "overall_primary": sum(item["primary"] for item in items.values()),
            "overall_strict": sum(item["strict"] for item in items.values()),
        }

    output = {
        "study": "010",
        "blinded": True,
        "mapping_opened_before_scoring": False,
        "mechanism_logs_opened_before_scoring": False,
        "calibration_passes": 3,
        "rater_passes": 3,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "arms": arms,
    }
    (EVAL / "rubric_scores.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
