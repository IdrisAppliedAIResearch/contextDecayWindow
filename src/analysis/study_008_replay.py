"""Fact-aware replay helpers for Study 008's pre-run gates."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from src.analysis.study_007_replay import (
    PROBE_TURNS,
    hash_tree,
    probe_queries,
    score,
    stm_block_ids,
)
from src.memory.arbitration import arbitrate_budgeted
from src.memory.distilled_ltm_store import get_distilled_retrieval_rows
from src.memory.retrieval_budget import BudgetSelection, topic_key


REPO = Path(__file__).resolve().parents[2]
PLANT_KEY = REPO / "experiments/study_008/q_facts_key.md"
STUDY_007_RUN = REPO / (
    "experiments/study_007/runs/study_007_full_001/condition_c"
)

DOMAIN_BY_HEADING = {
    "Civil engineering": "civil",
    "Renaissance art": "art",
    "Monetary policy": "monetary",
    "Marine biology": "marine",
}


@dataclass(frozen=True)
class FactRow:
    domain: str
    fact_id: str
    terms: tuple[str, ...]
    source_turns: tuple[int, ...]


@dataclass
class FactAwareProbe:
    turn: int
    selection: BudgetSelection
    matched_facts: dict[str, list[str]] = field(default_factory=dict)
    source_turns: list[int] = field(default_factory=list)
    containment_drops: int = 0

    @property
    def domains_covered(self) -> list[str]:
        return sorted(
            domain for domain, facts in self.matched_facts.items() if facts
        )

    @property
    def four_domain(self) -> bool:
        return len(self.domains_covered) == 4


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fact_rows(path: Path = PLANT_KEY) -> list[FactRow]:
    row_pattern = re.compile(
        r"^\|\s*((?:civil|art|monetary|marine)_[a-z_]+)\s*"
        r"\|\s*(.+?)\s*\|\s*([\d,\s]+)\s*\|"
    )
    domain = None
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            domain = DOMAIN_BY_HEADING.get(line[3:].strip())
            continue
        if domain is None:
            continue
        match = row_pattern.match(line)
        if not match:
            continue
        fact_id, terms_cell, turns_cell = match.groups()
        rows.append(
            FactRow(
                domain=domain,
                fact_id=fact_id,
                terms=tuple(
                    term.strip()
                    for term in terms_cell.split(";")
                    if term.strip()
                ),
                source_turns=tuple(
                    int(turn.strip())
                    for turn in turns_cell.split(",")
                    if turn.strip()
                ),
            )
        )
    unique = {row.fact_id: row for row in rows}
    return list(unique.values())


def rendered_episode_text(selected: list[dict]) -> str:
    return "\n".join(
        f"{candidate.get('user_message') or ''}\n"
        f"{candidate.get('assistant_message') or ''}"
        for candidate in selected
    )


def match_facts(text: str, fact_rows: list[FactRow]) -> dict[str, list[str]]:
    lowered = text.casefold()
    matched = {domain: [] for domain in DOMAIN_BY_HEADING.values()}
    for row in fact_rows:
        if all(term.casefold() in lowered for term in row.terms):
            matched[row.domain].append(row.fact_id)
    return matched


def load_candidates(run_dir: Path = STUDY_007_RUN) -> list[dict]:
    db_path = run_dir / "study.db"
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        return get_distilled_retrieval_rows(conn)
    finally:
        conn.close()


def replay_episode_probe(
    turn: int,
    scored_candidates: list[dict],
    *,
    b_ltm: int,
    k_min: int,
    fact_rows: list[FactRow],
    run_dir: Path = STUDY_007_RUN,
) -> FactAwareProbe:
    arbitration = arbitrate_budgeted(
        stm_candidates=[],
        ltm_candidates=scored_candidates,
        stm_block_episode_ids=stm_block_ids(turn, run_dir),
        ltm_budget=b_ltm,
        ltm_k_min=k_min,
    )
    selected = arbitration.budget.selected
    return FactAwareProbe(
        turn=turn,
        selection=arbitration.budget,
        matched_facts=match_facts(rendered_episode_text(selected), fact_rows),
        source_turns=sorted(
            {int(candidate["turn_number"]) for candidate in selected}
        ),
        containment_drops=arbitration.containment_drops,
    )


def scored_probes(
    candidates: list[dict],
) -> dict[int, list[dict]]:
    queries = probe_queries(
        str(REPO / "experiments/study_005/script.json")
    )
    return {
        turn: score(candidates, queries[turn])
        for turn in PROBE_TURNS
    }
