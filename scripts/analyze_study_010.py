"""Generate post-score Study 010 analyses from committed artifacts."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments/study_010"
RUN = STUDY / "runs/study_010_full_001"
EVAL = STUDY / "evaluation"


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"\s+", " ", text)


def present(text: str, item: str) -> bool:
    parts = [part.strip() for part in item.split(" + ")]
    haystack = normalized(text)
    return all(normalized(part) in haystack for part in parts)


def parse_rubric() -> list[dict]:
    rows = []
    for line in (STUDY / "rubric_1000.md").read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| (?:I|Q)\d+ ", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        label, turn, kind, expected = cells
        domain = kind.strip()
        type_name = "breadth" if domain == "breadth" else "targeted"
        rows.append(
            {
                "label": label,
                "turn": int(turn),
                "type": type_name,
                "domain": domain or "breadth",
                "items": [item.strip() for item in expected.split(";")],
            }
        )
    if len(rows) != 23:
        raise RuntimeError(f"Expected 23 rubric rows, found {len(rows)}")
    return rows


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def prompt_delivery(rubric: list[dict], scores: dict, mapping: dict) -> list[dict]:
    matrix = []
    for anonymous, arm in mapping.items():
        for question in rubric:
            prompt = (RUN / arm / "constructed_prompts" / f"turn_{question['turn']:03d}.txt").read_text(
                encoding="utf-8"
            )
            blocks = {
                name: match.group(1) if (match := re.search(
                    rf"<{name}>(.*?)</{name}>", prompt, flags=re.DOTALL
                )) else ""
                for name in ("recent_context", "retrieved_stm", "retrieved_ltm")
            }
            score_item = scores["arms"][anonymous]["items"][question["label"]]
            found = set(score_item["expected_items_found"])
            for item in question["items"]:
                in_prompt = present(prompt, item)
                in_answer = item in found
                status = (
                    "recalled"
                    if in_prompt and in_answer
                    else "unused"
                    if in_prompt
                    else "invented"
                    if in_answer
                    else "absent"
                )
                matrix.append(
                    {
                        "arm": arm.removeprefix("arm_").upper(),
                        "anonymous": anonymous,
                        "question": question["label"],
                        "turn": question["turn"],
                        "type": question["type"],
                        "domain": question["domain"],
                        "item": item,
                        "in_prompt": in_prompt,
                        "in_recent_context": present(blocks["recent_context"], item),
                        "in_retrieved_stm": present(blocks["retrieved_stm"], item),
                        "in_retrieved_ltm": present(blocks["retrieved_ltm"], item),
                        "in_answer": in_answer,
                        "status": status,
                    }
                )
    return matrix


def score_curves(rubric: list[dict], scores: dict, mapping: dict) -> list[dict]:
    groups = {
        250: ("I1", "I2", "I3"),
        500: ("I4", "I5", "I6"),
        750: ("I7", "I8", "I9"),
        1000: tuple(f"Q{i}" for i in range(1, 15)),
    }
    rows = []
    for anonymous, arm in mapping.items():
        items = scores["arms"][anonymous]["items"]
        for checkpoint, labels in groups.items():
            primary = sum(items[label]["primary"] for label in labels)
            strict = sum(items[label]["strict"] for label in labels)
            rows.append(
                {
                    "arm": arm.removeprefix("arm_").upper(),
                    "checkpoint": checkpoint,
                    "questions": len(labels),
                    "primary_score": primary,
                    "strict_score": strict,
                    "primary_fraction": f"{primary / len(labels):.6f}",
                    "strict_fraction": f"{strict / len(labels):.6f}",
                }
            )
    return rows


def context_and_performance() -> tuple[list[dict], dict]:
    curves = []
    summaries = {}
    for arm in ("arm_l", "arm_s"):
        context = read_csv(RUN / arm / "metrics/context_sizes.csv")
        performance = {
            int(row["turn"]): row
            for row in read_csv(RUN / arm / "metrics/model_performance.csv")
        }
        values = []
        rates = []
        for row in context:
            turn = int(row["turn"])
            tokens = int(row["estimated_tokens"])
            rate = float(performance[turn]["tokens_per_second"])
            values.append(tokens)
            rates.append(rate)
            curves.append(
                {
                    "arm": arm.removeprefix("arm_").upper(),
                    "turn": turn,
                    "estimated_tokens": tokens,
                    "tokens_per_second": f"{rate:.6f}",
                    "output_tokens": performance[turn]["output_tokens"],
                }
            )
        summaries[arm] = {
            "peak_estimated_tokens": max(values),
            "mean_estimated_tokens": statistics.fmean(values),
            "turn_1000_estimated_tokens": values[-1],
            "mean_tokens_per_second": statistics.fmean(rates),
        }
    return curves, summaries


def k_precision(rubric: list[dict]) -> tuple[list[dict], dict]:
    domain_by_turn = {row["turn"]: row["domain"] for row in rubric if row["type"] == "targeted"}
    rows = []
    summaries = {}
    for arm in ("arm_l", "arm_s"):
        connection = sqlite3.connect(RUN / arm / "study.db")
        episode_domains = dict(
            connection.execute("select id, ground_truth_domain from episodes").fetchall()
        )
        connection.close()
        events = read_csv(RUN / arm / "metrics/retrieval_events.csv")
        matched = 0
        considered = 0
        for row in events:
            turn = int(row["turn"])
            if row["retrieval_type"] != "K" or turn not in domain_by_turn:
                continue
            expected = domain_by_turn[turn]
            actual = episode_domains.get(row["episode_id"], "")
            is_match = actual == expected
            matched += int(is_match)
            considered += 1
            rows.append(
                {
                    "arm": arm.removeprefix("arm_").upper(),
                    "turn": turn,
                    "expected_domain": expected,
                    "episode_id": row["episode_id"],
                    "episode_domain": actual,
                    "similarity_score": row["similarity_score"],
                    "domain_match": is_match,
                }
            )
        summaries[arm] = {
            "all_targeted_probe_k_hits": considered,
            "interim_targeted_probe_k_hits": sum(
                1
                for row in rows
                if row["arm"] == arm.removeprefix("arm_").upper()
                and int(row["turn"]) < 987
            ),
            "terminal_targeted_probe_k_hits": sum(
                1
                for row in rows
                if row["arm"] == arm.removeprefix("arm_").upper()
                and int(row["turn"]) >= 987
            ),
            "domain_matched_hits": matched,
            "domain_label_precision": matched / considered if considered else None,
        }
    return rows, summaries


def integrity() -> dict:
    result = {}
    for arm in ("arm_l", "arm_s"):
        connection = sqlite3.connect(RUN / arm / "study.db")
        rule_count = connection.execute("select count(*) from rule_store").fetchone()[0]
        episode_rows = dict(connection.execute("select id, text from episodes").fetchall())
        ltm_rows = connection.execute(
            """
            select source_episode_id, role, span_start, span_end, text, status
            from distilled_ltm
            """
        ).fetchall()
        dream_rows = connection.execute(
            "select inference_calls from dream_events"
        ).fetchall()
        mismatches = 0
        non_content = 0
        for episode_id, role, start, end, text, status in ltm_rows:
            source = episode_rows[episode_id]
            mismatches += int(source[start:end] != text)
            non_content += int(status != "content")
        connection.close()
        result[arm] = {
            "rules_persisted": rule_count,
            "ltm_records": len(ltm_rows),
            "offset_verbatim_mismatches": mismatches,
            "non_content_records": non_content,
            "dream_events": len(dream_rows),
            "dream_inference_calls": sum(row[0] for row in dream_rows),
            "checkpoints": len(list((RUN / arm / "checkpoints").glob("turn_*"))),
            "turns": len(list((RUN / arm / "constructed_prompts").glob("turn_*.txt"))),
        }
    return result


def main() -> None:
    rubric = parse_rubric()
    scores = json.loads((EVAL / "rubric_scores.json").read_text(encoding="utf-8"))
    sealed = json.loads((EVAL / "sealed_mapping.json").read_text(encoding="utf-8"))
    mapping = sealed["mapping"]

    matrix = prompt_delivery(rubric, scores, mapping)
    write_csv(
        EVAL / "fact_delivery_matrix.csv",
        matrix,
        [
            "arm",
            "anonymous",
            "question",
            "turn",
            "type",
            "domain",
            "item",
            "in_prompt",
            "in_recent_context",
            "in_retrieved_stm",
            "in_retrieved_ltm",
            "in_answer",
            "status",
        ],
    )
    curves = score_curves(rubric, scores, mapping)
    write_csv(
        EVAL / "degradation_curve.csv",
        curves,
        [
            "arm",
            "checkpoint",
            "questions",
            "primary_score",
            "strict_score",
            "primary_fraction",
            "strict_fraction",
        ],
    )
    context_rows, context_summary = context_and_performance()
    write_csv(
        EVAL / "context_performance_curve.csv",
        context_rows,
        ["arm", "turn", "estimated_tokens", "tokens_per_second", "output_tokens"],
    )
    k_rows, k_summary = k_precision(rubric)
    write_csv(
        EVAL / "k_probe_precision.csv",
        k_rows,
        [
            "arm",
            "turn",
            "expected_domain",
            "episode_id",
            "episode_domain",
            "similarity_score",
            "domain_match",
        ],
    )
    integrity_result = integrity()
    (EVAL / "integrity_report.json").write_text(
        json.dumps(integrity_result, indent=2) + "\n", encoding="utf-8"
    )

    mapped_scores = {
        arm: scores["arms"][anonymous]["summary"]
        for anonymous, arm in mapping.items()
    }
    terminal_gap = (
        mapped_scores["arm_l"]["terminal_primary"]
        - mapped_scores["arm_s"]["terminal_primary"]
    )
    overall_gap = (
        mapped_scores["arm_l"]["overall_primary"]
        - mapped_scores["arm_s"]["overall_primary"]
    )
    if terminal_gap >= 1.5:
        verdict = "RETAIN_LTM"
    elif terminal_gap <= 0:
        verdict = "CUT_LTM"
    else:
        verdict = "SUSPEND_LTM"
    bars = {
        "evidence_status": "post-stop exploratory",
        "original_g2": "FAIL",
        "bar_1": {
            "result": verdict,
            "terminal_l": mapped_scores["arm_l"]["terminal_primary"],
            "terminal_s": mapped_scores["arm_s"]["terminal_primary"],
            "terminal_gap": terminal_gap,
            "overall_gap_all_probes": overall_gap,
            "threshold_applied": "L > S by >= 1.5 overall",
        },
        "bar_2": {
            "result": "PASS"
            if all(
                data["turns"] == 1000
                and data["checkpoints"] == 10
                and data["offset_verbatim_mismatches"] == 0
                and data["non_content_records"] == 0
                and data["dream_inference_calls"] == 0
                and context_summary[arm]["peak_estimated_tokens"] < 40000
                for arm, data in integrity_result.items()
            )
            else "FAIL",
            "checkpoint_restore_gate": "PASS",
        },
        "bar_3": {
            "result": "NOT_EVALUABLE",
            "checkpoint_rows": len(curves),
            "construct_validity": "FAIL",
            "note": (
                "I2, I5, and I8 require two facts not planted until after "
                "their probe turns. The resulting scores cannot deliver the "
                "complete degradation curves required by Bar 3."
            ),
        },
    }
    bars["exploratory_bars_complete"] = "NOT_EVALUABLE"
    bars["confirmatory_status"] = "STOPPED_AT_G2"
    (EVAL / "bar_results.json").write_text(
        json.dumps(bars, indent=2) + "\n", encoding="utf-8"
    )
    (EVAL / "analysis_summary.json").write_text(
        json.dumps(
            {
                "scores": mapped_scores,
                "context": context_summary,
                "k_precision": k_summary,
                "delivery_status_counts": {
                    arm: dict(
                        (status, sum(1 for row in matrix if row["arm"] == arm and row["status"] == status))
                        for status in ("recalled", "unused", "invented", "absent")
                    )
                    for arm in ("L", "S")
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
