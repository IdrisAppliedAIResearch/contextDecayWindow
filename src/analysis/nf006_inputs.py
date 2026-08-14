"""Hash-locked, outcome-blind inputs for NF-006."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = (
    REPO_ROOT
    / "experiments/surveys/retrieval_bakeoff/tier6/runs/"
    "tier6_live_121_corrected_001/context_matched_stm"
)
DATABASE = RUN_ROOT / "study.db"
TURN_LOG = RUN_ROOT / "logs/turns.jsonl"
PROBE_TURNS = (112, 113, 115, 116, 117, 118, 119, 120)
Q11_TURN = 120
E005_Q11 = (
    REPO_ROOT
    / "experiments/components/retrieval_mechanism_ledger/artifacts/"
    "e005/raw/q11_selection.jsonl"
)
E005_TARGETED = (
    REPO_ROOT
    / "experiments/components/retrieval_mechanism_ledger/artifacts/"
    "e005/raw/targeted_selection.jsonl"
)
E005_SWEEP = (
    REPO_ROOT
    / "experiments/components/retrieval_mechanism_ledger/artifacts/"
    "e005/configuration_sweep.csv"
)
IC001_ARM = (
    REPO_ROOT
    / "experiments/internal/packing_priority/runs/ic001/"
    "b1_k_first/b1_arm.json"
)
IC001_ITEMS = IC001_ARM.with_name("targeted_item_matrix.csv")
IC001_PROBES = IC001_ARM.with_name("targeted_per_probe.csv")
PRIMARY_CONFIGURATION = "A3_l0.1_r0.0_k16"
PRIMARY_POOL = "full_eligible_store"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> tuple[dict, ...]:
    return tuple(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def load_probe_texts() -> dict[int, str]:
    rows = read_jsonl(TURN_LOG)
    queries = {
        int(row["turn_number"]): str(row["user_message"])
        for row in rows
        if int(row["turn_number"]) in PROBE_TURNS
    }
    if tuple(sorted(queries)) != PROBE_TURNS:
        raise AssertionError("Corrected turn log has a different probe turn list")
    if len(set(queries.values())) != len(PROBE_TURNS):
        raise AssertionError("Probe texts are not unique by registered prefix")
    return queries


def load_parents() -> tuple[dict, ...]:
    connection = sqlite3.connect(
        f"file:{DATABASE.as_posix()}?mode=ro&immutable=1", uri=True
    )
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message, embedding,
                   COALESCE(ground_truth_domain, '') AS ground_truth_domain
            FROM episodes
            ORDER BY turn_number ASC, id ASC
            """
        ).fetchall()
    finally:
        connection.close()
    parents = tuple(dict(row) for row in rows)
    if any(row["embedding"] is None for row in parents):
        raise AssertionError("A parent episode has no stored vector")
    return parents


def eligible_parents(parents: tuple[dict, ...], turn: int) -> tuple[dict, ...]:
    result = tuple(row for row in parents if int(row["turn_number"]) < turn)
    if any(int(row["turn_number"]) >= turn for row in result):
        raise AssertionError("Temporal eligibility admitted a future parent")
    return result


def committed_primary_records(path: Path) -> dict[int, dict]:
    records = {
        int(row["probe_turn"]): row
        for row in read_jsonl(path)
        if row["configuration_id"] == PRIMARY_CONFIGURATION
        and row["pool"] == PRIMARY_POOL
    }
    return records
