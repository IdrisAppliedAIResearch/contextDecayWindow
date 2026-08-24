"""Disposable TC-011 Part 1 exploration; delete before registration lock."""

from __future__ import annotations

import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import numpy as np
import spacy

from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import CONVEX_SELECTIONS, allocate_subset
from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._selection import additive_weight

BUDGETS = (16_000, 32_000)
W_Q = 0.3
RHO = 0.5
OBJECTS = {"dobj", "obj", "pobj", "attr", "oprd", "dative", "nsubjpass"}


def unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("invalid vector")
    return vector / norm


def unit_matrix(episodes):
    return np.stack([unit(np.asarray(e.record["embedding"], dtype=np.float64)) for e in episodes])


def norm_words(tokens) -> str:
    words = [t.lemma_.casefold() for t in tokens if not t.is_space and not t.is_punct and (not t.is_stop or t.like_num)]
    return "_".join(words)


def facets(doc) -> frozenset[str]:
    found: set[str] = set()
    for ent in doc.ents:
        value = norm_words(ent)
        if value:
            found.add(f"entity:{ent.label_}:{value}")
        if ent.label_ == "DATE" and value:
            found.add(f"date:{value}")
    for token in doc:
        if token.like_num:
            found.add(f"number:{token.lower_}")
        if token.pos_ == "VERB":
            found.add(f"event:{token.lemma_.casefold()}")
        if token.dep_ in OBJECTS and token.head.pos_ in {"VERB", "AUX"}:
            value = norm_words(token.subtree)
            if value:
                found.add(f"relation:{token.head.lemma_.casefold()}:{token.dep_}:{value}")
    for chunk in doc.noun_chunks:
        value = norm_words(chunk)
        if value:
            found.add(f"noun:{value}")
    return frozenset(found)


def initial_indices(episodes, relevance, budget):
    packed = pack_stm_payload([], [episodes[i].record for i in relevance], budget // 2)
    by_id = {e.identity: i for i, e in enumerate(episodes)}
    return tuple(by_id[i] for i in packed.selected_ids)


def feasible(episodes, excluded, spent, half):
    return [i for i in range(len(episodes)) if i not in excluded and spent + additive_weight(episodes[i].record) <= half]


def chain_order(episodes, matrix, query, initial, half, anchored, rank):
    q = unit(np.asarray(query, dtype=np.float64))
    c = unit(matrix[np.asarray(initial)].mean(axis=0))
    start = c.copy()
    excluded = set(initial)
    chosen = []
    spent = EMPTY_PAYLOAD_CHARS
    ranks = []
    while True:
        fit = feasible(episodes, excluded, spent, half)
        if not fit:
            break
        cue = unit(W_Q * q + (1.0 - W_Q) * c) if anchored else c
        scores = matrix[np.asarray(fit)] @ cue
        pick = min(zip(fit, scores, strict=True), key=lambda item: (-float(item[1]), rank[item[0]]))[0]
        pos = fit.index(pick)
        chosen.append(pick)
        ranks.append(float(scores[pos]))
        excluded.add(pick)
        spent += additive_weight(episodes[pick].record)
        c = unit(RHO * c + (1.0 - RHO) * matrix[pick])
    return tuple(chosen), {
        "steps": len(chosen), "solo_chars": spent, "start_query_cos": float(start @ q),
        "final_query_cos": float(c @ q), "pick_cos_median": float(median(ranks)),
    }


def aspect_order(episodes, all_facets, idf, relevance_scores, initial, half, rank):
    covered: dict[str, float] = {}
    for i in initial:
        for f in all_facets[i]:
            covered[f] = max(covered.get(f, 0.0), relevance_scores[i] * idf[f])
    excluded = set(initial)
    chosen = []
    spent = EMPTY_PAYLOAD_CHARS
    gains = []
    while True:
        best = None
        for i in feasible(episodes, excluded, spent, half):
            raw = sum(max(0.0, relevance_scores[i] * idf[f] - covered.get(f, 0.0)) for f in all_facets[i])
            score = raw / additive_weight(episodes[i].record)
            key = (score, -rank[i])
            if best is None or key > best[0]:
                best = (key, i, raw)
        if best is None or best[2] <= 1e-12:
            break
        i, raw = best[1], best[2]
        chosen.append(i); excluded.add(i); spent += additive_weight(episodes[i].record); gains.append(raw)
        for f in all_facets[i]:
            covered[f] = max(covered.get(f, 0.0), relevance_scores[i] * idf[f])
    return tuple(chosen), {"steps": len(chosen), "solo_chars": spent, "gain_median": float(median(gains)) if gains else 0.0, "covered": len(covered)}


def logdet_order(episodes, matrix, relevance_scores, initial, half, rank):
    n = len(episodes)
    roots = np.sqrt(np.maximum(relevance_scores, 0.0))
    seed = np.asarray(initial, dtype=np.int64)
    gram_seed = matrix[seed] @ matrix.T
    k_seed_all = roots[seed, None] * roots[None, :] * gram_seed
    k_seed = k_seed_all[:, seed].copy()
    k_seed.flat[:: len(seed) + 1] += 1.0
    chol = np.linalg.cholesky(k_seed)
    projection = np.linalg.solve(chol, k_seed_all).T
    residual = 1.0 + relevance_scores - np.sum(projection * projection, axis=1)
    residual = np.maximum(residual, 1.0)
    excluded = set(initial)
    chosen = []
    spent = EMPTY_PAYLOAD_CHARS
    gains = []
    while True:
        best = None
        for i in feasible(episodes, excluded, spent, half):
            raw = math.log(max(1.0, float(residual[i])))
            score = raw / additive_weight(episodes[i].record)
            key = (score, -rank[i])
            if best is None or key > best[0]:
                best = (key, i, raw)
        if best is None or best[2] <= 1e-12:
            break
        j, raw = best[1], best[2]
        chosen.append(j); excluded.add(j); spent += additive_weight(episodes[j].record); gains.append(raw)
        cross = roots[j] * roots * (matrix @ matrix[j])
        cross[j] += 1.0
        d = math.sqrt(max(float(residual[j]), 1e-15))
        correction = (cross - projection @ projection[j]) / d
        projection = np.column_stack((projection, correction))
        residual = np.maximum(residual - correction * correction, 1.0)
    return tuple(chosen), {"steps": len(chosen), "solo_chars": spent, "gain_median": float(median(gains)) if gains else 0.0, "final_positive": sum(math.log(float(x)) > 1e-12 for x in residual)}


def dist(values):
    return {"n": len(values), "min": min(values), "median": median(values), "max": max(values), "nonzero": sum(v != 0 for v in values)}


def main():
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    source_rows = {}
    with gzip.open(CONVEX_SELECTIONS, "rt", encoding="utf-8") as handle:
        for row in map(json.loads, handle):
            source_rows[(row["sample_id"], int(row["source_index"]))] = row
    prepared = {}
    facet_stats = Counter()
    for case in cases:
        episodes = build_episodes(case, vectors)
        matrix = unit_matrix(episodes)
        docs = list(nlp.pipe([e.pair.text for e in episodes], batch_size=64))
        fs = tuple(facets(doc) for doc in docs)
        df = Counter(f for item in fs for f in item)
        idf = {f: math.log((len(episodes) + 1) / (count + 1)) + 1.0 for f, count in df.items()}
        for item in fs:
            facet_stats.update(f.split(":", 1)[0] for f in item)
        prepared[case.sample_id] = (episodes, matrix, fs, idf)
    metrics = defaultdict(list)
    set_diffs = Counter()
    traces = []
    for case in cases:
        episodes, matrix, fs, idf = prepared[case.sample_id]
        by_id = {e.identity: i for i, e in enumerate(episodes)}
        for question in case.questions:
            source = source_rows[(case.sample_id, question.source_index)]
            relevance = tuple(by_id[x] for x in source["arms"]["cc80"]["order"])
            rank = {candidate: position for position, candidate in enumerate(relevance)}
            score_by_i = np.zeros(len(episodes), dtype=np.float64)
            for i, score in zip(relevance, source["cc80"]["scores_in_order"], strict=True):
                score_by_i[i] = score
            for budget in BUDGETS:
                initial = initial_indices(episodes, relevance, budget)
                half = budget // 2
                orders = {}
                orders["logdet"], meta_log = logdet_order(episodes, matrix, score_by_i, initial, half, rank)
                orders["aspect"], meta_aspect = aspect_order(episodes, fs, idf, score_by_i, initial, half, rank)
                orders["chain_anchor"], meta_anchor = chain_order(episodes, matrix, vectors[question.question], initial, half, True, rank)
                orders["chain_pure"], meta_pure = chain_order(episodes, matrix, vectors[question.question], initial, half, False, rank)
                metas = {"logdet": meta_log, "aspect": meta_aspect, "chain_anchor": meta_anchor, "chain_pure": meta_pure}
                allocated = {arm: allocate_subset(episodes, relevance, order, budget) for arm, order in orders.items()}
                rank_one = {i: p + 1 for p, i in enumerate(relevance)}
                for arm, value in allocated.items():
                    metrics[(budget, arm, "initial")].append(len(value.initial_relevance_ids))
                    metrics[(budget, arm, "spread")].append(len(value.spread_ids))
                    metrics[(budget, arm, "returned")].append(len(value.returned_relevance_ids))
                    metrics[(budget, arm, "selected")].append(len(value.selected_ids))
                    metrics[(budget, arm, "chars")].append(len(value.payload))
                    metrics[(budget, arm, "spread_rank")].extend(rank_one[by_id[x]] for x in value.spread_ids)
                    for key, val in metas[arm].items():
                        metrics[(budget, arm, key)].append(val)
                set_diffs[(budget, "chain_anchor_vs_pure")] += set(allocated["chain_anchor"].selected_ids) != set(allocated["chain_pure"].selected_ids)
                set_diffs[(budget, "logdet_vs_aspect")] += set(allocated["logdet"].selected_ids) != set(allocated["aspect"].selected_ids)
                if len(traces) < 4:
                    traces.append({"sample": case.sample_id, "source_index": question.source_index, "budget": budget, "initial": len(initial), "meta": metas})
    result = {
        "identity": {
            "logdet": "greedy exact-cost-normalized marginal logdet, quality weighted by CC80 and conditioned on initial semantic admissions",
            "aspect": "greedy exact-cost-normalized saturation of deterministic entity/date/number/noun/event/relation facets, quality weighted by CC80",
            "chain_anchor": "semantic-centroid recurrence whose cue retains 0.3 of the original query and updates 0.5/0.5 after each admitted candidate",
            "chain_pure": "semantic-centroid recurrence with no original-query term after initial CC80 seeding and a 0.5/0.5 update",
        },
        "calls": {"cache_hits": reuse["hits"], "cache_misses": reuse["misses"], "embedding": 0, "llm": 0},
        "facet_types": dict(facet_stats),
        "metrics": {f"{b}:{a}:{k}": dist(v) for (b, a, k), v in metrics.items()},
        "set_diffs": {f"{b}:{k}": v for (b, k), v in set_diffs.items()},
        "real_traces": traces,
    }
    out = REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts" / "tc011" / "part1_exploration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "calls": result["calls"], "set_diffs": result["set_diffs"], "facet_types": result["facet_types"]}, indent=2))


if __name__ == "__main__":
    main()
