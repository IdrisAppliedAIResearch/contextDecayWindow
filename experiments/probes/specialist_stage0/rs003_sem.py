"""RS003 Stage-0 / R-SEM: semantic-lane admission arms (R2_RRF, R1_head).

Per RS003_STAGE0_PRE_REGISTRATION.md section 6. Population cat3+cat4 (n=74)
at 8k; cat3 reported separately. Zero model calls: dense/BM25 from frozen
components; head trained on gold labels is an oracle-cap simulation.
"""
from __future__ import annotations

import math
import re

import numpy as np

from episodic._ranking import normalize_scores, tokenize
from rs003_common import (ARTIFACTS, block_dia_ids, coverage, discordant,
                          double_run, get_vector, instrument_checks,
                          load_vectors, load_world, pack_ids, pack_order,
                          rank_all, save, sign_test_p_one_sided, summarize)

K0 = 60
FOLDS = [("conv-26", "conv-30"), ("conv-41", "conv-42"), ("conv-43", "conv-44"),
         ("conv-47", "conv-48"), ("conv-49", "conv-50")]
DIGIT = re.compile(r"\d")
LR, ITERS, L2 = 0.5, 2000, 1e-3


def orders(elems, q, qvec, vecs):
    r = rank_all(elems, q, qvec, vecs)
    n = len(elems)
    dense = np.array(r.dense_scores, dtype=np.float64)
    bm25 = np.array(r.bm25_scores, dtype=np.float64)
    d_order = sorted(range(n), key=lambda i: (-dense[i], i))
    b_order = sorted(range(n), key=lambda i: (-bm25[i], i))
    rrf = np.zeros(n)
    for rank, i in enumerate(d_order, 1):
        rrf[i] += 1.0 / (K0 + rank)
    for rank, i in enumerate(b_order, 1):
        rrf[i] += 1.0 / (K0 + rank)
    rrf_order = sorted(range(n), key=lambda i: (-rrf[i], i))
    return r, dense, bm25, rrf, rrf_order


def features(elems, q, dense, bm25, rrf, sess_frac):
    n = len(elems)
    qtoks = set(tokenize(q))
    X = np.zeros((n, 7), dtype=np.float64)
    bm_lo, bm_hi = float(bm25.min()), float(bm25.max())
    rf_lo, rf_hi = float(rrf.min()), float(rrf.max())
    for i, e in enumerate(elems):
        ov = (len(qtoks & set(tokenize(e["text"]))) / len(qtoks)) if qtoks else 0.0
        X[i] = (dense[i],
                (bm25[i] - bm_lo) / (bm_hi - bm_lo) if bm_hi > bm_lo else 0.0,
                (rrf[i] - rf_lo) / (rf_hi - rf_lo) if rf_hi > rf_lo else 0.0,
                ov,
                1.0 / (1.0 + (n - 1 - i)),
                math.log1p(len(e["element"])),
                sess_frac[i])
    return X


def hard_negatives(elems, pos_set, dense):
    n = len(elems)
    cand = [i for i in sorted(range(n), key=lambda j: dense[j], reverse=True)
            if i not in pos_set][:10]
    seen = set(cand)
    digits = [i for i in range(n)
              if i not in pos_set and i not in seen and DIGIT.search(elems[i]["text"])]
    out = cand + digits
    return out[:15]


def fit_head(X, y):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0.0] = 1.0
    Xs = np.hstack([(X - mu) / sd, np.ones((X.shape[0], 1))])
    w = np.zeros(Xs.shape[1])
    for _ in range(ITERS):
        p = 1.0 / (1.0 + np.exp(-Xs @ w))
        g = Xs.T @ (p - y) / len(y) + L2 * w
        w -= LR * g
    return mu, sd, w


def apply_head(mu, sd, w, X):
    Xs = np.hstack([(X - mu) / sd, np.ones((X.shape[0], 1))])
    return Xs @ w


def metric(order_fn, cap, qids, convs, golds, items):
    out = {}
    for q in qids:
        elems = convs[q.split(":")[0]]["elements"]
        chosen, chars = pack_order(order_fn(q), elems, cap)
        cov = coverage(golds[q]["gold_ids"], pack_ids(chosen, elems))
        out[q] = dict(coverage=cov, n_packed=len(chosen), chars=chars,
                      full=1 if cov == 1.0 else 0, zero=1 if cov == 0.0 else 0)
    return out


def compute():
    srcs, convs, items, audit, disc, golds = load_world()
    vecs = load_vectors()
    log = {}
    instrument_checks((srcs, convs, items, audit, disc, golds), vecs, log)

    allq = sorted(items)
    lane = sorted(q for q in allq if golds[q]["cat"] in ("3", "4"))
    cat3 = sorted(q for q in allq if golds[q]["cat"] == "3")
    reg_pop = sorted(q for q in allq if golds[q]["cat"] in ("1", "2"))

    sess_frac = {}
    for cid, c in convs.items():
        dates = sorted({e["date"] for e in c["elements"]})
        pos = {d: j / max(1, len(dates) - 1) for j, d in enumerate(dates)}
        sess_frac[cid] = np.array([pos[e["date"]] for e in c["elements"]])

    ctx = {}
    for q in allq:
        cid = q.split(":")[0]
        elems = convs[cid]["elements"]
        qv = get_vector(vecs, golds[q]["question"])
        r, dense, bm25, rrf, rrf_order = orders(elems, golds[q]["question"], qv, vecs)
        gset = set(golds[q]["gold_ids"])
        pos = [e["idx"] for e in elems if gset & set(e["dialogue_ids"])]
        X = features(elems, golds[q]["question"], dense, bm25, rrf, sess_frac[cid])
        ctx[q] = dict(order=list(r.order), rrf_order=rrf_order, X=X,
                      pos=set(pos))

    def oracle_order(q):
        elems = convs[q.split(":")[0]]["elements"]
        return sorted(ctx[q]["pos"]) + [e["idx"] for e in elems
                                        if e["idx"] not in ctx[q]["pos"]]

    # ORACLE instrument: gold cost <= 8k
    adm = 0
    for q in lane:
        elems = convs[q.split(":")[0]]["elements"]
        idxs = sorted(ctx[q]["pos"])
        cost = sum(len(elems[i]["element"]) for i in idxs) + max(0, len(idxs) - 1)
        if cost <= 8000:
            adm += 1
    log["oracle_gold_fits_8k_in_lane"] = {"n": len(lane), "fits": adm,
                                          "rate": round(adm / len(lane), 4)}

    # R1 head: conversation-level CV
    conv_of = {q: q.split(":")[0] for q in allq}
    head_order = {}
    for fold in FOLDS:
        test_cids = set(fold)
        train_rows_X, train_rows_y = [], []
        for q in allq:
            if conv_of[q] in test_cids:
                continue
            elems = convs[conv_of[q]]["elements"]
            pos = ctx[q]["pos"]
            negs = hard_negatives(elems, pos, ctx[q]["X"][:, 0])
            rows = [(ctx[q]["X"][i], 1.0) for i in sorted(pos)] + \
                   [(ctx[q]["X"][i], 0.0) for i in sorted(negs)]
            train_rows_X.extend(rows)
        Xtr = np.array([x for x, _ in train_rows_X])
        ytr = np.array([y for _, y in train_rows_X])
        mu, sd, w = fit_head(Xtr, ytr)
        for q in sorted(q for q in allq if conv_of[q] in test_cids):
            s = apply_head(mu, sd, w, ctx[q]["X"])
            head_order[q] = sorted(range(len(s)), key=lambda i: (-s[i], i))

    arms = {}
    for cap in (8000, 16000):
        arms[f"CC80_{cap}"] = metric(lambda q: ctx[q]["order"], cap, allq,
                                     convs, golds, items)
        arms[f"ORACLE_rerank_{cap}"] = metric(oracle_order, cap, allq, convs,
                                              golds, items)
        arms[f"R2_RRF_{cap}"] = metric(lambda q: ctx[q]["rrf_order"], cap,
                                       allq, convs, golds, items)
    for cap in (8000, 16000):
        out = {}
        for q in allq:
            elems = convs[q.split(":")[0]]["elements"]
            if cap == 8000:
                chosen, chars = pack_order(head_order[q], elems, cap)
            else:
                chosen, chars = pack_order(head_order[q], elems, cap)
            cov = coverage(golds[q]["gold_ids"], pack_ids(chosen, elems))
            out[q] = dict(coverage=cov, n_packed=len(chosen), chars=chars,
                          full=1 if cov == 1.0 else 0, zero=1 if cov == 0.0 else 0)
        arms[f"R1_head_{cap}"] = out
    for blk, name in (("block_b", "B_as_is"), ("block_c", "C_as_is")):
        out = {}
        for q in allq:
            ids = block_dia_ids(items[q][blk])
            cov = coverage(golds[q]["gold_ids"], ids)
            out[q] = dict(coverage=cov, n_packed=None, chars=len(items[q][blk]),
                          full=1 if cov == 1.0 else 0, zero=1 if cov == 0.0 else 0)
        arms[name] = out

    summary = {k: summarize(v, lane, audit) for k, v in arms.items()}
    summary_cat3 = {k: summarize(v, cat3, audit) for k, v in arms.items()}

    cc = summary["CC80_8000"]
    b0 = summary["B_as_is"]
    orc = summary["ORACLE_rerank_8000"]
    oracle_margin = orc["full_rate"] - cc["full_rate"]
    dispositions = {}
    any_build = any_signal = False
    for arm in ("R2_RRF", "R1_head"):
        s = summary[f"{arm}_8000"]
        w, l = discordant(arms[f"{arm}_8000"], arms["CC80_8000"], lane)
        p = sign_test_p_one_sided(len(w), len(l))
        reg = sum(1 for q in reg_pop
                  if arms[f"{arm}_8000"][q]["full"] == 0
                  and arms["CC80_8000"][q]["full"] == 1)
        adv_a = ((s["full_rate"] - cc["full_rate"]) >= 0.10
                 and (s["full_rate"] - b0["full_rate"]) >= 0.10)
        adv_b = p < 0.05
        if oracle_margin >= 0.10 and adv_a and adv_b and reg <= 2:
            disp = "BUILD"
            any_build = True
        elif (s["full_rate"] - cc["full_rate"]) >= 0.03 and p < 0.10:
            disp = "SIGNAL"
            any_signal = True
        else:
            disp = "DEAD"
        dispositions[arm] = dict(verdict=disp, full=s["full_rate"],
                                 cc80_full=cc["full_rate"],
                                 b_full=b0["full_rate"],
                                 margin=round(s["full_rate"] - cc["full_rate"], 4),
                                 p=round(p, 6), wins=len(w), losses=len(l),
                                 regressions_cat12=reg,
                                 discordant=dict(wins=w, losses=l))
    family = ("BUILD" if any_build else "SIGNAL" if any_signal else "DEAD")
    return {"pop": "cat3+cat4", "cat3_n": len(cat3), "lane_n": len(lane),
            "instrument": log, "arms": arms, "summary": summary,
            "summary_cat3": summary_cat3,
            "oracle_margin": round(oracle_margin, 4),
            "dispositions": dispositions, "family_verdict": family}


def main():
    results = double_run(compute)
    save(ARTIFACTS / "rs003_sem_results.json", results)
    print("R-SEM family:", results["family_verdict"],
          "| oracle margin", results["oracle_margin"],
          "| gold<=8k", results["instrument"]["oracle_gold_fits_8k_in_lane"])
    for a, x in results["dispositions"].items():
        print(f"  {a}: {x['verdict']} full={x['full']} margin={x['margin']} "
              f"p={x['p']} reg={x['regressions_cat12']}")
    for k in sorted(results["summary"]):
        s = results["summary"][k]
        print(f"  {k:24s} full={s['full']:2d}/{s['n']} "
              f"zero@Bmiss={s['zero_among_B_misses']:2d} cov={s['mean_coverage']}")


if __name__ == "__main__":
    main()
