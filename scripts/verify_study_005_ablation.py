"""Verify the registered 35-turn Study 005 GO/NO-GO ablation."""

import csv
import json
import os
import sqlite3
from pathlib import Path

from src.analysis.study_005_evaluation import evaluate_formation
from src.memory.distilled_ltm_store import (
    CONTENT_STATUS,
    get_distilled_records,
    is_record_faithful,
)
from src.memory.dream_engine import DreamEngine


DEFAULT_RUN = Path(
    "experiments/study_005/ablation/runs/"
    "study_005_ablation_001/condition_c"
)
DEFAULT_OUTPUT = Path(
    "experiments/study_005/ablation/ablation_verification.json"
)
FACT_KEY = Path("experiments/study_005/q_facts_key.md")
DETERMINISM_REPORT = Path(
    "experiments/study_005/runtime/"
    "determinism_prefix_003/determinism_report.json"
)


def _csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _turn_rows(run_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (
            run_path / "logs" / "turns.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]


def main() -> None:
    run_path = Path(os.environ.get("CDW_ABLATION_RUN", DEFAULT_RUN))
    output_path = Path(
        os.environ.get("CDW_ABLATION_REPORT", DEFAULT_OUTPUT)
    )
    dream_events = _csv_rows(
        run_path / "dream_analysis" / "dream_events.csv"
    )
    ltm_context = _csv_rows(
        run_path / "logs" / "ltm_context_episodes.csv"
    )
    purity_events = _csv_rows(
        run_path / "logs" / "consolidation_purity.csv"
    )
    arbitration = _csv_rows(
        run_path / "logs" / "arbitration_events.csv"
    )
    performance = _csv_rows(
        run_path / "metrics" / "model_performance.csv"
    )
    context_sizes = _csv_rows(
        run_path / "metrics" / "context_sizes.csv"
    )
    turns = _turn_rows(run_path)
    determinism = json.loads(
        DETERMINISM_REPORT.read_text(encoding="utf-8")
    )

    with sqlite3.connect(run_path / "study.db") as conn:
        conn.row_factory = sqlite3.Row
        records = get_distilled_records(conn)
        content_records = [
            record
            for record in records
            if record["status"] == CONTENT_STATUS
        ]
        raw_count = conn.execute(
            "SELECT COUNT(*) FROM episodes"
        ).fetchone()[0]
        unique_raw_count = conn.execute(
            "SELECT COUNT(DISTINCT id) FROM episodes"
        ).fetchone()[0]
        promoted_count = conn.execute(
            "SELECT COUNT(*) FROM ltm_episodes"
        ).fetchone()[0]
        undreamed_art_count = conn.execute(
            "SELECT COUNT(*) FROM episodes "
            "WHERE turn_number BETWEEN 31 AND 35 AND dreamed = 0"
        ).fetchone()[0]
        faithful = all(
            is_record_faithful(conn, record)
            for record in content_records
        )
        formation = evaluate_formation(conn, FACT_KEY)

    post_event_ltm_rows = [
        row for row in ltm_context if int(row["turn"]) >= 32
    ]
    post_event_prompts = [
        (
            run_path / turns[turn - 1]["constructed_prompt_path"]
        ).read_text(encoding="utf-8")
        for turn in range(32, 36)
    ]
    rates = [float(row["tokens_per_second"]) for row in performance]
    peak_context = max(
        int(row["estimated_tokens"]) for row in context_sizes
    )
    ltm_final_turns = [
        int(row["turn"])
        for row in arbitration
        if int(row["ltm_episodes_in_final_set"]) > 0
    ]
    source_turns = sorted(
        turn
        for record in content_records
        for turn in record["source_turns"]
    )

    checks = {
        "speed_floor": min(rates) > 30.0,
        "determinism_gate": (
            determinism["all_prompts_identical"]
            and determinism["all_turns_identical"]
        ),
        "raw_store_append_only": (
            raw_count == unique_raw_count == len(turns) == 35
        ),
        "promotion_absent": promoted_count == 0,
        "first_dream_pass": (
            len(dream_events) == 1
            and int(dream_events[0]["turn"]) == 31
            and dream_events[0]["event_type"] == "transition"
        ),
        "distilled_records_written": (
            len(content_records) == 3
            and all(
                record["salience"] >= DreamEngine.SALIENCE_FLOOR
                for record in content_records
            )
        ),
        "extractive_assertion": faithful,
        "zero_dream_inference_calls": all(
            int(row["inference_calls"]) == 0 for row in dream_events
        ),
        "read_path_from_distilled_ltm": (
            {int(row["turn"]) for row in post_event_ltm_rows}
            == {32, 33, 34, 35}
            and all(
                "<retrieved_ltm>" in prompt
                and 'source_turns="' in prompt
                for prompt in post_event_prompts
            )
        ),
        "civil_fact_present": formation["per_domain"]
        ["civil engineering"]["present"],
        "zero_non_content_records": formation["non_content_count"] == 0,
        "arbitration_intact": (
            len(arbitration) == 35
            and ltm_final_turns == [32, 33, 34, 35]
            and all(
                int(row["final_set_size"]) <= 5 for row in arbitration
            )
        ),
        "purity": not any(
            row["event_type"] == "cross_domain_merge"
            for row in purity_events
        ),
        "art_topic_not_dreamed": undreamed_art_count == 5,
        "context_ceiling": peak_context < 40_000,
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "status": "PASS" if not failed else "FAIL",
        "decision": "GO" if not failed else "NO-GO",
        "run": str(run_path),
        "checks": checks,
        "failed_checks": failed,
        "raw_episode_count": raw_count,
        "dream_event_turns": [
            int(row["turn"]) for row in dream_events
        ],
        "distilled_record_count": len(content_records),
        "distilled_source_turns": source_turns,
        "faithfulness": formation["faithfulness"],
        "non_content_count": formation["non_content_count"],
        "civil_fact_present": formation["per_domain"]
        ["civil engineering"]["present"],
        "post_event_ltm_turns": sorted(
            {int(row["turn"]) for row in post_event_ltm_rows}
        ),
        "ltm_final_turns": ltm_final_turns,
        "purity_event_count": len(purity_events),
        "minimum_tokens_per_second": min(rates),
        "average_tokens_per_second": sum(rates) / len(rates),
        "peak_context_tokens": peak_context,
    }
    output_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    if failed:
        raise AssertionError(f"Ablation checks failed: {failed}")
    print("PASS: Study 005 ablation decision is GO")


if __name__ == "__main__":
    main()
