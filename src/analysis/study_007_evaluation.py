"""Study 007 bar evaluation and retrieval-budget mechanism analysis.

Formation (Bar 3) reuses the Study 006 evaluator unchanged — formation is
carried, so the check that validated it should be too.

What is new here is Bar 1's **attribution requirement**: breadth counts as a
retrieval-budget effect only if the probe-turn LTM block actually contained all
four domains. That is checked twice, against two different artifacts:

  * `retrieval_budget.csv` — what the selector believed it admitted;
  * the constructed prompt's `<retrieved_ltm>` block — what the model received.

They should agree. Checking both is the point: Study 006's analysis reported
coverage from a third artifact (distilled record text) that turned out not to be
what the model saw at all, and no one noticed for a whole study.
"""

import csv
import json
import re
import sqlite3
from pathlib import Path

from src.analysis.study_006_evaluation import evaluate_formation, observations
from src.analysis.study_007_replay import DOMAIN_TERMS

LTM_BLOCK = re.compile(r"<retrieved_ltm>.*?</retrieved_ltm>", re.S)
EPISODE_HEAD = re.compile(r'<episode turn="(\d+)" topic="([^"]+)"')

PROBE_TURNS = (120, 121)
# From the locked rubric, experiments/study_002/rubric_filled.md.
# Bar 2 reads Cat 1-3 (plant survival); Cat 4 is bleed detection and Cat 5 is
# rule compliance, both scored but outside Bar 2's per-category condition.
CATEGORY_QUESTIONS = {
    "cat_1": ["Q1", "Q2", "Q3"],
    "cat_2": ["Q4", "Q5", "Q6"],
    "cat_3": ["Q7", "Q8"],
    "cat_4": ["Q9", "Q10", "Q11"],
    "cat_5": ["Q12", "Q13"],
}
BAR2_CATEGORIES = ("cat_1", "cat_2", "cat_3")


def rendered_block(run_dir: Path, turn: int) -> str:
    path = run_dir / "constructed_prompts" / f"turn_{turn:03d}.txt"
    if not path.exists():
        return ""
    match = LTM_BLOCK.search(path.read_text(encoding="utf-8"))
    return match.group(0) if match else ""


def block_coverage(run_dir: Path, turn: int) -> dict:
    """Domains present in the block the model actually received."""
    block = rendered_block(run_dir, turn)
    heads = EPISODE_HEAD.findall(block)
    found = {
        domain: [term for term in terms if term.lower() in block.lower()]
        for domain, terms in DOMAIN_TERMS.items()
    }
    covered = sorted(d for d, hits in found.items() if hits)
    return {
        "turn": turn,
        "block_chars": len(block),
        "episodes": len(heads),
        "topics": sorted({topic for _, topic in heads}),
        "topic_count": len({topic for _, topic in heads}),
        "domains_covered": covered,
        "four_domain": len(covered) == 4,
        "terms_found": found,
    }


def budget_log(run_dir: Path) -> list[dict]:
    path = run_dir / "logs" / "retrieval_budget.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def budget_coverage(run_dir: Path, turn: int) -> dict | None:
    """What the selector recorded admitting at `turn`."""
    for row in budget_log(run_dir):
        if int(row["turn"]) != turn:
            continue
        return {
            "turn": turn,
            "topic_count": int(row["topic_count"]),
            "topics_present": json.loads(row["topics_present"]),
            "chars_used": int(row["ltm_chars_used"]),
            "records_used": int(row["ltm_records_used"]),
            "floor_per_topic": json.loads(row["floor_selected_per_topic"]),
            "fill_selected": int(row["fill_selected"]),
            "containment_drops": int(row["containment_drops"]),
            "utilization": float(row["budget_utilization"]),
            "chars_per_topic": json.loads(row["chars_per_topic"]),
        }
    return None


def delivered_information(run_dir: Path) -> dict:
    """Characters of LTM the model received per turn, from the prompts."""
    per_turn = {}
    prompts = run_dir / "constructed_prompts"
    for path in sorted(prompts.glob("turn_*.txt")):
        turn = int(path.stem.split("_")[1])
        match = LTM_BLOCK.search(path.read_text(encoding="utf-8"))
        per_turn[turn] = len(match.group(0)) if match else 0
    non_empty = [chars for chars in per_turn.values() if chars > 0]
    return {
        "per_turn": per_turn,
        "turns_with_ltm": len(non_empty),
        "mean_chars_when_non_empty": (
            sum(non_empty) / len(non_empty) if non_empty else 0
        ),
        "max_chars": max(per_turn.values()) if per_turn else 0,
    }


def evaluate_bars(
    treatment_dir: Path,
    control_dir: Path,
    fact_key_path: str | Path,
    scores: dict,
) -> dict:
    """Bar 3 first — it is Bar 1's precondition."""
    with sqlite3.connect(
        f"file:{treatment_dir / 'study.db'}?mode=ro", uri=True
    ) as conn:
        formation = evaluate_formation(conn, fact_key_path)
        obs = observations(conn)

    inference_calls = obs.get("inference_calls_total")
    bar3 = {
        "domains_formed": formation["domains_formed"],
        "records_content": formation["records_content"],
        "records_non_content": formation["records_non_content"],
        "unfaithful": formation["unfaithful"],
        "inference_calls": inference_calls,
        "pass": (
            formation["domains_formed"] == 4
            and formation["records_non_content"] == 0
            and formation["unfaithful"] == 0
            and (inference_calls in (0, None))
        ),
    }

    coverage = {
        turn: {
            "rendered": block_coverage(treatment_dir, turn),
            "logged": budget_coverage(treatment_dir, turn),
            "control_rendered": block_coverage(control_dir, turn),
        }
        for turn in PROBE_TURNS
    }

    q11 = float(scores["treatment"]["primary"]["Q11"])
    q14 = float(scores["treatment"]["primary"]["Q14"])
    four_domain_both = all(
        coverage[turn]["rendered"]["four_domain"] for turn in PROBE_TURNS
    )
    bar1 = {
        "evaluable": bar3["pass"],
        "q11": q11,
        "q14": q14,
        "sum": q11 + q14,
        "four_domain_in_block": four_domain_both,
        "per_probe": {
            turn: {
                "treatment_domains": coverage[turn]["rendered"][
                    "domains_covered"
                ],
                "control_domains": coverage[turn]["control_rendered"][
                    "domains_covered"
                ],
            }
            for turn in PROBE_TURNS
        },
        "pass": (
            bar3["pass"] and q11 >= 0.5 and q14 >= 0.5 and q11 + q14 >= 1.5
        ),
        "attribution": (
            "four-domain coverage confirmed in the probe-turn block"
            if four_domain_both
            else "coverage NOT four-domain — a pass here is unattributed"
        ),
    }

    def q_total(arm: str, scoring: str, questions: list[str]) -> float:
        return sum(float(scores[arm][scoring][q]) for q in questions)

    q1_13 = [f"Q{i}" for i in range(1, 14)]
    bar2 = {}
    for scoring in ("primary", "strict"):
        treatment_total = q_total("treatment", scoring, q1_13)
        control_total = q_total("control", scoring, q1_13)
        categories = {
            name: {
                "treatment": q_total("treatment", scoring, questions),
                "control": q_total("control", scoring, questions),
            }
            for name, questions in CATEGORY_QUESTIONS.items()
            if name in BAR2_CATEGORIES
        }
        bar2[scoring] = {
            "treatment_q1_13": treatment_total,
            "control_q1_13": control_total,
            "categories": categories,
            "categories_not_below": all(
                v["treatment"] >= v["control"] for v in categories.values()
            ),
            "pass": (
                treatment_total >= control_total
                and all(
                    v["treatment"] >= v["control"] for v in categories.values()
                )
            ),
        }

    return {
        "bar3_formation": bar3,
        "bar1_breadth": bar1,
        "bar2_targeted": bar2,
        "coverage": coverage,
        "observations": obs,
        "verdict": (
            "VALIDATED"
            if bar3["pass"] and bar1["pass"] and bar2["primary"]["pass"]
            else "PARTIAL"
        ),
    }
