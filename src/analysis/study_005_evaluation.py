"""Study 005 formation, faithfulness, non-content, and bar evaluation."""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.memory.distilled_ltm_store import (
    CONTENT_STATUS,
    get_distilled_records,
    get_source_texts,
    is_record_faithful,
)
from src.memory.dream_engine import DreamEngine


DOMAIN_HEADINGS = {
    "civil engineering",
    "renaissance art",
    "monetary policy",
    "marine biology",
}
ACKNOWLEDGMENT_WORDS = {
    "acknowledged",
    "alright",
    "confirmed",
    "got",
    "great",
    "it",
    "noted",
    "ok",
    "okay",
    "sure",
    "thanks",
    "thank",
    "understood",
    "you",
}


@dataclass(frozen=True)
class FactTarget:
    domain: str
    fact_id: str
    required_terms: tuple[str, ...]
    source_turns: tuple[int, ...]
    rubric_dependency: str


def load_fact_key(path: str | Path) -> list[FactTarget]:
    targets = []
    domain = None
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            candidate = line.removeprefix("## ").strip().casefold()
            domain = candidate if candidate in DOMAIN_HEADINGS else None
            continue
        if domain is None or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if (
            len(cells) != 4
            or cells[0] in {"Fact ID", "---"}
            or set(cells[0]) == {"-"}
        ):
            continue
        targets.append(
            FactTarget(
                domain=domain,
                fact_id=cells[0],
                required_terms=tuple(
                    term.strip()
                    for term in cells[1].split(";")
                    if term.strip()
                ),
                source_turns=tuple(
                    int(turn)
                    for turn in re.findall(r"\d+", cells[2])
                ),
                rubric_dependency=cells[3],
            )
        )
    if not targets:
        raise ValueError(f"No fact targets found in {path}")
    missing_domains = DOMAIN_HEADINGS - {target.domain for target in targets}
    if missing_domains:
        raise ValueError(
            "Fact key is missing domains: "
            + ", ".join(sorted(missing_domains))
        )
    return targets


def _normalize(text: str) -> str:
    return " ".join(
        text.casefold()
        .replace("–", "-")
        .replace("—", "-")
        .split()
    )


def _is_acknowledgment(text: str) -> bool:
    content = re.sub(r"(?im)^(user|assistant):\s*", "", text)
    words = re.findall(r"[a-z]+", content.casefold())
    return bool(words) and len(words) <= 8 and set(words) <= ACKNOWLEDGMENT_WORDS


def evaluate_formation(
    conn: sqlite3.Connection,
    fact_key_path: str | Path,
) -> dict:
    targets = load_fact_key(fact_key_path)
    records = get_distilled_records(conn)
    content_records = [
        record for record in records if record["status"] == CONTENT_STATUS
    ]
    record_details = []
    provenance_by_record = {}
    for record in content_records:
        source_texts = get_source_texts(
            conn,
            record["source_episode_ids"],
        )
        provenance = "\n".join(source_texts.values())
        provenance_by_record[record["id"]] = provenance
        faithful = is_record_faithful(conn, record)
        non_content = (
            record["salience"] < DreamEngine.SALIENCE_FLOOR
            or _is_acknowledgment(record["text"])
        )
        record_details.append({
            "distilled_id": record["id"],
            "source_episode_id": record["source_episode_id"],
            "source_turns": record["source_turns"],
            "salience": record["salience"],
            "faithful": faithful,
            "non_content": non_content,
        })

    target_results = []
    for target in targets:
        matching_records = []
        for record in content_records:
            normalized = _normalize(provenance_by_record[record["id"]])
            has_terms = all(
                _normalize(term) in normalized
                for term in target.required_terms
            )
            has_source_turn = bool(
                set(target.source_turns) & set(record["source_turns"])
            )
            if has_terms and has_source_turn:
                matching_records.append(record["id"])
        target_results.append({
            "domain": target.domain,
            "fact_id": target.fact_id,
            "required_terms": list(target.required_terms),
            "source_turns": list(target.source_turns),
            "present": bool(matching_records),
            "matching_distilled_ids": matching_records,
        })

    per_domain = {}
    for domain in sorted(DOMAIN_HEADINGS):
        domain_targets = [
            result for result in target_results
            if result["domain"] == domain
        ]
        per_domain[domain] = {
            "present": any(result["present"] for result in domain_targets),
            "targets": domain_targets,
        }

    faithful_count = sum(detail["faithful"] for detail in record_details)
    total_content = len(record_details)
    faithfulness = (
        faithful_count / total_content if total_content else 1.0
    )
    non_content_ids = [
        detail["distilled_id"]
        for detail in record_details
        if detail["non_content"]
    ]
    domains_present = sum(
        result["present"] for result in per_domain.values()
    )
    bar_1_pass = (
        domains_present >= 3
        and faithfulness == 1.0
        and not non_content_ids
    )
    return {
        "extractor": DreamEngine.EXTRACTOR,
        "domains_present": domains_present,
        "all_four_domains_present": domains_present == 4,
        "per_domain": per_domain,
        "faithful_records": faithful_count,
        "content_records": total_content,
        "faithfulness": faithfulness,
        "non_content_count": len(non_content_ids),
        "non_content_distilled_ids": non_content_ids,
        "marker_count": sum(
            record["status"] != CONTENT_STATUS for record in records
        ),
        "records": record_details,
        "bar_1_pass": bar_1_pass,
    }


def validate_scores(scores: dict[str, float]) -> None:
    expected = {f"Q{index}" for index in range(1, 15)}
    actual = set(scores)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"Scores must contain Q1-Q14; missing={missing}, extra={extra}"
        )
    invalid = {
        question: score
        for question, score in scores.items()
        if score not in {0.0, 0.5, 1.0}
    }
    if invalid:
        raise ValueError(f"Scores must use 0/0.5/1.0: {invalid}")


def _category_totals(scores: dict[str, float]) -> dict[str, float]:
    return {
        "cat_1": sum(scores[f"Q{index}"] for index in range(1, 4)),
        "cat_2": sum(scores[f"Q{index}"] for index in range(4, 7)),
        "cat_3": sum(scores[f"Q{index}"] for index in range(7, 9)),
        "cat_4": sum(scores[f"Q{index}"] for index in range(9, 12)),
        "cat_5": sum(scores[f"Q{index}"] for index in range(12, 14)),
    }


def evaluate_bars(
    *,
    formation: dict,
    treatment_scores: dict[str, float],
    control_scores: dict[str, float],
    probe_distilled_ltm: dict[str, bool],
) -> dict:
    validate_scores(treatment_scores)
    validate_scores(control_scores)
    if set(probe_distilled_ltm) != {"Q11", "Q14"}:
        raise ValueError("Probe provenance must contain Q11 and Q14")

    treatment_categories = _category_totals(treatment_scores)
    control_categories = _category_totals(control_scores)
    treatment_q1_q13 = sum(
        treatment_scores[f"Q{index}"] for index in range(1, 14)
    )
    control_q1_q13 = sum(
        control_scores[f"Q{index}"] for index in range(1, 14)
    )

    bar_1 = bool(formation["bar_1_pass"])
    if not bar_1:
        bar_2_status = "NOT EVALUABLE"
        bar_2_pass = None
    else:
        breadth_scores_pass = (
            treatment_scores["Q11"] >= 0.5
            and treatment_scores["Q14"] >= 0.5
            and treatment_scores["Q11"] + treatment_scores["Q14"] >= 1.5
        )
        bar_2_pass = breadth_scores_pass and all(
            probe_distilled_ltm.values()
        )
        bar_2_status = "PASS" if bar_2_pass else "FAIL"

    categories_held = all(
        treatment_categories[name] >= control_categories[name]
        for name in ("cat_1", "cat_2", "cat_3")
    )
    bar_3 = (
        treatment_q1_q13 >= control_q1_q13
        and categories_held
    )
    all_pass = bar_1 and bar_2_pass is True and bar_3
    return {
        "bar_1": {
            "status": "PASS" if bar_1 else "FAIL",
            "pass": bar_1,
        },
        "bar_2": {
            "status": bar_2_status,
            "pass": bar_2_pass,
            "probe_distilled_ltm": dict(probe_distilled_ltm),
        },
        "bar_3": {
            "status": "PASS" if bar_3 else "FAIL",
            "pass": bar_3,
            "treatment_q1_q13": treatment_q1_q13,
            "control_q1_q13": control_q1_q13,
            "categories_held": categories_held,
            "treatment_categories": treatment_categories,
            "control_categories": control_categories,
        },
        "confirmatory_outcome": (
            "VALIDATED" if all_pass else "PARTIAL"
        ),
    }
