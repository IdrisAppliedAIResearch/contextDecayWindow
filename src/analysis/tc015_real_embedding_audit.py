"""Independent real-vector replay of the stopped TC-015 mechanism."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc005_ranking import prepare_rankers, rank_all
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_convex_fusion_probe import convex_scores, normalize_scores, score_order
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import CONVEX_SELECTIONS, allocate_subset
from analysis.tc015_exploration import TC014_SELECTIONS
from analysis.tc015_opportunity_utility import opportunity_then_utility

ROOT = REPO_ROOT / "experiments" / "components" / "tier_cost"
OUTPUT = ROOT / "artifacts" / "tc015" / "real_embedding_audit.json"
BUDGETS = (16_000, 32_000)
TC014_SHA256 = "32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7"
CONVEX_SHA256 = "17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202"


class TC015RealEmbeddingAuditError(RuntimeError):
    pass


def _rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(map(json.loads, handle))


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if sha256_file(TC014_SELECTIONS) != TC014_SHA256:
        raise TC015RealEmbeddingAuditError("TC-014 anchor drift")
    if sha256_file(CONVEX_SELECTIONS) != CONVEX_SHA256:
        raise TC015RealEmbeddingAuditError("CC80 anchor drift")

    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    source_rows = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _rows(CONVEX_SELECTIONS)
    }
    tc014_rows = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _rows(TC014_SELECTIONS)
    }
    cc80_order_reproductions = 0
    cc80_score_reproductions = 0
    parent_cosine_checks = 0
    selected_identity_differences = {str(budget): 0 for budget in BUDGETS}
    max_score_error = 0.0
    max_dense_contribution_error = 0.0
    max_parent_cosine_error = 0.0
    dimensions: set[int] = set()
    minimum_norm = float("inf")
    maximum_norm = 0.0

    for case in cases:
        episodes = build_episodes(case, vectors)
        prepared = prepare_rankers(episodes)
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        for episode in episodes:
            vector = np.asarray(episode.record["embedding"], dtype=np.float64)
            norm = float(np.linalg.norm(vector))
            dimensions.add(int(vector.size))
            minimum_norm = min(minimum_norm, norm)
            maximum_norm = max(maximum_norm, norm)
            if not np.isfinite(vector).all() or norm == 0:
                raise TC015RealEmbeddingAuditError("invalid cached candidate vector")

        for question in case.questions:
            query = np.asarray(vectors[question.question], dtype=np.float64)
            query_norm = float(np.linalg.norm(query))
            dimensions.add(int(query.size))
            minimum_norm = min(minimum_norm, query_norm)
            maximum_norm = max(maximum_norm, query_norm)
            if not np.isfinite(query).all() or query_norm == 0:
                raise TC015RealEmbeddingAuditError("invalid cached query vector")

            source = source_rows[(case.sample_id, question.source_index)]
            rankings = rank_all(episodes, question.question, query, prepared)
            dense = np.asarray(rankings["dense"].scores, dtype=np.float64)
            bm25 = np.asarray(rankings["bm25"].scores, dtype=np.float64)
            scores = convex_scores(dense, bm25)
            order = score_order(case, scores)
            identities = [episodes[index].identity for index in order]
            if identities != source["arms"]["cc80"]["order"]:
                raise TC015RealEmbeddingAuditError("real-vector CC80 order drift")
            cc80_order_reproductions += 1
            stored_scores = np.asarray(source["cc80"]["scores_in_order"], dtype=np.float64)
            stored_dense = np.asarray(
                source["cc80"]["dense_contribution_in_order"], dtype=np.float64
            )
            score_error = float(np.max(np.abs(scores[np.asarray(order)] - stored_scores)))
            dense_error = float(
                np.max(
                    np.abs(
                        0.8 * normalize_scores(dense)[np.asarray(order)] - stored_dense
                    )
                )
            )
            max_score_error = max(max_score_error, score_error)
            max_dense_contribution_error = max(max_dense_contribution_error, dense_error)
            if score_error > 1e-12 or dense_error > 1e-12:
                raise TC015RealEmbeddingAuditError("real-vector CC80 score drift")
            cc80_score_reproductions += 1

            frozen = tc014_rows[(case.sample_id, question.source_index)]
            relevance = tuple(by_id[value] for value in identities)
            for budget in BUDGETS:
                opportunity = frozen["budgets"][str(budget)]["opportunity"]
                trace = opportunity["trace"]
                for parent_id, child_id, expected in zip(
                    trace["parent_for_child"],
                    trace["assigned_children"],
                    trace["parent_cosine"],
                    strict=True,
                ):
                    parent = np.asarray(
                        episodes[by_id[parent_id]].record["embedding"], dtype=np.float64
                    )
                    child = np.asarray(
                        episodes[by_id[child_id]].record["embedding"], dtype=np.float64
                    )
                    actual = float(
                        np.dot(parent, child)
                        / (np.linalg.norm(parent) * np.linalg.norm(child))
                    )
                    error = abs(actual - float(expected))
                    max_parent_cosine_error = max(max_parent_cosine_error, error)
                    if error > 1e-12:
                        raise TC015RealEmbeddingAuditError("TC-014 edge-vector drift")
                    parent_cosine_checks += 1

                ordered = opportunity_then_utility(
                    trace["assigned_children"],
                    trace["utility"],
                    trace["emitted_children"],
                )
                allocation = allocate_subset(
                    episodes,
                    relevance,
                    tuple(by_id[value] for value in ordered),
                    budget,
                )
                selected_identity_differences[str(budget)] += int(
                    set(allocation.selected_ids) != set(opportunity["selected_ids"])
                )

    passing = (
        reuse["misses"] == 0
        and cc80_order_reproductions == 871
        and cc80_score_reproductions == 871
        and parent_cosine_checks > 0
        and not any(selected_identity_differences.values())
    )
    result = {
        "schema": "tc015-real-embedding-audit-v1",
        "status": "PASS" if passing else "FAIL",
        "anchors": {
            "tc014_sha256": sha256_file(TC014_SELECTIONS),
            "convex_sha256": sha256_file(CONVEX_SELECTIONS),
            "blind_sha256": sha256_file(BLIND),
        },
        "real_vectors": {
            "dimensions": sorted(dimensions),
            "minimum_l2_norm": minimum_norm,
            "maximum_l2_norm": maximum_norm,
            "cache_hits": reuse["hits"],
            "cache_misses": reuse["misses"],
        },
        "reproduction": {
            "cc80_orders": cc80_order_reproductions,
            "cc80_scores": cc80_score_reproductions,
            "parent_cosines": parent_cosine_checks,
            "max_cc80_score_abs_error": max_score_error,
            "max_dense_contribution_abs_error": max_dense_contribution_error,
            "max_parent_cosine_abs_error": max_parent_cosine_error,
        },
        "selected_identity_differences_vs_opportunity": selected_identity_differences,
        "calls": {"embedding_model": 0, "llm_or_generative": 0},
        "boundary": "label-blind real-cache replay; no evidence labels or answers opened",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passing:
        raise TC015RealEmbeddingAuditError("real-embedding audit failed")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
