"""Reproduce the Study 009 Arm S ablation integrity and prefix audit."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARM_S = ROOT / "experiments/study_009/runs/study_009_ablation_001/arm_s"
ARM_L = ROOT / (
    "experiments/study_007/ablation/runs/"
    "study_007_ablation_001/condition_c"
)
OUTPUT = ROOT / "experiments/study_009/ablation/ablation_results.json"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    turns = read_jsonl(ARM_S / "logs/turns.jsonl")
    audit = json.loads(
        (ARM_S / "runtime_audit.json").read_text(encoding="utf-8")
    )
    with (ARM_S / "metrics/model_performance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        performance = list(csv.DictReader(handle))
    with (ARM_S / "metrics/context_sizes.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        contexts = list(csv.DictReader(handle))

    raw_equal = 0
    normalized_equal = 0
    first_raw_difference = None
    first_normalized_difference = None
    for turn in range(1, 31):
        arm_s = (
            ARM_S / "constructed_prompts" / f"turn_{turn:03d}.txt"
        ).read_text(encoding="utf-8")
        arm_l = (
            ARM_L / "constructed_prompts" / f"turn_{turn:03d}.txt"
        ).read_text(encoding="utf-8")
        if arm_s == arm_l:
            raw_equal += 1
        elif first_raw_difference is None:
            first_raw_difference = turn
        normalized = arm_l.replace("\n\n<retrieved_ltm/>", "")
        if arm_s == normalized:
            normalized_equal += 1
        elif first_normalized_difference is None:
            first_normalized_difference = turn

    arm_l_turns = read_jsonl(ARM_L / "logs/turns.jsonl")
    response_equal = sum(
        left["assistant_message"] == right["assistant_message"]
        for left, right in zip(turns[:30], arm_l_turns[:30])
    )
    first_response_difference = next(
        (
            index + 1
            for index, (left, right) in enumerate(
                zip(turns[:30], arm_l_turns[:30])
            )
            if left["assistant_message"] != right["assistant_message"]
        ),
        None,
    )

    prompts = [
        path.read_text(encoding="utf-8")
        for path in sorted((ARM_S / "constructed_prompts").glob("turn_*.txt"))
    ]
    speeds = [float(row["tokens_per_second"]) for row in performance]
    results = {
        "run": "study_009_ablation_001",
        "arm": "S",
        "turns": len(turns),
        "duration_seconds": audit["duration_seconds"],
        "speed_tokens_per_second": {
            "minimum": min(speeds),
            "mean": sum(speeds) / len(speeds),
            "maximum": max(speeds),
        },
        "peak_estimated_tokens": max(
            int(row["estimated_tokens"]) for row in contexts
        ),
        "context_ceiling_tokens": 40000,
        "forbidden_modules_loaded": audit["forbidden_modules_loaded"],
        "ltm_tag_occurrences": sum(
            prompt.count("retrieved_ltm") for prompt in prompts
        ),
        "digest_tag_occurrences": sum(
            prompt.count("topic_digest") for prompt in prompts
        ),
        "prefix": {
            "turns_checked": 30,
            "raw_prompt_equal": raw_equal,
            "first_raw_prompt_difference": first_raw_difference,
            "empty_ltm_normalized_prompt_equal": normalized_equal,
            "first_normalized_prompt_difference": (
                first_normalized_difference
            ),
            "response_equal": response_equal,
            "first_response_difference": first_response_difference,
        },
    }
    results["runtime_passed"] = (
        results["turns"] == 35
        and results["speed_tokens_per_second"]["minimum"] > 30
        and results["peak_estimated_tokens"] < results["context_ceiling_tokens"]
        and not results["forbidden_modules_loaded"]
        and results["ltm_tag_occurrences"] == 0
        and results["digest_tag_occurrences"] == 0
    )
    results["prefix_passed"] = raw_equal == 30 and response_equal == 30
    results["decision"] = (
        "GO" if results["runtime_passed"] and results["prefix_passed"] else "STOP"
    )
    OUTPUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
