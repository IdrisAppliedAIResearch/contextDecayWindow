"""Run or compare seeded prefixes across fresh server lifecycles."""

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from urllib.request import urlopen

from src.study.runner import StudyRunner


PREFIX_TURNS = 10


def _turn_rows(path: Path) -> list[dict]:
    turns_path = path / "condition_c" / "logs" / "turns.jsonl"
    return [
        json.loads(line)
        for line in turns_path.read_text(encoding="utf-8").splitlines()
    ]


def _responses(path: Path) -> list[str]:
    return [row["assistant_message"] for row in _turn_rows(path)]


def _prompts(path: Path) -> list[str]:
    condition_path = path / "condition_c"
    return [
        (condition_path / row["constructed_prompt_path"]).read_text(
            encoding="utf-8"
        )
        for row in _turn_rows(path)
    ]


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    phase = os.environ.get("CDW_DETERMINISM_PHASE", "").casefold()
    if phase not in {"a", "b", "compare"}:
        raise ValueError(
            "Set CDW_DETERMINISM_PHASE to a, b, or compare"
        )
    output_root = Path(
        os.environ.get(
            "CDW_RUNTIME_VERIFY_DIR",
            "experiments/study_005/runtime/determinism_prefix_003",
        )
    )
    output_root.mkdir(parents=True, exist_ok=True)

    if phase in {"a", "b"}:
        run_id = f"prefix_{phase}"
        run_path = output_root / run_id
        if run_path.exists():
            raise FileExistsError(
                f"Refusing to reuse prefix directory: {run_path}"
            )
        server_url = os.environ["CDW_INFERENCE_SERVER_URL"].rstrip("/")
        with urlopen(f"{server_url}/props", timeout=30) as response:
            server_props = json.loads(response.read().decode("utf-8"))
        runner = StudyRunner(
            script_path="experiments/study_005/script.json",
            study_dir=str(output_root),
            run_id=run_id,
            max_turns=PREFIX_TURNS,
            memory_formation="dreaming",
            context_capacity=50000,
            strict_monitoring=True,
        )
        runner.CONDITION_ORDER = ["iterative"]
        runner.CONDITION_OUTPUT_NAMES = {"iterative": "condition_c"}
        runner.run()
        responses = _responses(run_path)
        prompts = _prompts(run_path)
        with sqlite3.connect(
            run_path / "condition_c" / "study.db"
        ) as conn:
            dream_event_count = conn.execute(
                "SELECT COUNT(*) FROM dream_events"
            ).fetchone()[0]
            distilled_count = conn.execute(
                "SELECT COUNT(*) FROM distilled_ltm"
            ).fetchone()[0]
        if dream_event_count or distilled_count:
            raise AssertionError(
                "The ten-turn prefix must retain an empty distilled LTM"
            )
        manifest = {
            "phase": phase,
            "seed": 5005,
            "prefix_turns": PREFIX_TURNS,
            "single_slot": True,
            "speculative_decoding": False,
            "server_pid": int(os.environ["CDW_SERVER_PID"]),
            "server_props": server_props,
            "dream_event_count": dream_event_count,
            "distilled_count": distilled_count,
            "prompt_sha256": [
                _hash_text(prompt) for prompt in prompts
            ],
            "response_sha256": [
                _hash_text(response) for response in responses
            ],
        }
        (output_root / f"{run_id}_manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        print(f"PASS: completed seeded prefix phase {phase}")
        return

    first = _responses(output_root / "prefix_a")
    second = _responses(output_root / "prefix_b")
    first_prompts = _prompts(output_root / "prefix_a")
    second_prompts = _prompts(output_root / "prefix_b")
    first_manifest = json.loads(
        (output_root / "prefix_a_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    second_manifest = json.loads(
        (output_root / "prefix_b_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if first_manifest["server_pid"] == second_manifest["server_pid"]:
        raise AssertionError(
            "Determinism phases must use fresh server processes"
        )
    matches = [
        left == right
        for left, right in zip(first, second, strict=True)
    ]
    prompt_matches = [
        left == right
        for left, right in zip(
            first_prompts,
            second_prompts,
            strict=True,
        )
    ]
    report = {
        "seed": 5005,
        "prefix_turns": PREFIX_TURNS,
        "single_slot": True,
        "speculative_decoding": False,
        "fresh_server_per_phase": True,
        "server_pids": [
            first_manifest["server_pid"],
            second_manifest["server_pid"],
        ],
        "all_prompts_identical": all(prompt_matches),
        "all_turns_identical": all(matches),
        "turns": [
            {
                "turn": index,
                "prompt_identical": prompt_matches[index - 1],
                "identical": identical,
                "prompt_sha256": _hash_text(first_prompts[index - 1]),
                "response_sha256": _hash_text(first[index - 1]),
            }
            for index, identical in enumerate(matches, start=1)
        ],
    }
    (output_root / "determinism_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    if not report["all_prompts_identical"] or not report["all_turns_identical"]:
        mismatches = [
            item["turn"] for item in report["turns"]
            if not item["identical"]
        ]
        prompt_mismatches = [
            item["turn"] for item in report["turns"]
            if not item["prompt_identical"]
        ]
        raise AssertionError(
            f"Seeded prefix mismatch: prompts={prompt_mismatches}, "
            f"responses={mismatches}"
        )

    print(
        f"PASS: {PREFIX_TURNS} seeded prefix turns were byte-identical"
    )


if __name__ == "__main__":
    main()
