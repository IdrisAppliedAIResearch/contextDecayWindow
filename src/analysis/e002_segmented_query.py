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

from src.analysis.retrieval_bakeoff_tier6_121 import (
    ATOMIC_ITEMS,
    TARGETED_ITEMS,
)
from src.memory.context_matched_stm import (
    pack_stm_payload,
    render_stm_payload,
)
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_mechanism_ledger.e002 import (
    assert_mechanism_path_allowed,
    configuration_id,
    eligible_candidates,
    exhaustive_configurations,
    result_record,
    retrieve_segmented,
    segment_query,
)


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
BREADTH_MEASUREMENT = ANALYSIS_ROOT / "breadth_fact_delivery.csv"
TARGETED_MEASUREMENT = ANALYSIS_ROOT / "targeted_fact_delivery.csv"
MECHANISM_SOURCE = (
    REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e002.py"
)
PROTOCOL = COMPONENT_ROOT / "E002_segmented_query_protocol.md"

Q11_TURN = 120
BUDGET_CHARS = 32_000
HISTORICAL_BUDGET_CHARS = 60_595
HISTORICAL_HURDLE = 13
INTEREST_THRESHOLD = 14
TARGET_PROBE_TURNS = tuple(
    sorted({turn for turn, _needles in TARGETED_ITEMS.values()})
)
SWEEP_FIELDS = (
    "configuration_id",
    "segment_width",
    "boundary_offset",
    "per_segment_budget",
    "q11_fact_count",
    "q11_domain_count",
    "serialized_chars",
    "selected_episode_count",
    "targeted_preserved",
    "targeted_required",
    "q4_item_count",
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


def run_e002(output_dir: Path, embedding_model: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite E002 output: {output_dir}")
    output_dir.mkdir(parents=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir()

    inputs = _input_paths()
    before = _hash_paths(inputs)
    seal = verify_e002_source_seal()
    if seal["status"] != "PASS":
        raise RuntimeError("Corrected Tier 6 mechanism seal failed")
    leakage = leakage_audit()
    if leakage["status"] != "PASS":
        raise RuntimeError("E002 leakage audit failed")

    embedder = CarriedEmbedder(embedding_model)
    embedder.assert_carried_model()
    cache = EmbeddingCache(embedder)
    queries = load_queries()
    candidates = load_candidates()
    by_id = {str(candidate["id"]): candidate for candidate in candidates}

    baseline = same_budget_baseline(queries, candidates)
    _write_json(output_dir / "same_budget_baseline.json", baseline)
    _write_json(output_dir / "leakage_audit.json", leakage)

    q11_query = queries[Q11_TURN]
    configurations = exhaustive_configurations(q11_query)
    cache.prime(
        segment.text
        for width, offset, _per_segment_budget in configurations
        for segment in segment_query(
            q11_query,
            segment_width=width,
            boundary_offset=offset,
        )
    )
    q11_eligible = eligible_candidates(candidates, probe_turn=Q11_TURN)
    q11_records = _retrieve_records(
        query=q11_query,
        probe_turn=Q11_TURN,
        candidates=q11_eligible,
        configurations=configurations,
        embed=cache,
    )
    q11_path = raw_dir / "q11_retrieval.jsonl"
    q11_rerun_path = raw_dir / "q11_retrieval_rerun.jsonl"
    _write_jsonl(q11_path, q11_records)
    _write_jsonl(
        q11_rerun_path,
        _retrieve_records(
            query=q11_query,
            probe_turn=Q11_TURN,
            candidates=q11_eligible,
            configurations=configurations,
            embed=cache,
        ),
    )

    q11_metrics = {
        record["configuration_id"]: q11_availability(record, by_id)
        for record in q11_records
    }
    best_q11_count = max(
        metric["fact_count"] for metric in q11_metrics.values()
    )
    target_config_ids = {
        config_id
        for config_id, metric in q11_metrics.items()
        if metric["fact_count"] >= INTEREST_THRESHOLD
    }
    if not target_config_ids:
        target_config_ids = {
            config_id
            for config_id, metric in q11_metrics.items()
            if metric["fact_count"] == best_q11_count
        }
    target_configurations = [
        configuration
        for configuration in configurations
        if configuration_id(*configuration) in target_config_ids
    ]

    cache.prime(
        segment.text
        for turn in TARGET_PROBE_TURNS
        for width, offset, _per_segment_budget in target_configurations
        for segment in segment_query(
            queries[turn],
            segment_width=width,
            boundary_offset=offset,
        )
    )
    targeted_records = []
    targeted_rerun = []
    for turn in TARGET_PROBE_TURNS:
        probe_candidates = eligible_candidates(candidates, probe_turn=turn)
        targeted_records.extend(
            _retrieve_records(
                query=queries[turn],
                probe_turn=turn,
                candidates=probe_candidates,
                configurations=target_configurations,
                embed=cache,
            )
        )
        targeted_rerun.extend(
            _retrieve_records(
                query=queries[turn],
                probe_turn=turn,
                candidates=probe_candidates,
                configurations=target_configurations,
                embed=cache,
            )
        )
    targeted_path = raw_dir / "targeted_retrieval.jsonl"
    targeted_rerun_path = raw_dir / "targeted_retrieval_rerun.jsonl"
    _write_jsonl(targeted_path, targeted_records)
    _write_jsonl(targeted_rerun_path, targeted_rerun)

    targeted_metrics = targeted_availability(targeted_records, by_id)
    committed_targeted = committed_targeted_items()
    targeted_required = sum(
        row["committed_available"] for row in committed_targeted
    )
    sweep_rows = []
    q11_by_config = {
        record["configuration_id"]: record for record in q11_records
    }
    for width, offset, per_segment_budget in configurations:
        config_id = configuration_id(width, offset, per_segment_budget)
        q11 = q11_metrics[config_id]
        targeted = targeted_metrics.get(config_id)
        preserved = (
            targeted["preserved_count"] if targeted is not None else None
        )
        q4_count = targeted["q4_item_count"] if targeted is not None else None
        primary_gate = q11["fact_count"] >= INTEREST_THRESHOLD
        no_regression = (
            preserved == targeted_required if preserved is not None else False
        )
        surrogate = q11["domain_count"] == 4
        sweep_rows.append(
            {
                "configuration_id": config_id,
                "segment_width": width,
                "boundary_offset": offset,
                "per_segment_budget": per_segment_budget,
                "q11_fact_count": q11["fact_count"],
                "q11_domain_count": q11["domain_count"],
                "serialized_chars": q11_by_config[config_id][
                    "serialized_chars"
                ],
                "selected_episode_count": len(
                    q11_by_config[config_id]["selected_ids"]
                ),
                "targeted_preserved": (
                    preserved if preserved is not None else ""
                ),
                "targeted_required": targeted_required,
                "q4_item_count": q4_count if q4_count is not None else "",
                "primary_gate": primary_gate,
                "no_regression_gate": no_regression,
                "surrogate_gate": surrogate,
            }
        )

    primary_candidates = [
        row
        for row in sweep_rows
        if row["primary_gate"]
        and row["no_regression_gate"]
        and row["surrogate_gate"]
    ]
    if primary_candidates:
        outcome = "PROMOTION_ELIGIBLE"
        selection_pool = primary_candidates
    elif best_q11_count < INTEREST_THRESHOLD:
        outcome = "KILL"
        selection_pool = [
            row
            for row in sweep_rows
            if row["q11_fact_count"] == best_q11_count
        ]
    else:
        outcome = "REJECT_NO_REGRESSION"
        selection_pool = [
            row for row in sweep_rows if row["primary_gate"]
        ]
    primary = sorted(selection_pool, key=_selection_key)[0]
    primary_id = str(primary["configuration_id"])
    primary_record = q11_by_config[primary_id]
    primary_q11 = q11_metrics[primary_id]
    primary_targeted = targeted_metrics[primary_id]

    _write_csv(output_dir / "configuration_sweep.csv", sweep_rows, SWEEP_FIELDS)
    _write_primary_selection(
        output_dir / "primary_segment_selection.csv",
        primary_record,
    )
    _write_q11_matrix(
        output_dir / "q11_item_matrix.csv",
        primary_q11["items"],
    )
    _write_targeted_matrix(
        output_dir / "targeted_no_regression.csv",
        committed_targeted,
        primary_targeted["availability"],
    )
    primary_payload = _payload_for_record(primary_record, by_id)
    (output_dir / "primary_payload.txt").write_text(
        primary_payload,
        encoding="utf-8",
        newline="\n",
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
        raise AssertionError("E002 retrieval rerun was not byte-identical")

    after = _hash_paths(inputs)
    source_integrity = {
        "status": "PASS" if before == after else "FAIL",
        "before": before,
        "after": after,
    }
    _write_json(output_dir / "source_integrity.json", source_integrity)
    if source_integrity["status"] != "PASS":
        raise AssertionError("An E002 input changed during execution")

    result = {
        "entry": "E002",
        "status": "COMPLETE",
        "outcome": outcome,
        "inference_calls": 0,
        "design_commit": _git("rev-parse", "b42f4f81"),
        "execution_commit": _git("rev-parse", "HEAD"),
        "embedding_model_sha256": _sha256(embedding_model),
        "expected_embedding_model_sha256": CARRIED_EMBEDDING_SHA256,
        "mechanism_seal_status": seal["status"],
        "leakage_audit_status": leakage["status"],
        "source_integrity_status": source_integrity["status"],
        "determinism_status": determinism["status"],
        "historical_hurdle": {
            "budget_chars": HISTORICAL_BUDGET_CHARS,
            "fact_count": HISTORICAL_HURDLE,
        },
        "same_budget_baseline": baseline,
        "configuration_count": len(configurations),
        "targeted_configuration_count": len(target_configurations),
        "best_q11_fact_count": best_q11_count,
        "primary_configuration": primary,
        "primary_q11_items": primary_q11["items"],
        "primary_targeted_preserved": primary_targeted["preserved_count"],
        "targeted_required": targeted_required,
        "promotion_blocked_on_literature_scan": outcome == "PROMOTION_ELIGIBLE",
        "interpretation": (
            "Availability only; no answer-correctness or live-run claim."
        ),
    }
    _write_json(output_dir / "e002_results.json", result)
    (output_dir / "E002_report.md").write_text(
        _report(result),
        encoding="utf-8",
        newline="\n",
    )
    _write_artifact_manifest(output_dir)
    return result


def load_queries() -> dict[int, str]:
    rows = _read_jsonl(TURN_LOG)
    queries = {
        int(row["turn_number"]): str(row["user_message"])
        for row in rows
        if int(row["turn_number"]) in {*TARGET_PROBE_TURNS, Q11_TURN}
    }
    expected = {*TARGET_PROBE_TURNS, Q11_TURN}
    if set(queries) != expected:
        raise AssertionError("Corrected run is missing an E002 probe query")
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
        raise AssertionError("E002 raw store contains an episode without embedding")
    return candidates


def same_budget_baseline(
    queries: dict[int, str],
    candidates: Sequence[dict],
) -> dict:
    del queries
    context = next(
        row for row in _read_jsonl(CONTEXT_LOG)
        if int(row["turn_number"]) == Q11_TURN
    )
    by_id = {str(candidate["id"]): candidate for candidate in candidates}
    n_candidates = [by_id[str(value)] for value in context["n_candidate_ids"]]
    n_ids = {str(value) for value in context["n_candidate_ids"]}
    k_candidates = [
        by_id[str(value)]
        for value in context["k_candidate_ids"]
        if str(value) not in n_ids
    ]
    packed = pack_stm_payload(n_candidates, k_candidates, BUDGET_CHARS)
    measurement = _q11_payload_availability(packed.payload)
    return {
        "budget_chars": BUDGET_CHARS,
        "serialized_chars": packed.serialized_chars,
        "selected_episode_count": len(packed.selected_ids),
        "selected_ids": list(packed.selected_ids),
        "selected_source_turns": [
            int(candidate["turn_number"])
            for candidate in (*packed.recent_episodes, *packed.stm_episodes)
        ],
        "fact_count": measurement["fact_count"],
        "domain_count": measurement["domain_count"],
        "items": measurement["items"],
        "payload_sha256": hashlib.sha256(
            packed.payload.encode("utf-8")
        ).hexdigest(),
        "interpretation": (
            "Unchanged corrected-run candidate order under compact exact-cost "
            "packing at the enforced budget."
        ),
    }


def q11_availability(record: dict, candidates: dict[str, dict]) -> dict:
    return _q11_payload_availability(_payload_for_record(record, candidates))


def targeted_availability(
    records: Sequence[dict],
    candidates: dict[str, dict],
) -> dict[str, dict]:
    committed = committed_targeted_items()
    by_key = {
        (int(row["turn"]), str(row["item"])): row for row in committed
    }
    result: dict[str, dict] = {}
    for record in records:
        config_id = str(record["configuration_id"])
        turn = int(record["probe_turn"])
        payload = _normalize(_payload_for_record(record, candidates))
        availability = result.setdefault(
            config_id,
            {
                "availability": {},
                "preserved_count": 0,
                "q4_item_count": 0,
            },
        )
        for key, committed_row in by_key.items():
            item_turn, item = key
            if item_turn != turn:
                continue
            present = _normalize(item) in payload
            availability["availability"][key] = present
            if committed_row["committed_available"] and present:
                availability["preserved_count"] += 1
            if turn == 115 and present:
                availability["q4_item_count"] += 1
    return result


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
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden_imports = [
        name
        for name in imported
        if any(
            part in name.lower()
            for part in (
                "q_facts_key",
                "rubric",
                "atomic_items",
                "targeted_items",
            )
        )
    ]
    planted_rejected = False
    try:
        assert_mechanism_path_allowed(
            REPO_ROOT / "experiments" / "study_009" / "q_facts_key.md"
        )
    except ValueError:
        planted_rejected = True
    return {
        "status": (
            "PASS" if not forbidden_imports and planted_rejected else "FAIL"
        ),
        "mechanism_source": str(MECHANISM_SOURCE.relative_to(REPO_ROOT)),
        "imports": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "planted_forbidden_path_rejected": planted_rejected,
    }


def verify_e002_source_seal() -> dict:
    seal = json.loads(
        (RUN_ROOT / "mechanism_seal.json").read_text(encoding="utf-8")
    )
    expected_files = dict(seal["mechanism_files"])
    run_relative = RUN_ROOT.relative_to(REPO_ROOT).as_posix()
    verified: dict[str, str] = {}
    mismatches = []
    representations = {
        "sealed_canonical_lf": 0,
        "sealed_materialized_crlf": 0,
        "exact_untracked_binary": 0,
    }

    for relative, expected in sorted(expected_files.items()):
        path = RUN_ROOT / relative
        if not path.is_file():
            mismatches.append(
                {
                    "path": relative,
                    "status": "MISSING",
                    "expected": expected,
                    "actual": None,
                }
            )
            continue
        repository_path = f"{run_relative}/{relative}"
        tracked = subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{repository_path}"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        ).returncode == 0
        checkout = path.read_bytes()
        checkout_digest = hashlib.sha256(checkout).hexdigest()
        if not tracked:
            if checkout_digest != expected:
                mismatches.append(
                    {
                        "path": relative,
                        "status": "UNTRACKED_HASH_MISMATCH",
                        "expected": expected,
                        "actual": checkout_digest,
                    }
                )
                continue
            verified[relative] = expected
            representations["exact_untracked_binary"] += 1
            continue

        blob = subprocess.check_output(
            ["git", "show", f"HEAD:{repository_path}"],
            cwd=REPO_ROOT,
        )
        canonical = _normalize_newlines(blob)
        canonical_digest = hashlib.sha256(canonical).hexdigest()
        materialized = canonical.replace(b"\n", b"\r\n")
        materialized_digest = hashlib.sha256(materialized).hexdigest()
        if expected not in {canonical_digest, materialized_digest}:
            mismatches.append(
                {
                    "path": relative,
                    "status": "SEALED_REPRESENTATION_MISMATCH",
                    "expected": expected,
                    "canonical_lf": canonical_digest,
                    "materialized_crlf": materialized_digest,
                }
            )
            continue
        if _normalize_newlines(checkout) != canonical:
            mismatches.append(
                {
                    "path": relative,
                    "status": "CHECKOUT_CONTENT_MISMATCH",
                    "expected": expected,
                    "actual": checkout_digest,
                }
            )
            continue
        representation = (
            "sealed_canonical_lf"
            if expected == canonical_digest
            else "sealed_materialized_crlf"
        )
        representations[representation] += 1
        verified[relative] = expected

    aggregate = hashlib.sha256()
    for relative, digest in sorted(verified.items()):
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\0")

    excluded = {"scoring_surface.json", "mechanism_seal.json"}
    observed_files = {
        path.relative_to(RUN_ROOT).as_posix()
        for path in RUN_ROOT.rglob("*")
        if path.is_file() and path.name not in excluded
    }
    extras = sorted(observed_files - set(expected_files))
    missing = sorted(set(expected_files) - observed_files)
    aggregate_digest = aggregate.hexdigest()
    status = (
        "PASS"
        if not mismatches
        and not extras
        and not missing
        and len(verified) == int(seal["mechanism_file_count"])
        and aggregate_digest == seal["aggregate_sha256"]
        else "FAIL"
    )
    return {
        "status": status,
        "seal_status": seal["status"],
        "mechanism_file_count": len(verified),
        "expected_file_count": int(seal["mechanism_file_count"]),
        "aggregate_sha256": aggregate_digest,
        "expected_aggregate_sha256": seal["aggregate_sha256"],
        "representations": representations,
        "mismatches": mismatches,
        "extra_files": extras,
        "missing_files": missing,
    }


def _retrieve_records(
    *,
    query: str,
    probe_turn: int,
    candidates: Sequence[dict],
    configurations: Sequence[tuple[int, int, int]],
    embed,
) -> list[dict]:
    records = []
    for width, offset, per_segment_budget in configurations:
        result = retrieve_segmented(
            query=query,
            candidates=candidates,
            segment_width=width,
            boundary_offset=offset,
            per_segment_budget=per_segment_budget,
            budget_chars=BUDGET_CHARS,
            embed=embed,
        )
        records.append(
            result_record(
                result,
                configuration_id=configuration_id(
                    width,
                    offset,
                    per_segment_budget,
                ),
                probe_turn=probe_turn,
            )
        )
    return records


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
    return {
        "fact_count": len(available),
        "domain_count": len({row["domain"] for row in available}),
        "items": items,
    }


def _payload_for_record(record: dict, candidates: dict[str, dict]) -> str:
    payload = render_stm_payload(
        [],
        [candidates[str(value)] for value in record["selected_ids"]],
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if digest != record["payload_sha256"]:
        raise AssertionError("Raw E002 identity record did not reproduce its payload")
    if len(payload) != int(record["serialized_chars"]):
        raise AssertionError("Raw E002 character count did not reproduce")
    return payload


def _selection_key(row: dict) -> tuple:
    targeted = row["targeted_preserved"]
    q4 = row["q4_item_count"]
    return (
        -int(row["q11_fact_count"]),
        -int(targeted) if targeted != "" else 0,
        -int(q4) if q4 != "" else 0,
        int(row["serialized_chars"]),
        int(row["selected_episode_count"]),
        int(row["per_segment_budget"]),
        -int(row["segment_width"]),
        int(row["boundary_offset"]),
    )


def _write_primary_selection(path: Path, record: dict) -> None:
    fields = (
        "segment_index",
        "segment_text",
        "local_rank",
        "candidate_id",
        "source_turn",
        "domain",
        "cosine",
        "outcome",
    )
    _write_csv(path, record["hits"], fields)


def _write_q11_matrix(path: Path, rows: list[dict]) -> None:
    _write_csv(path, rows, ("domain", "item", "available"))


def _write_targeted_matrix(
    path: Path,
    committed: list[dict],
    availability: dict[tuple[int, str], bool],
) -> None:
    rows = [
        {
            **row,
            "candidate_available": availability[
                (int(row["turn"]), str(row["item"]))
            ],
            "preserved": (
                not row["committed_available"]
                or availability[(int(row["turn"]), str(row["item"]))]
            ),
        }
        for row in committed
    ]
    _write_csv(
        path,
        rows,
        (
            "question",
            "turn",
            "item",
            "committed_available",
            "candidate_available",
            "preserved",
        ),
    )


def _report(result: dict) -> str:
    primary = result["primary_configuration"]
    baseline = result["same_budget_baseline"]
    lines = [
        "# E002 Segmented Query Retrieval",
        "",
        f"**Design commit:** `{result['design_commit']}`  ",
        f"**Execution commit:** `{result['execution_commit']}`  ",
        f"**Outcome:** **{result['outcome']}**",
        "",
        "## Result",
        "",
        (
            f"The same-budget unchanged-selector baseline delivered "
            f"**{baseline['fact_count']}/17** items at "
            f"{baseline['serialized_chars']:,} of 32,000 characters. The "
            f"historical 13/17 hurdle came from the 60,595-character corrected "
            "run and is retained as the stricter comparison."
        ),
        "",
        (
            f"The best segmented configuration delivered "
            f"**{primary['q11_fact_count']}/17** items across "
            f"**{primary['q11_domain_count']}/4** domains. It used "
            f"`S={primary['segment_width']}`, "
            f"`o={primary['boundary_offset']}`, "
            f"`b={primary['per_segment_budget']}`, selected "
            f"{primary['selected_episode_count']} episodes, and serialized "
            f"{primary['serialized_chars']:,} characters."
        ),
        "",
        (
            f"Targeted no-regression preserved "
            f"**{result['primary_targeted_preserved']}/"
            f"{result['targeted_required']}** committed-available items."
        ),
        "",
        "## Integrity",
        "",
        (
            f"Mechanism seal: **{result['mechanism_seal_status']}**. Leakage "
            f"audit: **{result['leakage_audit_status']}**. Source integrity: "
            f"**{result['source_integrity_status']}**. Byte-identical raw "
            f"rerun: **{result['determinism_status']}**."
        ),
        "",
        "This is an offline availability result. It makes no answer-correctness "
        "claim and authorizes no inference run.",
        "",
    ]
    if result["promotion_blocked_on_literature_scan"]:
        lines.extend(
            [
                "Promotion remains blocked on the ledger's diversity-aware "
                "selection literature scan.",
                "",
            ]
        )
    return "\n".join(lines)


def _input_paths() -> list[Path]:
    return [
        DATABASE,
        CONTEXT_LOG,
        TURN_LOG,
        BREADTH_MEASUREMENT,
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


def _normalize_newlines(value: bytes) -> bytes:
    return value.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


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
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
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
        description="Run the prospective E002 offline retrieval test."
    )
    parser.add_argument("--embedding-model", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run_e002(args.output_dir, args.embedding_model.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
