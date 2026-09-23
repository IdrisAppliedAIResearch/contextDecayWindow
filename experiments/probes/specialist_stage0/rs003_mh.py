"""RS003 Stage-0 / R-MH: multi-hop set-coverage admission arms (D1/D2/D4).

Per RS003_STAGE0_PRE_REGISTRATION.md section 5. Index-time graph per
conversation from cached vectors + frozen spaCy NER; query-time zero LM.
"""
from __future__ import annotations

import spacy
import numpy as np

from rs003_common import (ARTIFACTS, CAPS, block_dia_ids, coverage,
                          discordant, double_run, get_vector,
                          instrument_checks, load_vectors, load_world,
                          pack_ids, pack_order, rank_all, save,
                          sign_test_p_one_sided, summarize)

NN_K, TAU = 4, 0.30
ALPHA, PPR_ITERS = 0.85, 30
FL_POOL, PROTECT = 200, 4
CLUSTER_K, LLOYD_ITERS, LAMBDA = 16, 10, 0.1
ENT_LABELS = {"PERSON", "ORG", "GPE", "LOC", "FAC", "NORP", "WORK_OF_ART",
              "PRODUCT", "EVENT"}
NLP = spacy.load("en_core_web_sm", disable=["parser", "tagger", "senter",
                                            "lemmatizer", "morphologizer",
                                            "attribute_ruler"])


def extract_ents(texts):
    out = []
    for doc in NLP.pipe(texts):
        ents = set()
        for ent in doc.ents:
            if ent.label_ in ENT_LABELS:
                t = ent.text.strip().lower()
                if len(t) >= 2:
                    ents.add(t)
        out.append(ents)
    return out


def conversation_graph(elems, U, texts):
    n = len(elems)
    S = U @ U.T
    W = np.zeros((n, n), dtype=np.float64)
    # (a) kNN cosine edges, floor tau
    for i in range(n):
        row = S[i].copy()
        row[i] = -np.inf
        for j in np.argsort(-row, kind="stable")[:NN_K]:
            if row[j] >= TAU:
                if row[j] > W[i, j]:
                    W[i, j] = W[j, i] = float(row[j])
    # (b) temporal adjacency +-1, +-2 by adapter index
    for i in range(n):
        for d in (1, 2):
            if i + d < n:
                W[i, i + d] = W[i + d, i] = max(W[i, i + d], 1.0)
    # (c) entity co-occurrence, df in [2, 0.20n]
    doc_ents = extract_ents(texts)
    ent_elems = {}
    for i, ents in enumerate(doc_ents):
        for e in sorted(ents):
            ent_elems.setdefault(e, []).append(i)
    cap_df = max(2, int(0.20 * n))
    for e, ids in sorted(ent_elems.items()):
        if not (2 <= len(ids) <= cap_df):
            continue
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                if 0.5 > W[ids[a], ids[b]]:
                    W[ids[a], ids[b]] = W[ids[b], ids[a]] = 0.5
    return S, W, doc_ents


def ppr(W, seeds, n):
    deg = W.sum(axis=0)
    deg[deg == 0.0] = 1.0
    Wn = W / deg
    v = np.zeros(n)
    v[sorted(seeds)] = 1.0 / len(seeds)
    p = v.copy()
    for _ in range(PPR_ITERS):
        p = ALPHA * (Wn @ p) + (1.0 - ALPHA) * v
    return p


def fl_pack(S, pool, elems, cap):
    """Pack-aware greedy facility location over pool (cc80 order), protected
    top-PROTECT prefix; targets are pool members only."""
    m = len(pool)
    Sp = np.maximum(S[np.ix_(pool, pool)], 0.0)
    chosen, chosen_set, chars = [], set(), 0
    cur = np.zeros(m)

    def try_add(pos):
        nonlocal chars
        s = elems[pool[pos]]["element"]
        add = len(s) + (1 if chosen else 0)
        if chars + add <= cap:
            chosen.append(pool[pos])
            chosen_set.add(pos)
            chars += add
            return True
        return False

    for pos in range(min(PROTECT, m)):
        try_add(pos)
    for pos in range(m):
        cur = np.maximum(cur, Sp[pos]) if pos in chosen_set else cur
    remaining = [p for p in range(m) if p not in chosen_set]
    while remaining:
        best_pos, best_gain = None, 0.0
        for pos in remaining:
            gain = float(np.sum(np.maximum(Sp[pos] - cur, 0.0)))
            # registered tie-break: ascending adapter index
            if gain > best_gain or (
                    gain == best_gain and best_pos is not None
                    and pool[pos] < pool[best_pos]):
                best_pos, best_gain = pos, gain
        if best_pos is None:
            break
        remaining.remove(best_pos)
        if try_add(best_pos):
            cur = np.maximum(cur, Sp[best_pos])
    return chosen


def cluster_pack(U, pool, elems, cap):
    """E005-A3 style: deterministic farthest-first init + Lloyd(k) over pool;
    admission score = cc80 rank score + LAMBDA per not-yet-visited cluster."""
    m = len(pool)
    X = U[pool]
    k = min(CLUSTER_K, m)
    centers = [0]
    maxsim = X[0] @ X.T
    while len(centers) < k:
        cand = min(range(m), key=lambda i: (maxsim[i], pool[i]))
        if cand in set(centers):
            break
        centers.append(cand)
        maxsim = np.maximum(maxsim, X[cand] @ X.T)
    C = X[centers].copy()
    assign = np.zeros(m, dtype=np.int64)
    for _ in range(LLOYD_ITERS):
        assign = (X @ C.T).argmax(axis=1)
        newC = np.empty_like(C)
        for c in range(len(centers)):
            members = np.where(assign == c)[0]
            if len(members):
                ctr = X[members].mean(axis=0)
                nrm = np.linalg.norm(ctr)
                newC[c] = ctr / nrm if nrm > 0 else C[c]
            else:
                newC[c] = C[c]
        C = newC
    cc80 = np.array([1.0 - p / max(1, m - 1) for p in range(m)])
    chosen, chars = [], 0
    visited = set()
    remaining = list(range(m))
    while remaining:
        scored = sorted(((cc80[p] + (0.0 if assign[p] in visited else LAMBDA), p)
                          for p in remaining),
                         key=lambda x: (-x[0], pool[x[1]]))
        pos = scored[0][1]
        remaining.remove(pos)
        s = elems[pool[pos]]["element"]
        add = len(s) + (1 if chosen else 0)
        if chars + add <= cap:
            chosen.append(pool[pos])
            chars += add
            visited.add(int(assign[pos]))
    return chosen


def compute():
    srcs, convs, items, audit, disc, golds = load_world()
    vecs = load_vectors()
    log = {}
    instrument_checks((srcs, convs, items, audit, disc, golds), vecs, log)
    allq = sorted(items)
    cat1 = sorted(q for q in items if golds[q]["cat"] == "1")
    noncat1 = sorted(q for q in items if golds[q]["cat"] != "1")

    bmiss = [q for q in allq if audit[q]["B"] == 0]
    adm = 0
    for q in bmiss:
        elems = convs[q.split(":")[0]]["elements"]
        gset = set(golds[q]["gold_ids"])
        idxs = [e["idx"] for e in elems if gset & set(e["dialogue_ids"])]
        cost = sum(len(elems[i]["element"]) for i in idxs) + max(0, len(idxs) - 1)
        if cost <= 16000:
            adm += 1
    if adm < 10:
        raise SystemExit(f"instrument failure: only {adm} B-misses mechanically"
                         " admissible at 16k (need >=10); no D dispositions")
    log["bmiss_mechanically_admissible_16k"] = adm

    graphs = {}
    for cid in sorted(convs):
        elems = convs[cid]["elements"]
        U = np.stack([unit_cached(vecs, e["text"]) for e in elems])
        S, W, ents = conversation_graph(elems, U, [e["text"] for e in elems])
        graphs[cid] = dict(U=U, S=S, W=W, ents=ents)

    _rank_memo = {}

    def rank_ctx(q):
        if q not in _rank_memo:
            elems = convs[q.split(":")[0]]["elements"]
            r = rank_all(elems, golds[q]["question"],
                         get_vector(vecs, golds[q]["question"]), vecs)
            _rank_memo[q] = (elems, r)
        return _rank_memo[q]

    def d1_order(q, cap=None):
        elems, r = rank_ctx(q)
        g = graphs[q.split(":")[0]]
        n = len(elems)
        rank_of = {idx: pos for pos, idx in enumerate(r.order)}
        qents = {e.text.strip().lower()
                 for e in NLP(golds[q]["question"]).ents
                 if e.label_ in ENT_LABELS and len(e.text.strip()) >= 2}
        seeds = []
        if qents:
            ent_seed = [e["idx"] for e in elems
                        if (g["ents"][e["idx"]] & qents) or
                        any(en in e["text"].lower() for en in qents)]
            seeds = sorted(ent_seed, key=lambda i: rank_of[i])[:10]
        seeds = list(dict.fromkeys(seeds + list(r.order[:5])))
        p = ppr(g["W"], seeds, n)
        ppr_order = sorted(range(n), key=lambda i: (-p[i], i))
        protected = list(r.order[:PROTECT])
        rest = [i for i in ppr_order if i not in set(protected)]
        return protected + rest

    def metric(order_provider, cap, packed=False):
        out = {}
        for q in allq:
            elems = convs[q.split(":")[0]]["elements"]
            res = order_provider(q, cap)
            chosen = list(res) if packed else pack_order(res, elems, cap)[0]
            chars = (sum(len(elems[i]["element"]) for i in chosen)
                     + max(0, len(chosen) - 1))
            cov = coverage(golds[q]["gold_ids"], pack_ids(chosen, elems))
            out[q] = dict(coverage=cov, n_packed=len(chosen), chars=chars,
                          full=1 if cov == 1.0 else 0,
                          zero=1 if cov == 0.0 else 0)
        return out

    arms = {}
    for cap in CAPS:
        arms[f"CC80_{cap}"] = metric(
            lambda q, c: list(rank_ctx(q)[1].order), cap)
        arms[f"D1_ray_{cap}"] = metric(d1_order, cap)
        arms[f"D2_FL_{cap}"] = metric(
            lambda q, c: fl_pack(graphs[q.split(":")[0]]["S"],
                                 list(rank_ctx(q)[1].order[:FL_POOL]),
                                 convs[q.split(":")[0]]["elements"], c),
            cap, packed=True)
        arms[f"D4_A3_{cap}"] = metric(
            lambda q, c: cluster_pack(graphs[q.split(":")[0]]["U"],
                                      list(rank_ctx(q)[1].order[:FL_POOL]),
                                      convs[q.split(":")[0]]["elements"], c),
            cap, packed=True)

        def oracle(q, c):
            elems, r = rank_ctx(q)
            gset = set(golds[q]["gold_ids"])
            gold = [e["idx"] for e in elems if gset & set(e["dialogue_ids"])]
            return gold + [i for i in r.order if i not in set(gold)]
        arms[f"ORACLE_pack_{cap}"] = metric(oracle, cap)

    for blk in ("block_b", "block_c"):
        out = {}
        for q in allq:
            ids = block_dia_ids(items[q][blk])
            cov = coverage(golds[q]["gold_ids"], ids)
            out[q] = dict(coverage=cov, n_packed=None,
                          chars=len(items[q][blk]),
                          full=1 if cov == 1.0 else 0,
                          zero=1 if cov == 0.0 else 0)
        arms["B_as_is" if blk == "block_b" else "C_as_is"] = out

    summary = {k: summarize(v, cat1, audit) for k, v in arms.items()}
    cc = summary["CC80_16000"]
    b0 = summary["B_as_is"]
    dispositions = {}
    for d in ("D1_ray", "D2_FL", "D4_A3"):
        s = summary[f"{d}_16000"]
        w, l = discordant(arms[f"{d}_16000"], arms["CC80_16000"], cat1)
        p = sign_test_p_one_sided(len(w), len(l))
        reg = sum(1 for q in noncat1
                  if arms[f"{d}_16000"][q]["full"] == 0
                  and arms["CC80_16000"][q]["full"] == 1)
        adv_a = ((s["full_rate"] - cc["full_rate"]) >= 0.10
                 and (s["full_rate"] - b0["full_rate"]) >= 0.10)
        adv_b = p < 0.05
        adv_c = reg <= 1
        adv_d = (cc["zero_among_B_misses"] > 0
                 and s["zero_among_B_misses"] <= 0.5 * cc["zero_among_B_misses"])
        if adv_a and adv_b and adv_c and adv_d:
            disp = "BUILD"
        elif (s["full_rate"] - cc["full_rate"]) >= 0.05 and p < 0.10:
            disp = "SIGNAL"
        else:
            disp = "KILL"
        dispositions[d] = dict(verdict=disp, full=s["full_rate"],
                               cc80_full=cc["full_rate"],
                               b_full=b0["full_rate"], p=round(p, 6),
                               wins=len(w), losses=len(l),
                               regressions_noncat1=reg,
                               zeroB=s["zero_among_B_misses"],
                               cc80_zeroB=cc["zero_among_B_misses"],
                               checks=dict(a=adv_a, b=adv_b, c=adv_c, d=adv_d),
                               discordant=dict(wins=w, losses=l))
    return {"cat": "1", "instrument": log, "arms": arms, "summary": summary,
            "dispositions": dispositions}


_UNIT_MEMO = {}


def unit_cached(vecs, text):
    if text not in _UNIT_MEMO:
        from rs003_common import unit
        _UNIT_MEMO[text] = unit(get_vector(vecs, text))
    return _UNIT_MEMO[text]


def main():
    results = double_run(compute)
    save(ARTIFACTS / "rs003_mh_results.json", results)
    print("R-MH dispositions:")
    for d, x in results["dispositions"].items():
        print(f"  {d}: {x['verdict']} full={x['full']} cc80={x['cc80_full']} "
              f"p={x['p']} reg={x['regressions_noncat1']} "
              f"zeroB={x['zeroB']}/{x['cc80_zeroB']} checks={x['checks']}")
    for k in sorted(results["summary"]):
        s = results["summary"][k]
        print(f"  {k:24s} full={s['full']:2d}/{s['n']} "
              f"zero@Bmiss={s['zero_among_B_misses']:2d} cov={s['mean_coverage']}")


if __name__ == "__main__":
    main()
