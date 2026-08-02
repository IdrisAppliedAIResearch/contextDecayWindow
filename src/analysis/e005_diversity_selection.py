from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import sqlite3
import subprocess
import unicodedata
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

from src.analysis.e002_segmented_query import same_budget_baseline
from src.analysis.retrieval_bakeoff_tier6_121 import (
    ATOMIC_ITEMS,
    TARGETED_ITEMS,
)
from src.memory.context_matched_stm import render_stm_payload
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_mechanism_ledger.e005 import (
    assert_mechanism_path_allowed,
    build_selectors,
    eligible_candidates,
    relevance_vector,
    result_record,
    select,
    vector,
)
from src.retrieval_mechanism_ledger.seal import verify_mixed_source_seal


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
RUN_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
)
ANALYSIS_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "analysis_corrected_121"
)
CONTEXT_LOG = RUN_ROOT / "logs" / "context_match.jsonl"
TURN_LOG = RUN_ROOT / "logs" / "turns.jsonl"
DATABASE = RUN_ROOT / "study.db"
TARGETED_MEASUREMENT = ANALYSIS_ROOT / "targeted_fact_delivery.csv"
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e005.py"
PROTOCOL = COMPONENT_ROOT / "E005_diversity_selection_protocol.md"

DESIGN_COMMIT = "ebbf384e18f38c5af017464e4723a3c77d81e73b"
Q11_TURN = 120
BUDGET_CHARS = 32_000
A0_FACT_COUNT = 6
KILL_BAR = A0_FACT_COUNT + 1
BUG_SIGNAL_ABOVE = len(ATOMIC_ITEMS)
COSINE_POOL_SIZE = 100
TARGET_PROBE_TURNS = tuple(
    sorted({turn for turn, _needles in TARGETED_ITEMS.values()})
)
PRIMARY_POOL = "full_eligible_store"
SECONDARY_POOLS = ("cosine_top_100", "deployed_n_union_k")

ORACLE_EPISODES = (
    ("1dec9c9e-b948-4ef8-9eaa-aa889c083470", 90),
    ("5c4446e4-fc4b-40f8-8b27-04cb33c7be57", 112),
    ("dd904725-094b-4f94-a8fc-ca18668ad246", 113),
    ("4c611a05-6ad0-434a-a188-1cdb941acf58", 116),
    ("77a1d148-12da-4a70-874d-42e816497c9a", 118),
)
ORACLE_FACT_COUNT = 15
ORACLE_CHARS = 5_455

SWEEP_FIELDS = (
    "configuration_id",
    "arm",
    "pool",
    "lambda",
    "r",
    "k",
    "q11_fact_count",
    "q11_domain_count",
    "civil",
    "art",
    "monetary",
    "marine",
    "serialized_chars",
    "selected_episode_count",
    "facts_per_10k_chars",
    "prior_answer_fraction",
    "oracle_overlap",
    "optimality_ratio",
    "targeted_preserved",
    "targeted_required",
    "primary_gate",
    "no_regression_gate",
    "surrogate_gate",
)


class EmbeddingCache:
    def __init__(self, embedder: CarriedEmbedder) -> None:
        self.embedder = embedder
        self.values: dict[str, object] = {}

    def prime(self, texts: Iterable[str]) -> None:
        missing = sorted(set(texts) - self.values.keys())
        if not missing:
            return
        embedded = self.embedder.embed_many(missing)
        self.values.update(zip(missing, embedded, strict=True))

    def __call__(self, text: str):
        return self.values[text]


def run_e005(output_dir: Path, embedding_model: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite E005 output: {output_dir}")
    output_dir.mkdir(parents=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir()

    inputs = _input_paths()
    before = _hash_paths(inputs)
    seal = verify_mixed_source_seal(REPO_ROOT, RUN_ROOT)
    if seal["status"] != "PASS":
        raise RuntimeError("Corrected Tier 6 mechanism seal failed")
    leakage = leakage_audit()
    if leakage["status"] != "PASS":
        raise RuntimeError("E005 leakage audit failed")
    _write_json(output_dir / "leakage_audit.json", leakage)

    embedder = CarriedEmbedder(embedding_model)
    embedder.assert_carried_model()
    cache = EmbeddingCache(embedder)
    queries = load_queries()
    cache.prime(queries.values())
    candidates = load_candidates()
    by_id = {str(candidate["id"]): candidate for candidate in candidates}

    baseline = same_budget_baseline(queries, candidates)
    if baseline["fact_count"] != A0_FACT_COUNT:
        raise AssertionError(
            "A0 baseline did not reproduce its committed 6/17 fact count"
        )
    _write_json(output_dir / "a0_baseline.json", baseline)

    q11_query = queries[Q11_TURN]
    q11_embedding = cache(q11_query)
    pools = build_pools(candidates, q11_query, q11_embedding)

    q11_records: list[dict] = []
    q11_rerun: list[dict] = []
    for pool_name, pool in pools.items():
        for records in (q11_records, q11_rerun):
            records.extend(
                _select_records(
                    query_embedding=q11_embedding,
                    candidates=pool,
                    probe_turn=Q11_TURN,
                    pool=pool_name,
                )
            )
    q11_path = raw_dir / "q11_selection.jsonl"
    q11_rerun_path = raw_dir / "q11_selection_rerun.jsonl"
    _write_jsonl(q11_path, q11_records)
    _write_jsonl(q11_rerun_path, q11_rerun)

    q11_metrics = {
        (record["pool"], record["configuration_id"]): q11_availability(
            record,
            by_id,
        )
        for record in q11_records
    }
    for (pool_name, config_id), metric in q11_metrics.items():
        if metric["fact_count"] > BUG_SIGNAL_ABOVE:
            raise AssertionError(
                f"Fact count above {BUG_SIGNAL_ABOVE}/17 for "
                f"{pool_name}/{config_id} is a detection bug signal"
            )

    targeted_records: list[dict] = []
    targeted_rerun: list[dict] = []
    for turn in TARGET_PROBE_TURNS:
        probe_pool = eligible_candidates(candidates, probe_turn=turn)
        probe_embedding = cache(queries[turn])
        for records in (targeted_records, targeted_rerun):
            records.extend(
                _select_records(
                    query_embedding=probe_embedding,
                    candidates=probe_pool,
                    probe_turn=turn,
                    pool=PRIMARY_POOL,
                )
            )
    targeted_path = raw_dir / "targeted_selection.jsonl"
    targeted_rerun_path = raw_dir / "targeted_selection_rerun.jsonl"
    _write_jsonl(targeted_path, targeted_records)
    _write_jsonl(targeted_rerun_path, targeted_rerun)

    committed_targeted = committed_targeted_items()
    targeted_required = sum(
        row["committed_available"] for row in committed_targeted
    )
    targeted_metrics = targeted_availability(targeted_records, by_id)

    sweep_rows = _sweep_rows(
        q11_records,
        q11_metrics,
        targeted_metrics,
        targeted_required,
    )
    _write_csv(output_dir / "configuration_sweep.csv", sweep_rows, SWEEP_FIELDS)

    primary_rows = [
        row for row in sweep_rows if row["pool"] == PRIMARY_POOL
    ]
    best_fact_count = max(row["q11_fact_count"] for row in primary_rows)
    passing = [
        row
        for row in primary_rows
        if row["primary_gate"] and row["no_regression_gate"] and row["surrogate_gate"]
    ]
    if passing:
        outcome = "PROMOTION_ELIGIBLE"
        selection_pool = passing
    elif best_fact_count < KILL_BAR:
        outcome = "KILL"
        selection_pool = [
            row
            for row in primary_rows
            if row["q11_fact_count"] == best_fact_count
        ]
    else:
        outcome = "REJECT_NO_REGRESSION"
        selection_pool = [row for row in primary_rows if row["primary_gate"]]
    primary = sorted(selection_pool, key=_selection_key)[0]
    primary_key = (PRIMARY_POOL, str(primary["configuration_id"]))
    primary_record = next(
        record
        for record in q11_records
        if (record["pool"], record["configuration_id"]) == primary_key
    )

    _write_diagnostics(
        output_dir,
        q11_records=q11_records,
        q11_metrics=q11_metrics,
        sweep_rows=sweep_rows,
        committed_targeted=committed_targeted,
        targeted_metrics=targeted_metrics,
        primary_key=primary_key,
        candidates=by_id,
    )
    (output_dir / "primary_payload.txt").write_text(
        _payload_for_record(primary_record, by_id),
        encoding="utf-8",
        newline="\n",
    )
    _write_csv(
        output_dir / "q11_item_matrix.csv",
        q11_metrics[primary_key]["items"],
        ("domain", "item", "available"),
    )

    determinism = {
        "status": (
            "PASS"
            if _sha256(q11_path) == _sha256(q11_rerun_path)
            and _sha256(targeted_path) == _sha256(targeted_rerun_path)
            else "FAIL"
        ),
        "q11_sha256": _sha256(q11_path),
        "q11_rerun_sha256": _sha256(q11_rerun_path),
        "targeted_sha256": _sha256(targeted_path),
        "targeted_rerun_sha256": _sha256(targeted_rerun_path),
    }
    _write_json(output_dir / "determinism.json", determinism)
    if determinism["status"] != "PASS":
        raise AssertionError("E005 selection rerun was not byte-identical")

    after = _hash_paths(inputs)
    source_integrity = {
        "status": "PASS" if before == after else "FAIL",
        "before": before,
        "after": after,
    }
    _write_json(output_dir / "source_integrity.json", source_integrity)
    if source_integrity["status"] != "PASS":
        raise AssertionError("An E005 input changed during execution")

    result = {
        "entry": "E005",
        "status": "COMPLETE",
        "outcome": outcome,
        "inference_calls": 0,
        "design_commit": _git("rev-parse", DESIGN_COMMIT),
        "execution_commit": _git("rev-parse", "HEAD"),
        "embedding_model_sha256": _sha256(embedding_model),
        "expected_embedding_model_sha256": CARRIED_EMBEDDING_SHA256,
        "mechanism_seal_status": seal["status"],
        "leakage_audit_status": leakage["status"],
        "source_integrity_status": source_integrity["status"],
        "determinism_status": determinism["status"],
        "budget_chars": BUDGET_CHARS,
        "kill_bar": KILL_BAR,
        "a0_baseline": {
            "fact_count": baseline["fact_count"],
            "domain_count": baseline["domain_count"],
            "serialized_chars": baseline["serialized_chars"],
            "selected_episode_count": baseline["selected_episode_count"],
        },
        "primary_pool": PRIMARY_POOL,
        "pool_sizes": {name: len(pool) for name, pool in pools.items()},
        "configuration_count": len(primary_rows),
        "best_q11_fact_count": best_fact_count,
        "best_by_pool": {
            name: max(
                row["q11_fact_count"]
                for row in sweep_rows
                if row["pool"] == name
            )
            for name in pools
        },
        "best_by_arm": {
            arm: max(
                row["q11_fact_count"]
                for row in primary_rows
                if row["arm"] == arm
            )
            for arm in ("A1", "A2", "A3")
        },
        "primary_configuration": primary,
        "oracle": {
            "fact_count": ORACLE_FACT_COUNT,
            "serialized_chars": ORACLE_CHARS,
            "episode_ids": [episode for episode, _turn in ORACLE_EPISODES],
            "source": "AR-001, carried, never re-derived",
        },
        "secondary_reference_points": {
            "e002_best": 10,
            "rubric_threshold": 14,
            "ar_001_greedy": ORACLE_FACT_COUNT,
            "ar_001_exact_frontier_17": 7_592,
        },
        "targeted_required": targeted_required,
        "interpretation": (
            "Availability only; one breadth probe against one store. No "
            "answer-correctness claim, no general breadth claim, no live run."
        ),
    }
    _write_json(output_dir / "e005_results.json", result)
    (output_dir / "E005_report.md").write_text(
        _report(result, sweep_rows),
        encoding="utf-8",
        newline="\n",
    )
    _write_artifact_manifest(output_dir)
    return result


def build_pools(
    candidates: Sequence[dict],
    query: str,
    query_embedding,
) -> dict[str, tuple[dict, ...]]:
    del query
    full = eligible_candidates(candidates, probe_turn=Q11_TURN)
    relevance = relevance_vector(vector(query_embedding), full)
    ordered = sorted(
        range(len(full)),
        key=lambda index: (
            -float(relevance[index]),
            int(full[index]["turn_number"]),
            str(full[index]["id"]),
        ),
    )
    cosine_pool = tuple(full[index] for index in sorted(ordered[:COSINE_POOL_SIZE]))
    context = next(
        row
        for row in _read_jsonl(CONTEXT_LOG)
        if int(row["turn_number"]) == Q11_TURN
    )
    deployed_ids = {
        *(str(value) for value in context["n_candidate_ids"]),
        *(str(value) for value in context["k_candidate_ids"]),
    }
    deployed = tuple(
        candidate for candidate in full if str(candidate["id"]) in deployed_ids
    )
    return {
        PRIMARY_POOL: full,
        SECONDARY_POOLS[0]: cosine_pool,
        SECONDARY_POOLS[1]: deployed,
    }


def load_queries() -> dict[int, str]:
    rows = _read_jsonl(TURN_LOG)
    expected = {*TARGET_PROBE_TURNS, Q11_TURN}
    queries = {
        int(row["turn_number"]): str(row["user_message"])
        for row in rows
        if int(row["turn_number"]) in expected
    }
    if set(queries) != expected:
        raise AssertionError("Corrected run is missing an E005 probe query")
    return queries


def load_candidates() -> tuple[dict, ...]:
    connection = sqlite3.connect(
        f"file:{DATABASE.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                episodes.id,
                episodes.turn_number,
                episodes.user_message,
                episodes.assistant_message,
                episodes.embedding,
                COALESCE(episodes.ground_truth_domain, '') AS ground_truth_domain
            FROM episodes
            ORDER BY episodes.turn_number ASC, episodes.id ASC
            """
        ).fetchall()
    finally:
        connection.close()
    candidates = tuple(dict(row) for row in rows)
    if any(candidate["embedding"] is None for candidate in candidates):
        raise AssertionError("E005 raw store contains an episode without embedding")
    return candidates


def q11_availability(record: dict, candidates: dict[str, dict]) -> dict:
    return _q11_payload_availability(_payload_for_record(record, candidates))


def targeted_availability(
    records: Sequence[dict],
    candidates: dict[str, dict],
) -> dict[str, dict]:
    committed = committed_targeted_items()
    result: dict[str, dict] = {}
    for record in records:
        config_id = str(record["configuration_id"])
        turn = int(record["probe_turn"])
        payload = _normalize(_payload_for_record(record, candidates))
        entry = result.setdefault(
            config_id,
            {"availability": {}, "preserved_count": 0, "per_probe": {}},
        )
        probe = entry["per_probe"].setdefault(
            turn,
            {"preserved": 0, "required": 0},
        )
        for committed_row in committed:
            if int(committed_row["turn"]) != turn:
                continue
            present = _normalize(committed_row["item"]) in payload
            entry["availability"][targeted_key(committed_row)] = present
            if committed_row["committed_available"]:
                probe["required"] += 1
                if present:
                    entry["preserved_count"] += 1
                    probe["preserved"] += 1
    return result


def targeted_key(row: dict) -> tuple[str, int, str]:
    """Question-scoped identity.

    Q7 and Q10 both probe turn 118 and share two items. Keying on
    ``(turn, item)`` alone collapses those two rows while the denominator
    still counts them, which makes the no-regression gate unpassable by
    construction. The question qualifier keeps numerator and denominator on
    the same unit.
    """
    return (str(row["question"]), int(row["turn"]), str(row["item"]))


def committed_targeted_items() -> list[dict]:
    rows = _read_csv(TARGETED_MEASUREMENT)
    return [
        {
            "question": row["question"],
            "turn": int(row["turn"]),
            "item": row["item"],
            "committed_available": row["in_retrieval_payload"] == "True",
        }
        for row in rows
        if row["arm"] == "T6"
    ]


def leakage_audit() -> dict:
    source = MECHANISM_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden_tokens = (
        "q_facts_key",
        "rubric",
        "atomic_items",
        "targeted_items",
    )
    forbidden_imports = [
        name
        for name in imported
        if any(token in name.lower() for token in forbidden_tokens)
    ]
    literal_hits = sorted(
        {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and any(token in node.value.lower() for token in forbidden_tokens)
            and node.value not in forbidden_tokens
        }
    )
    planted_rejected = False
    try:
        assert_mechanism_path_allowed(
            REPO_ROOT / "experiments" / "study_009" / "q_facts_key.md"
        )
    except ValueError:
        planted_rejected = True
    return {
        "status": (
            "PASS"
            if not forbidden_imports and not literal_hits and planted_rejected
            else "FAIL"
        ),
        "mechanism_source": str(MECHANISM_SOURCE.relative_to(REPO_ROOT)),
        "imports": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "forbidden_literals": literal_hits,
        "planted_forbidden_path_rejected": planted_rejected,
    }


def _select_records(
    *,
    query_embedding,
    candidates: Sequence[dict],
    probe_turn: int,
    pool: str,
) -> list[dict]:
    embedding = vector(query_embedding)
    return [
        result_record(
            select(
                candidates=candidates,
                query_embedding=embedding,
                selector=selector,
                budget_chars=BUDGET_CHARS,
            ),
            configuration_id=config_id,
            probe_turn=probe_turn,
            pool=pool,
        )
        for config_id, selector in build_selectors(candidates)
    ]


def _sweep_rows(
    q11_records: Sequence[dict],
    q11_metrics: dict,
    targeted_metrics: dict,
    targeted_required: int,
) -> list[dict]:
    rows = []
    for record in q11_records:
        pool = str(record["pool"])
        config_id = str(record["configuration_id"])
        metric = q11_metrics[(pool, config_id)]
        parameters = record["parameters"]
        targeted = (
            targeted_metrics.get(config_id) if pool == PRIMARY_POOL else None
        )
        preserved = targeted["preserved_count"] if targeted else None
        chars = int(record["serialized_chars"])
        selected = list(record["selected_ids"])
        oracle_ids = {episode for episode, _turn in ORACLE_EPISODES}
        prior_turns = set(TARGET_PROBE_TURNS)
        prior = sum(
            1
            for turn in record["selected_source_turns"]
            if int(turn) in prior_turns
        )
        bound = record["optimality_bound"]
        objective = record["objective_value"]
        rows.append(
            {
                "configuration_id": config_id,
                "arm": record["arm"],
                "pool": pool,
                "lambda": parameters.get("lambda", ""),
                "r": parameters.get("r", ""),
                "k": (
                    int(parameters["k"]) if "k" in parameters else ""
                ),
                "q11_fact_count": metric["fact_count"],
                "q11_domain_count": metric["domain_count"],
                **metric["per_domain"],
                "serialized_chars": chars,
                "selected_episode_count": len(selected),
                "facts_per_10k_chars": round(
                    metric["fact_count"] * 10_000 / chars, 3
                ),
                "prior_answer_fraction": (
                    round(prior / len(selected), 3) if selected else ""
                ),
                "oracle_overlap": sum(
                    1 for value in selected if value in oracle_ids
                ),
                "optimality_ratio": (
                    round(objective / bound, 4)
                    if bound not in (None, 0) and objective is not None
                    else ""
                ),
                "targeted_preserved": preserved if preserved is not None else "",
                "targeted_required": targeted_required,
                "primary_gate": metric["fact_count"] >= KILL_BAR,
                "no_regression_gate": (
                    preserved == targeted_required
                    if preserved is not None
                    else False
                ),
                "surrogate_gate": metric["domain_count"] == 4,
            }
        )
    return rows


def _write_diagnostics(
    output_dir: Path,
    *,
    q11_records: Sequence[dict],
    q11_metrics: dict,
    sweep_rows: Sequence[dict],
    committed_targeted: Sequence[dict],
    targeted_metrics: dict,
    primary_key: tuple[str, str],
    candidates: dict[str, dict],
) -> None:
    _write_csv(
        output_dir / "per_domain_counts.csv",
        [
            {
                "configuration_id": row["configuration_id"],
                "arm": row["arm"],
                "pool": row["pool"],
                "civil": row["civil"],
                "art": row["art"],
                "monetary": row["monetary"],
                "marine": row["marine"],
                "q11_fact_count": row["q11_fact_count"],
                "q11_domain_count": row["q11_domain_count"],
            }
            for row in sweep_rows
        ],
        (
            "configuration_id",
            "arm",
            "pool",
            "civil",
            "art",
            "monetary",
            "marine",
            "q11_fact_count",
            "q11_domain_count",
        ),
    )

    prefix_rows = []
    for record in q11_records:
        if record["pool"] != PRIMARY_POOL:
            continue
        selected: list[str] = []
        for step in record["steps"]:
            selected.append(str(step["candidate_id"]))
            payload = render_stm_payload(
                [],
                [candidates[value] for value in selected],
            )
            measurement = _q11_payload_availability(payload)
            prefix_rows.append(
                {
                    "configuration_id": record["configuration_id"],
                    "arm": record["arm"],
                    "step": step["step"],
                    "candidate_id": step["candidate_id"],
                    "source_turn": step["source_turn"],
                    "additive_chars": step["additive_chars"],
                    "cumulative_chars": step["cumulative_chars"],
                    "scaled_gain": step["scaled_gain"],
                    "facts_available": measurement["fact_count"],
                    "domains_available": measurement["domain_count"],
                }
            )
    _write_csv(
        output_dir / "selection_prefix.csv",
        prefix_rows,
        (
            "configuration_id",
            "arm",
            "step",
            "candidate_id",
            "source_turn",
            "additive_chars",
            "cumulative_chars",
            "scaled_gain",
            "facts_available",
            "domains_available",
        ),
    )

    oracle_rows = []
    for record in q11_records:
        selected = set(record["selected_ids"])
        oracle_rows.append(
            {
                "configuration_id": record["configuration_id"],
                "arm": record["arm"],
                "pool": record["pool"],
                **{
                    f"turn_{turn}": episode in selected
                    for episode, turn in ORACLE_EPISODES
                },
                "found": sum(
                    1 for episode, _turn in ORACLE_EPISODES if episode in selected
                ),
                "missed": sum(
                    1
                    for episode, _turn in ORACLE_EPISODES
                    if episode not in selected
                ),
            }
        )
    _write_csv(
        output_dir / "oracle_overlap.csv",
        oracle_rows,
        (
            "configuration_id",
            "arm",
            "pool",
            *(f"turn_{turn}" for _episode, turn in ORACLE_EPISODES),
            "found",
            "missed",
        ),
    )

    _write_csv(
        output_dir / "prior_answer_fraction.csv",
        [
            {
                "configuration_id": row["configuration_id"],
                "arm": row["arm"],
                "pool": row["pool"],
                "selected_episode_count": row["selected_episode_count"],
                "prior_answer_fraction": row["prior_answer_fraction"],
            }
            for row in sweep_rows
        ],
        (
            "configuration_id",
            "arm",
            "pool",
            "selected_episode_count",
            "prior_answer_fraction",
        ),
    )

    _write_csv(
        output_dir / "optimality_bounds.csv",
        [
            {
                "configuration_id": record["configuration_id"],
                "arm": record["arm"],
                "pool": record["pool"],
                "objective_value": record["objective_value"],
                "optimality_bound": record["optimality_bound"],
                "optimality_ratio": (
                    record["objective_value"] / record["optimality_bound"]
                    if record["optimality_bound"]
                    else ""
                ),
                "computable": record["optimality_bound"] is not None,
            }
            for record in q11_records
        ],
        (
            "configuration_id",
            "arm",
            "pool",
            "objective_value",
            "optimality_bound",
            "optimality_ratio",
            "computable",
        ),
    )

    _write_csv(
        output_dir / "pool_secondaries.csv",
        [
            {
                "configuration_id": row["configuration_id"],
                "arm": row["arm"],
                "pool": row["pool"],
                "q11_fact_count": row["q11_fact_count"],
                "q11_domain_count": row["q11_domain_count"],
                "serialized_chars": row["serialized_chars"],
                "oracle_overlap": row["oracle_overlap"],
            }
            for row in sweep_rows
        ],
        (
            "configuration_id",
            "arm",
            "pool",
            "q11_fact_count",
            "q11_domain_count",
            "serialized_chars",
            "oracle_overlap",
        ),
    )

    targeted_rows = []
    for config_id, metrics in sorted(targeted_metrics.items()):
        for row in committed_targeted:
            present = metrics["availability"][targeted_key(row)]
            targeted_rows.append(
                {
                    "configuration_id": config_id,
                    "question": row["question"],
                    "turn": row["turn"],
                    "item": row["item"],
                    "committed_available": row["committed_available"],
                    "candidate_available": present,
                    "preserved": not row["committed_available"] or present,
                }
            )
    _write_csv(
        output_dir / "targeted_no_regression.csv",
        targeted_rows,
        (
            "configuration_id",
            "question",
            "turn",
            "item",
            "committed_available",
            "candidate_available",
            "preserved",
        ),
    )
    del q11_metrics, primary_key


def _q11_payload_availability(payload: str) -> dict:
    normalized = _normalize(payload)
    items = [
        {
            "domain": domain,
            "item": item,
            "available": needle in normalized,
        }
        for domain, item, needle, _plant_turns in ATOMIC_ITEMS
    ]
    available = [row for row in items if row["available"]]
    per_domain = {domain: 0 for domain, _i, _n, _t in ATOMIC_ITEMS}
    for row in available:
        per_domain[row["domain"]] += 1
    return {
        "fact_count": len(available),
        "domain_count": len({row["domain"] for row in available}),
        "per_domain": per_domain,
        "items": items,
    }


def _payload_for_record(record: dict, candidates: dict[str, dict]) -> str:
    payload = render_stm_payload(
        [],
        [candidates[str(value)] for value in record["selected_ids"]],
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if digest != record["payload_sha256"]:
        raise AssertionError("Raw E005 identity record did not reproduce its payload")
    if len(payload) != int(record["serialized_chars"]):
        raise AssertionError("Raw E005 character count did not reproduce")
    return payload


def _selection_key(row: dict) -> tuple:
    targeted = row["targeted_preserved"]
    return (
        -int(row["q11_fact_count"]),
        -int(row["q11_domain_count"]),
        -int(targeted) if targeted != "" else 0,
        int(row["serialized_chars"]),
        int(row["selected_episode_count"]),
        str(row["arm"]),
        float(row["lambda"]) if row["lambda"] != "" else 0.0,
        float(row["r"]) if row["r"] != "" else 0.0,
        int(row["k"]) if row["k"] != "" else 0,
    )


def _report(result: dict, sweep_rows: Sequence[dict]) -> str:
    primary = result["primary_configuration"]
    baseline = result["a0_baseline"]
    by_arm = result["best_by_arm"]
    by_pool = result["best_by_pool"]
    lines = [
        "# E005 Diversity-Aware Selection",
        "",
        f"**Design commit:** `{result['design_commit']}`  ",
        f"**Execution commit:** `{result['execution_commit']}`  ",
        f"**Outcome:** **{result['outcome']}**",
        "",
        "## Result",
        "",
        (
            f"The committed A0 baseline delivers **{baseline['fact_count']}/17** "
            f"items across {baseline['domain_count']}/4 domains, spending "
            f"{baseline['serialized_chars']:,} of {result['budget_chars']:,} "
            f"characters on {baseline['selected_episode_count']} episodes. The "
            f"kill bar is {result['kill_bar']}/17."
        ),
        "",
        (
            f"The best set-level selector delivered "
            f"**{primary['q11_fact_count']}/17** items across "
            f"**{primary['q11_domain_count']}/4** domains "
            f"(`{primary['configuration_id']}`), selecting "
            f"{primary['selected_episode_count']} episodes for "
            f"{primary['serialized_chars']:,} characters at "
            f"{primary['facts_per_10k_chars']} facts per 10,000 characters. "
            f"It recovered {primary['oracle_overlap']}/5 of the carried oracle "
            f"episodes."
        ),
        "",
        "### Best Q11 availability by arm, primary pool",
        "",
        "| Arm | Selector | Best Q11 |",
        "|---|---|---:|",
        f"| A0 | committed baseline | {baseline['fact_count']}/17 |",
        f"| A1 | MMR | {by_arm['A1']}/17 |",
        f"| A2 | facility location | {by_arm['A2']}/17 |",
        f"| A3 | relevance plus cluster diversity | {by_arm['A3']}/17 |",
        (
            f"| A4 | oracle, carried from AR-001 | "
            f"{result['oracle']['fact_count']}/17 |"
        ),
        "",
        "### Candidate pool, registered primary against secondaries",
        "",
        "| Pool | Episodes | Best Q11 |",
        "|---|---:|---:|",
    ]
    for name, size in result["pool_sizes"].items():
        lines.append(f"| `{name}` | {size} | {by_pool[name]}/17 |")
    lines.extend(
        [
            "",
            (
                f"Targeted no-regression: the primary configuration preserved "
                f"**{primary['targeted_preserved']}/{result['targeted_required']}** "
                f"committed-available items. Per-probe detail is in "
                f"`targeted_no_regression.csv`."
            ),
            "",
            "## Integrity",
            "",
            (
                f"Mechanism seal: **{result['mechanism_seal_status']}**. Leakage "
                f"audit: **{result['leakage_audit_status']}**. Source "
                f"integrity: **{result['source_integrity_status']}**. "
                f"Byte-identical raw rerun: **{result['determinism_status']}**. "
                f"Inference calls: {result['inference_calls']}. Configurations "
                f"swept per pool: {result['configuration_count']}."
            ),
            "",
            "## Interpretation Boundary",
            "",
            (
                "Availability only. Every arm is evaluated on one breadth probe, "
                "Q11, against one store, so no arm may claim general breadth "
                "capability from this result. A4 is AR-001's committed greedy "
                "set cover carried in as a reference point; it was not "
                "re-derived and is never deployable. This result makes no "
                "answer-correctness claim and authorizes no inference run."
            ),
            "",
        ]
    )
    del sweep_rows
    return "\n".join(lines)


def _input_paths() -> list[Path]:
    return [
        DATABASE,
        CONTEXT_LOG,
        TURN_LOG,
        TARGETED_MEASUREMENT,
        MECHANISM_SOURCE,
        REPO_ROOT / "src" / "memory" / "context_builder.py",
        REPO_ROOT / "src" / "memory" / "context_matched_stm.py",
        PROTOCOL,
    ]


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).lower()


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _hash_paths(paths: Iterable[Path]) -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)): _sha256(path)
        for path in sorted(paths)
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_encode) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _encode(value: object) -> object:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Unserializable value: {type(value)!r}")


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(
                row,
                sort_keys=True,
                separators=(",", ":"),
                default=_encode,
            )
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _write_csv(
    path: Path,
    rows: Iterable[dict],
    fields: Sequence[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_artifact_manifest(output_dir: Path) -> None:
    paths = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    _write_json(
        output_dir / "artifact_manifest.json",
        {
            "status": "COMPLETE",
            "artifacts": {
                path.relative_to(output_dir).as_posix(): _sha256(path)
                for path in paths
            },
        },
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the prospective E005 offline selection test."
    )
    parser.add_argument("--embedding-model", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run_e005(args.output_dir, args.embedding_model.resolve())
    print(json.dumps(result, indent=2, sort_keys=True, default=_encode))


if __name__ == "__main__":
    main()
