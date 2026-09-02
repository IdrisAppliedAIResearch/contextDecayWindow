"""Evidence-blind edge features for DA-003."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da001_linked_context import BUDGET
from analysis.da002_provenance import order_with_provenance
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file
from analysis.nf004_mechanism import Candidate, pack, ranking_orders
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256

TOKEN = re.compile(r"[A-Za-z0-9]+")
FEATURES = (
    "seed_query_coverage", "neighbor_query_coverage", "union_query_coverage",
    "neighbor_only_query_coverage", "seed_only_query_coverage", "seed_query_matches",
    "neighbor_query_matches", "neighbor_only_query_matches", "seed_numeric_matches",
    "neighbor_numeric_matches", "seed_year_matches", "neighbor_year_matches",
    "seed_query_cosine", "neighbor_query_cosine", "neighbor_minus_seed_cosine",
    "max_query_cosine", "seed_neighbor_cosine", "residual_semantic_score",
    "neighbor_chars", "seed_chars", "direct_slack", "counterfactual_packed_chars",
    "displaced_count", "displaced_chars", "displaced_score_sum", "displaced_score_max",
    "displaced_score_min", "displaced_score_mean", "neighbor_minus_displaced_max",
    "neighbor_minus_displaced_mean", "neighbor_already_direct", "seed_rank",
    "neighbor_direct_rank", "signed_direction", "rank_gap",
)


class DA003Error(RuntimeError):
    pass


def tokens(text: str) -> frozenset[str]:
    return frozenset(token.lower() for token in TOKEN.findall(text))


def corpus_idf(cases: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    documents = [tokens(candidate.text) for case in cases for candidate in case["candidates"]]
    counts = Counter(token for document in documents for token in document)
    total = len(documents)
    return {token: math.log((1 + total) / (1 + count)) + 1 for token, count in counts.items()}


def weighted_coverage(query: frozenset[str], text: frozenset[str], idf: Mapping[str, float]) -> float:
    denominator = sum(idf.get(token, 1.0) for token in query)
    return sum(idf.get(token, 1.0) for token in query & text) / denominator if denominator else 0.0


def one_edge_order(direct_order: Sequence[int], seed: int, neighbor: int) -> tuple[int, ...]:
    emitted: list[int] = []
    for index in direct_order:
        if index == neighbor:
            continue
        emitted.append(index)
        if index == seed:
            emitted.append(neighbor)
    if len(emitted) != len(direct_order) or len(set(emitted)) != len(emitted):
        raise DA003Error("One-edge order is not a permutation")
    return tuple(emitted)


def edge_features(
    *, question_text: str, candidates: Sequence[Candidate], vectors: np.ndarray,
    scores: np.ndarray, direct_order: Sequence[int], seed: int, neighbor: int,
    idf: Mapping[str, float],
) -> tuple[dict[str, float | int], dict[str, Any]]:
    direct = pack(candidates, direct_order, BUDGET)
    order = one_edge_order(direct_order, seed, neighbor)
    treatment = pack(candidates, order, BUDGET)
    by_id = {candidate.identity: index for index, candidate in enumerate(candidates)}
    displaced_ids = [identity for identity in direct.selected if identity not in treatment.selected]
    displaced = [by_id[identity] for identity in displaced_ids]
    q, seed_tokens, neighbor_tokens = tokens(question_text), tokens(candidates[seed].text), tokens(candidates[neighbor].text)
    numeric = {token for token in q if token.isdigit()}
    years = {token for token in numeric if len(token) == 4}
    normalized = vectors / np.linalg.norm(vectors, axis=1)[:, None]
    seed_neighbor = float(normalized[seed] @ normalized[neighbor])
    displaced_scores = [float(scores[index]) for index in displaced]
    dmax = max(displaced_scores) if displaced_scores else 0.0
    dmin = min(displaced_scores) if displaced_scores else 0.0
    dmean = float(np.mean(displaced_scores)) if displaced_scores else 0.0
    seed_score, neighbor_score = float(scores[seed]), float(scores[neighbor])
    ranks = {index: rank for rank, index in enumerate(direct_order, 1)}
    features: dict[str, float | int] = {
        "seed_query_coverage": weighted_coverage(q, seed_tokens, idf),
        "neighbor_query_coverage": weighted_coverage(q, neighbor_tokens, idf),
        "union_query_coverage": weighted_coverage(q, seed_tokens | neighbor_tokens, idf),
        "neighbor_only_query_coverage": weighted_coverage(q, neighbor_tokens - seed_tokens, idf),
        "seed_only_query_coverage": weighted_coverage(q, seed_tokens - neighbor_tokens, idf),
        "seed_query_matches": len(q & seed_tokens), "neighbor_query_matches": len(q & neighbor_tokens),
        "neighbor_only_query_matches": len(q & neighbor_tokens - seed_tokens),
        "seed_numeric_matches": len(numeric & seed_tokens), "neighbor_numeric_matches": len(numeric & neighbor_tokens),
        "seed_year_matches": len(years & seed_tokens), "neighbor_year_matches": len(years & neighbor_tokens),
        "seed_query_cosine": seed_score, "neighbor_query_cosine": neighbor_score,
        "neighbor_minus_seed_cosine": neighbor_score - seed_score,
        "max_query_cosine": max(seed_score, neighbor_score), "seed_neighbor_cosine": seed_neighbor,
        "residual_semantic_score": neighbor_score - seed_neighbor * seed_score,
        "neighbor_chars": candidates[neighbor].chars, "seed_chars": candidates[seed].chars,
        "direct_slack": BUDGET - direct.packed_chars, "counterfactual_packed_chars": treatment.packed_chars,
        "displaced_count": len(displaced), "displaced_chars": sum(candidates[index].chars for index in displaced),
        "displaced_score_sum": sum(displaced_scores), "displaced_score_max": dmax,
        "displaced_score_min": dmin, "displaced_score_mean": dmean,
        "neighbor_minus_displaced_max": neighbor_score - dmax,
        "neighbor_minus_displaced_mean": neighbor_score - dmean,
        "neighbor_already_direct": int(candidates[neighbor].identity in direct.selected),
        "seed_rank": ranks[seed], "neighbor_direct_rank": ranks[neighbor],
        "signed_direction": candidates[neighbor].pair_order - candidates[seed].pair_order,
        "rank_gap": ranks[neighbor] - ranks[seed],
    }
    if set(features) != set(FEATURES) or not all(math.isfinite(float(value)) for value in features.values()):
        raise DA003Error("DA-003 feature schema or finiteness differs")
    audit = {
        "direct_selected_ids": list(direct.selected), "counterfactual_selected_ids": list(treatment.selected),
        "displaced_ids": displaced_ids, "admitted": candidates[neighbor].identity in treatment.selected,
        "direct_complete_anchor": hashlib.sha256("\0".join(direct.selected).encode("ascii")).hexdigest(),
    }
    return features, audit


def build_rows(dataset_path: Path, cache_path: Path, manifest_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from episodic import EmbeddingCache

    cases = load_blind_cases(dataset_path)
    idf = corpus_idf(cases)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["cache"]
    rows: list[dict[str, Any]] = []
    duplicate_nominations = 0
    with EmbeddingCache(cache_path, mode="reuse", expected_file_sha256=manifest["file_sha256"],
                        expected_content_sha256=manifest["content_sha256"],
                        expected_model_sha256=CARRIED_EMBEDDING_SHA256) as cache:
        for case in cases:
            candidates = case["candidates"]
            vectors = np.vstack([np.asarray(cache(candidate.text), dtype=np.float32) for candidate in candidates])
            normalized = vectors / np.linalg.norm(vectors, axis=1)[:, None]
            for question in case["questions"]:
                query = np.asarray(cache(question["text"]), dtype=np.float32)
                scores = normalized @ (query / np.linalg.norm(query))
                _, direct_order = ranking_orders(candidates, vectors, query)
                _, provenance = order_with_provenance(candidates, direct_order, "TEMPORAL", 16)
                raw = 0
                by_session: dict[str, list[int]] = {}
                for index, candidate in enumerate(candidates):
                    by_session.setdefault(candidate.session_identity, []).append(index)
                for members in by_session.values():
                    members.sort(key=lambda index: candidates[index].pair_order)
                for seed in direct_order[:16]:
                    members = by_session[candidates[seed].session_identity]
                    position = members.index(seed)
                    raw += int(position > 0) + int(position + 1 < len(members))
                duplicate_nominations += raw - len(provenance)
                for neighbor, detail in sorted(provenance.items(), key=lambda item: (item[1]["seed_direct_rank"], item[1]["signed_offset"])):
                    seed = int(detail["seed_index"])
                    features, audit = edge_features(question_text=question["text"], candidates=candidates,
                        vectors=vectors, scores=scores, direct_order=direct_order, seed=seed, neighbor=neighbor, idf=idf)
                    rows.append({"comparison_key": question["comparison_key"], "duplicate_ordinal": question["duplicate_ordinal"],
                        "sample_id": question["sample_id"], "source_index": question["source_index"],
                        "seed_id": candidates[seed].identity, "neighbor_id": candidates[neighbor].identity,
                        "features": features, **audit})
        record = cache.record()
    rows.sort(key=lambda row: (row["comparison_key"], row["duplicate_ordinal"], row["features"]["seed_rank"], row["features"]["signed_direction"]))
    return rows, {"cache": record, "idf_terms": len(idf), "duplicate_nominations": duplicate_nominations}


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(dataset_path: Path, cache_path: Path, manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows, audit = build_rows(dataset_path, cache_path, manifest_path)
    path = output_dir / "blind_edges.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da003-") as directory:
        replay, replay_audit = build_rows(dataset_path, cache_path, manifest_path)
        replay_path = Path(directory) / path.name
        write_rows(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    source = Path(__file__).read_text(encoding="utf-8").lower()
    declaration = "forbidden_tokens ="
    forbidden_tokens = ("nf004_measurement", "g6_holdout_outcomes", '["answer"]', '["evidence"]')
    scanned = "\n".join(line for line in source.splitlines() if declaration not in line)
    clean = not any(token in scanned for token in forbidden_tokens)
    result = {"schema": "da003-edge-preflight-v1", "status": "PASS" if identical and clean and audit["cache"]["misses"] == 0 else "FAIL",
        "rows": len(rows), "questions": len({(row["comparison_key"], row["duplicate_ordinal"]) for row in rows}),
        "features": list(FEATURES), "edge_sha256": sha256_file(path), "replay_byte_identical": identical,
        "leakage_scan_clean": clean, "idf_terms": audit["idf_terms"], "duplicate_nominations": audit["duplicate_nominations"],
        "cache": {"hits": audit["cache"]["hits"], "misses": audit["cache"]["misses"]}, "calls": {"embedding": 0, "model": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS" or replay_audit["cache"]["misses"]:
        raise DA003Error("DA-003 blind preflight failed")
    return result


__all__ = ["DA003Error", "FEATURES", "corpus_idf", "edge_features", "one_edge_order", "run_preflight", "tokens"]
