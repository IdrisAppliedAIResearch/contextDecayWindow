"""Evidence-blind whole-pack perturbation features for DA-004."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from analysis.da003_edge_features import FEATURES as EDGE_FEATURES
from analysis.da003_edge_features import corpus_idf, tokens, weighted_coverage, write_rows
from analysis.nf004_anatomy_features import load_blind_cases, sha256_file

DA003_SHA256 = "0d669cc7a0b2da9b0bfa7439fdd7c182ee4ea6f60a0bf6e0c8fdf79567b02c5c"
DA002_SHA256 = "25c6f2f8731b19341c440236418e47de95334eb706728b4a5d580cafe7cac8ca"
SET_FEATURES = (
    "added_count", "added_chars", "added_score_sum", "added_score_mean", "added_score_min",
    "added_score_max", "added_score_char_weighted_mean", "added_query_coverage",
    "added_query_matches", "added_numeric_matches", "added_year_matches",
    "downstream_count", "downstream_chars", "downstream_score_sum", "downstream_query_coverage",
    "set_displaced_count", "set_displaced_chars", "set_displaced_score_sum",
    "set_displaced_score_mean", "set_displaced_score_min", "set_displaced_score_max",
    "set_displaced_score_char_weighted_mean", "set_displaced_query_coverage",
    "set_displaced_query_matches", "set_displaced_numeric_matches", "set_displaced_year_matches",
    "balance_count", "balance_chars", "balance_score_sum", "balance_score_mean",
    "balance_query_coverage", "ratio_chars", "ratio_score_sum", "ratio_query_coverage",
    "selected_jaccard", "changed_identity_count", "neighbor_share_added_chars",
    "neighbor_share_added_score_sum",
)
FEATURES = EDGE_FEATURES + SET_FEATURES


class DA004Error(RuntimeError):
    pass


def read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _aggregate(identities: set[str], candidates: Mapping[str, Mapping[str, Any]],
               texts: Mapping[str, str], query: frozenset[str], idf: Mapping[str, float]) -> dict[str, float | int]:
    chars = [int(candidates[item]["chars"]) for item in identities]
    scores = [float(candidates[item]["direct_score"]) for item in identities]
    union = frozenset().union(*(tokens(texts[item]) for item in identities)) if identities else frozenset()
    numeric = {token for token in query if token.isdigit()}
    years = {token for token in numeric if len(token) == 4}
    total_chars = sum(chars)
    return {
        "count": len(identities), "chars": total_chars, "score_sum": sum(scores),
        "score_mean": sum(scores) / len(scores) if scores else 0.0,
        "score_min": min(scores) if scores else 0.0, "score_max": max(scores) if scores else 0.0,
        "score_char_weighted_mean": sum(score * char for score, char in zip(scores, chars, strict=True)) / total_chars if total_chars else 0.0,
        "query_coverage": weighted_coverage(query, union, idf), "query_matches": len(query & union),
        "numeric_matches": len(numeric & union), "year_matches": len(years & union),
    }


def perturbation_features(row: Mapping[str, Any], candidate_rows: Mapping[str, Mapping[str, Any]],
                          texts: Mapping[str, str], question_text: str,
                          idf: Mapping[str, float]) -> dict[str, float | int]:
    direct, treatment = set(row["direct_selected_ids"]), set(row["counterfactual_selected_ids"])
    added, displaced = treatment - direct, direct - treatment
    if set(row["displaced_ids"]) != displaced:
        raise DA004Error("DA-003 displaced identity delta differs")
    unknown = (direct | treatment) - set(candidate_rows)
    if unknown or (direct | treatment) - set(texts):
        raise DA004Error("Pack perturbation contains an unknown candidate")
    query = tokens(question_text)
    add = _aggregate(added, candidate_rows, texts, query, idf)
    drop = _aggregate(displaced, candidate_rows, texts, query, idf)
    downstream = _aggregate(added - {row["neighbor_id"]}, candidate_rows, texts, query, idf)
    union = direct | treatment
    neighbor_chars = int(candidate_rows[row["neighbor_id"]]["chars"]) if row["neighbor_id"] in added else 0
    neighbor_score = float(candidate_rows[row["neighbor_id"]]["direct_score"]) if row["neighbor_id"] in added else 0.0
    output: dict[str, float | int] = dict(row["features"])
    for name, value in add.items():
        output[f"added_{name}"] = value
    output.update({
        "downstream_count": downstream["count"], "downstream_chars": downstream["chars"],
        "downstream_score_sum": downstream["score_sum"], "downstream_query_coverage": downstream["query_coverage"],
    })
    for name, value in drop.items():
        output[f"set_displaced_{name}"] = value
    output.update({
        "balance_count": int(add["count"]) - int(drop["count"]),
        "balance_chars": int(add["chars"]) - int(drop["chars"]),
        "balance_score_sum": float(add["score_sum"]) - float(drop["score_sum"]),
        "balance_score_mean": float(add["score_mean"]) - float(drop["score_mean"]),
        "balance_query_coverage": float(add["query_coverage"]) - float(drop["query_coverage"]),
        "ratio_chars": float(add["chars"]) / max(float(drop["chars"]), 1e-9),
        "ratio_score_sum": float(add["score_sum"]) / max(float(drop["score_sum"]), 1e-9),
        "ratio_query_coverage": float(add["query_coverage"]) / max(float(drop["query_coverage"]), 1e-9),
        "selected_jaccard": len(direct & treatment) / len(union) if union else 1.0,
        "changed_identity_count": len(added) + len(displaced),
        "neighbor_share_added_chars": neighbor_chars / float(add["chars"]) if add["chars"] else 0.0,
        "neighbor_share_added_score_sum": neighbor_score / float(add["score_sum"]) if add["score_sum"] else 0.0,
    })
    if set(output) != set(FEATURES) or not all(math.isfinite(float(value)) for value in output.values()):
        raise DA004Error("DA-004 feature schema or finiteness differs")
    return output


def build_rows(dataset_path: Path, edge_path: Path, provenance_path: Path) -> list[dict[str, Any]]:
    if sha256_file(edge_path) != DA003_SHA256 or sha256_file(provenance_path) != DA002_SHA256:
        raise DA004Error("DA-004 sealed input hash differs")
    cases = load_blind_cases(dataset_path)
    idf = corpus_idf(cases)
    question_text, candidate_text = {}, {}
    for case in cases:
        for question in case["questions"]:
            question_text[(question["comparison_key"], int(question["duplicate_ordinal"]))] = question["text"]
        for candidate in case["candidates"]:
            candidate_text[candidate.identity] = candidate.text
    provenance = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in read_gzip(provenance_path)}
    edges = read_gzip(edge_path)
    rows = []
    seen = set()
    for edge in edges:
        key = (edge["comparison_key"], int(edge["duplicate_ordinal"]))
        edge_key = (*key, edge["seed_id"], edge["neighbor_id"])
        if edge_key in seen:
            raise DA004Error("Duplicate DA-004 edge key")
        seen.add(edge_key)
        if key not in provenance or key not in question_text:
            raise DA004Error("DA-004 question join is incomplete")
        rows.append({
            "comparison_key": key[0], "duplicate_ordinal": key[1], "sample_id": edge["sample_id"],
            "source_index": edge["source_index"], "seed_id": edge["seed_id"], "neighbor_id": edge["neighbor_id"],
            "direct_selected_ids": edge["direct_selected_ids"],
            "counterfactual_selected_ids": edge["counterfactual_selected_ids"],
            "added_ids": sorted(set(edge["counterfactual_selected_ids"]) - set(edge["direct_selected_ids"])),
            "displaced_ids": edge["displaced_ids"],
            "features": perturbation_features(edge, provenance[key]["candidates"], candidate_text,
                                                question_text[key], idf),
        })
    if len(rows) != 26_100 or len(question_text) != 1_104:
        raise DA004Error("DA-004 blind population differs")
    return rows


def run_preflight(dataset_path: Path, edge_path: Path, provenance_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(dataset_path, edge_path, provenance_path)
    path = output_dir / "blind_perturbations.jsonl.gz"
    write_rows(path, rows)
    with tempfile.TemporaryDirectory(prefix="da004-") as directory:
        replay = build_rows(dataset_path, edge_path, provenance_path)
        replay_path = Path(directory) / path.name
        write_rows(replay_path, replay)
        identical = path.read_bytes() == replay_path.read_bytes()
    source = Path(__file__).read_text(encoding="utf-8").lower()
    declaration = "forbidden_tokens ="
    forbidden_tokens = ("nf004_measurement", "g6_holdout_outcomes", '["answer"]', '["evidence"]', "embeddingcache")
    scanned = "\n".join(line for line in source.splitlines() if declaration not in line)
    clean = not any(token in scanned for token in forbidden_tokens)
    result = {"schema": "da004-pack-preflight-v1", "status": "PASS" if identical and clean else "FAIL",
              "rows": len(rows), "questions": 1_104, "features": list(FEATURES),
              "perturbation_sha256": sha256_file(path), "replay_byte_identical": identical,
              "leakage_and_cache_scan_clean": clean, "calls": {"embedding": 0, "model": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise DA004Error("DA-004 blind preflight failed")
    return result


__all__ = ["DA004Error", "FEATURES", "perturbation_features", "run_preflight"]
