"""Run EC-001 Tier 1 on all 500 pinned LongMemEval-S questions.

The runner refuses to start without a committed-design-compatible Tier 2
subset manifest.  It writes score artifacts separately from a mechanism log;
commit the scores before opening the mechanism log.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "episodic" / "src"))

from src.analysis.ec001_longmemeval import (  # noqa: E402
    CachingSoloEmbedder,
    EC001Error,
    aggregate_tier1,
    assert_repository_ready,
    build_instrument_audit_registration,
    load_adaptation_record,
    load_longmemeval,
    retrieve_tier1_instance,
    sha256_file,
    validate_subset_manifest,
)
from src.retrieval_bakeoff.embedding import CarriedEmbedder  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--subset", type=Path, required=True)
    parser.add_argument("--instrument-audit", type=Path, required=True)
    parser.add_argument("--embedding-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    script_sha256 = sha256_file(script_path)
    repository = assert_repository_ready(require_clean=True)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite Tier 1 output: {args.output}")
    if not args.subset.is_file():
        raise EC001Error(
            "Tier 2 subset must exist and be committed before Tier 1"
        )
    if not args.instrument_audit.is_file():
        raise EC001Error(
            "Pre-retrieval instrument audit must be committed before Tier 1"
        )

    record = load_adaptation_record()
    benchmark = record["benchmark"]
    if args.data.stat().st_size != int(benchmark["dataset_bytes"]):
        raise EC001Error("Dataset byte size does not match the adaptation pin")
    dataset = load_longmemeval(
        args.data,
        expected_sha256=str(benchmark["dataset_sha256"]),
    )
    subset = json.loads(args.subset.read_text(encoding="utf-8"))
    validate_subset_manifest(subset, dataset)
    registered_audit = json.loads(
        args.instrument_audit.read_text(encoding="utf-8")
    )
    if registered_audit != build_instrument_audit_registration(dataset):
        raise EC001Error(
            "Pre-retrieval instrument audit does not match the pinned dataset"
        )

    from episodic import EpisodicConfig

    config = EpisodicConfig()
    decisions = record["decisions"]
    if config.recency_window_n != int(
        decisions["recency_window"]["recency_window_n"]
    ):
        raise EC001Error("Carried recency config drifted from adaptation record")
    if config.embedder_sha256 != str(
        decisions["embedder"]["model_sha256"]
    ):
        raise EC001Error("Carried embedder pin drifted from adaptation record")
    budget_chars = int(decisions["budget"]["budget_chars"])

    carried = CarriedEmbedder(args.embedding_model)
    carried.assert_carried_model()
    embedder = CachingSoloEmbedder(carried)

    args.output.mkdir(parents=True)
    scores_path = args.output / "tier1_scores.jsonl"
    mechanism_path = args.output / "SEALED_MECHANISM_DO_NOT_OPEN.jsonl"
    started = time.time()
    score_rows: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="ec001-tier1-") as temporary:
        stores = Path(temporary)
        with (
            scores_path.open("w", encoding="utf-8") as scores_handle,
            mechanism_path.open("w", encoding="utf-8") as mechanism_handle,
        ):
            for index, bundle in enumerate(dataset.instances, 1):
                scores, mechanism = retrieve_tier1_instance(
                    bundle,
                    store_path=stores / f"{bundle.mechanism.question_id}.db",
                    embedder=embedder,
                    budget_chars=budget_chars,
                )
                score_rows.append(scores)
                scores_handle.write(
                    json.dumps(scores, ensure_ascii=False) + "\n"
                )
                mechanism_handle.write(
                    json.dumps(mechanism, ensure_ascii=False) + "\n"
                )
                scores_handle.flush()
                mechanism_handle.flush()
                if index % 10 == 0 or index == len(dataset.instances):
                    elapsed = time.time() - started
                    print(
                        f"{index:3d}/{len(dataset.instances)} questions; "
                        f"{elapsed / index:.1f}s/question"
                    )

    dataset_after = sha256_file(args.data)
    script_after = sha256_file(script_path)
    if dataset_after != dataset.source_sha256:
        raise EC001Error("Dataset changed during Tier 1")
    if script_after != script_sha256:
        raise EC001Error("Tier 1 script changed during decoding")

    write_json(args.output / "tier1_summary.json", aggregate_tier1(score_rows))
    write_json(
        args.output / "instrument_audit.json",
        {
            "question_count": len(dataset.instances),
            "finding_count": len(dataset.annotation_findings),
            "findings": list(dataset.annotation_findings),
        },
    )
    write_json(
        args.output / "source_integrity.json",
        {
            "dataset_sha256_before": dataset.source_sha256,
            "dataset_sha256_after": dataset_after,
            "script_sha256_before": script_sha256,
            "script_sha256_after": script_after,
            "subset_sha256": sha256_file(args.subset),
            "registered_instrument_audit_sha256": sha256_file(
                args.instrument_audit
            ),
            "scores_sha256": sha256_file(scores_path),
            "sealed_mechanism_sha256": sha256_file(mechanism_path),
            "status": "PASS",
        },
    )
    write_json(
        args.output / "run_header.json",
        {
            "record": "EC-001 Tier 1 retrieval only",
            "registration_sha": repository["registration_sha"],
            "adaptation_sha": repository["adaptation_sha"],
            "amendment_001_sha": repository["amendment_001_sha"],
            "amendment_002_sha": repository["amendment_002_sha"],
            "amendment_003_sha": repository["amendment_003_sha"],
            "head": repository["head"],
            "branch": repository["branch"],
            "launch_command": shlex.join(sys.argv),
            "parallel": 1,
            "seed": config.seed,
            "speculative_decoding": False,
            "inference_server": None,
            "server_build_hash": None,
            "question_count": len(dataset.instances),
            "budget_chars": budget_chars,
            "episodic_config": json.loads(config.to_json()),
            "embedding_model_sha256": embedder.model_sha256,
            "dataset_sha256": dataset.source_sha256,
            "foreign_store_adaptation": dataset.adaptation_stats,
            "benchmark_code_commit": benchmark["code_commit"],
            "benchmark_dataset_commit": benchmark["dataset_commit"],
            "started_utc": datetime.fromtimestamp(
                started, timezone.utc
            ).isoformat(),
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - started, 3),
            "embedding_cache_entries": embedder.cache_size,
            "mechanism_log_status": (
                "SEALED: commit score artifacts before opening"
            ),
        },
    )
    print(
        f"Tier 1 complete at {args.output}. Commit tier1_scores.jsonl, "
        "tier1_summary.json, instrument_audit.json, source_integrity.json, "
        "and run_header.json before opening the sealed mechanism log."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
