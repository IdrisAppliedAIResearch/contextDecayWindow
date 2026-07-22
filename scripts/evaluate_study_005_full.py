"""Evaluate the completed seeded control and full Study 005 treatment."""

import csv
import json
import os
import sqlite3
from pathlib import Path

from src.analysis.study_005_evaluation import (
    evaluate_bars,
    evaluate_formation,
    load_fact_key,
)


CONTROL = Path(
    "experiments/study_005/controls/promotion_seeded/"
    "promotion_seeded_001/condition_c"
)
TREATMENT = Path(
    "experiments/study_005/runs/study_005_full_001/condition_c"
)
FACT_KEY = Path("experiments/study_005/q_facts_key.md")
OUTPUT = Path("experiments/study_005/evaluation/study_005_results.json")

CONTROL_SCORES = {
    **{f"Q{index}": 1.0 for index in range(1, 11)},
    "Q11": 0.0,
    "Q12": 1.0,
    "Q13": 1.0,
    "Q14": 0.0,
}
TREATMENT_SCORES = {
    "Q1": 1.0,
    "Q2": 1.0,
    "Q3": 1.0,
    "Q4": 1.0,
    "Q5": 0.5,
    "Q6": 1.0,
    "Q7": 1.0,
    "Q8": 0.5,
    "Q9": 1.0,
    "Q10": 1.0,
    "Q11": 0.0,
    "Q12": 1.0,
    "Q13": 1.0,
    "Q14": 0.5,
}


def _csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _jsonl_rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def _normalize(text: str) -> str:
    return " ".join(
        text.casefold().replace("\N{EN DASH}", "-").replace("\N{EM DASH}", "-").split()
    )


def _prefix_result(control: Path, treatment: Path) -> dict:
    prompt_matches = []
    for turn in range(1, 31):
        name = f"turn_{turn:03d}.txt"
        prompt_matches.append(
            (control / "constructed_prompts" / name).read_bytes()
            == (treatment / "constructed_prompts" / name).read_bytes()
        )
    control_turns = _jsonl_rows(control / "logs" / "turns.jsonl")
    treatment_turns = _jsonl_rows(treatment / "logs" / "turns.jsonl")
    response_matches = [
        control_turns[index]["assistant_message"]
        == treatment_turns[index]["assistant_message"]
        for index in range(30)
    ]
    return {
        "turns_checked": 30,
        "prompt_matches": sum(prompt_matches),
        "response_matches": sum(response_matches),
        "prompt_mismatch_turns": [
            index + 1
            for index, matches in enumerate(prompt_matches)
            if not matches
        ],
        "response_mismatch_turns": [
            index + 1
            for index, matches in enumerate(response_matches)
            if not matches
        ],
        "pass": all(prompt_matches) and all(response_matches),
    }


def _performance(run: Path) -> dict:
    performance = _csv_rows(run / "metrics" / "model_performance.csv")
    contexts = _csv_rows(run / "metrics" / "context_sizes.csv")
    rates = [float(row["tokens_per_second"]) for row in performance]
    context_tokens = [int(row["estimated_tokens"]) for row in contexts]
    return {
        "turns": len(performance),
        "peak_context_tokens": max(context_tokens),
        "peak_context_fraction_of_50000": max(context_tokens) / 50_000,
        "minimum_tokens_per_second": min(rates),
        "average_tokens_per_second": sum(rates) / len(rates),
        "output_tokens": sum(int(row["output_tokens"]) for row in performance),
    }


def _probe_result(run: Path) -> dict:
    arbitration = {
        int(row["turn"]): row
        for row in _csv_rows(run / "logs" / "arbitration_events.csv")
    }
    ltm_rows = _csv_rows(run / "logs" / "ltm_context_episodes.csv")
    result = {}
    for question, turn in (("Q11", 120), ("Q14", 121)):
        row = arbitration[turn]
        selected_ltm = [
            item for item in ltm_rows if int(item["turn"]) == turn
        ]
        result[question] = {
            "turn": turn,
            "stm_candidates": int(row["stm_candidates"]),
            "ltm_candidates": int(row["ltm_candidates"]),
            "final_set_size": int(row["final_set_size"]),
            "ltm_records_in_final_set": int(
                row["ltm_episodes_in_final_set"]
            ),
            "ltm_source_turns": [
                int(item["episode_turn"]) for item in selected_ltm
            ],
            "dream_events": [
                int(item["dream_event"])
                for item in selected_ltm
                if item["dream_event"]
            ],
        }
    return result


def _dream_result(run: Path, fact_key: Path) -> dict:
    events = _csv_rows(run / "dream_analysis" / "dream_events.csv")
    salience = _csv_rows(run / "dream_analysis" / "episode_salience.csv")
    selected = [row for row in salience if row["selected"] == "True"]
    ranks = []
    for target in load_fact_key(fact_key):
        for source_turn in target.source_turns:
            row = next(
                item
                for item in salience
                if int(item["episode_turn"]) == source_turn
            )
            event_rows = sorted(
                (
                    item
                    for item in salience
                    if item["turn"] == row["turn"]
                ),
                key=lambda item: int(item["salience"]),
                reverse=True,
            )
            rank = next(
                index
                for index, item in enumerate(event_rows, start=1)
                if item["episode_id"] == row["episode_id"]
            )
            ranks.append({
                "domain": target.domain,
                "fact_id": target.fact_id,
                "source_turn": source_turn,
                "dream_event": int(row["turn"]),
                "salience": int(row["salience"]),
                "rank": rank,
                "selected": row["selected"] == "True",
            })
    return {
        "event_count": len(events),
        "event_turns": [int(row["turn"]) for row in events],
        "records_written": sum(int(row["records_written"]) for row in events),
        "inference_calls": sum(int(row["inference_calls"]) for row in events),
        "duplicates_collapsed": sum(
            int(row["duplicates_collapsed"]) for row in events
        ),
        "selected_source_turns": [
            int(row["episode_turn"]) for row in selected
        ],
        "selected_records": [
            {
                "dream_event": int(row["turn"]),
                "topic": row["topic"],
                "source_turn": int(row["episode_turn"]),
                "salience": int(row["salience"]),
                "named_entities": int(row["named_entities"]),
                "numeric_tokens": int(row["numeric_tokens"]),
            }
            for row in selected
        ],
        "rubric_fact_source_ranks": ranks,
    }


def _control_store_coverage(run: Path, fact_key: Path) -> dict:
    targets = load_fact_key(fact_key)
    with sqlite3.connect(run / "study.db") as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT episodes.turn_number, episodes.user_message, "
            "episodes.assistant_message FROM ltm_episodes "
            "JOIN episodes ON episodes.id = ltm_episodes.episode_id "
            "ORDER BY episodes.turn_number"
        ).fetchall()
    per_domain = {}
    for domain in sorted({target.domain for target in targets}):
        matches = []
        for target in [item for item in targets if item.domain == domain]:
            for row in rows:
                source_text = _normalize(
                    row["user_message"] + "\n" + row["assistant_message"]
                )
                if (
                    row["turn_number"] in target.source_turns
                    and all(
                        _normalize(term) in source_text
                        for term in target.required_terms
                    )
                ):
                    matches.append(target.fact_id)
                    break
        per_domain[domain] = {
            "present": bool(matches),
            "fact_ids": matches,
        }
    return {
        "record_count": len(rows),
        "source_turns": [row["turn_number"] for row in rows],
        "domains_present": sum(
            item["present"] for item in per_domain.values()
        ),
        "per_domain": per_domain,
    }


def main() -> None:
    control = Path(os.environ.get("CDW_STUDY005_CONTROL", CONTROL))
    treatment = Path(os.environ.get("CDW_STUDY005_TREATMENT", TREATMENT))
    output = Path(os.environ.get("CDW_STUDY005_RESULTS", OUTPUT))

    with sqlite3.connect(treatment / "study.db") as conn:
        conn.row_factory = sqlite3.Row
        formation = evaluate_formation(conn, FACT_KEY)
        raw_count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        dreamed_count = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE dreamed = 1"
        ).fetchone()[0]

    probes = _probe_result(treatment)
    probe_distilled_ltm = {
        question: details["ltm_records_in_final_set"] > 0
        for question, details in probes.items()
    }
    bars = evaluate_bars(
        formation=formation,
        treatment_scores=TREATMENT_SCORES,
        control_scores=CONTROL_SCORES,
        probe_distilled_ltm=probe_distilled_ltm,
    )
    memory_rows = _csv_rows(treatment / "metrics" / "memory_store.csv")
    purity_rows = _csv_rows(
        treatment / "logs" / "consolidation_purity.csv"
    )
    results = {
        "study": "study_005",
        "status": "complete",
        "scores_locked_at_commit": "1bbfad7",
        "confirmatory": bars,
        "formation": formation,
        "same_seed_prefix": _prefix_result(control, treatment),
        "dreaming": _dream_result(treatment, FACT_KEY),
        "probe_retrieval": probes,
        "control_promoted_store": _control_store_coverage(
            control, FACT_KEY
        ),
        "compression": {
            "raw_episode_count": raw_count,
            "dreamed_episode_count": dreamed_count,
            "distilled_content_records": formation["content_records"],
            "distilled_to_dreamed_ratio": (
                formation["content_records"] / dreamed_count
            ),
            "distilled_to_full_run_ratio": (
                formation["content_records"] / raw_count
            ),
        },
        "consolidation": {
            "final_topic_count": int(memory_rows[-1]["topic_count"]),
            "purity_event_count": len(purity_rows),
            "probe_bridge_guard_exercised": bool(purity_rows),
        },
        "runtime": {
            "control": _performance(control),
            "treatment": _performance(treatment),
            "context_monitor_ceiling_tokens": 40_000,
            "strict_monitor_abort": False,
        },
        "scores": {
            "control": CONTROL_SCORES,
            "treatment": TREATMENT_SCORES,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "bar_1": bars["bar_1"]["status"],
        "bar_2": bars["bar_2"]["status"],
        "bar_3": bars["bar_3"]["status"],
        "outcome": bars["confirmatory_outcome"],
    }, indent=2))


if __name__ == "__main__":
    main()
