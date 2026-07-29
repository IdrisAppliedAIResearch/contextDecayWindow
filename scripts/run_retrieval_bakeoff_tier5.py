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
import gc
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

from src.retrieval_bakeoff.ann import (
    SCALES,
    benchmark_ann,
    build_scaled_vector_store,
)
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
from src.retrieval_bakeoff.harness import RetrievalHarness
from src.retrieval_bakeoff.leakage import (
    assert_planted_violations,
    audit_import_graph,
    guard_measurement_files,
)
from src.retrieval_bakeoff.models import RetrievalResult
from src.retrieval_bakeoff.progressive import ARM_SPECS, ProgressiveIndex
from src.retrieval_bakeoff.tier5_analysis import analyze_tier5


REGISTRATION_ANCHOR = "b60b7084741eb5d30298261076b4bca78abe713a"
PROTOCOL_ANCHOR = "d6d80fbb"
CORRECTED_TIER1_3_ANCHOR = "f3e9735b"
TIER4_RESULT_ANCHOR = "9ea96278"
TIER5_PROTOCOL_ANCHOR = "ade5741b"
TIER5_SCOPE_ANCHOR = "673bfcfa"
HNSW_DEPENDENCY_ANCHOR = "43df4223"
PRIMARY_CORPORA = ("c121_l", "c1000_l")
BUDGETS = (32_000, 64_000, 160_000, 320_000)
REPETITIONS = 9
OUTPUT_ROOT = SURVEY_ROOT / "tier5"
SETTINGS_PATH = (
    SURVEY_ROOT / "settings" / "tier5_execution_settings.json"
)
CORRECTED_ANALYSIS = (
    SURVEY_ROOT
    / "corrections"
    / "amendment_002"
    / "corrected_analysis.json"
)
TIER4_EVALUATION = (
    SURVEY_ROOT / "tier4" / "tier4a_evaluation_results.jsonl"
)
TIER4_RESULTS = SURVEY_ROOT / "tier4" / "tier4a_results.json"
MECHANISM_ENTRY_POINTS = [
    REPO_ROOT / "src" / "retrieval_bakeoff" / name
    for name in (
        "ann.py",
        "classifier.py",
        "config.py",
        "corpus.py",
        "embedding.py",
        "harness.py",
        "methods.py",
        "models.py",
        "progressive.py",
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
    _event(events, "Tier 5 pre-run gates")
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    corrected = json.loads(CORRECTED_ANALYSIS.read_text(encoding="utf-8"))
    tier4 = json.loads(TIER4_RESULTS.read_text(encoding="utf-8"))
    _validate_settings(settings, corrected, tier4)
    locked_hashes_before = validate_locked_artifacts()
    static_audit = audit_import_graph(MECHANISM_ENTRY_POINTS)
    with tempfile.TemporaryDirectory(prefix="retrieval-bakeoff-leakage-") as temp:
        planted_audit = assert_planted_violations(Path(temp))

    source_paths = _source_paths()
    source_hashes_before = _hash_files(source_paths)
    embedder = CarriedEmbedder(args.embedding_model)
    embedder.assert_carried_model()
    embedder.warmup()

    budget_retrieval: list[dict] = []
    budget_evaluation: list[dict] = []
    progressive_retrieval: list[dict] = []
    progressive_evaluation: list[dict] = []
    ann_results: list[dict] = []
    ann_provenance: list[dict] = []
    axis_reports: dict[str, dict] = {}
    arm_statuses: dict[str, dict] = {}
    observed_open_count = 0

    _event(events, "T5.0 fixed-policy budget multiples")
    for corpus_id in PRIMARY_CORPORA:
        spec = CORPORA[corpus_id]
        with guard_measurement_files() as observed:
            queries = load_queries(spec)
            corpus_results = []
            with RetrievalHarness(spec, embedder=embedder) as harness:
                harness.build("M3")
                for budget in BUDGETS:
                    _event(events, f"T5.0 {corpus_id} budget {budget}")
                    corpus_results.extend(
                        harness.retrieve(
                            "M3",
                            query,
                            budget=budget,
                            repetitions=REPETITIONS,
                        )
                        for query in queries
                    )
        observed_open_count += len(observed)
        evaluator = HoldoutEvaluator(corpus_id)
        for result in corpus_results:
            budget_retrieval.append(_retrieval_record(result))
            budget_evaluation.append(evaluator.evaluate(result))

    _event(events, "T5.1 exact-cosine versus HNSW")
    ann_spec = CORPORA["c1000_l"]
    with tempfile.TemporaryDirectory(prefix="retrieval-bakeoff-hnsw-") as temp:
        with guard_measurement_files() as observed:
            ann_candidates = load_raw_episodes(ann_spec)
            ann_queries = load_queries(ann_spec)
            query_vectors = [embedder(query.text) for query in ann_queries]
            for scale in SCALES:
                _event(events, f"T5.1 ANN scale {scale}")
                store = build_scaled_vector_store(ann_candidates, scale)
                ann_provenance.extend(store.provenance_rows())
                ann_results.append(
                    benchmark_ann(
                        store,
                        query_vectors,
                        Path(temp),
                    )
                )
                del store
                gc.collect()
        observed_open_count += len(observed)

    _event(events, "T5.2-T5.3 progressive and orthogonal tiers")
    for corpus_id in PRIMARY_CORPORA:
        spec = CORPORA[corpus_id]
        with guard_measurement_files() as observed:
            candidates = load_raw_episodes(spec)
            queries = load_queries(spec)
            index = ProgressiveIndex(spec, candidates)
            statuses = index.arm_statuses()
            corpus_outcomes = []
            for arm_id in ARM_SPECS:
                if statuses[arm_id]["status"] != "EVALUABLE":
                    _event(
                        events,
                        f"T5.3 {corpus_id} {arm_id} NOT_EVALUABLE",
                    )
                    continue
                _event(events, f"T5.2-T5.3 {corpus_id} {arm_id}")
                corpus_outcomes.extend(
                    index.retrieve(
                        arm_id,
                        query,
                        embedder,
                        repetitions=REPETITIONS,
                    )
                    for query in queries
                )
        observed_open_count += len(observed)
        axis_reports[corpus_id] = {
            **index.axes.report,
            "axis_validation_ms": index.axis_validation_ms,
            "total_index_build_ms": index.total_index_build_ms,
            "tier_counts": index.tier_counts,
        }
        arm_statuses[corpus_id] = statuses
        evaluator = HoldoutEvaluator(corpus_id)
        for outcome in corpus_outcomes:
            record = _retrieval_record(outcome.result)
            record.update(_progressive_metadata(outcome))
            progressive_retrieval.append(record)
            row = evaluator.evaluate(outcome.result)
            row.update(_progressive_metadata(outcome))
            progressive_evaluation.append(row)

    if len(budget_evaluation) != 2 * len(BUDGETS) * 24:
        raise AssertionError("T5.0 row count is incomplete")
    if len(ann_results) != len(SCALES):
        raise AssertionError("T5.1 scale count is incomplete")
    if len(ann_provenance) != sum(SCALES):
        raise AssertionError("T5.1 row provenance is incomplete")
    if len(progressive_evaluation) != 120:
        raise AssertionError(
            "Expected 96 c121 and 24 c1000 progressive rows"
        )

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
        raise RuntimeError("Locked holdout artifacts changed during Tier 5")

    graph_rows = _read_jsonl(TIER4_EVALUATION)
    analysis = analyze_tier5(
        budget_rows=budget_evaluation,
        progressive_rows=progressive_evaluation,
        graph_rows=graph_rows,
        ann_results=ann_results,
        axis_reports=axis_reports,
    )
    payload = {
        "tier": "T5",
        "status": "COMPLETE",
        "evidence_class": "registered",
        "query_set": "holdout",
        "registration_anchor": REGISTRATION_ANCHOR,
        "protocol_anchor": PROTOCOL_ANCHOR,
        "corrected_tier1_3_anchor": CORRECTED_TIER1_3_ANCHOR,
        "tier4_result_anchor": TIER4_RESULT_ANCHOR,
        "tier5_protocol_anchor": TIER5_PROTOCOL_ANCHOR,
        "tier5_scope_anchor": TIER5_SCOPE_ANCHOR,
        "hnsw_dependency_anchor": HNSW_DEPENDENCY_ANCHOR,
        "code_commit": _git("rev-parse", "HEAD"),
        "seed": SEED,
        "settings": settings,
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
        "arm_statuses": arm_statuses,
        "analysis": analysis,
    }
    _event(events, "Tier 5 analysis complete")
    _write_outputs(
        payload=payload,
        budget_retrieval=budget_retrieval,
        budget_evaluation=budget_evaluation,
        ann_results=ann_results,
        ann_provenance=ann_provenance,
        progressive_retrieval=progressive_retrieval,
        progressive_evaluation=progressive_evaluation,
        events=events,
    )
    return 0


def _progressive_metadata(outcome) -> dict:
    return {
        "searched_tiers": outcome.searched_tiers,
        "stop_reason": outcome.stop_reason,
        "selected_topic_id": outcome.selected_topic_id,
        "searched_candidate_count": outcome.searched_candidate_count,
        "best_searched_cosine": outcome.best_searched_cosine,
        "tier_timings": outcome.tier_timings,
    }


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
    return sorted(
        {
            SETTINGS_PATH,
            CORRECTED_ANALYSIS,
            TIER4_EVALUATION,
            TIER4_RESULTS,
            REPO_ROOT / "pyproject.toml",
            REPO_ROOT / "uv.lock",
            *(
                CORPORA[corpus_id].database_path
                for corpus_id in PRIMARY_CORPORA
            ),
        }
    )


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


def _read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _write_outputs(
    *,
    payload: dict,
    budget_retrieval: list[dict],
    budget_evaluation: list[dict],
    ann_results: list[dict],
    ann_provenance: list[dict],
    progressive_retrieval: list[dict],
    progressive_evaluation: list[dict],
    events: list[str],
) -> None:
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"Refusing to overwrite registered output: {OUTPUT_ROOT}")
    OUTPUT_ROOT.mkdir(parents=True)
    _write_json(OUTPUT_ROOT / "tier5_results.json", payload)
    _write_jsonl(
        OUTPUT_ROOT / "t5_0_retrieval_results.jsonl",
        budget_retrieval,
    )
    _write_jsonl(
        OUTPUT_ROOT / "t5_0_evaluation_results.jsonl",
        budget_evaluation,
    )
    _write_json(
        OUTPUT_ROOT / "t5_1_ann_results.json",
        {"status": "COMPLETE", "scales": ann_results},
    )
    _write_jsonl(
        OUTPUT_ROOT / "t5_1_ann_row_provenance.jsonl",
        ann_provenance,
    )
    _write_jsonl(
        OUTPUT_ROOT / "t5_2_3_progressive_retrieval_results.jsonl",
        progressive_retrieval,
    )
    _write_jsonl(
        OUTPUT_ROOT / "t5_2_3_progressive_evaluation_results.jsonl",
        progressive_evaluation,
    )
    (OUTPUT_ROOT / "tier5_report.md").write_text(
        _report(payload),
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "tier5_execution.log").write_text(
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
    budget = analysis["T5.0_budget_multiples"]
    lines = [
        "# Retrieval Bakeoff Tier 5 Report",
        "",
        f"**Status:** {payload['status']}",
        "",
        "## T5.0 Budget Multiples",
        "",
        "| Budget | Recall | Coverage | Chars | Selected |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in budget["overall_by_budget"]:
        lines.append(
            f"| {row['budget']} | {row['fact_recall_exact']} | "
            f"{row['domain_coverage']:.4f} | "
            f"{row['delivered_characters']:.1f} | "
            f"{row['selected_count']:.1f} |"
        )
    lines.extend(
        [
            "",
            "Fact-recall collapse above 2x: "
            f"**{budget['fact_recall_collapse_above_2x']}**.",
            "",
            "## T5.1 ANN",
            "",
            "| Scale | Synthetic | R@10 | R@50 | Exact ms | HNSW ms | "
            "Build ms | Index MiB |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in analysis["T5.1_ann"]["scales"]:
        lines.append(
            f"| {row['scale']} | {row['synthetic_rows']} | "
            f"{row['recall_at_10']:.4f} | {row['recall_at_50']:.4f} | "
            f"{row['exact_query_median_ns'] / 1e6:.3f} | "
            f"{row['hnsw_query_median_ns'] / 1e6:.3f} | "
            f"{row['build_ms']:.1f} | "
            f"{row['index_bytes'] / 1024 / 1024:.2f} |"
        )
    lines.extend(
        [
            "",
            "## T5.2-T5.3 Progressive Search",
            "",
            "| Arm | Queries | Recall | Old miss | Latency ms |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in analysis["T5.2_progressive_search"]["overall_by_arm"]:
        lines.append(
            f"| {row['method_id']} | {row['query_count']} | "
            f"{row['fact_recall_exact']} | "
            f"{row['old_fact_miss_rate_exact']} | "
            f"{row['latency_ms']:.3f} |"
        )
    lines.extend(["", "### Axis Validation", ""])
    for corpus_id, report in analysis["T5.3_axis_validation"].items():
        lines.append(
            f"- `{corpus_id}` topic: "
            f"`{report['topic_axis']['status']}`; pinned rules: "
            f"`{report['pinned_rule_axis']['status']}`."
        )
    comparison = analysis["T5.4_tiering_comparison"]
    lines.extend(
        [
            "",
            "## T5.4 Tiering Comparison",
            "",
            "Any depth configuration matches or beats a partition arm on "
            "recall, latency, and old-fact miss jointly: "
            f"**{comparison['any_depth_matches_or_beats_partition']}**.",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_settings(
    settings: dict,
    corrected: dict,
    tier4: dict,
) -> None:
    if settings["status"] != "LOCKED_BEFORE_TIER5_IMPLEMENTATION":
        raise AssertionError("Tier 5 settings are not locked")
    if settings["fixed_policy"]["method_id"] != "M3":
        raise AssertionError("Tier 5 fixed policy changed")
    if tuple(settings["T5.0"]["budgets"]) != BUDGETS:
        raise AssertionError("Tier 5 budgets changed")
    if tuple(settings["T5.1"]["scales"]) != SCALES:
        raise AssertionError("Tier 5 ANN scales changed")
    if settings["T5.1"]["hnswlib_version"] != "0.8.0":
        raise AssertionError("Tier 5 HNSW version changed")
    advancing = {
        row["method_id"]
        for row in corrected["T2_corrected_summary"]["advancement"]
        if row["advances"]
    }
    if "M3" not in advancing:
        raise AssertionError("Locked Tier 2 evidence no longer advances M3")
    pooled = corrected["T2_corrected_summary"]["pooled_class"]
    eligible_recall = {}
    for method_id in advancing:
        rows = [row for row in pooled if row["method_id"] == method_id]
        eligible_recall[method_id] = sum(
            (Fraction(row["fact_recall_exact"]) for row in rows),
            Fraction(),
        ) / len(rows)
    winner = sorted(
        eligible_recall,
        key=lambda method_id: (-eligible_recall[method_id], method_id),
    )[0]
    if winner != "M3" or eligible_recall[winner] != Fraction(67, 96):
        raise AssertionError("Tier 5 fixed-policy derivation changed")
    if tier4["analysis"]["gate_passes"]:
        raise AssertionError("Tier 4 unexpectedly contains an advancing graph")


def _runtime_metadata() -> dict:
    return {
        "argv": [sys.executable, *sys.argv],
        "pid": os.getpid(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"),
        "hnswlib": importlib.metadata.version("hnswlib"),
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
        raise RuntimeError("Registered Tier 5 requires a clean worktree")
    if _git("branch", "--show-current") != "retrieval-bakeoff":
        raise RuntimeError("Registered Tier 5 must run on retrieval-bakeoff")
    for anchor in (
        REGISTRATION_ANCHOR,
        PROTOCOL_ANCHOR,
        CORRECTED_TIER1_3_ANCHOR,
        TIER4_RESULT_ANCHOR,
        TIER5_PROTOCOL_ANCHOR,
        TIER5_SCOPE_ANCHOR,
        HNSW_DEPENDENCY_ANCHOR,
    ):
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", anchor, "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"Registered Tier 5 output exists: {OUTPUT_ROOT}")


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
