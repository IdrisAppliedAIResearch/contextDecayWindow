"""Disposable label-blind TC-012 dynamic-ASPECT exploration."""

from __future__ import annotations

import gzip
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np
import spacy

from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import CONVEX_SELECTIONS, allocate_subset
from analysis.tc011_spread import RHO, W_Q, extract_facets, facet_idf, unit, unit_matrix
from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._selection import additive_weight

BUDGETS = (16_000, 32_000)
TC011_SELECTIONS = REPO_ROOT / "experiments/components/tier_cost/artifacts/tc011/preflight/selections.jsonl.gz"


def normalize(values: np.ndarray) -> np.ndarray:
    span = float(values.max() - values.min())
    if not np.isfinite(values).all() or span <= 0:
        raise RuntimeError("degenerate dynamic dense scores")
    return (values - values.min()) / span


def dynamic_scores(matrix: np.ndarray, cue: np.ndarray, bm25_contribution: np.ndarray) -> np.ndarray:
    return 0.8 * normalize(matrix @ cue) + bm25_contribution


def feasible(episodes, excluded, spent, half):
    return [i for i in range(len(episodes)) if i not in excluded and spent + additive_weight(episodes[i].record) <= half]


def coverage(selected, candidate_facets, idf, scores):
    state = {}
    for index in selected:
        for facet in sorted(candidate_facets[index]):
            state[facet] = max(state.get(facet, 0.0), scores[index] * idf[facet])
    return state


def dynamic_aspect(
    episodes,
    matrix,
    candidate_facets,
    idf,
    query_vector,
    query_facets,
    bm25_contribution,
    relevance_order,
    initial,
    half,
    residual,
):
    query = unit(np.asarray(query_vector, dtype=np.float64))
    context = unit(matrix[np.asarray(initial)].mean(axis=0))
    selected = list(initial)
    excluded = set(initial)
    chosen = []
    spent = EMPTY_PAYLOAD_CHARS
    cue_query = []
    uncovered_counts = []
    residual_fallbacks = 0
    rank = {candidate: position for position, candidate in enumerate(relevance_order)}
    while True:
        fit = feasible(episodes, excluded, spent, half)
        if not fit:
            reason = "no_complete_candidate_fits"
            break
        if residual:
            covered_query = set().union(*(candidate_facets[index] for index in selected))
            uncovered = set(query_facets) - covered_query
            weights = np.asarray([
                sum(idf.get(facet, 0.0) for facet in candidate_facets[index] & uncovered)
                for index in range(len(episodes))
            ], dtype=np.float64)
            if uncovered and float(weights.sum()) > 0:
                aspect_cue = unit(weights @ matrix)
                cue = unit(W_Q * query + (1.0 - W_Q) * aspect_cue)
            else:
                cue = query
                residual_fallbacks += 1
            uncovered_counts.append(len(uncovered))
        else:
            cue = unit(W_Q * query + (1.0 - W_Q) * context)
            uncovered_counts.append(0)
        scores = dynamic_scores(matrix, cue, bm25_contribution)
        covered = coverage(selected, candidate_facets, idf, scores)
        options = []
        for candidate in fit:
            raw = sum(max(0.0, scores[candidate] * idf[facet] - covered.get(facet, 0.0)) for facet in sorted(candidate_facets[candidate]))
            ratio = raw / additive_weight(episodes[candidate].record)
            options.append((ratio, -rank[candidate], candidate, raw))
        _, _, candidate, raw = max(options)
        if raw <= 1e-12:
            reason = "no_positive_marginal"
            break
        chosen.append(candidate)
        selected.append(candidate)
        excluded.add(candidate)
        spent += additive_weight(episodes[candidate].record)
        context = unit(RHO * context + (1.0 - RHO) * matrix[candidate])
        cue_query.append(float(cue @ query))
    return tuple(chosen), {
        "steps": len(chosen),
        "solo_chars": spent,
        "cue_query_median": median(cue_query) if cue_query else 1.0,
        "cue_query_final": cue_query[-1] if cue_query else 1.0,
        "uncovered_median": median(uncovered_counts) if uncovered_counts else 0,
        "residual_fallbacks": residual_fallbacks,
        "stop": reason,
    }


def dist(values):
    return {"n": len(values), "min": min(values), "median": median(values), "max": max(values), "nonzero": sum(value != 0 for value in values)}


def main():
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        sources = list(map(json.loads, handle))
    with gzip.open(TC011_SELECTIONS, "rt", encoding="utf-8") as handle:
        static = {(row["sample_id"], int(row["source_index"])): row for row in map(json.loads, handle)}
    prepared = {}
    question_lookup = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        matrix = unit_matrix(episodes)
        candidate_docs = list(nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        candidate_facets = tuple(extract_facets(doc) for doc in candidate_docs)
        idf, _ = facet_idf(candidate_facets)
        question_docs = list(nlp.pipe([question.question for question in case.questions], batch_size=64))
        for question, doc in zip(case.questions, question_docs, strict=True):
            question_lookup[(case.sample_id, question.source_index)] = (question.question, extract_facets(doc))
        prepared[case.sample_id] = episodes, matrix, candidate_facets, idf
    metrics = defaultdict(list)
    diffs = defaultdict(int)
    stops = defaultdict(int)
    rows = []
    for source in sources:
        episodes, matrix, candidate_facets, idf = prepared[source["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(by_id[identifier] for identifier in source["arms"]["cc80"]["order"])
        bm25 = np.zeros(len(episodes), dtype=np.float64)
        for index, value in zip(relevance, source["cc80"]["bm25_contribution_in_order"], strict=True):
            bm25[index] = value
        question_text, question_facets = question_lookup[(source["sample_id"], int(source["source_index"]))]
        budget_rows = {}
        for budget in BUDGETS:
            initial_pack = pack_stm_payload([], [episodes[index].record for index in relevance], budget // 2)
            initial = tuple(by_id[identifier] for identifier in initial_pack.selected_ids)
            arms = {}
            metas = {}
            for arm, residual in (("dynamic_prompt", False), ("residual_aspect", True)):
                order, meta = dynamic_aspect(
                    episodes, matrix, candidate_facets, idf, vectors[question_text], question_facets,
                    bm25, relevance, initial, budget // 2, residual,
                )
                value = allocate_subset(episodes, relevance, order, budget)
                arms[arm] = value
                metas[arm] = meta
                rank = {episode.identity: position + 1 for position, index in enumerate(relevance) for episode in (episodes[index],)}
                for key, datum in (("steps", meta["steps"]), ("selected", len(value.selected_ids)), ("spread", len(value.spread_ids)), ("returned", len(value.returned_relevance_ids)), ("chars", len(value.payload)), ("cue_query_median", meta["cue_query_median"]), ("cue_query_final", meta["cue_query_final"]), ("uncovered_median", meta["uncovered_median"]), ("residual_fallbacks", meta["residual_fallbacks"])):
                    metrics[(budget, arm, key)].append(datum)
                metrics[(budget, arm, "spread_rank")].extend(rank[identifier] for identifier in value.spread_ids)
                stops[(budget, arm, meta["stop"])] += 1
            prior = static[(source["sample_id"], int(source["source_index"]))]["budgets"][str(budget)]["aspect"]
            prior_ids = set(prior["selected_ids"])
            for arm, value in arms.items():
                diffs[(budget, f"{arm}_vs_static")] += set(value.selected_ids) != prior_ids
            diffs[(budget, "dynamic_vs_residual")] += set(arms["dynamic_prompt"].selected_ids) != set(arms["residual_aspect"].selected_ids)
            budget_rows[str(budget)] = {
                arm: {"selected_ids": list(value.selected_ids), "payload_sha256": value.payload_sha256, "meta": metas[arm]}
                for arm, value in arms.items()
            }
        rows.append({"blind_key": source["blind_key"], "sample_id": source["sample_id"], "source_index": source["source_index"], "budgets": budget_rows})
    result = {
        "identity": {
            "dynamic_prompt": "ASPECT with per-hop CC80 dense score recomputed against .3 original query + .7 growing selected-context centroid",
            "residual_aspect": "ASPECT with per-hop CC80 dense score recomputed against .3 original query + .7 centroid of candidates carrying uncovered query facets; query fallback when none",
        },
        "metrics": {f"{budget}:{arm}:{key}": dist(values) for (budget, arm, key), values in metrics.items()},
        "set_diffs": {f"{budget}:{name}": value for (budget, name), value in diffs.items()},
        "stops": {f"{budget}:{arm}:{reason}": value for (budget, arm, reason), value in stops.items()},
        "calls": {"cache_hits": reuse["hits"], "cache_misses": reuse["misses"], "embedding": 0, "llm": 0},
        "rows": len(rows),
    }
    out = REPO_ROOT / "experiments/components/tier_cost/artifacts/tc012/part1_exploration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "set_diffs": result["set_diffs"], "stops": result["stops"], "calls": result["calls"]}, indent=2))


if __name__ == "__main__":
    main()
