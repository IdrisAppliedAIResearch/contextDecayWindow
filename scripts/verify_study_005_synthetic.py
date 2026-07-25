"""Verify the real-model Study 005 synthetic run and its replay."""

import csv
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from src.analysis.study_005_evaluation import _is_acknowledgment
from src.memory.distilled_ltm_store import (
    CONTENT_STATUS,
    NO_SALIENT_FACT_STATUS,
    get_distilled_records,
    is_record_faithful,
)
from src.memory.dream_engine import DreamEngine


DEFAULT_RUN = Path(
    "experiments/study_005/tests/runs/"
    "synthetic_study005_003/iterative"
)
DEFAULT_REPLAY = Path(
    "experiments/study_005/tests/runs/"
    "synthetic_study005_004/iterative"
)
DEFAULT_OUTPUT = Path(
    "experiments/study_005/tests/synthetic_verification.json"
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


def _prompts(run_path: Path, turns: list[dict]) -> list[str]:
    return [
        (run_path / row["constructed_prompt_path"]).read_text(
            encoding="utf-8"
        )
        for row in turns
    ]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    run_path = Path(os.environ.get("CDW_SYNTHETIC_RUN", DEFAULT_RUN))
    replay_path = Path(
        os.environ.get("CDW_SYNTHETIC_REPLAY", DEFAULT_REPLAY)
    )
    output_path = Path(
        os.environ.get("CDW_SYNTHETIC_REPORT", DEFAULT_OUTPUT)
    )
    dream_events = _csv_rows(
        run_path / "dream_analysis" / "dream_events.csv"
    )
    dedup_events = _csv_rows(
        run_path / "dream_analysis" / "dedup_events.csv"
    )
    purity_events = _csv_rows(
        run_path / "logs" / "consolidation_purity.csv"
    )
    ltm_context = _csv_rows(
        run_path / "logs" / "ltm_context_episodes.csv"
    )
    context_sizes = _csv_rows(
        run_path / "metrics" / "context_sizes.csv"
    )

    with sqlite3.connect(run_path / "study.db") as conn:
        conn.row_factory = sqlite3.Row
        records = get_distilled_records(conn)
        content_records = [
            record
            for record in records
            if record["status"] == CONTENT_STATUS
        ]
        markers = [
            record
            for record in records
            if record["status"] == NO_SALIENT_FACT_STATUS
        ]
        raw_count = conn.execute(
            "SELECT COUNT(*) FROM episodes"
        ).fetchone()[0]
        sparse_raw_count = conn.execute(
            "SELECT COUNT(*) FROM episodes "
            "WHERE turn_number BETWEEN 6 AND 9"
        ).fetchone()[0]
        dreamed_pre_probe = conn.execute(
            "SELECT COUNT(*) FROM episodes "
            "WHERE turn_number <= 19 AND dreamed = 1"
        ).fetchone()[0]
        probe_dreamed = conn.execute(
            "SELECT COUNT(*) FROM episodes "
            "WHERE turn_number >= 20 AND dreamed = 1"
        ).fetchone()[0]
        promoted_count = conn.execute(
            "SELECT COUNT(*) FROM ltm_episodes"
        ).fetchone()[0]
        faithful = all(
            is_record_faithful(conn, record)
            for record in content_records
        )

    distilled_text = "\n".join(
        record["text"] or "" for record in content_records
    ).casefold()
    fact_presence = {
        "pulsar": all(
            term in distilled_text
            for term in ("ax-17", "43.7", "livia noor")
        ),
        "orchid": all(
            term in distilled_text
            for term in ("dz-53", "17.2", "ren ito")
        ),
        "treaty": all(
            term in distilled_text
            for term in ("cy-41", "14-day", "amara voss")
        ),
        "withheld_nv_99": "nv-99" in distilled_text,
    }
    non_content_count = sum(
        record["salience"] < DreamEngine.SALIENCE_FLOOR
        or _is_acknowledgment(record["text"])
        for record in content_records
    )

    turns = _turn_rows(run_path)
    replay_turns = _turn_rows(replay_path)
    responses = [row["assistant_message"] for row in turns]
    replay_responses = [
        row["assistant_message"] for row in replay_turns
    ]
    prompts = _prompts(run_path, turns)
    replay_prompts = _prompts(replay_path, replay_turns)
    response_matches = [
        left == right
        for left, right in zip(
            responses,
            replay_responses,
            strict=True,
        )
    ]
    prompt_matches = [
        left == right
        for left, right in zip(
            prompts,
            replay_prompts,
            strict=True,
        )
    ]

    event_turns = [int(row["turn"]) for row in dream_events]
    checks = {
        "raw_store_permissive": raw_count == 24 and sparse_raw_count == 4,
        "promotion_absent": promoted_count == 0,
        "dedup_collapsed": len(dedup_events) >= 1,
        "per_topic_cap_respected": all(
            int(row["records_written"]) <= DreamEngine.PER_TOPIC_CAP
            for row in dream_events
        ),
        "number_weight_visible": any(
            record["salience"] >= 4 for record in content_records
        ),
        "sparse_marker_only": (
            len(markers) == 1
            and markers[0]["dream_event"] == 10
            and markers[0]["text"] is None
        ),
        "extractive_faithfulness": faithful,
        "zero_dream_inference_calls": all(
            int(row["inference_calls"]) == 0 for row in dream_events
        ),
        "cadence": event_turns == [6, 10, 15, 19],
        "pre_probe_dreamed": dreamed_pre_probe == 19,
        "probe_block_undreamed": probe_dreamed == 0,
        "distilled_read_path": any(
            int(row["turn"]) >= 20 for row in ltm_context
        ),
        "facts_present": all(
            fact_presence[name] for name in ("pulsar", "orchid", "treaty")
        ),
        "withheld_fact_absent": not fact_presence["withheld_nv_99"],
        "zero_non_content_records": non_content_count == 0,
        "probe_bridge_blocked": any(
            row["event_type"] == "probe_bridge_blocked"
            for row in purity_events
        ),
        "prompt_replay_identical": all(prompt_matches),
        "response_replay_identical": all(response_matches),
        "context_ceiling": max(
            int(row["estimated_tokens"]) for row in context_sizes
        ) < 40_000,
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "status": "PASS" if not failed else "FAIL",
        "run": str(run_path),
        "replay": str(replay_path),
        "checks": checks,
        "failed_checks": failed,
        "raw_episode_count": raw_count,
        "content_record_count": len(content_records),
        "marker_count": len(markers),
        "dream_event_turns": event_turns,
        "dedup_event_count": len(dedup_events),
        "non_content_count": non_content_count,
        "fact_presence": fact_presence,
        "purity_event_types": [
            row["event_type"] for row in purity_events
        ],
        "peak_context_tokens": max(
            int(row["estimated_tokens"]) for row in context_sizes
        ),
        "turns": [
            {
                "turn": index,
                "prompt_identical": prompt_matches[index - 1],
                "response_identical": response_matches[index - 1],
                "prompt_sha256": _sha256(prompts[index - 1]),
                "response_sha256": _sha256(responses[index - 1]),
            }
            for index in range(1, len(turns) + 1)
        ],
    }
    output_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    if failed:
        raise AssertionError(f"Synthetic checks failed: {failed}")
    print("PASS: all Study 005 synthetic checks passed")


if __name__ == "__main__":
    main()
