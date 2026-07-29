from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT
from .models import Candidate, RetrievalResult


Q11_KEY_PATH = REPO_ROOT / "experiments" / "study_008" / "q_facts_key.md"
STUDY_010_KEY_PATH = (
    REPO_ROOT / "experiments" / "study_010" / "q_facts_key_1000.md"
)

RAW_121_STORES = {
    "study_005_condition_c": REPO_ROOT
    / "experiments/study_005/runs/study_005_full_001/condition_c/study.db",
    "study_006_condition_c": REPO_ROOT
    / "experiments/study_006/runs/study_006_full_001/condition_c/study.db",
    "study_007_condition_c": REPO_ROOT
    / "experiments/study_007/runs/study_007_full_001/condition_c/study.db",
    "study_009_arm_s": REPO_ROOT
    / "experiments/study_009/runs/study_009_full_001/arm_s/study.db",
}
RAW_1000_STORES = {
    "study_010_arm_l": REPO_ROOT
    / "experiments/study_010/runs/study_010_full_001/arm_l/study.db",
    "study_010_arm_s": REPO_ROOT
    / "experiments/study_010/runs/study_010_full_001/arm_s/study.db",
}


@dataclass(frozen=True)
class AtomicFact:
    fact_id: str
    domain: str
    term: str
    source_turns: tuple[int, ...]


def load_q11_atomic_facts() -> list[AtomicFact]:
    lines = Q11_KEY_PATH.read_text(encoding="utf-8").splitlines()
    start = lines.index("## Study 007 correction's 17-item Q11 matrix")
    facts: list[AtomicFact] = []
    row_pattern = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([\d,\s]+)\s*\|$"
    )
    for line in lines[start + 1 :]:
        if line.startswith("**Span-granularity"):
            break
        match = row_pattern.match(line)
        if match is None:
            continue
        domain, term, turns = match.groups()
        if domain == "Domain":
            continue
        source_turns = tuple(
            int(value.strip()) for value in turns.split(",") if value.strip()
        )
        facts.append(
            AtomicFact(
                fact_id=f"q11_atomic_{len(facts) + 1:02d}",
                domain=domain,
                term=term,
                source_turns=source_turns,
            )
        )
    if len(facts) != 17:
        raise AssertionError(f"Expected 17 Q11 atomic facts, found {len(facts)}")
    return facts


def run_presence_inventory() -> dict:
    q11_facts = load_q11_atomic_facts()
    inventories_121 = {
        store_id: _inventory_atomic_store(path, q11_facts, cutoff=111)
        for store_id, path in RAW_121_STORES.items()
    }
    plant_rows = _load_study_010_rows()
    inventories_1000 = {
        store_id: _inventory_study_010_store(path, plant_rows, cutoff=986)
        for store_id, path in RAW_1000_STORES.items()
    }
    return {
        "test_id": "T1.1",
        "q11_key": str(Q11_KEY_PATH.relative_to(REPO_ROOT)),
        "q11_key_sha256": hashlib.sha256(Q11_KEY_PATH.read_bytes()).hexdigest(),
        "study_010_key": str(STUDY_010_KEY_PATH.relative_to(REPO_ROOT)),
        "study_010_key_sha256": hashlib.sha256(
            STUDY_010_KEY_PATH.read_bytes()
        ).hexdigest(),
        "lineage_121": inventories_121,
        "study_010": inventories_1000,
        "status": (
            "PASS"
            if all(row["all_present"] for row in inventories_121.values())
            and all(row["all_present"] for row in inventories_1000.values())
            else "FAIL"
        ),
    }


def evaluate_q11_reachability(result: RetrievalResult) -> dict:
    facts = load_q11_atomic_facts()
    matches: dict[str, str] = {}
    for fact in facts:
        for ranked in result.selected:
            candidate = ranked.candidate
            if candidate.turn_number not in fact.source_turns:
                continue
            if fact.term.casefold() in candidate.searchable_text.casefold():
                matches[fact.fact_id] = candidate.candidate_id
                break
    matched_domains = sorted(
        {
            fact.domain
            for fact in facts
            if fact.fact_id in matches
        }
    )
    return {
        "corpus_id": result.corpus_id,
        "method_id": result.method_id,
        "query_id": result.query.query_id,
        "matched_fact_count": len(matches),
        "required_fact_count": len(facts),
        "fact_recall": len(matches) / len(facts),
        "matched_fact_ids": sorted(matches),
        "fact_matches": matches,
        "matched_domains": matched_domains,
        "domain_count": len(matched_domains),
        "delivered_characters": result.delivered_characters,
        "selected_count": len(result.selected),
        "reaches_14_of_17": len(matches) >= 14,
    }


def _inventory_atomic_store(
    path: Path,
    facts: list[AtomicFact],
    *,
    cutoff: int,
) -> dict:
    episodes = _load_episode_text(path, cutoff)
    rows = []
    for fact in facts:
        matching_turns = [
            turn
            for turn in fact.source_turns
            if fact.term.casefold() in episodes.get(turn, "").casefold()
        ]
        rows.append(
            {
                "fact_id": fact.fact_id,
                "domain": fact.domain,
                "term": fact.term,
                "source_turns": list(fact.source_turns),
                "matching_turns": matching_turns,
                "present": bool(matching_turns),
            }
        )
    return {
        "database": str(path.relative_to(REPO_ROOT)),
        "database_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "eligible_turn_max": cutoff,
        "present_count": sum(row["present"] for row in rows),
        "required_count": len(rows),
        "all_present": all(row["present"] for row in rows),
        "facts": rows,
    }


def _load_study_010_rows() -> list[dict]:
    rows = []
    for line in STUDY_010_KEY_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7 or cells[0] == "Domain":
            continue
        domain, project, lead, primary, specification, threshold, turns = cells
        rows.append(
            {
                "domain": domain,
                "facts": {
                    "project": project,
                    "lead": lead,
                    "primary_value": primary,
                    "specification": specification,
                    "threshold": threshold,
                },
                "source_turns": [
                    int(value.strip())
                    for value in turns.split(",")
                    if value.strip()
                ],
            }
        )
    if len(rows) != 12:
        raise AssertionError(f"Expected 12 Study 010 key rows, found {len(rows)}")
    return rows


def _inventory_study_010_store(
    path: Path,
    plant_rows: list[dict],
    *,
    cutoff: int,
) -> dict:
    episodes = _load_episode_text(path, cutoff)
    facts = []
    for row in plant_rows:
        for field, term in row["facts"].items():
            matching_turns = [
                turn
                for turn in row["source_turns"]
                if term.casefold() in episodes.get(turn, "").casefold()
            ]
            facts.append(
                {
                    "fact_id": f"{row['domain']}:{field}",
                    "domain": row["domain"],
                    "field": field,
                    "term": term,
                    "source_turns": row["source_turns"],
                    "matching_turns": matching_turns,
                    "present": bool(matching_turns),
                }
            )
    return {
        "database": str(path.relative_to(REPO_ROOT)),
        "database_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "eligible_turn_max": cutoff,
        "present_count": sum(row["present"] for row in facts),
        "required_count": len(facts),
        "all_present": all(row["present"] for row in facts),
        "facts": facts,
    }


def _load_episode_text(path: Path, cutoff: int) -> dict[int, str]:
    connection = sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    try:
        rows = connection.execute(
            """
            SELECT turn_number, user_message, assistant_message
            FROM episodes
            WHERE turn_number BETWEEN 1 AND ?
            ORDER BY turn_number
            """,
            (cutoff,),
        ).fetchall()
    finally:
        connection.close()
    return {
        int(turn): f"{user or ''}\n{assistant or ''}"
        for turn, user, assistant in rows
    }
