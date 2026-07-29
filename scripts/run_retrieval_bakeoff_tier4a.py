from __future__ import annotations

import os

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from src.retrieval_bakeoff.config import (
    CORPORA,
    REPO_ROOT,
    SEED,
    SURVEY_ROOT,
)
from src.retrieval_bakeoff.corpus import load_queries, load_raw_episodes
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_bakeoff.evaluation import (
    HoldoutEvaluator,
    validate_locked_artifacts,
)
from src.retrieval_bakeoff.graph import (
    GRAPH_CONFIGS,
    AssociativeGraphIndex,
    GraphRetriever,
)
from src.retrieval_bakeoff.graph_analysis import analyze_graph_results
from src.retrieval_bakeoff.graph_benchmark import (
    run_incremental_update_benchmark,
)
from src.retrieval_bakeoff.leakage import (
    assert_planted_violations,
    audit_import_graph,
    guard_measurement_files,
)
from src.retrieval_bakeoff.models import RetrievalResult


REGISTRATION_ANCHOR = "b60b7084741eb5d30298261076b4bca78abe713a"
HOLDOUT_ANCHOR = "23b9bb99"
PROTOCOL_ANCHOR = "d6d80fbb"
CORRECTED_TIER1_3_ANCHOR = "f3e9735b"
GRAPH_PROTOCOL_ANCHOR = "6938e379"
TIER2_EVALUATION = SURVEY_ROOT / "tier2" / "evaluation_results.jsonl"
CORRECTED_ANALYSIS = (
    SURVEY_ROOT
    / "corrections"
    / "amendment_002"
    / "corrected_analysis.json"
)
OUTPUT_ROOT = SURVEY_ROOT / "tier4"
PRIMARY_CORPORA = ("c121_l", "c1000_l")
DEPTHS = (1, 2, 3)
REPETITIONS = 9
MECHANISM_ENTRY_POINTS = [
    REPO_ROOT / "src" / "retrieval_bakeoff" / name
    for name in (
        "config.py",
        "corpus.py",
        "embedding.py",
        "graph.py",
        "graph_benchmark.py",
        "models.py",
        "serialization.py",
    )
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding-model", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _assert_ready()
    events: list[str] = []
    _event(events, "T4A pre-run gates")
    locked_hashes_before = validate_locked_artifacts()
    static_audit = audit_import_graph(MECHANISM_ENTRY_POINTS)
    with tempfile.TemporaryDirectory(prefix="retrieval-bakeoff-leakage-") as temp:
        planted_audit = assert_planted_violations(Path(temp))

    source_paths = _source_paths()
    source_hashes_before = _hash_files(source_paths)
    embedder = CarriedEmbedder(args.embedding_model)
    embedder.assert_carried_model()
    embedder.warmup()

    retrieval_records: list[dict] = []
    evaluation_rows: list[dict] = []
    graph_statistics: dict[str, dict] = {}
    update_benchmark: dict | None = None
    observed_open_count = 0

    for corpus_id in PRIMARY_CORPORA:
        spec = CORPORA[corpus_id]
        _event(events, f"T4A graph build {corpus_id}")
        with guard_measurement_files() as observed:
            graph = AssociativeGraphIndex(spec, load_raw_episodes(spec))
            queries = load_queries(spec)
            retriever = GraphRetriever(graph, embedder)
            corpus_results = []
            for config_id in GRAPH_CONFIGS:
                for depth in DEPTHS:
                    _event(
                        events,
                        f"T4A {corpus_id} {config_id} depth {depth}",
                    )
                    corpus_results.extend(
                        retriever.retrieve(
                            config_id,
                            depth,
                            query,
                            repetitions=REPETITIONS,
                        )
                        for query in queries
                    )
            if corpus_id == "c1000_l":
                _event(events, "T4A synthetic incremental-update benchmark")
                update_benchmark = run_incremental_update_benchmark(graph)
        observed_open_count += len(observed)
        graph_statistics[corpus_id] = graph.statistics()

        evaluator = HoldoutEvaluator(corpus_id)
        for result in corpus_results:
            if result.delivered_characters > result.budget:
                raise AssertionError("T4A serialized block exceeded its budget")
            retrieval_records.append(_retrieval_record(result))
            evaluation_rows.append(evaluator.evaluate(result))

    expected_rows = (
        len(PRIMARY_CORPORA)
        * len(GRAPH_CONFIGS)
        * len(DEPTHS)
        * 24
    )
    if len(retrieval_records) != expected_rows:
        raise AssertionError(
            f"Expected {expected_rows} T4A rows, got {len(retrieval_records)}"
        )
    if update_benchmark is None:
        raise AssertionError("T4A update benchmark did not run")

    source_hashes_after = _hash_files(source_paths)
    changed_sources = sorted(
        path
        for path in source_hashes_before.keys() | source_hashes_after.keys()
        if source_hashes_before.get(path) != source_hashes_after.get(path)
    )
    if changed_sources:
        raise RuntimeError(f"Read-only source artifacts changed: {changed_sources}")
    locked_hashes_after = validate_locked_artifacts()
    if locked_hashes_before != locked_hashes_after:
        raise RuntimeError("Locked holdout artifacts changed during T4A")

    corrected = json.loads(CORRECTED_ANALYSIS.read_text(encoding="utf-8"))
    baseline_rows = _baseline_old_fact_rows()
    analysis = analyze_graph_results(
        evaluation_rows,
        tier2_corrected_summary=corrected["T2_corrected_summary"],
        baseline_rows=baseline_rows,
        update_benchmark=update_benchmark,
    )
    t4b_status = (
        "GATE_OPEN"
        if analysis["gate_passes"]
        else "CLOSED_NOT_RUN_BY_BINDING_GATE"
    )
    payload = {
        "test": "T4A",
        "status": "COMPLETE",
        "evidence_class": "registered",
        "query_set": "holdout",
        "registration_anchor": REGISTRATION_ANCHOR,
        "holdout_anchor": HOLDOUT_ANCHOR,
        "protocol_anchor": PROTOCOL_ANCHOR,
        "corrected_tier1_3_anchor": CORRECTED_TIER1_3_ANCHOR,
        "graph_protocol_anchor": GRAPH_PROTOCOL_ANCHOR,
        "code_commit": _git("rev-parse", "HEAD"),
        "seed": SEED,
        "budget": 32_000,
        "depths": list(DEPTHS),
        "benchmark_repetitions": REPETITIONS,
        "runtime": _runtime_metadata(),
        "model_path": str(embedder.model_path),
        "model_sha256": embedder.model_sha256,
        "locked_hashes_before": locked_hashes_before,
        "locked_hashes_after": locked_hashes_after,
        "static_leakage_audit": static_audit,
        "planted_leakage_audit": planted_audit,
        "runtime_guard_open_count": observed_open_count,
        "source_hashes_before": source_hashes_before,
        "source_hashes_after": source_hashes_after,
        "graph_statistics": graph_statistics,
        "incremental_update_benchmark": update_benchmark,
        "analysis": analysis,
        "T4B_status": t4b_status,
    }
    _event(events, f"T4A gate result: {t4b_status}")
    _write_outputs(
        payload,
        retrieval_records,
        evaluation_rows,
        baseline_rows,
        events,
    )
    return 0


def _baseline_old_fact_rows() -> list[dict]:
    evaluators = {
        corpus_id: HoldoutEvaluator(corpus_id)
        for corpus_id in PRIMARY_CORPORA
    }
    rows = []
    with TIER2_EVALUATION.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if (
                row["method_id"] != "M1"
                or row["corpus_id"] not in PRIMARY_CORPORA
            ):
                continue
            old_metrics = evaluators[row["corpus_id"]].old_fact_metrics(
                row["query_id"],
                row["matched_fact_ids"],
            )
            rows.append({**row, **old_metrics})
    if len(rows) != len(PRIMARY_CORPORA) * 24:
        raise AssertionError("Expected 48 primary-corpus M1 baseline rows")
    return rows


def _retrieval_record(result: RetrievalResult) -> dict:
    return {
        "evidence_class": "registered",
        "query_set": "holdout",
        "corpus_id": result.corpus_id,
        "method_id": result.method_id,
        "query_id": result.query.query_id,
        "query_text": result.query.text,
        "budget": result.budget,
        "ranked_count": result.ranked_count,
        "selected_count": len(result.selected),
        "delivered_characters": result.delivered_characters,
        "rendered_sha256": hashlib.sha256(
            result.rendered_block.encode("utf-8")
        ).hexdigest(),
        "rendered_block": result.rendered_block,
        "selected": [
            {
                "candidate_id": item.candidate.candidate_id,
                "source_episode_id": item.candidate.source_episode_id,
                "turn_number": item.candidate.turn_number,
                "unit_type": item.candidate.unit_type,
                "score": item.score,
                "component_scores": item.component_scores,
                "phase": result.phases.get(item.candidate.rendered_identity),
            }
            for item in result.selected
        ],
        "skipped_oversized": result.skipped_oversized,
        "duplicate_drops": result.duplicate_drops,
        "query_encode_ms": result.query_encode_ms,
        "rank_ms": result.rank_ms,
        "pack_ms": result.pack_ms,
        "rank_pack_ms": result.rank_pack_ms,
        "latency_ms": result.latency_ms,
        "index_build_ms": result.index_build_ms,
        "benchmark_repetitions": result.benchmark_repetitions,
    }


def _source_paths() -> list[Path]:
    paths = {TIER2_EVALUATION, CORRECTED_ANALYSIS}
    for corpus_id in PRIMARY_CORPORA:
        spec = CORPORA[corpus_id]
        paths.add(spec.database_path)
        prompt_root = spec.run_directory / "constructed_prompts"
        prompts = [
            prompt_root / f"turn_{turn:03d}.txt"
            for turn in range(
                spec.eligible_turn_min,
                spec.eligible_turn_max + 1,
            )
        ]
        if not all(path.is_file() for path in prompts):
            raise FileNotFoundError(
                f"Missing eligible constructed prompt for {corpus_id}"
            )
        paths.update(prompts)
    return sorted(paths)


def _hash_files(paths: list[Path]) -> dict[str, str]:
    result = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        result[str(path.relative_to(REPO_ROOT))] = digest.hexdigest()
    return result


def _write_outputs(
    payload: dict,
    retrieval_records: list[dict],
    evaluation_rows: list[dict],
    baseline_rows: list[dict],
    events: list[str],
) -> None:
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"Refusing to overwrite registered output: {OUTPUT_ROOT}")
    OUTPUT_ROOT.mkdir(parents=True)
    _write_json(OUTPUT_ROOT / "tier4a_results.json", payload)
    _write_jsonl(OUTPUT_ROOT / "tier4a_retrieval_results.jsonl", retrieval_records)
    _write_jsonl(OUTPUT_ROOT / "tier4a_evaluation_results.jsonl", evaluation_rows)
    _write_jsonl(OUTPUT_ROOT / "tier4a_m1_old_fact_baseline.jsonl", baseline_rows)
    (OUTPUT_ROOT / "tier4a_report.md").write_text(
        _report(payload),
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "tier4a_execution.log").write_text(
        "\n".join(events) + "\n",
        encoding="utf-8",
    )


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _report(payload: dict) -> str:
    analysis = payload["analysis"]
    lines = [
        "# Retrieval Bakeoff Tier 4A Report",
        "",
        f"**Status:** {payload['status']}",
        "",
        f"**T4B gate:** {payload['T4B_status']}",
        "",
        "## Graph Structure",
        "",
        "| Corpus | Edge | Nodes | Edges | Density | Build ms | Update ns |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for corpus_id, corpus in payload["graph_statistics"].items():
        for component_id, component in corpus["components"].items():
            lines.append(
                f"| {corpus_id} | {component_id} | "
                f"{corpus['node_count']} | "
                f"{component['undirected_edge_count']} | "
                f"{component['density']:.6f} | "
                f"{component['build_ms']:.3f} | "
                f"{component['actual_update_median_ns']:.1f} |"
            )
    lines.extend(
        [
            "",
            "## Advancement",
            "",
            "| Method | Recall gate | Update gate | Advances | Wins | Regressions |",
            "|---|---:|---:|---:|---|---|",
        ]
    )
    for row in analysis["advancement"]:
        lines.append(
            f"| {row['method_id']} | {row['recall_pass']} | "
            f"{row['update_cost_pass']} | {row['advances']} | "
            f"{','.join(row['winning_classes']) or 'none'} | "
            f"{','.join(row['regressing_classes']) or 'none'} |"
        )
    lines.extend(
        [
            "",
            "## Update Slopes",
            "",
            "| Edge | Log-log slope | Passes <= 1.10 |",
            "|---|---:|---:|",
        ]
    )
    for component_id, row in payload[
        "incremental_update_benchmark"
    ]["component_slopes"].items():
        lines.append(
            f"| {component_id} | {row['log10_slope']:.6f} | "
            f"{row['passes_at_most_1_10']} |"
        )
    lines.extend(
        [
            "",
            "All retrieval rows use the registered holdout, exact 32,000-character "
            "serializer, and nine measured rank-plus-pack repetitions after one "
            "warm-up. E4 is descriptive and cannot open T4B.",
            "",
        ]
    )
    return "\n".join(lines)


def _runtime_metadata() -> dict:
    return {
        "argv": [sys.executable, *sys.argv],
        "pid": os.getpid(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"),
        "llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
        "thread_environment": {
            name: os.environ[name]
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
    }


def _event(events: list[str], message: str) -> None:
    events.append(message)
    print(message, flush=True)


def _assert_ready() -> None:
    if _git("status", "--porcelain"):
        raise RuntimeError("Registered T4A requires a clean worktree")
    if _git("branch", "--show-current") != "retrieval-bakeoff":
        raise RuntimeError("Registered T4A must run on retrieval-bakeoff")
    for anchor in (
        REGISTRATION_ANCHOR,
        HOLDOUT_ANCHOR,
        PROTOCOL_ANCHOR,
        CORRECTED_TIER1_3_ANCHOR,
        GRAPH_PROTOCOL_ANCHOR,
    ):
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", anchor, "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"Registered T4A output already exists: {OUTPUT_ROOT}")


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
