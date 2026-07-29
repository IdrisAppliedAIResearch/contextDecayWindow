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
import csv
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import tempfile
from pathlib import Path

from src.retrieval_bakeoff.config import (
    CACHE_ROOT,
    CORPORA,
    REPO_ROOT,
    SURVEY_ROOT,
)
from src.retrieval_bakeoff.corpus import load_queries
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_bakeoff.evaluation import (
    HoldoutEvaluator,
    aggregate_rows,
    validate_locked_artifacts,
)
from src.retrieval_bakeoff.harness import RetrievalHarness
from src.retrieval_bakeoff.k_collapse import (
    SCRIPT_PATH,
    STORES as K_COLLAPSE_STORES,
    run_k_collapse_diagnostic,
)
from src.retrieval_bakeoff.leakage import (
    assert_planted_violations,
    audit_import_graph,
    guard_measurement_files,
)
from src.retrieval_bakeoff.methods import METHOD_IDS
from src.retrieval_bakeoff.models import Query, RetrievalResult
from src.retrieval_bakeoff.presence import (
    Q11_KEY_PATH,
    RAW_1000_STORES,
    RAW_121_STORES,
    STUDY_010_KEY_PATH,
    evaluate_q11_reachability,
    run_presence_inventory,
)
from src.retrieval_bakeoff.tier3_analysis import analyze_tier3


REGISTRATION_ANCHOR = "b60b7084741eb5d30298261076b4bca78abe713a"
HOLDOUT_ANCHOR = "23b9bb99"
PROTOCOL_ANCHOR = "d6d80fbb"
TIER0_ANCHOR = "a615c3a8"
MECHANISM_ENTRY_POINTS = [
    REPO_ROOT / "src" / "retrieval_bakeoff" / name
    for name in (
        "classifier.py",
        "config.py",
        "corpus.py",
        "embedding.py",
        "embedding_cache.py",
        "harness.py",
        "methods.py",
        "models.py",
        "serialization.py",
    )
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding-model", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=9)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _assert_ready()
    locked_hashes = validate_locked_artifacts()
    static_audit = audit_import_graph(MECHANISM_ENTRY_POINTS)
    with tempfile.TemporaryDirectory(prefix="retrieval-bakeoff-leakage-") as temp:
        planted_audit = assert_planted_violations(Path(temp))

    source_paths = _source_paths()
    source_hashes_before = _hash_files(source_paths)
    embedder = CarriedEmbedder(args.embedding_model)
    embedder.assert_carried_model()
    embedder.warmup()

    print("T1.1 presence inventory", flush=True)
    presence = run_presence_inventory()
    print("T1.3 K-collapse diagnostic", flush=True)
    k_collapse = run_k_collapse_diagnostic(embedder)

    retrieval_records: list[dict] = []
    evaluation_rows: list[dict] = []
    q11_rows: list[dict] = []
    observed_open_count = 0
    q11_query = _q11_query()

    for corpus_id, spec in CORPORA.items():
        method_ids = (
            METHOD_IDS
            if spec.has_distilled_ltm
            else tuple(method for method in METHOD_IDS if method != "M1")
        )
        corpus_results: list[RetrievalResult] = []
        q11_results: list[RetrievalResult] = []
        with guard_measurement_files() as observed:
            queries = load_queries(spec)
            for method_id in method_ids:
                print(f"Tier 2 {corpus_id} {method_id}", flush=True)
                with RetrievalHarness(spec, embedder=embedder) as harness:
                    harness.build(method_id)
                    if corpus_id.startswith("c121") and method_id != "M1":
                        q11_results.append(
                            harness.retrieve(
                                method_id,
                                q11_query,
                                repetitions=args.repetitions,
                            )
                        )
                    corpus_results.extend(
                        harness.retrieve(
                            method_id,
                            query,
                            repetitions=args.repetitions,
                        )
                        for query in queries
                    )
        observed_open_count += len(observed)

        evaluator = HoldoutEvaluator(corpus_id)
        for result in corpus_results:
            retrieval_records.append(_retrieval_record(result))
            evaluation_rows.append(evaluator.evaluate(result))
        for result in q11_results:
            q11_rows.append(evaluate_q11_reachability(result))

    source_hashes_after = _hash_files(source_paths)
    changed_sources = sorted(
        path
        for path in source_hashes_before.keys() | source_hashes_after.keys()
        if source_hashes_before.get(path) != source_hashes_after.get(path)
    )
    if changed_sources:
        raise RuntimeError(f"Read-only source artifacts changed: {changed_sources}")

    tier2_summary = aggregate_rows(evaluation_rows)
    tier3 = analyze_tier3(evaluation_rows, tier2_summary)
    q11_ceiling = sorted(
        (
            row for row in q11_rows if row["corpus_id"] == "c121_l"
        ),
        key=lambda row: (
            -row["matched_fact_count"],
            row["delivered_characters"],
            row["method_id"],
        ),
    )[0]
    tier1 = {
        "evidence_class": "registered",
        "presence": presence,
        "reachability": {
            "test_id": "T1.2",
            "query_set": "development",
            "rows": q11_rows,
            "primary_ceiling": q11_ceiling,
            "pivotal_outcome": (
                "breadth_is_an_engineering_problem"
                if q11_ceiling["reaches_14_of_17"]
                else "capture_or_budget_is_the_constraint"
            ),
        },
        "k_collapse": k_collapse,
    }
    metadata = {
        "registration_anchor": REGISTRATION_ANCHOR,
        "holdout_anchor": HOLDOUT_ANCHOR,
        "protocol_anchor": PROTOCOL_ANCHOR,
        "tier0_anchor": TIER0_ANCHOR,
        "code_commit": _git("rev-parse", "HEAD"),
        "command": (
            ".venv\\Scripts\\python.exe "
            "scripts\\run_retrieval_bakeoff_tiers_1_3.py "
            f"--embedding-model {args.embedding_model} "
            f"--repetitions {args.repetitions}"
        ),
        "model_path": str(embedder.model_path),
        "model_sha256": embedder.model_sha256,
        "threading": {
            "llama_cpp_n_threads": 1,
            "llama_cpp_n_threads_batch": 1,
            **{
                name: os.environ[name]
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "numpy": importlib.metadata.version("numpy"),
            "llama_cpp_python": importlib.metadata.version("llama-cpp-python"),
        },
        "locked_artifact_hashes": locked_hashes,
        "source_hashes_before": source_hashes_before,
        "source_hashes_after": source_hashes_after,
        "changed_source_files": changed_sources,
        "leakage": {
            "static": static_audit,
            "planted": planted_audit,
            "runtime_observed_open_count": observed_open_count,
            "status": "PASS",
        },
    }
    provenance_violations = sum(
        bool(row["provenance_violations"]) for row in evaluation_rows
    )
    tier2_payload = {
        "evidence_class": "registered",
        "query_set": "holdout",
        "status": (
            "COMPLETE"
            if not provenance_violations
            else "COMPLETE_WITH_PROVENANCE_VIOLATIONS"
        ),
        "query_result_count": len(evaluation_rows),
        "provenance_violation_query_count": provenance_violations,
        "summary": tier2_summary,
        "metadata": metadata,
    }
    tier3_payload = {
        "evidence_class": "registered",
        "query_set": "holdout",
        "status": "COMPLETE",
        "analysis": tier3,
        "metadata": metadata,
    }

    _write_outputs(
        tier1=tier1,
        tier2=tier2_payload,
        tier3=tier3_payload,
        retrieval_records=retrieval_records,
        evaluation_rows=evaluation_rows,
    )
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "tier2_rows": len(evaluation_rows),
                "q11_ceiling": q11_ceiling["matched_fact_count"],
            }
        ),
        flush=True,
    )
    return 0


def _q11_query() -> Query:
    payload = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    row = next(item for item in payload["turns"] if int(item["turn"]) == 120)
    return Query(query_id="development_q11_turn_120", text=str(row["user"]))


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
    paths = {
        spec.database_path for spec in CORPORA.values()
    }
    paths.update(RAW_121_STORES.values())
    paths.update(RAW_1000_STORES.values())
    paths.update(run / "study.db" for run in K_COLLAPSE_STORES.values())
    paths.update(run / "logs" / "retrieval.jsonl" for run in K_COLLAPSE_STORES.values())
    paths.update(
        {
            SCRIPT_PATH,
            Q11_KEY_PATH,
            STUDY_010_KEY_PATH,
        }
    )
    return sorted(paths)


def _hash_files(paths: list[Path]) -> dict[str, str]:
    result = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        result[str(path.relative_to(REPO_ROOT))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return result


def _write_outputs(
    *,
    tier1: dict,
    tier2: dict,
    tier3: dict,
    retrieval_records: list[dict],
    evaluation_rows: list[dict],
) -> None:
    tier1_root = SURVEY_ROOT / "tier1"
    tier2_root = SURVEY_ROOT / "tier2"
    tier3_root = SURVEY_ROOT / "tier3"
    for root in (tier1_root, tier2_root, tier3_root):
        if root.exists():
            raise RuntimeError(f"Refusing to overwrite registered output: {root}")
        root.mkdir(parents=True)

    _write_json(tier1_root / "tier1_results.json", tier1)
    (tier1_root / "tier1_report.md").write_text(
        _tier1_report(tier1),
        encoding="utf-8",
    )
    _write_k_distribution_csv(
        tier1_root / "k_similarity_distribution.csv",
        tier1["k_collapse"],
    )

    _write_json(tier2_root / "tier2_summary.json", tier2)
    _write_jsonl(tier2_root / "retrieval_results.jsonl", retrieval_records)
    _write_jsonl(tier2_root / "evaluation_results.jsonl", evaluation_rows)
    (tier2_root / "tier2_report.md").write_text(
        _tier2_report(tier2),
        encoding="utf-8",
    )

    _write_json(tier3_root / "tier3_results.json", tier3)
    (tier3_root / "tier3_report.md").write_text(
        _tier3_report(tier3),
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


def _write_k_distribution_csv(path: Path, payload: dict) -> None:
    fields = [
        "store_id",
        "turn_number",
        "episode_id",
        "stored_similarity",
        "stored_rank",
        "recomputed_pair_similarity",
        "recomputed_pair_rank",
        "recomputed_user_similarity",
        "assistant_characters",
        "pair_text_sha256",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for store_id, store in payload["stores"].items():
            for row in store["distribution"]:
                writer.writerow({"store_id": store_id, **row})


def _tier1_report(payload: dict) -> str:
    reachability = payload["reachability"]
    ceiling = reachability["primary_ceiling"]
    presence_121 = payload["presence"]["lineage_121"]
    presence_1000 = payload["presence"]["study_010"]
    k_stores = payload["k_collapse"]["stores"]
    return (
        "# Retrieval Bakeoff Tier 1 Report\n\n"
        f"**T1.1 status:** {payload['presence']['status']}\n\n"
        "All 17 Q11 atomic facts were checked at their registered source "
        f"turns in {len(presence_121)} preserved 121-turn stores. The "
        f"Study 010 inventory checked 60 atomic fields in "
        f"{len(presence_1000)} stores.\n\n"
        "## T1.2 Reachability\n\n"
        f"The primary raw-store ceiling is **{ceiling['matched_fact_count']}/17** "
        f"under `{ceiling['method_id']}` at "
        f"{ceiling['delivered_characters']:,} serialized characters. "
        f"Threshold 14/17: **{'PASS' if ceiling['reaches_14_of_17'] else 'FAIL'}**.\n\n"
        "## T1.3 K Collapse\n\n"
        f"Study 009 recomputed K count: "
        f"{k_stores['study_009_arm_s']['recomputed_pair']['at_or_above_0_50']}; "
        f"Study 002: "
        f"{k_stores['study_002_condition_c']['recomputed_pair']['at_or_above_0_50']}.\n\n"
        f"Most likely mechanism: "
        f"`{payload['k_collapse']['most_likely_mechanism']}`.\n"
    )


def _tier2_report(payload: dict) -> str:
    rows = payload["summary"]["pooled_class"]
    lines = [
        "# Retrieval Bakeoff Tier 2 Report",
        "",
        f"**Status:** {payload['status']}",
        "",
        "| Method | Class | Recall | Coverage | Precision | Chars | Latency ms |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['method_id']} | {row['query_class']} | "
            f"{row['fact_recall_at_budget']:.4f} | "
            f"{row['domain_coverage']:.4f} | "
            f"{row['precision_proxy']:.4f} | "
            f"{row['delivered_characters']:.1f} | "
            f"{row['latency_ms']:.3f} |"
        )
    lines.extend(["", "## Advancement", ""])
    for row in payload["summary"]["advancement"]:
        lines.append(
            f"- `{row['method_id']}`: "
            f"{'ADVANCES' if row['advances'] else 'DOES NOT ADVANCE'}; "
            f"wins={','.join(row['winning_classes']) or 'none'}; "
            f"regressions={','.join(row['regressing_classes']) or 'none'}."
        )
    return "\n".join(lines) + "\n"


def _tier3_report(payload: dict) -> str:
    analysis = payload["analysis"]
    winner_lines = "\n".join(
        f"| {query_class} | {row['method_id']} | "
        f"{row['fact_recall_at_budget']:.4f} |"
        for query_class, row in analysis["T3.1_per_class_winners"].items()
    )
    router = analysis["T3.2_oracle_router"]
    classifier = analysis["T3.3_classifier"]
    gain = (
        "undefined"
        if router["relative_gain"] is None
        else f"{router['relative_gain']:.2%}"
    )
    return (
        "# Retrieval Bakeoff Tier 3 Report\n\n"
        "## Per-Class Winners\n\n"
        "| Class | Method | Recall |\n"
        "|---|---|---:|\n"
        f"{winner_lines}\n\n"
        "## Routing Value\n\n"
        f"Oracle recall: {router['oracle_macro_query_recall']:.4f}. "
        f"Single-best recall: {router['single_best_macro_query_recall']:.4f}. "
        f"Relative gain: {gain}. "
        f"Interpretation: `{router['interpretation']}`.\n\n"
        "## Classifier\n\n"
        f"Accuracy: {classifier['correct']}/{classifier['total']} "
        f"({classifier['accuracy']:.2%}).\n"
    )


def _assert_ready() -> None:
    if _git("status", "--porcelain"):
        raise RuntimeError("Registered Tiers 1-3 require a clean worktree")
    if _git("branch", "--show-current") != "retrieval-bakeoff":
        raise RuntimeError("Registered Tiers 1-3 must run on retrieval-bakeoff")
    for anchor in (
        REGISTRATION_ANCHOR,
        HOLDOUT_ANCHOR,
        PROTOCOL_ANCHOR,
        TIER0_ANCHOR,
    ):
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", anchor, "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    existing_caches = sorted(CACHE_ROOT.glob("*.sqlite*"))
    if existing_caches:
        raise RuntimeError(
            f"Cold index run requires empty mechanism cache: {existing_caches}"
        )
    for root in (
        SURVEY_ROOT / "tier1",
        SURVEY_ROOT / "tier2",
        SURVEY_ROOT / "tier3",
    ):
        if root.exists():
            raise RuntimeError(f"Registered output already exists: {root}")


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
