"""Checkpointed, label-blind BEAM-001 three-arm Part 1 exploration."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from unittest.mock import patch

from analysis.beam001_adapter import adapt_conversation, assert_mechanism_only
from analysis.beam001_anchors import OUTPUT as ANCHOR_PATH
from analysis.beam001_anchors import SELECTOR_SHA256
from analysis.beam001_anchors import run as run_anchors
from analysis.beam001_gpu_embedding import (
    CACHE_PATH,
    CachedEmbedder,
    EmbeddingCache,
    FAILURE_PATH as EMBEDDING_FAILURE_PATH,
    MECHANISM_SURFACE,
    MODEL_SHA256,
)
from analysis.beam001_parent_opportunity import build_parent_opportunity_context
from episodic import EpisodeStore, EpisodicConfig
from episodic._aspect import prepare_facets
from episodic._retrieval import RetrievalAllocation, retrieve_long_term
from episodic._render import render_stm_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "experiments/comparisons/beam_001"
ARTIFACT_ROOT = ROOT / "artifacts/exploration"
STORE_ROOT = ARTIFACT_ROOT / "stores"
CHECKPOINT_PATH = ARTIFACT_ROOT / "checkpoint.jsonl"
CONTEXTS_PATH = ARTIFACT_ROOT / "contexts.jsonl.gz"
RANKINGS_PATH = ARTIFACT_ROOT / "rankings.jsonl.gz"
PAYLOADS_PATH = ARTIFACT_ROOT / "payloads.sealed.jsonl.gz"
SUMMARY_PATH = ARTIFACT_ROOT / "summary.json"
SHUFFLE_PATH = ARTIFACT_ROOT / "shuffle_replay.json"
FACET_REPRESENTATION_PATH = ARTIFACT_ROOT / "facet_representation.jsonl.gz"
RUNTIME_PATH = ROOT / "artifacts/runtime/exploration_progress.json"
FAILURE_PATH = ROOT / "artifacts/runtime/exploration_failure.json"

ARMS = (
    "A0_CC80_QWEN_GPU_COMMON",
    "C0_STATIC_ASPECT_QWEN_GPU_COMMON",
    "T1_PARENT_OPPORTUNITY_ASPECT_QWEN_GPU_COMMON",
)
EXPECTED_QUESTIONS = 1_800
EXPECTED_ROWS = EXPECTED_QUESTIONS * len(ARMS)
EXPECTED_VECTORS = 60_990
EXPECTED_BINDINGS = 61_011
PACKAGE_TREE_SHA256 = "ae3058f072a9c5b8ce59b130066db11a977e7ab1"


class BeamExplorationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _iter_mechanism(path: Path = MECHANISM_SURFACE) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            assert_mechanism_only(row)
            yield row


def _append_checkpoint(
    row: Mapping[str, Any], path: Path | None = None
) -> None:
    path = CHECKPOINT_PATH if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(raw + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _load_checkpoints() -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    paths = [CHECKPOINT_PATH]
    paths.extend(sorted(CHECKPOINT_PATH.parent.glob("checkpoint.shard-*.jsonl")))
    for path in paths:
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                if line_number == len(lines):
                    break
                raise BeamExplorationError(
                    f"Corrupt nonterminal checkpoint row: {path}"
                ) from error
            key = (str(row["question_key"]), str(row["arm"]))
            if key in rows and rows[key] != row:
                raise BeamExplorationError(f"Conflicting checkpoint: {key}")
            rows[key] = row
    return rows


def _write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            for row in rows:
                line = json.dumps(
                    row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
                compressed.write(line + b"\n")
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def _shuffled_questions(
    questions: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Return the frozen, order-independent Part 1 replay schedule."""

    return sorted(
        questions,
        key=lambda item: hashlib.sha256(
            b"beam001-shuffle-v1\0" + str(item["question_key"]).encode("ascii")
        ).digest(),
    )


def _stable_maps(
    stored: Sequence[dict[str, Any]], adapted: Sequence[dict[str, Any]]
) -> tuple[dict[str, str], dict[int, str]]:
    if len(stored) != len(adapted):
        raise BeamExplorationError("Stored/adapted episode count drift")
    internal_to_stable: dict[str, str] = {}
    index_to_stable: dict[int, str] = {}
    for index, (record, source) in enumerate(zip(stored, adapted)):
        if (
            int(record["turn_number"]) != int(source["turn_number"])
            or record["user_message"] != source["user_message"]
            or record["assistant_message"] != source["assistant_message"]
        ):
            raise BeamExplorationError("Public store changed an adapted episode")
        stable = str(source["episode_key"])
        internal_to_stable[str(record["id"])] = stable
        index_to_stable[index] = stable
    return internal_to_stable, index_to_stable


def _store_count(path: Path) -> int:
    if not path.is_file():
        return 0
    with sqlite3.connect(path) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0])


def _prepare_stores(
    row: Mapping[str, Any], embedder: CachedEmbedder
) -> tuple[EpisodeStore, EpisodeStore, list[dict[str, Any]]]:
    adapted = adapt_conversation(row)
    conversation_key = str(row["conversation_key"])
    directory = STORE_ROOT / conversation_key
    directory.mkdir(parents=True, exist_ok=True)
    a0_path = directory / "a0.db"
    c0_path = directory / "c0.db"
    expected = len(adapted)
    existing = _store_count(a0_path)
    if existing not in (0, expected):
        raise BeamExplorationError(f"Partial A0 store: {existing}/{expected}")
    a0 = EpisodeStore(a0_path, config=EpisodicConfig(), embedder=embedder)
    if existing == 0:
        for episode in adapted:
            a0.append("user", str(episode["user_message"]))
            a0.append("assistant", str(episode["assistant_message"]))
    if _store_count(c0_path) == 0:
        a0.close()
        shutil.copy2(a0_path, c0_path)
        rebound = EpisodeStore(
            c0_path,
            config=EpisodicConfig(aspect_enabled=True),
            embedder=embedder,
            override_config=True,
        )
        rebound.close()
        a0 = EpisodeStore(a0_path, config=EpisodicConfig(), embedder=embedder)
    elif _store_count(c0_path) != expected:
        a0.close()
        raise BeamExplorationError("Partial C0 store")
    c0 = EpisodeStore(
        c0_path, config=EpisodicConfig(aspect_enabled=True), embedder=embedder
    )
    a0_ids = [str(item["id"]) for item in a0._all_episodes()]
    c0_ids = [str(item["id"]) for item in c0._all_episodes()]
    if a0_ids != c0_ids:
        a0.close()
        c0.close()
        raise BeamExplorationError("Control stores do not share exact internal identities")
    return a0, c0, adapted


@contextmanager
def _cached_public_facets(bundle: Any) -> Iterator[None]:
    # This memoizes deterministic parser output; selection remains inside the
    # unmodified public EpisodeStore.context path.
    with patch("episodic._retrieval.prepare_facets", return_value=bundle):
        yield


def _map_ids(values: Sequence[str], mapping: Mapping[str, str]) -> list[str]:
    return [mapping[str(value)] for value in values]


def _ranking_record(
    *,
    question: Mapping[str, Any],
    row: Mapping[str, Any],
    retrieval: RetrievalAllocation,
    index_to_stable: Mapping[int, str],
) -> dict[str, Any]:
    ranking = retrieval.ranking
    record = {
        "schema": "beam001-ranking-v1",
        "question_key": question["question_key"],
        "conversation_key": row["conversation_key"],
        "split": row["split"],
        "category": question["category"],
        "order": [index_to_stable[index] for index in ranking.order],
        "scores": list(ranking.scores),
        "dense_scores": list(ranking.dense_scores),
        "bm25_scores": list(ranking.bm25_scores),
        "dense_normalized": list(ranking.dense_normalized),
        "bm25_normalized": list(ranking.bm25_normalized),
    }
    record["ranking_sha256"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return record


def _control_record(
    *,
    arm: str,
    row: Mapping[str, Any],
    question: Mapping[str, Any],
    payload: str,
    report: Any,
    retrieval: RetrievalAllocation,
    internal_to_stable: Mapping[str, str],
    index_to_stable: Mapping[int, str],
    ranking_sha256: str,
    elapsed: float,
) -> dict[str, Any]:
    trace = retrieval.aspect_trace
    aspect = (
        {
            "order": [index_to_stable[index] for index in trace.order],
            "marginal": list(trace.marginal),
            "covered_counts": list(trace.covered_counts),
            "solo_chars": trace.solo_chars,
            "stopping_reason": trace.stopping_reason,
        }
        if trace is not None
        else {
            "order": [],
            "marginal": [],
            "covered_counts": [],
            "solo_chars": 0,
            "stopping_reason": None,
        }
    )
    report_record = asdict(report)
    report_record["recent_ids"] = _map_ids(report.recent_ids, internal_to_stable)
    report_record["dropped_ids"] = _map_ids(report.dropped_ids, internal_to_stable)
    return {
        "schema": "beam001-context-v1",
        "arm": arm,
        "question_key": question["question_key"],
        "conversation_key": row["conversation_key"],
        "split": row["split"],
        "category": question["category"],
        "ranking_sha256": ranking_sha256,
        "recent_ids": _map_ids(report.recent_ids, internal_to_stable),
        "semantic_parent_ids": _map_ids(
            retrieval.initial_semantic_ids, internal_to_stable
        ),
        "proposed_child_ids": aspect["order"],
        "retained_child_ids": _map_ids(retrieval.aspect_ids, internal_to_stable),
        "returned_semantic_ids": _map_ids(
            retrieval.returned_semantic_ids, internal_to_stable
        ),
        "selected_long_term_ids": _map_ids(retrieval.selected_ids, internal_to_stable),
        "dropped_ids": _map_ids(retrieval.dropped_ids, internal_to_stable),
        "aspect": aspect,
        "retrieval_payload_sha256": hashlib.sha256(
            retrieval.payload.encode("utf-8")
        ).hexdigest(),
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "retrieval_chars": len(retrieval.payload),
        "final_chars": len(payload),
        "report": report_record,
        "elapsed_seconds": elapsed,
        "payload": payload,
    }


def _t1_record(
    *,
    row: Mapping[str, Any],
    question: Mapping[str, Any],
    result: Any,
    index_to_stable: Mapping[int, str],
    ranking_sha256: str,
    elapsed: float,
) -> dict[str, Any]:
    stable = lambda indices: [index_to_stable[index] for index in indices]
    decisions = []
    for decision in result.trace.decisions:
        decisions.append(
            {
                **asdict(decision),
                "parent_id": index_to_stable[decision.parent_index],
                "child_id": index_to_stable[decision.child_index],
                "displaced_ids": stable(decision.displaced_indices),
            }
        )
    return {
        "schema": "beam001-context-v1",
        "arm": ARMS[2],
        "question_key": question["question_key"],
        "conversation_key": row["conversation_key"],
        "split": row["split"],
        "category": question["category"],
        "ranking_sha256": ranking_sha256,
        "recent_ids": stable(result.recent_indices),
        "semantic_parent_ids": stable(result.semantic_parent_indices),
        "proposed_child_ids": stable(result.trace.proposed_children),
        "parent_for_child_ids": stable(result.trace.parent_for_child),
        "retained_child_ids": stable(result.aspect_indices),
        "returned_semantic_ids": stable(result.returned_semantic_indices),
        "selected_long_term_ids": stable(result.selected_indices),
        "dropped_ids": stable(result.dropped_indices),
        "aspect": {
            "decisions": decisions,
            "no_positive_child": result.trace.no_positive_child,
            "no_fitting_child": result.trace.no_fitting_child,
            "rejected_capacity": result.trace.rejected_capacity,
            "rejected_value": result.trace.rejected_value,
            "finite_attempts": result.trace.finite_attempts,
            "facet_families": dict(result.facet_families),
        },
        "retrieval_payload_sha256": result.retrieval_payload_sha256,
        "payload_sha256": result.payload_sha256,
        "retrieval_chars": len(result.retrieval_payload),
        "final_chars": len(result.payload),
        "elapsed_seconds": elapsed,
        "payload": result.payload,
    }


def _assert_composition(record: Mapping[str, Any]) -> None:
    if int(record["retrieval_chars"]) > 32_000:
        raise BeamExplorationError("Long-term budget exceeded")
    recent = tuple(record["recent_ids"])
    selected = tuple(record["selected_long_term_ids"])
    if set(recent) & set(selected) or len((*recent, *selected)) != len(
        set((*recent, *selected))
    ):
        raise BeamExplorationError("Composition duplicated an episode")
    if record["arm"] == ARMS[0]:
        aspect = record["aspect"]
        if any(aspect[key] for key in ("order", "marginal", "covered_counts")):
            raise BeamExplorationError("A0 acquired an ASPECT trace")
        if int(aspect["solo_chars"]) != 0:
            raise BeamExplorationError("A0 spent protected characters")


def _separation_gate() -> dict[str, Any]:
    source_path = Path(__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    forbidden = [value for value in imports if "beam001_outcomes" in value]
    if forbidden:
        raise BeamExplorationError("Exploration imports the sealed outcome reader")
    planted = {"question": "safe", "ideal_response": "forbidden"}
    rejected = False
    try:
        assert_mechanism_only(planted)
    except Exception:
        rejected = True
    if not rejected:
        raise BeamExplorationError("Planted outcome field was not rejected")
    return {"planted_field_rejected": True, "forbidden_imports": forbidden}


def _anchors() -> dict[str, Any]:
    if ANCHOR_PATH.is_file():
        prior = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
        selector = REPO_ROOT / "src/analysis/beam001_parent_opportunity.py"
        if (
            prior.get("status") == "PASS"
            and prior.get("package_tree") == PACKAGE_TREE_SHA256
            and prior.get("selector_sha256") == SELECTOR_SHA256
            and sha256_file(selector) == SELECTOR_SHA256
            and prior.get("tc014_opportunity", {}).get("checked") == 871
            and prior.get("tc014_opportunity", {}).get("mismatches") == 0
        ):
            return prior
    return run_anchors()


def _run_with_embedder(
    existing: dict[tuple[str, str], dict[str, Any]],
    *,
    shard_index: int = 0,
    shard_count: int = 1,
    checkpoint_path: Path = CHECKPOINT_PATH,
    runtime_path: Path = RUNTIME_PATH,
) -> None:
    if shard_count < 1 or shard_index < 0 or shard_index >= shard_count:
        raise BeamExplorationError("Invalid conversation shard")
    embedder = CachedEmbedder(CACHE_PATH)
    try:
        completed_at_start = len(existing)
        completed_by_shard = 0
        for conversation_number, row in enumerate(_iter_mechanism(), 1):
            if (conversation_number - 1) % shard_count != shard_index:
                continue
            a0, c0, adapted = _prepare_stores(row, embedder)
            try:
                a0_records = a0._all_episodes()
                c0_records = c0._all_episodes()
                internal_to_stable, index_to_stable = _stable_maps(a0_records, adapted)
                c0_map, _ = _stable_maps(c0_records, adapted)
                if c0_map != internal_to_stable:
                    raise BeamExplorationError("Control identity maps drifted")
                facet_bundle = prepare_facets(a0_records, EpisodicConfig().aspect_model)
                for question in row["questions"]:
                    key = str(question["question_key"])
                    query = str(question["question"])
                    query_vector = embedder(query)
                    ranking_record: dict[str, Any] | None = None
                    if (key, ARMS[0]) not in existing:
                        before = a0._conn.total_changes
                        t0 = time.perf_counter()
                        payload, report = a0.context(query)
                        elapsed = time.perf_counter() - t0
                        if a0._conn.total_changes != before:
                            raise BeamExplorationError("A0 context mutated its store")
                        retrieval = retrieve_long_term(
                            episodes=a0_records,
                            query_text=query,
                            query_embedding=query_vector,
                            budget=32_000,
                            config=EpisodicConfig(),
                            excluded_ids=report.recent_ids,
                        )
                        if payload != render_stm_payload(
                            [a0_records[index] for index in range(max(0, len(a0_records) - 32), len(a0_records))],
                            [a0_records[index] for index in retrieval.selected_indices],
                        ):
                            raise BeamExplorationError("A0 introspection did not reproduce public payload")
                        ranking_record = _ranking_record(
                            question=question,
                            row=row,
                            retrieval=retrieval,
                            index_to_stable=index_to_stable,
                        )
                        record = _control_record(
                            arm=ARMS[0], row=row, question=question, payload=payload,
                            report=report, retrieval=retrieval,
                            internal_to_stable=internal_to_stable,
                            index_to_stable=index_to_stable,
                            ranking_sha256=ranking_record["ranking_sha256"], elapsed=elapsed,
                        )
                        record["_ranking"] = ranking_record
                        _assert_composition(record)
                        _append_checkpoint(record, checkpoint_path)
                        existing[(key, ARMS[0])] = record
                        completed_by_shard += 1
                    else:
                        a0_record = existing[(key, ARMS[0])]
                        ranking_record = {"ranking_sha256": a0_record["ranking_sha256"]}

                    if (key, ARMS[1]) not in existing:
                        before = c0._conn.total_changes
                        t0 = time.perf_counter()
                        with _cached_public_facets(facet_bundle):
                            payload, report = c0.context(query)
                        elapsed = time.perf_counter() - t0
                        if c0._conn.total_changes != before:
                            raise BeamExplorationError("C0 context mutated its store")
                        with _cached_public_facets(facet_bundle):
                            retrieval = retrieve_long_term(
                                episodes=c0_records,
                                query_text=query,
                                query_embedding=query_vector,
                                budget=32_000,
                                config=EpisodicConfig(aspect_enabled=True),
                                excluded_ids=report.recent_ids,
                            )
                        expected = render_stm_payload(
                            [c0_records[index] for index in range(max(0, len(c0_records) - 32), len(c0_records))],
                            [c0_records[index] for index in retrieval.selected_indices],
                        )
                        if payload != expected:
                            raise BeamExplorationError("C0 introspection did not reproduce public payload")
                        c0_ranking = _ranking_record(
                            question=question,
                            row=row,
                            retrieval=retrieval,
                            index_to_stable=index_to_stable,
                        )
                        if c0_ranking["ranking_sha256"] != ranking_record["ranking_sha256"]:
                            raise BeamExplorationError("A0/C0 common CC80 ranking drifted")
                        record = _control_record(
                            arm=ARMS[1], row=row, question=question, payload=payload,
                            report=report, retrieval=retrieval,
                            internal_to_stable=internal_to_stable,
                            index_to_stable=index_to_stable,
                            ranking_sha256=str(ranking_record["ranking_sha256"]), elapsed=elapsed,
                        )
                        _assert_composition(record)
                        _append_checkpoint(record, checkpoint_path)
                        existing[(key, ARMS[1])] = record
                        completed_by_shard += 1

                    if (key, ARMS[2]) not in existing:
                        t0 = time.perf_counter()
                        result = build_parent_opportunity_context(
                            episodes=a0_records,
                            query_text=query,
                            query_embedding=query_vector,
                            config=EpisodicConfig(),
                            facet_bundle=facet_bundle,
                        )
                        elapsed = time.perf_counter() - t0
                        t1_ranking = {
                            "order": [index_to_stable[index] for index in result.ranking.order],
                            "scores": list(result.ranking.scores),
                        }
                        a0_ranking = existing[(key, ARMS[0])].get("_ranking")
                        if a0_ranking is not None and (
                            t1_ranking["order"] != a0_ranking["order"]
                            or t1_ranking["scores"] != a0_ranking["scores"]
                        ):
                            raise BeamExplorationError("A0/T1 common CC80 ranking drifted")
                        record = _t1_record(
                            row=row, question=question, result=result,
                            index_to_stable=index_to_stable,
                            ranking_sha256=str(ranking_record["ranking_sha256"]), elapsed=elapsed,
                        )
                        _assert_composition(record)
                        _append_checkpoint(record, checkpoint_path)
                        existing[(key, ARMS[2])] = record
                        completed_by_shard += 1
                    _write_json(
                        runtime_path,
                        {
                            "status": "RUNNING",
                            "shard_index": shard_index,
                            "shard_count": shard_count,
                            "completed_at_shard_start": completed_at_start,
                            "new_completed_by_shard": completed_by_shard,
                            "expected_question_arms": EXPECTED_ROWS,
                            "conversation": conversation_number,
                            "expected_conversations": 90,
                            "api_calls": 0,
                            "outcomes_opened": False,
                            "updated_unix": time.time(),
                        },
                    )
            finally:
                a0.close()
                c0.close()
        _write_json(
            runtime_path,
            {
                "status": "COMPLETE",
                "shard_index": shard_index,
                "shard_count": shard_count,
                "completed_at_shard_start": completed_at_start,
                "new_completed_by_shard": completed_by_shard,
                "api_calls": 0,
                "outcomes_opened": False,
                "updated_unix": time.time(),
            },
        )
    finally:
        embedder.close()


def _finalize(existing: Mapping[tuple[str, str], Mapping[str, Any]]) -> dict[str, Any]:
    if len(existing) != EXPECTED_ROWS:
        raise BeamExplorationError(f"Incomplete checkpoint set: {len(existing)}/{EXPECTED_ROWS}")
    ordered = [existing[key] for key in sorted(existing)]
    contexts = []
    payloads = []
    rankings_by_digest: dict[str, dict[str, Any]] = {}
    for row in ordered:
        context = dict(row)
        payload = str(context.pop("payload"))
        ranking = context.pop("_ranking", None)
        if ranking is not None:
            rankings_by_digest[str(ranking["ranking_sha256"])] = ranking
        contexts.append(context)
        payloads.append(
            {
                "question_key": row["question_key"],
                "arm": row["arm"],
                "payload_sha256": row["payload_sha256"],
                "payload": payload,
            }
        )
    _write_gzip_jsonl(CONTEXTS_PATH, contexts)
    _write_gzip_jsonl(PAYLOADS_PATH, payloads)
    _write_gzip_jsonl(RANKINGS_PATH, list(rankings_by_digest.values()))
    changed = {
        pair: 0
        for pair in ("A0_C0", "C0_T1", "A0_T1")
    }
    by_question: dict[str, dict[str, Mapping[str, Any]]] = {}
    for row in ordered:
        by_question.setdefault(str(row["question_key"]), {})[str(row["arm"])] = row
    for arms in by_question.values():
        changed["A0_C0"] += set(arms[ARMS[0]]["selected_long_term_ids"]) != set(arms[ARMS[1]]["selected_long_term_ids"])
        changed["C0_T1"] += set(arms[ARMS[1]]["selected_long_term_ids"]) != set(arms[ARMS[2]]["selected_long_term_ids"])
        changed["A0_T1"] += set(arms[ARMS[0]]["selected_long_term_ids"]) != set(arms[ARMS[2]]["selected_long_term_ids"])
    summary = {
        "schema": "beam001-part1-summary-v1",
        "status": "COMPLETE",
        "question_arms": len(ordered),
        "questions": len(by_question),
        "selection_set_changes": changed,
        "gates": {
            "G_BASELINE": "PASS",
            "G_BUDGET": "PASS",
            "G_TREATMENT": "PASS" if 0 < changed["C0_T1"] < EXPECTED_QUESTIONS else "FAIL",
        },
        "calls": {"embedding_model": 0, "llm_or_generative": 0},
        "outcomes_opened": False,
        "artifacts": {
            "contexts_sha256": sha256_file(CONTEXTS_PATH),
            "payloads_sha256": sha256_file(PAYLOADS_PATH),
            "rankings_sha256": sha256_file(RANKINGS_PATH),
        },
    }
    _write_json(SUMMARY_PATH, summary)
    _write_json(RUNTIME_PATH, {**summary, "updated_unix": time.time()})
    return summary


def run() -> dict[str, Any]:
    os.environ.pop("OPENAI_API_KEY", None)
    FAILURE_PATH.unlink(missing_ok=True)
    separation = _separation_gate()
    existing = _load_checkpoints()
    try:
        anchors = _anchors()
        _run_with_embedder(existing)
        refreshed = _load_checkpoints()
        result = _finalize(refreshed)
        result["separation"] = separation
        result["anchors"] = {
            "status": anchors["status"],
            "path": ANCHOR_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(ANCHOR_PATH),
        }
        _write_json(SUMMARY_PATH, result)
        _write_json(RUNTIME_PATH, {**result, "updated_unix": time.time()})
        return result
    except Exception as error:
        _write_json(
            FAILURE_PATH,
            {
                "status": "FAILED",
                "error_type": type(error).__name__,
                "error": str(error),
                "completed_question_arms": len(_load_checkpoints()),
                "api_calls": 0,
                "outcomes_opened": False,
                "failed_unix": time.time(),
            },
        )
        raise


def run_shard(shard_index: int, shard_count: int) -> dict[str, Any]:
    """Run one disjoint conversation shard without finalizing shared output."""

    os.environ.pop("OPENAI_API_KEY", None)
    checkpoint = ARTIFACT_ROOT / f"checkpoint.shard-{shard_index:02d}.jsonl"
    runtime = ROOT / (
        f"artifacts/runtime/exploration_progress.shard-{shard_index:02d}.json"
    )
    failure = ROOT / (
        f"artifacts/runtime/exploration_failure.shard-{shard_index:02d}.json"
    )
    failure.unlink(missing_ok=True)
    try:
        _separation_gate()
        _anchors()
        existing = _load_checkpoints()
        _run_with_embedder(
            existing,
            shard_index=shard_index,
            shard_count=shard_count,
            checkpoint_path=checkpoint,
            runtime_path=runtime,
        )
        return {
            "status": "COMPLETE",
            "shard_index": shard_index,
            "shard_count": shard_count,
            "checkpoint": checkpoint.relative_to(REPO_ROOT).as_posix(),
            "api_calls": 0,
            "outcomes_opened": False,
        }
    except Exception as error:
        _write_json(
            failure,
            {
                "status": "FAILED",
                "shard_index": shard_index,
                "shard_count": shard_count,
                "error_type": type(error).__name__,
                "error": str(error),
                "api_calls": 0,
                "outcomes_opened": False,
                "failed_unix": time.time(),
            },
        )
        raise


def parallel_run(workers: int = 8) -> dict[str, Any]:
    """Run deterministic conversation shards concurrently, then finalize."""

    if workers < 2 or workers > 16:
        raise BeamExplorationError("Parallel worker count must be in [2,16]")
    os.environ.pop("OPENAI_API_KEY", None)
    FAILURE_PATH.unlink(missing_ok=True)
    separation = _separation_gate()
    anchors = _anchors()
    environment = dict(os.environ)
    environment.pop("OPENAI_API_KEY", None)
    environment["PYTHONPATH"] = str(REPO_ROOT / "src")
    processes: list[tuple[int, subprocess.Popen[Any], Any, Any]] = []
    try:
        for index in range(workers):
            stdout_path = ROOT / (
                f"artifacts/runtime/exploration_shard_{index:02d}_stdout.log"
            )
            stderr_path = ROOT / (
                f"artifacts/runtime/exploration_shard_{index:02d}_stderr.log"
            )
            stdout = stdout_path.open("ab")
            stderr = stderr_path.open("ab")
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "analysis.beam001_exploration",
                    "shard",
                    "--shard-index",
                    str(index),
                    "--shard-count",
                    str(workers),
                ],
                cwd=REPO_ROOT,
                env=environment,
                stdout=stdout,
                stderr=stderr,
            )
            processes.append((index, process, stdout, stderr))
        failures = []
        for index, process, stdout, stderr in processes:
            returncode = process.wait()
            stdout.close()
            stderr.close()
            if returncode:
                failures.append({"shard_index": index, "returncode": returncode})
        if failures:
            raise BeamExplorationError(f"Conversation shards failed: {failures}")
        result = _finalize(_load_checkpoints())
        result["separation"] = separation
        result["anchors"] = {
            "status": anchors["status"],
            "path": ANCHOR_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(ANCHOR_PATH),
        }
        result["runtime"] = {
            "mode": "disjoint_conversation_shards",
            "workers": workers,
            "gpu_required": False,
        }
        _write_json(SUMMARY_PATH, result)
        _write_json(RUNTIME_PATH, {**result, "updated_unix": time.time()})
        return result
    except Exception as error:
        for _, process, stdout, stderr in processes:
            if process.poll() is None:
                process.terminate()
            if not stdout.closed:
                stdout.close()
            if not stderr.closed:
                stderr.close()
        _write_json(
            FAILURE_PATH,
            {
                "status": "FAILED",
                "error_type": type(error).__name__,
                "error": str(error),
                "completed_question_arms": len(_load_checkpoints()),
                "api_calls": 0,
                "outcomes_opened": False,
                "failed_unix": time.time(),
            },
        )
        raise


def run_shuffle_shard(shard_index: int, shard_count: int) -> dict[str, Any]:
    """Replay one conversation shard in a frozen shuffled question order."""

    if shard_count < 1 or shard_index < 0 or shard_index >= shard_count:
        raise BeamExplorationError("Invalid shuffle shard")
    os.environ.pop("OPENAI_API_KEY", None)
    expected = _load_checkpoints()
    if len(expected) != EXPECTED_ROWS:
        raise BeamExplorationError(
            f"Shuffle replay requires complete exploration: {len(expected)}/{EXPECTED_ROWS}"
        )
    output = ARTIFACT_ROOT / f"shuffle.shard-{shard_index:02d}.json"
    embedder = CachedEmbedder(CACHE_PATH)
    checked = 0
    conversations = 0
    changed_orders = 0
    order_keys: list[str] = []
    mismatches: list[dict[str, str]] = []
    facet_rows: list[dict[str, Any]] = []
    try:
        for conversation_number, row in enumerate(_iter_mechanism(), 1):
            if (conversation_number - 1) % shard_count != shard_index:
                continue
            conversations += 1
            questions = list(row["questions"])
            shuffled = _shuffled_questions(questions)
            source_keys = [str(question["question_key"]) for question in questions]
            shuffled_keys = [str(question["question_key"]) for question in shuffled]
            changed_orders += shuffled_keys != source_keys
            order_keys.extend(shuffled_keys)
            a0, c0, adapted = _prepare_stores(row, embedder)
            try:
                a0_records = a0._all_episodes()
                c0_records = c0._all_episodes()
                _, index_to_stable = _stable_maps(a0_records, adapted)
                facet_bundle = prepare_facets(
                    a0_records, EpisodicConfig().aspect_model
                )
                facets_by_id = {
                    index_to_stable[index]: facets
                    for index, facets in enumerate(facet_bundle[0])
                }
                for question in shuffled:
                    key = str(question["question_key"])
                    query = str(question["question"])
                    query_vector = embedder(query)
                    before_a0 = a0._conn.total_changes
                    a0_payload, _ = a0.context(query)
                    if a0._conn.total_changes != before_a0:
                        raise BeamExplorationError("Shuffle A0 mutated its store")
                    before_c0 = c0._conn.total_changes
                    with _cached_public_facets(facet_bundle):
                        c0_payload, _ = c0.context(query)
                    if c0._conn.total_changes != before_c0:
                        raise BeamExplorationError("Shuffle C0 mutated its store")
                    t1 = build_parent_opportunity_context(
                        episodes=a0_records,
                        query_text=query,
                        query_embedding=query_vector,
                        config=EpisodicConfig(),
                        facet_bundle=facet_bundle,
                    )
                    for arm, payload in zip(
                        ARMS, (a0_payload, c0_payload, t1.payload), strict=True
                    ):
                        observed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                        wanted = str(expected[(key, arm)]["payload_sha256"])
                        checked += 1
                        if observed != wanted:
                            mismatches.append(
                                {
                                    "question_key": key,
                                    "arm": arm,
                                    "expected": wanted,
                                    "observed": observed,
                                }
                            )
                        selected = expected[(key, arm)]["selected_long_term_ids"]
                        family_episodes: Counter[str] = Counter()
                        family_facets: Counter[str] = Counter()
                        covered: set[str] = set()
                        for identifier in selected:
                            episode_families: set[str] = set()
                            for facet in facets_by_id[str(identifier)]:
                                family = facet.split(":", 1)[0]
                                family_facets[family] += 1
                                episode_families.add(family)
                                covered.add(facet)
                            family_episodes.update(episode_families)
                        facet_rows.append(
                            {
                                "schema": "beam001-facet-representation-v1",
                                "question_key": key,
                                "arm": arm,
                                "split": row["split"],
                                "category": question["category"],
                                "selected_long_term_count": len(selected),
                                "covered_unique_facets": len(covered),
                                "family_episode_counts": dict(
                                    sorted(family_episodes.items())
                                ),
                                "family_facet_occurrences": dict(
                                    sorted(family_facets.items())
                                ),
                            }
                        )
            finally:
                a0.close()
                c0.close()
    finally:
        embedder.close()
    result = {
        "schema": "beam001-shuffle-shard-v1",
        "status": "PASS" if not mismatches else "FAIL",
        "shard_index": shard_index,
        "shard_count": shard_count,
        "conversations": conversations,
        "conversations_with_changed_order": changed_orders,
        "question_arms_checked": checked,
        "mismatches": mismatches,
        "question_order": order_keys,
        "question_order_sha256": hashlib.sha256(
            "\n".join(order_keys).encode("ascii")
        ).hexdigest(),
        "embedding_calls": 0,
        "generation_calls": 0,
        "outcomes_opened": False,
    }
    facet_path = ARTIFACT_ROOT / f"facet_representation.shard-{shard_index:02d}.jsonl.gz"
    _write_gzip_jsonl(facet_path, facet_rows)
    result["facet_representation_sha256"] = sha256_file(facet_path)
    _write_json(output, result)
    if mismatches:
        raise BeamExplorationError(
            f"Shuffle shard {shard_index} found {len(mismatches)} payload mismatches"
        )
    return result


def parallel_shuffle_replay(workers: int = 8) -> dict[str, Any]:
    """Run the registered shuffled-order replay over every question-arm."""

    if workers < 2 or workers > 16:
        raise BeamExplorationError("Parallel worker count must be in [2,16]")
    os.environ.pop("OPENAI_API_KEY", None)
    processes: list[tuple[int, subprocess.Popen[Any], Any, Any]] = []
    environment = dict(os.environ)
    environment.pop("OPENAI_API_KEY", None)
    environment["PYTHONPATH"] = str(REPO_ROOT / "src")
    for index in range(workers):
        stdout = (ROOT / f"artifacts/runtime/shuffle_{index:02d}_stdout.log").open("ab")
        stderr = (ROOT / f"artifacts/runtime/shuffle_{index:02d}_stderr.log").open("ab")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "analysis.beam001_exploration",
                "shuffle-shard",
                "--shard-index",
                str(index),
                "--shard-count",
                str(workers),
            ],
            cwd=REPO_ROOT,
            env=environment,
            stdout=stdout,
            stderr=stderr,
        )
        processes.append((index, process, stdout, stderr))
    failures = []
    for index, process, stdout, stderr in processes:
        returncode = process.wait()
        stdout.close()
        stderr.close()
        if returncode:
            failures.append({"shard_index": index, "returncode": returncode})
    if failures:
        raise BeamExplorationError(f"Shuffle replay shards failed: {failures}")
    shards = [
        json.loads(
            (ARTIFACT_ROOT / f"shuffle.shard-{index:02d}.json").read_text(
                encoding="utf-8"
            )
        )
        for index in range(workers)
    ]
    order = [key for shard in shards for key in shard["question_order"]]
    facet_rows = []
    for index in range(workers):
        path = ARTIFACT_ROOT / f"facet_representation.shard-{index:02d}.jsonl.gz"
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            facet_rows.extend(json.loads(line) for line in handle)
    facet_rows.sort(key=lambda row: (str(row["question_key"]), str(row["arm"])))
    _write_gzip_jsonl(FACET_REPRESENTATION_PATH, facet_rows)
    result = {
        "schema": "beam001-shuffle-replay-v1",
        "status": "PASS",
        "workers": workers,
        "conversations": sum(int(shard["conversations"]) for shard in shards),
        "conversations_with_changed_order": sum(
            int(shard["conversations_with_changed_order"]) for shard in shards
        ),
        "question_arms_checked": sum(
            int(shard["question_arms_checked"]) for shard in shards
        ),
        "payload_mismatches": sum(len(shard["mismatches"]) for shard in shards),
        "question_order_sha256": hashlib.sha256(
            "\n".join(order).encode("ascii")
        ).hexdigest(),
        "embedding_calls": 0,
        "generation_calls": 0,
        "outcomes_opened": False,
        "facet_representation": {
            "rows": len(facet_rows),
            "sha256": sha256_file(FACET_REPRESENTATION_PATH),
        },
    }
    if (
        result["conversations"] != 90
        or result["conversations_with_changed_order"] != 90
        or result["question_arms_checked"] != EXPECTED_ROWS
        or result["facet_representation"]["rows"] != EXPECTED_ROWS
    ):
        raise BeamExplorationError(f"Incomplete shuffled replay: {result}")
    _write_json(SHUFFLE_PATH, result)
    return result


def wait_and_run(interval_seconds: int = 60) -> dict[str, Any]:
    os.environ.pop("OPENAI_API_KEY", None)
    while True:
        try:
            with EmbeddingCache(CACHE_PATH, read_only=True) as cache:
                counts = cache.counts()
                if (
                    counts["vectors"] == EXPECTED_VECTORS
                    and counts["bindings"] == EXPECTED_BINDINGS
                ):
                    verified = cache.verify()
                    if verified["vector_digest_mismatches"] != 0:
                        raise BeamExplorationError("Embedding cache digest mismatch")
                    break
                if counts["vectors"] > EXPECTED_VECTORS or counts["bindings"] > EXPECTED_BINDINGS:
                    raise BeamExplorationError("Embedding cache exceeded frozen counts")
        except (FileNotFoundError, sqlite3.OperationalError):
            pass
        time.sleep(interval_seconds)
    return run()


def resume_and_run(interval_seconds: int = 60, max_restarts: int = 3) -> dict[str, Any]:
    """Resume a failed cache population locally, then execute Part 1."""

    os.environ.pop("OPENAI_API_KEY", None)
    restarts = 0
    while True:
        complete = False
        try:
            with EmbeddingCache(CACHE_PATH, read_only=True) as cache:
                counts = cache.counts()
                complete = (
                    counts["vectors"] == EXPECTED_VECTORS
                    and counts["bindings"] == EXPECTED_BINDINGS
                )
        except (FileNotFoundError, sqlite3.OperationalError):
            pass
        if complete:
            return run()
        if EMBEDDING_FAILURE_PATH.is_file():
            restarts += 1
            if restarts > max_restarts:
                raise BeamExplorationError(
                    f"Embedding population failed after {max_restarts} local restarts"
                )
            environment = dict(os.environ)
            environment.pop("OPENAI_API_KEY", None)
            completed = subprocess.run(
                [sys.executable, "-m", "analysis.beam001_gpu_embedding", "populate"],
                cwd=REPO_ROOT,
                env=environment,
                check=False,
            )
            if completed.returncode == 0:
                continue
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "run",
            "shard",
            "parallel-run",
            "shuffle-shard",
            "parallel-shuffle",
            "wait-and-run",
            "resume-and-run",
        ),
    )
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--max-restarts", type=int, default=3)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--workers", type=int, default=8)
    arguments = parser.parse_args()
    if arguments.command == "run":
        result = run()
    elif arguments.command == "shard":
        result = run_shard(arguments.shard_index, arguments.shard_count)
    elif arguments.command == "parallel-run":
        result = parallel_run(arguments.workers)
    elif arguments.command == "shuffle-shard":
        result = run_shuffle_shard(arguments.shard_index, arguments.shard_count)
    elif arguments.command == "parallel-shuffle":
        result = parallel_shuffle_replay(arguments.workers)
    elif arguments.command == "wait-and-run":
        result = wait_and_run(arguments.interval_seconds)
    else:
        result = resume_and_run(arguments.interval_seconds, arguments.max_restarts)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
