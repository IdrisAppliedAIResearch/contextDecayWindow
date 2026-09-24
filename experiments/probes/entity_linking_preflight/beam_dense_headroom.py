"""BEAM dense-baseline headroom on a SAMPLE (GPU embeddings, no API, no LLM reader).

Closes the decisive cell left open by beam_headroom2.py: of the gold mentions the
lexical retriever (BM25) misses, does the PRODUCT dense retriever (Qwen3-Embedding,
cosine) reach them? Entity-linking only has headroom if there is gold that BOTH
the lexical path AND the dense path miss, yet that is same-entity coreference an
entity bridge would resolve.

Call shape mirrors src/analysis/beam001_gpu_embedding.py exactly:
    Llama(model_path=QWEN, embedding=True, n_ctx=32768, n_gpu_layers=-1).embed(text)
Vectors are L2-normalized for cosine. Questions and messages share one space (the
product uses no query-instruction prefix; model.embed is the pinned call).

Measurement boundary: source_chat_ids used measurement-only, never as input.
"""
from __future__ import annotations
import argparse, gzip, hashlib, io, json, os, re, sys
from collections import Counter
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.abspath(os.path.join(HERE, "..", "..", "comparisons", "beam_001", "artifacts", "corpus"))
MECH = os.path.join(CORPUS, "mechanism_surface.jsonl.gz")
OUT = os.path.join(CORPUS, "outcome_surface.sealed.jsonl.gz")
QWEN = r"C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF\Qwen3-Embedding-0.6B-Q8_0.gguf"
EMBED_DIM = 1024
N_CTX = 32768

WORD = re.compile(r"[a-z0-9]+")
CAP = re.compile(r"[A-Z][A-Za-z0-9]{1,}")
STOP = set("""a about above after again against all also am an and any are as at be because been before being
below between both but by can cannot could did do does doing down during each few for from further had has have
having he her here hers him his how i if in into is it its just me more most my no nor not now of off on once only
or other our out over own same she should so some such than that the their them then there these they this those
through to too under until up very was we were what when where which while who whom why will with you your
hmm okay ok yes yeah great thanks thank sure""".split())


def content_words(s):
    return set(w for w in WORD.findall(s.lower()) if w not in STOP and len(w) > 2)


def entities(s):
    return set(m.lower() for m in CAP.findall(s))


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.doc_t, self.df = [], Counter()
        for _id, text in docs:
            tf = Counter(content_words(text)); self.doc_t.append((_id, tf, sum(tf.values())))
            for t in tf: self.df[t] += 1
        self.N = len(docs)
        self.avgdl = (sum(d[2] for d in self.doc_t) / self.N) if self.N else 1.0

    def rank(self, query):
        q = content_words(query); sc = []
        for _id, tf, dl in self.doc_t:
            s = 0.0
            for t in q & set(tf):
                n = self.df[t]; idf = math.log(1 + (self.N - n + 0.5) / (n + 0.5)); f = tf[t]
                s += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            sc.append((_id, s))
        return [i for i, _ in sorted(sc, key=lambda x: -x[1])]


import math  # used inside BM25.rank


def load():
    mech = [json.loads(l) for l in gzip.open(MECH, "rt", encoding="utf-8")]
    out = {r["question_key"]: r["official_fields"]
           for r in (json.loads(l) for l in gzip.open(OUT, "rt", encoding="utf-8"))}
    return mech, out


def unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--convs", type=int, default=8, help="number of sample conversations")
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    mech, out = load()
    # conversations that HAVE multi_session_reasoning gold, deterministic sample
    cand = []
    for ci, c in enumerate(mech):
        gs = [q for q in c["questions"] if q["category"] == "multi_session_reasoning"
              and isinstance(out[q["question_key"]].get("source_chat_ids"), list)
              and out[q["question_key"]]["source_chat_ids"]]
        if gs:
            cand.append((ci, c, gs))
    import random
    rng = random.Random(a.seed)
    sample = cand if len(cand) <= a.convs else rng.sample(cand, a.convs)
    print(f"sampled {len(sample)} of {len(cand)} gold-bearing conversations")

    from llama_cpp import Llama
    llm = Llama(model_path=QWEN, embedding=True, n_ctx=N_CTX, n_gpu_layers=-1, verbose=False)
    vcache = os.path.join(HERE, "_beam_dense_vecs.npz")
    store = {}
    if os.path.exists(vcache):
        z = np.load(vcache, allow_pickle=False)
        for k in z.files:
            store[k] = z[k]
    dirty = False

    def embed(text):
        nonlocal dirty
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if h in store:
            return store[h]
        v = unit(np.asarray(llm.embed(text), dtype=np.float32))
        store[h] = v; dirty = True
        return v

    tot = dict(mentions=0, bm_reached=0, dense_reached=0,
               bm_miss=0, dense_miss=0, both_miss=0, both_miss_coref=0, both_miss_lex_like=0)
    examples = []
    for ci, c, gs in sample:
        id2m = {}
        for b in c["chat_batches"]:
            for msg in b: id2m.setdefault(msg["id"], msg)
        user_msgs = [(msg["id"], msg["content"]) for b in c["chat_batches"] for msg in b if msg.get("role") == "user"]
        if not user_msgs:
            continue
        bm = BM25(user_msgs)
        # embed messages
        emap = {}
        for mid, txt in user_msgs:
            emap[mid] = embed(txt)
        for q in gs:
            sc = out[q["question_key"]]["source_chat_ids"]
            bmrank = {i: r for r, i in enumerate(bm.rank(q["question"]))}
            qv = embed(q["question"])
            qc, qe = content_words(q["question"]), entities(q["question"])
            drank = sorted((mid for mid, _ in user_msgs), key=lambda m: -float(qv @ emap[m]))
            drank = {i: r for r, i in enumerate(drank)}
            for i in sc:
                msg = id2m.get(i)
                if not msg or i not in emap:
                    continue
                tot["mentions"] += 1
                bm_r = bmrank.get(i, 10**9) < a.topk
                de_r = drank.get(i, 10**9) < a.topk
                if de_r:
                    tot["dense_reached"] += 1
                if bm_r: tot["bm_reached"] += 1
                else:
                    tot["bm_miss"] += 1
                    if not de_r:
                        tot["dense_miss"] += 1
                        tot["both_miss"] += 1
                        mc, me = content_words(msg["content"]), entities(msg["content"])
                        if (qc & mc) or (qe & me):
                            tot["both_miss_lex_like"] += 1
                        else:
                            tot["both_miss_coref"] += 1
                            if len(examples) < 12:
                                examples.append((c["conversation_id"], q["question"],
                                                 msg["content"], drank.get(i, 10**9),
                                                 float(qv @ emap[i])))
    M = tot["mentions"]
    if dirty:
        np.savez(vcache, **store)
    print(f"\n=== BEAM DENSE-BASELINE headroom (sample, topk={a.topk}, seed={a.seed}) ===")
    print(f"gold mentions                          = {M}")
    print(f"reached by BM25@{a.topk}                     = {tot['bm_reached']} ({tot['bm_reached']/max(1,M):.1%})")
    print(f"reached by DENSE@{a.topk}                    = {tot['dense_reached']} ({tot['dense_reached']/max(1,M):.1%})  [dense-only reached counted below via both_miss]")
    bm_only_miss = tot['bm_miss'] - tot['dense_miss']
    print(f"BM25 missed but DENSE reaches          = {bm_only_miss} ({bm_only_miss/max(1,tot['bm_miss']):.0%} of BM25 misses)")
    print(f"MISSED BY BOTH dense AND lexical       = {tot['both_miss']} ({tot['both_miss']/max(1,M):.1%} of gold)  <-- ceiling for ANY retriever improvement")
    print(f"  of those: shares surface link (ranking/dense-failure, NOT coref) = {tot['both_miss_lex_like']}")
    print(f"  of those: NO surface link (coref-resolution headroom)            = {tot['both_miss_coref']} ({tot['both_miss_coref']/max(1,M):.3%} of gold)")
    print("\n--- gold that BOTH paths miss with NO surface link (entity-linking's ONLY possible headroom) ---")
    for cid, q, txt, rank, cos in examples:
        print("-" * 60, f"[dense_rank={rank} cos={cos:.3f}]")
        print("Q:", q[:160].replace(chr(10), " "))
        print("MISS:", txt[:200].replace(chr(10), " "))


if __name__ == "__main__":
    main()
