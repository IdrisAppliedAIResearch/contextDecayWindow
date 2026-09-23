"""RS003 Stage-0 shared harness: pool, packs, coverage, controls, stats.

Zero model calls: every vector is a content-cache lookup; a miss raises.
Design and bars: RS003_STAGE0_PRE_REGISTRATION.md (commit locked first).
"""
from __future__ import annotations

import gzip
import json
import math
import os
import re
import sqlite3
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("PYTHONHASHSEED", "0")
import numpy as np  # noqa: E402

np.seterr(all="raise")
np.random.seed(20261023)  # never used for selection; belt only

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "episodic" / "src"))
from episodic._ranking import rank_cc80, tokenize  # noqa: E402

ART = ROOT / "experiments/probes/anchor_reader/artifacts/af_read002"
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
ADAPTER = ROOT / "experiments/locomo_relevance_timeline/artifacts/adapter.jsonl.gz"
CACHE_DBs = [
    ROOT / "experiments/external/locomo/artifacts/locomo_dev_embeddings.db",
    ROOT / "experiments/components/biological_memory/nf_004/artifacts/nf004_holdout_embeddings.db",
]
LOCOMO = Path("C:/Users/muzaf/Downloads/locomo10.json")
CAPS = (8000, 16000)


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def load_world():
    srcs = {c["sample_id"]: c for c in json.load(open(LOCOMO, encoding="utf-8"))}
    adapter = {}
    with gzip.open(ADAPTER, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            adapter.setdefault(r["conversation"], []).append(r)
    ctx = jload(ART / "contexts.json")
    items = {it["qid"]: it for it in ctx["items"]}
    audit = {r["qid"]: r for r in jload(ROOT / "scratch/audit002_table.json")}
    disc = jload(ROOT / "scratch/audit002_disc_items.json")
    convs = {}
    for cid, c in srcs.items():
        conv = c["conversation"]
        for idx, e in enumerate(adapter[cid]):
            e["idx"] = idx
        convs[cid] = {
            "elements": adapter[cid],
            "qa": c["qa"],
            "turn_date": {},
        }
        for k, v in conv.items():
            if k.startswith("session_") and isinstance(v, list):
                for t in v:
                    convs[cid]["turn_date"][t["dia_id"]] = conv.get(
                        f"{k}_date_time", "")
        for e in adapter[cid]:
            for d in e["dialogue_ids"]:
                convs[cid]["turn_date"].setdefault(d, e["date"])
    golds = {}
    for qid in items:
        cid, sidx = qid.split(":")[0], int(qid.split(":")[1])
        qa = srcs[cid]["qa"][sidx]
        golds[qid] = {
            "cat": str(qa.get("category")),
            "question": qa["question"],
            "gold_answer": qa.get("answer", ""),
            "gold_ids": [e for e in qa.get("evidence", [])
                         if e in convs[cid]["turn_date"]],
        }
    return srcs, convs, items, audit, disc, golds


def load_vectors():
    vecs = {}
    for db in CACHE_DBs:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for text, blob in con.execute("select text, embedding from cache"):
            prior = vecs.get(text)
            if prior is not None and prior != bytes(blob):
                raise SystemExit(
                    f"frozen-cache conflict for {text[:60]!r}: "
                    f"identical text maps to different embeddings across "
                    f"{CACHE_DBs}")
            vecs.setdefault(text, bytes(blob))
        con.close()
    return vecs


def get_vector(vecs, text):
    v = vecs.get(text)
    if v is None:
        raise KeyError(f"cache miss (PF1 violation): {text[:60]!r}")
    return np.frombuffer(v, dtype=np.float32)


def unit(vec):
    n = float(np.linalg.norm(vec.astype(np.float64)))
    if n == 0.0:
        raise ValueError("zero-norm cached vector")
    return vec.astype(np.float64) / n


def episodic_elements(elems, vecs):
    """Episode dicts exactly as af_read002 built them (PF2 identity)."""
    return [dict(id=e["id"], turn_number=j, user_message=e["text"],
                 assistant_message="", searchable_text=e["text"],
                 embedding=vecs[e["text"]])
            for j, e in enumerate(elems)]


def rank_all(elems, question, qvec, vecs):
    """Frozen rank_cc80 over the pool; returns order + component scores."""
    eps = episodic_elements(elems, vecs)
    r = rank_cc80(eps, question, qvec,
                  dense_weight=0.8, bm25_k1=1.2, bm25_b=0.75)
    return r


# --- packer (registered rule: skip-on-overflow exact charge) ---------------

def pack_order(order, elems, cap):
    chosen = []
    chars = 0
    for i in order:
        s = elems[i]["element"]
        add = len(s) + (1 if chosen else 0)
        if chars + add <= cap:
            chosen.append(i)
            chars += add
    return chosen, chars


def pack_ids(ids, elems):
    out = set()
    for i in ids:
        out.update(elems[i]["dialogue_ids"])
    return out


def coverage(gold_ids, pack_ids):
    g = set(gold_ids)
    if not g:
        return None
    return len(g & pack_ids) / len(g)


# --- committed blocks -------------------------------------------------------

DID_RE = re.compile(r'dialogue_ids="([^"]*)"')


def block_dia_ids(block):
    out = set()
    for m in DID_RE.finditer(block):
        out.update(m.group(1).split())
    return out


# --- stats ------------------------------------------------------------------

def sign_test_p_one_sided(wins, losses):
    """Exact one-sided binomial sign test p-value (math only)."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(wins, n + 1))
    return min(1.0, tail / (2 ** n))


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


# --- instrument checks (PF3: run before any metrics are written) -----------

def instrument_checks(world, vecs, log):
    srcs, convs, items, audit, disc, golds = world
    # 1) ORACLE_full coverage == 1.0 on all items
    bad = []
    for qid in items:
        cid = qid.split(":")[0]
        elems = convs[cid]["elements"]
        g = golds[qid]["gold_ids"]
        if not g:
            bad.append((qid, "no gold ids in pool"))
            continue
        pool = set()
        for e in elems:
            pool.update(e["dialogue_ids"])
        if not set(g) <= pool:
            bad.append((qid, "gold outside pool"))
    if bad:
        raise SystemExit(f"ORACLE_full instrument failure: {bad[:5]}")
    log["oracle_full_coverage_1_of_120"] = True

    # 2) B_as_is zero-gold rate on the 14-item forensic population
    n0 = 0
    for d in disc:
        qid = d["qid"]
        cid = qid.split(":")[0]
        bb = block_dia_ids(items[qid]["block_b"])
        if coverage(golds[qid]["gold_ids"], bb) == 0.0:
            n0 += 1
    log["audit14_zero_gold_in_B"] = {"n_items": len(disc), "zero": n0,
                                     "rate": round(n0 / len(disc), 4),
                                     "recorded_note": "forensics recorded ~72%"
                                     " over a 24-item subset; population"
                                     " definition file absent in repo"}

    # 3) B blocks within cap (packer identity check vs committed windows)
    over = [q for q, it in items.items() if len(it["block_b"]) > 8000
            or len(it["block_c"]) > 16000]
    if over:
        raise SystemExit(f"committed blocks over cap: {over[:3]}")
    log["committed_blocks_within_cap"] = True

    # 4) gold cost within 8k / 16k (mechanical admissibility, per family)
    adm8 = adm16 = 0
    for qid in items:
        cid = qid.split(":")[0]
        elems = convs[cid]["elements"]
        gset = set(golds[qid]["gold_ids"])
        idxs = [e["idx"] for e in elems
                if gset & set(e["dialogue_ids"])]
        allc = sum(len(elems[i]["element"]) for i in idxs) + max(0, len(idxs) - 1)
        if allc <= 8000:
            adm8 += 1
        if allc <= 16000:
            adm16 += 1
    log["gold_fits_8k"] = adm8
    log["gold_fits_16k"] = adm16

    # 5) CC80 reproduction identity (AMENDMENT_RS003_001): exact equality of
    #    rank order vs retrieve_long_term's own ranking AND of selected count
    #    vs committed n_cc80. Replaces the registered +-2 pack-count proxy,
    #    which cannot hold: retrieve_long_term budgets its rendered episode
    #    tags, not raw joined text (verified: committed 8k selections carry
    #    >8000 raw chars while ranking order is exactly reproduced).
    from episodic._config import EpisodicConfig
    from episodic._retrieval import retrieve_long_term
    cfg = EpisodicConfig(read_policy="legacy_cc80", recency_window_n=0)
    order_mismatch, count_mismatch = [], []
    for qid, it in items.items():
        cid = qid.split(":")[0]
        elems = convs[cid]["elements"]
        q = golds[qid]["question"]
        if q not in vecs:
            raise SystemExit(f"question vector missing from cache: {qid}")
        alloc = retrieve_long_term(episodes=episodic_elements(elems, vecs),
                                   query_text=q, query_embedding=get_vector(vecs, q),
                                   budget=8000, config=cfg)
        r = rank_all(elems, q, get_vector(vecs, q), vecs)
        if list(alloc.ranking.order) != list(r.order):
            order_mismatch.append(qid)
        if len(alloc.selected_ids) != it["n_cc80"]:
            count_mismatch.append(qid)
    if order_mismatch or count_mismatch:
        raise SystemExit(f"CC80 reproduction failure: order {order_mismatch[:3]}"
                         f" count {count_mismatch[:3]}")
    log["cc80_reproduction_identity"] = {
        "items": len(items), "order_exact": True, "count_exact": True,
        "committed_mean_n_cc80": round(mean(it["n_cc80"] for it in items.values()), 2)}
    return log


def metrics_for_arm(order_fn, qids, convs, golds, cap, vecs):
    """order_fn(qid, elems) -> total order over pool indices."""
    out = {}
    for qid in qids:
        cid = qid.split(":")[0]
        elems = convs[cid]["elements"]
        order = order_fn(qid, elems)
        chosen, chars = pack_order(order, elems, cap)
        cov = coverage(golds[qid]["gold_ids"], pack_ids(chosen, elems))
        out[qid] = dict(coverage=cov, n_packed=len(chosen), chars=chars,
                        full=1 if cov == 1.0 else 0,
                        zero=1 if cov == 0.0 else 0)
    return out


def summarize(metrics, pop_qids, audit):
    pop = [q for q in pop_qids]
    full = sum(m["full"] for q, m in metrics.items() if q in pop)
    zero = sum(m["zero"] for q, m in metrics.items() if q in pop)
    cov = [metrics[q]["coverage"] for q in pop if metrics[q]["coverage"] is not None]
    bmiss = [q for q in pop if audit[q]["B"] == 0]
    bmiss_zero = sum(metrics[q]["zero"] for q in bmiss)
    return dict(n=len(pop), full=full,
                full_rate=round(full / max(1, len(pop)), 4),
                zero=zero, zero_among_B_misses=bmiss_zero,
                n_B_misses=len(bmiss),
                mean_coverage=round(mean(cov), 4),
                mean_chars=round(mean([metrics[q]["chars"] for q in pop]), 1))


def discordant(arm_m, ctrl_m, pop_qids):
    wins = [q for q in pop_qids if arm_m[q]["full"] == 1 and ctrl_m[q]["full"] == 0]
    losses = [q for q in pop_qids if arm_m[q]["full"] == 0 and ctrl_m[q]["full"] == 1]
    return wins, losses


def save(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False,
                                     sort_keys=True), encoding="utf-8")


def double_run(fn):
    """PF6: run a metrics-producing fn twice; require identical output."""
    a = fn()
    b = fn()
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        raise SystemExit("determinism violation: double-run divergence")
    return a
