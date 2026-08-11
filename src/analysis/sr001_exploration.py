from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from src.retrieval_bakeoff.config import corpus_spec
from src.retrieval_bakeoff.corpus import load_raw_episodes
from src.retrieval_bakeoff.models import Candidate, RankedCandidate
from src.retrieval_mechanism_ledger.sr001 import (
    BUDGET_CHARS,
    assert_mechanism_path_allowed,
    episode_to_spans,
    pack_control,
    pack_treatment,
    rank_sources,
    source_content_sha256,
    source_identity_sequence,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments/components/retrieval_mechanism_ledger"
DEFAULT_OUTPUT = COMPONENT_ROOT / "artifacts/sr001_exploration/part1_process_1"
DESIGN = COMPONENT_ROOT / "SR_001_EXTRACTIVE_SPAN_REPRESENTATION.md"
AUTHORIZATION = COMPONENT_ROOT / "SR_001_AUTHORIZATION.md"
DATABASE_Q11 = (
    REPO_ROOT
    / "experiments/surveys/retrieval_bakeoff/tier6/runs/"
    "tier6_live_121_corrected_001/context_matched_stm/study.db"
)
RANK_INVENTORY = COMPONENT_ROOT / "artifacts/rd001/full_rank_inventory.csv"
QUERY_MANIFEST = REPO_ROOT / "experiments/surveys/retrieval_bakeoff/holdout/queries_121.json"
QUERY_CACHE = COMPONENT_ROOT / "artifacts/e006_p3_tier4a_capture/query_vectors.sqlite"
TIER2_RETRIEVAL = REPO_ROOT / "experiments/surveys/retrieval_bakeoff/tier2/retrieval_results.jsonl"
COMPONENT_SOURCE = REPO_ROOT / "src/retrieval_mechanism_ledger/sr001.py"

DESIGN_COMMIT = "baa317db41cb45b90087f4ec1cb1d4bd558cf55a"
AUTHORIZATION_COMMIT = "f99b86a4"

# The compact table is kept explicit so accidental input substitution stops early.
FROZEN_INPUTS = {
    "HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md": (17505, "dbc6a1c4134df37877d6f5a77acdf61db4ce8361a1f7b2a2810b6182a6d6f926"),
    "experiments/components/retrieval_mechanism_ledger/BA_001_REPORT.md": (6861, "efaa03b10a90da68c7f284bb092a80d1edbbb724a84d871cb89a5e4a4a18d14c"),
    "experiments/components/retrieval_mechanism_ledger/artifacts/ba001/results.json": (41619, "1c0d6fb6ef01e991fd7f14ebba2900d0770325c564b64648b9d716a84e1630f1"),
    "experiments/surveys/retrieval_bakeoff/tier2/retrieval_results.jsonl": (23523340, "97ce339f0ce50b3af77c76f4707266c537349a20e8067361e45d65fd23fd9273"),
    "experiments/surveys/retrieval_bakeoff/tier2/evaluation_results.jsonl": (674786, "4dd8aecc17b8f21d7f5dbcd2ee40249532662205d5a262f7180452d2587e8e50"),
    "experiments/components/retrieval_mechanism_ledger/artifacts/rd001/full_rank_inventory.csv": (10642, "8d6f9eee6ebe232608981aac0c0d4816eaec4710ae551db028ae0b323253ac03"),
    "experiments/surveys/retrieval_bakeoff/tier6/runs/tier6_live_121_corrected_001/context_matched_stm/study.db": (1978368, "5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41"),
    "experiments/surveys/retrieval_bakeoff/holdout/queries_121.json": (4231, "ae950fda20dce9f519f31ee2670a815a5599648cab618d42309db7e3f23d36f4"),
    "experiments/components/retrieval_mechanism_ledger/artifacts/e006_p3_tier4a_capture/query_vectors.sqlite": (249856, "d9741edb0545d8cfe050663340599a31813d6025c38f0467e0ec7671573a1e6a"),
    "experiments/surveys/retrieval_bakeoff/holdout/answer_key_121.json": (9832, "2d43a31d3c04f4ad690ff2910abde71f508a3f6ce776545a9f2b16f90fae5320"),
    "src/memory/span_segmenter.py": (13468, "141c7ebda6af73dd7b69b00150de200c03f65105f2e76afd55fd9f767a8a5bda"),
    "src/retrieval_bakeoff/serialization.py": (4075, "737ffa0b182682a24f433259b4790308a374dfc8e9998402f2fcafc1e1f9aadc"),
    "src/retrieval_bakeoff/corpus.py": (8031, "3f87655aa794cea8254f24a9c5bda79b816852e5345a4bfc6f666ca6fed445f5"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_inputs() -> list[dict[str, Any]]:
    rows = []
    for relative, (size, digest) in FROZEN_INPUTS.items():
        path = REPO_ROOT / relative
        if not path.is_file() or path.stat().st_size != size or sha256_file(path) != digest:
            raise AssertionError(f"Frozen input mismatch: {relative}")
        rows.append({"path": relative, "bytes": size, "sha256": digest})
    return rows


def load_queries() -> list[dict[str, str]]:
    payload = json.loads(QUERY_MANIFEST.read_text(encoding="utf-8"))
    rows = [{"query_id": str(row["query_id"]), "text": str(row["text"])} for row in payload["queries"]]
    if len(rows) != 24 or len({row["query_id"] for row in rows}) != 24:
        raise AssertionError("SR-001 requires 24 unique sealed holdout queries")
    return rows


def load_query_vectors(queries: Sequence[dict[str, str]]) -> dict[str, np.ndarray]:
    with sqlite3.connect(f"file:{QUERY_CACHE.as_posix()}?mode=ro&immutable=1", uri=True) as connection:
        vectors = {}
        for query in queries:
            row = connection.execute("SELECT embedding FROM cache WHERE text = ?", (query["text"],)).fetchone()
            if row is None:
                raise AssertionError(f"Missing exact query-cache hit: {query['query_id']}")
            vector = np.frombuffer(row[0], dtype=np.float32).copy()
            if vector.shape != (1024,):
                raise AssertionError("Query vector dimension changed")
            norm = float(np.linalg.norm(vector))
            vectors[query["query_id"]] = vector / norm if norm else vector
    return vectors


def load_q11_sources() -> tuple[list[Candidate], list[float]]:
    with sqlite3.connect(f"file:{DATABASE_Q11.as_posix()}?mode=ro&immutable=1", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT episodes.id, episodes.turn_number, episodes.user_message,
                   episodes.assistant_message, episodes.topic_id,
                   COALESCE(topics.label, episodes.topic_id, '') AS topic_label
            FROM episodes LEFT JOIN topics ON topics.id = episodes.topic_id
            WHERE episodes.turn_number BETWEEN 1 AND 119
            """
        ).fetchall()
    by_id = {
        str(row["id"]): Candidate(
            candidate_id=str(row["id"]), source_episode_id=str(row["id"]),
            turn_number=int(row["turn_number"]), unit_type="episode",
            user_message=str(row["user_message"] or ""),
            assistant_message=str(row["assistant_message"] or ""),
            topic_id=str(row["topic_id"] or ""), topic_label=str(row["topic_label"] or ""),
        )
        for row in rows
    }
    with RANK_INVENTORY.open(encoding="utf-8", newline="") as handle:
        inventory = list(csv.DictReader(handle))
    candidates = [by_id[str(row["episode_id"])] for row in inventory]
    scores = [float(row["cosine"]) for row in inventory]
    if len(candidates) != 119:
        raise AssertionError("Q11 rank inventory must contain 119 sources")
    return candidates, scores


def load_m2_rows() -> dict[str, dict[str, Any]]:
    rows = {}
    with TIER2_RETRIEVAL.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["corpus_id"] == "c121_l" and row["method_id"] == "M2":
                rows[str(row["query_id"])] = row
    if len(rows) != 24:
        raise AssertionError("Expected 24 committed c121_l M2 rows")
    return rows


def rank_holdout_sources(
    episodes: Sequence[Candidate], query_vector: np.ndarray
) -> list:
    matrix = np.vstack([np.asarray(row.embedding, dtype=np.float32) for row in episodes])
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms != 0)
    scores = matrix @ query_vector
    return rank_sources(episodes, [float(score) for score in scores])


def anchor_committed_display_scores(
    ranked: Sequence[RankedCandidate], committed: dict[str, Any]
) -> tuple[list[RankedCandidate], dict[str, Any]]:
    committed_scores = {
        str(row["candidate_id"]): float(row["score"])
        for row in committed["selected"]
    }
    before = source_identity_sequence(ranked)
    anchored = [
        RankedCandidate(
            candidate=row.candidate,
            score=committed_scores.get(row.candidate.source_episode_id, row.score),
            component_scores={
                "dense": committed_scores.get(row.candidate.source_episode_id, row.score)
            },
        )
        for row in ranked
    ]
    after = source_identity_sequence(anchored)
    if before != after:
        raise AssertionError("Display-score anchoring changed source identity order")
    positions = {
        row.candidate.source_episode_id: index for index, row in enumerate(anchored)
    }
    committed_ids = [str(row["candidate_id"]) for row in committed["selected"]]
    anchored_positions = [positions[candidate_id] for candidate_id in committed_ids]
    if anchored_positions != sorted(anchored_positions):
        raise AssertionError("Committed M2 selected identities changed relative order")
    return anchored, {
        "anchored_count": len(committed_scores),
        "source_order_unchanged": before == after,
        "committed_selected_order_preserved": anchored_positions == sorted(anchored_positions),
    }


def query_record(query_id: str, ranked: Sequence, committed: dict[str, Any] | None) -> dict[str, Any]:
    score_anchor = None
    if committed is not None:
        ranked, score_anchor = anchor_committed_display_scores(ranked, committed)
    control = pack_control(ranked)
    treatment = pack_treatment(ranked)
    spans = [episode_to_spans(row.candidate) for row in ranked]
    span_lengths = [len(span.span_text) for group in spans for span in group]
    source_ids = list(source_identity_sequence(ranked))
    selected_t1_sources = [row.candidate.source_episode_id for row in treatment.selected]
    selected_counts = Counter(selected_t1_sources)
    source_span_counts = {row.candidate.source_episode_id: len(group) for row, group in zip(ranked, spans, strict=True)}
    partial = sum(0 < selected_counts[source] < count for source, count in source_span_counts.items())
    record = {
        "query_id": query_id,
        "source_identity_sha256": canonical_digest(source_ids),
        "source_identities": source_ids,
        "source_turns": [row.candidate.turn_number for row in ranked],
        "source_scores": [row.score for row in ranked],
        "C0": {
            "selected_unit_ids": [row.candidate.rendered_identity for row in control.selected],
            "selected_source_ids": [source_content_sha256(row.candidate) for row in control.selected],
            "selected_count": len(control.selected),
            "delivered_chars": len(control.rendered_block),
            "payload_sha256": hashlib.sha256(control.rendered_block.encode("utf-8")).hexdigest(),
            "skipped_oversized": control.skipped_oversized,
        },
        "T1": {
            "span_count": len(span_lengths),
            "role_counts": dict(sorted(Counter(span.role for group in spans for span in group).items())),
            "span_length_min": min(span_lengths),
            "span_length_max": max(span_lengths),
            "span_length_median": float(np.median(span_lengths)),
            "selected_unit_ids": [row.candidate.rendered_identity for row in treatment.selected],
            "selected_source_ids": selected_t1_sources,
            "selected_unit_count": len(treatment.selected),
            "selected_unique_source_count": len(set(selected_t1_sources)),
            "partial_source_count": partial,
            "delivered_chars": len(treatment.rendered_block),
            "payload_sha256": hashlib.sha256(treatment.rendered_block.encode("utf-8")).hexdigest(),
            "skipped_oversized": treatment.skipped_oversized,
        },
    }
    if committed is not None:
        record["score_anchor"] = score_anchor
        record["C0"]["committed_reproduction"] = {
            "selected_ids_equal": record["C0"]["selected_unit_ids"] == [row["candidate_id"] for row in committed["selected"]],
            "delivered_chars_equal": record["C0"]["delivered_chars"] == committed["delivered_characters"],
            "payload_sha256_equal": record["C0"]["payload_sha256"] == committed["rendered_sha256"],
        }
    return record


def source_audit() -> dict[str, Any]:
    text = COMPONENT_SOURCE.read_text(encoding="utf-8").casefold()
    tree = ast.parse(text)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.casefold() for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append((node.module or "").casefold())
    forbidden = [
        name for name in imported
        if any(marker in name for marker in ("answer_key", "q_facts_key", "rubric", "evaluation_results", "span_embeddings", "ta001"))
    ]
    planted_stopped = False
    try:
        assert_mechanism_path_allowed("fixtures/answer_key_planted.json")
    except PermissionError:
        planted_stopped = True
    return {"status": "PASS" if not forbidden and planted_stopped else "FAIL", "forbidden_markers": forbidden, "planted_path_stopped": planted_stopped}


def eligibility(records: Sequence[dict[str, Any]], audit: dict[str, Any]) -> dict[str, Any]:
    holdouts = [row for row in records if row["query_id"] != "q11"]
    checks = {
        "query_count_25": len(records) == 25,
        "source_rank_count": all(len(row["source_identities"]) == (119 if row["query_id"] == "q11" else 111) for row in records),
        "payloads_within_budget": all(row[arm]["delivered_chars"] <= BUDGET_CHARS for row in records for arm in ("C0", "T1")),
        "all_sources_have_spans": all(row["T1"]["span_count"] >= len(row["source_identities"]) for row in records),
        "holdout_m2_exact": all(all(row["C0"]["committed_reproduction"].values()) for row in holdouts),
        "source_audit": audit["status"] == "PASS",
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run(output_dir: Path, process_tag: str) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite exploration output: {output_dir}")
    started = time.perf_counter()
    inventory = verify_inputs()
    queries = load_queries()
    vectors = load_query_vectors(queries)
    committed = load_m2_rows()
    holdout_sources = load_raw_episodes(corpus_spec("c121_l"))
    q11_candidates, q11_scores = load_q11_sources()
    records = [query_record("q11", rank_sources(q11_candidates, q11_scores), None)]
    records.extend(
        query_record(query["query_id"], rank_holdout_sources(holdout_sources, vectors[query["query_id"]]), committed[query["query_id"]])
        for query in queries
    )
    audit = source_audit()
    gate = eligibility(records, audit)
    core = {
        "study": "SR-001 extractive span representation",
        "part": "label-blind exploration",
        "parameters": {"budget_chars": BUDGET_CHARS, "source_rank_preserved": True, "span_reranking": False},
        "calls": {"embedding": 0, "model_generation": 0},
        "input_inventory": inventory,
        "query_cache_hits": len(vectors),
        "records": records,
        "distribution": {
            "control_selected_counts": dict(sorted(Counter(row["C0"]["selected_count"] for row in records).items())),
            "treatment_selected_unit_counts": dict(sorted(Counter(row["T1"]["selected_unit_count"] for row in records).items())),
            "treatment_unique_source_counts": dict(sorted(Counter(row["T1"]["selected_unique_source_count"] for row in records).items())),
            "partial_source_counts": dict(sorted(Counter(row["T1"]["partial_source_count"] for row in records).items())),
        },
        "source_audit": audit,
        "eligibility": gate,
    }
    deterministic_digest = canonical_digest(core)
    result = {
        **core,
        "deterministic_digest": deterministic_digest,
        "process": {"tag": process_tag, "pid": os.getpid(), "python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "elapsed_seconds": time.perf_counter() - started},
    }
    output_dir.mkdir(parents=True)
    write_json(output_dir / "exploration.json", result)
    with (output_dir / "query_traces.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n")
    files = [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in sorted(output_dir.iterdir())]
    write_json(output_dir / "artifact_manifest.json", {"files": files, "deterministic_digest": deterministic_digest})
    return result


def compare(first: Path, second: Path, output: Path) -> dict[str, Any]:
    left = json.loads((first / "exploration.json").read_text(encoding="utf-8"))
    right = json.loads((second / "exploration.json").read_text(encoding="utf-8"))
    result = {"status": "PASS" if left["deterministic_digest"] == right["deterministic_digest"] else "FAIL", "first_digest": left["deterministic_digest"], "second_digest": right["deterministic_digest"]}
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite comparison: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    if result["status"] != "PASS":
        raise AssertionError("SR-001 fresh-process determinism failed")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--process-tag", default="process_1")
    parser.add_argument("--compare", nargs=2, type=Path)
    parser.add_argument("--comparison-output", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.compare:
        if args.comparison_output is None:
            raise SystemExit("--comparison-output is required with --compare")
        output = compare(args.compare[0], args.compare[1], args.comparison_output)
        print(json.dumps(output, sort_keys=True))
    else:
        output = run(args.output, args.process_tag)
        print(json.dumps({"status": output["eligibility"]["status"], "deterministic_digest": output["deterministic_digest"]}, sort_keys=True))
