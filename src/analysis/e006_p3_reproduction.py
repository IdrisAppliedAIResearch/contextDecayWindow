from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

from episodic import EmbeddingCache
from src.analysis.e006_p3_tier4a_capture import sha256_file
from src.analysis.e006_rev5_offline import configuration_id, pack_phase
from src.analysis.e006_rev5_preflight import run_registered_cells, selection_record
from src.retrieval_bakeoff.config import CORPORA
from src.retrieval_bakeoff.corpus import load_queries, load_raw_episodes
from src.retrieval_bakeoff.graph import AssociativeGraphIndex, GraphRetriever
from src.retrieval_bakeoff.serialization import pack_ranked_candidates


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
CAPTURE_ROOT = COMPONENT_ROOT / "artifacts" / "e006_p3_tier4a_capture"
CAPTURE_MANIFEST = CAPTURE_ROOT / "capture_manifest.json"
CAPTURE_CACHE = CAPTURE_ROOT / "query_vectors.sqlite"
TIER4_ROOT = REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff" / "tier4"
TIER4_RESULTS = TIER4_ROOT / "tier4a_results.json"
TIER4_RETRIEVAL = TIER4_ROOT / "tier4a_retrieval_results.jsonl"
REV5_ROOT = COMPONENT_ROOT / "artifacts" / "e006_rev5_s4"
REV5_SNAPSHOT = REV5_ROOT / "selection_snapshot.json"
REV5_PAYLOADS = REV5_ROOT / "payloads"

CAPTURE_MANIFEST_SHA256 = "2c24ea75d7551beb6658d8b9208225b985e25a9111cfd3766ec4f7980a7f18e4"
TIER4_RESULTS_SHA256 = "7eb1cddfeb48cd2a2902f4849f13810bf4dbdb4e1740071d7aaa685384fb203c"
TIER4_RETRIEVAL_SHA256 = "3836475f98158ba92c7fb983c70ea1770a008e8174c92987badfd7dd4f0bcec6"
TIER4_CODE_COMMIT = "8f016975504b03953dc3c8f95bc4d8424ea3d6e9"
TIER4_SOURCE_PATHS = (
    "src/retrieval_bakeoff/config.py",
    "src/retrieval_bakeoff/corpus.py",
    "src/retrieval_bakeoff/embedding.py",
    "src/retrieval_bakeoff/graph.py",
    "src/retrieval_bakeoff/models.py",
    "src/retrieval_bakeoff/serialization.py",
)


def _assert_sha(path: Path, expected: str) -> None:
    observed = sha256_file(path)
    if observed != expected:
        raise AssertionError(f"Input digest changed for {path}: {observed} != {expected}")


def assert_tier4_source_identity() -> dict[str, Any]:
    completed = subprocess.run(
        ("git", "diff", "--quiet", TIER4_CODE_COMMIT, "--", *TIER4_SOURCE_PATHS),
        cwd=REPO_ROOT,
    )
    return {
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "historical_commit": TIER4_CODE_COMMIT,
        "paths": list(TIER4_SOURCE_PATHS),
    }


def _expected_tier4_rows() -> dict[tuple[str, str, str], dict[str, Any]]:
    rows = {}
    with TIER4_RETRIEVAL.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if not str(row["method_id"]).startswith("G_E3_d"):
                continue
            key = (str(row["corpus_id"]), str(row["query_id"]), str(row["method_id"]))
            rows[key] = row
    if len(rows) != 144:
        raise AssertionError(f"Expected 144 committed Tier 4A E3 rows, got {len(rows)}")
    return rows


def reproduce_tier4a_e3() -> dict[str, Any]:
    _assert_sha(CAPTURE_MANIFEST, CAPTURE_MANIFEST_SHA256)
    _assert_sha(TIER4_RESULTS, TIER4_RESULTS_SHA256)
    _assert_sha(TIER4_RETRIEVAL, TIER4_RETRIEVAL_SHA256)
    capture = json.loads(CAPTURE_MANIFEST.read_text(encoding="utf-8"))
    expected = _expected_tier4_rows()
    source_identity = assert_tier4_source_identity()
    if source_identity["status"] != "PASS":
        raise AssertionError("Tier 4A carried sources differ from the historical run")

    comparisons = []
    with EmbeddingCache(
        CAPTURE_CACHE,
        mode="reuse",
        expected_file_sha256=capture["cache"]["file_sha256"],
        expected_content_sha256=capture["cache"]["content_sha256"],
        expected_model_sha256=capture["execution"]["model_sha256"],
    ) as cache:
        for corpus_id in ("c121_l", "c1000_l"):
            spec = CORPORA[corpus_id]
            graph = AssociativeGraphIndex(spec, load_raw_episodes(spec))
            retriever = GraphRetriever(graph, embedder=None)
            transition = graph.transition_for("E3")
            for query in load_queries(spec):
                query_vector = cache(query.text)
                for depth in (1, 2, 3):
                    method_id = f"G_E3_d{depth}"
                    ranked = retriever._rank(transition, depth, query_vector)
                    packed = pack_ranked_candidates(
                        method_id, [(item, "fill") for item in ranked], 32_000
                    )
                    committed = expected[(corpus_id, query.query_id, method_id)]
                    identities = [item.candidate.candidate_id for item in packed.selected]
                    committed_identities = [
                        str(item["candidate_id"]) for item in committed["selected"]
                    ]
                    rendered_sha256 = hashlib.sha256(
                        packed.rendered_block.encode("utf-8")
                    ).hexdigest()
                    comparisons.append(
                        {
                            "corpus_id": corpus_id,
                            "query_id": query.query_id,
                            "method_id": method_id,
                            "selected_identity_equal": identities == committed_identities,
                            "selected_count": len(identities),
                            "rendered_sha256_equal": rendered_sha256
                            == committed["rendered_sha256"],
                            "rendered_sha256": rendered_sha256,
                            "serialized_chars_equal": len(packed.rendered_block)
                            == int(committed["delivered_characters"]),
                        }
                    )
        cache_hits = cache.hits
        cache_misses = cache.misses
    passing = sum(
        row["selected_identity_equal"]
        and row["rendered_sha256_equal"]
        and row["serialized_chars_equal"]
        for row in comparisons
    )
    return {
        "status": "PASS" if passing == 144 and cache_misses == 0 else "FAIL",
        "row_count": len(comparisons),
        "passing_row_count": passing,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "source_identity": source_identity,
        "rows": comparisons,
    }


def reproduce_a1() -> dict[str, Any]:
    selections, _inputs = run_registered_cells()
    records = []
    for selection in selections:
        if selection.query_weight != 0.3 or selection.retention != 0.5:
            continue
        record = selection_record(selection)
        record["configuration_id"] = configuration_id(record)
        records.append(record)
    if len(records) != 8:
        raise AssertionError(f"Expected eight A1 cells, got {len(records)}")
    packed, payloads = pack_phase(records)
    snapshot = json.loads(REV5_SNAPSHOT.read_text(encoding="utf-8"))
    comparisons = []
    for record in packed:
        config_id = str(record["configuration_id"])
        expected = snapshot[config_id]
        expected_payload = REV5_PAYLOADS / f"{config_id}.txt"
        comparisons.append(
            {
                "configuration_id": config_id,
                "candidate_sequence_equal": record["ranked_seen_content_sha256"]
                == expected["ranked_seen_content_sha256"],
                "selection_sha256_equal": record["selection_sha256"]
                == expected["selection_sha256"],
                "payload_sha256_equal": record["payload_sha256"]
                == sha256_file(expected_payload),
                "serialized_chars": record["serialized_chars"],
                "selected_episode_count": record["selected_episode_count"],
            }
        )
    passing = sum(
        row["candidate_sequence_equal"]
        and row["selection_sha256_equal"]
        and row["payload_sha256_equal"]
        for row in comparisons
    )
    primary = next(row for row in comparisons if row["configuration_id"] == "D2_m5_wq0.3_rho0.5")
    return {
        "status": "PASS" if passing == 8 else "FAIL",
        "cell_count": len(comparisons),
        "passing_cell_count": passing,
        "primary_cell": primary,
        "cells": comparisons,
    }


def build_reproduction_gate() -> dict[str, Any]:
    tier4 = reproduce_tier4a_e3()
    if tier4["status"] != "PASS":
        decision = "STOP_BEFORE_A2"
        a1: dict[str, Any] = {"status": "NOT_RUN_AFTER_TIER4_FAILURE"}
    else:
        a1 = reproduce_a1()
        decision = "CONTINUE_TO_A2_EXPLORATION" if a1["status"] == "PASS" else "STOP_BEFORE_A2"
    return {
        "study": "E006-P3",
        "stage": "Part 1 reproduction gate",
        "status": "PASS" if decision == "CONTINUE_TO_A2_EXPLORATION" else "FAIL",
        "decision": decision,
        "zero_additional_embedding_calls": True,
        "tier4a_e3_reproduction": tier4,
        "a1_reproduction": a1,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006-P3 reproduction gates")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = build_reproduction_gate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": result["status"], "decision": result["decision"]}))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
