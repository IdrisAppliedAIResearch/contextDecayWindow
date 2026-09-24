"""BEAM cross-session entity-bridging HEADROOM probe (zero API, zero LLM).

Question: on BEAM's multi_session_reasoning questions (gold = source_chat_ids =
the exact message ids that carry the answer, scattered across sessions), is the
gold evidence reachable by the lexical retriever the product runs (BM25), or does
reaching it require an entity bridge that BM25/dense cannot form?

Headroom definition (mirrors the LoCoMo content-join preflight):
  gold mention M is an ENTITY-BRIDGE OPPORTUNITY if
    (a) BM25(question) does NOT surface M in top-K, AND
    (b) M shares an entity (proper-noun / rare-token) with the question or with
        another gold mention that IS reachable  -- i.e. a linking edge exists
        that the lexical/dense path does not exploit.
  Headroom = fraction of questions with >=1 such unreachable-but-linked gold
  mention. Zero headroom (like LoCoMo) => entity linking is the wrong lever.

Measurement boundary: outcome_surface (source_chat_ids) is used MEASUREMENT-ONLY
to score; it is never a retrieval input. No model call is made.

Usage:
  python beam_headroom.py [--topk 10] [--cat multi_session_reasoning]
"""
from __future__ import annotations
import argparse, collections, gzip, json, math, os, re, sys
from collections import Counter, defaultdict

CORPUS = r"C:\Users\muzaf\PycharmProjects\contextDecayWindow\experiments\comparisons\beam_001\artifacts\corpus"
MECH = os.path.join(CORPUS, "mechanism_surface.jsonl.gz")
OUT = os.path.join(CORPUS, "outcome_surface.sealed.jsonl.gz")


def load():
    mech = [json.loads(l) for l in gzip.open(MECH, "rt", encoding="utf-8")]
    out = {r["question_key"]: r["official_fields"]
           for r in (json.loads(l) for l in gzip.open(OUT, "rt", encoding="utf-8"))}
    return mech, out


WORD = re.compile(r"[a-z0-9]+")
STOP = set("""a an and are as at be but by for from has have he her his i if in into is it its me my of on or our so that the their them they this to was we were what when which who will with you your not no than then them""".split())


def toks(s):
    return [w for w in WORD.findall(s.lower()) if w not in STOP]


# Proper-noun-ish entities: capitalized runs, and lowercase rare technical tokens.
ENT = re.compile(r"[A-Z][A-Za-z0-9]+(?:[ \-][A-Z][A-Za-z0-9]+)*")


def ents(s):
    out = set()
    for m in ENT.findall(s):
        m = m.strip(" -")
        # drop single leading capital that is just sentence start (word is common lowercase)
        out.add(m)
        out.add(m.lower())
    return out


def rare_tokens(counter_df, min_df, max_df):
    return None  # placeholder; computed per-conversation below


class BM25:
    """Standard Okapi BM25 over a list of (id, text)."""
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.doc_t = []
        self.df = Counter()
        for _id, text in docs:
            tf = Counter(toks(text))
            self.doc_t.append((_id, tf, sum(tf.values())))
            for t in tf:
                self.df[t] += 1
        self.N = len(docs)
        self.avgdl = (sum(d[2] for d in self.doc_t) / self.N) if self.N else 1.0

    def score(self, query):
        q = set(toks(query))
        scores = []
        for _id, tf, dl in self.doc_t:
            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                n = self.df[t]
                idf = math.log(1 + (self.N - n + 0.5) / (n + 0.5))
                f = tf[t]
                s += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            scores.append((_id, s))
        return scores


def analyze(cat, topk):
    mech, out = load()
    n_q = 0
    has_gold = 0
    span_sessions = Counter()
    unreachable_linked = 0     # HEADROOM: >=1 gold mention not in BM25 top-K but entity-linked
    all_reachable = 0          # every gold mention surfaced by BM25 top-K (no bridge needed)
    no_bridge = 0              # unreachable gold mention with NO entity edge either (dense's job, not entity's)
    frac_gold_in_topk = []     # per-question recall of gold by BM25@K
    examples = []
    for c in mech:
        id2m = {}
        for b in c["chat_batches"]:
            for m in b:
                id2m.setdefault(m["id"], m)
        user_docs = []
        for b in c["chat_batches"]:
            for m in b:
                if m.get("role") == "user":
                    user_docs.append((m["id"], m["content"]))
        if not user_docs:
            continue
        bm = BM25(user_docs)
        all_ent = Counter()
        for _id, m in id2m.items():
            for e in ents(m["content"]):
                all_ent[e] += 1
        for q in c["questions"]:
            if q["category"] != cat:
                continue
            n_q += 1
            sc = out[q["question_key"]].get("source_chat_ids")
            if not isinstance(sc, list) or not sc:
                continue
            has_gold += 1
            gold = [id2m[i] for i in sc if i in id2m]
            gsess = set()
            for b in c["chat_batches"]:
                for m in b:
                    if m["id"] in sc:
                        gsess.add(id(b))
            span_sessions[len(gsess)] += 1
            ranked = [i for i, _ in sorted(bm.score(q["question"]), key=lambda x: -x[1])]
            rank = {i: r for r, i in enumerate(ranked)}
            in_topk = [i for i in sc if rank.get(i, 10**9) < topk]
            frac_gold_in_topk.append(len(in_topk) / len(sc))
            qe = ents(q["question"])
            # entity-linked if a gold mention shares an entity with the question
            linked = any(qe & ents(m["content"]) for m in gold)
            if len(in_topk) == len(sc):
                all_reachable += 1
            else:
                if linked:
                    unreachable_linked += 1
                    if len(examples) < 6:
                        miss = [m for m in gold if rank.get(m["id"], 10**9) >= topk]
                        examples.append((q["question"], len(sc), len(in_topk),
                                         [e for e in qe if any(e in mm["content"] for mm in miss)][:6],
                                         [m["content"][:110] for m in miss[:3]]))
                else:
                    no_bridge += 1
    import statistics
    print(f"=== BEAM headroom probe: category={cat} topk={topk} ===")
    print(f"questions in category        = {n_q}")
    print(f"with gold source_chat_ids    = {has_gold}")
    print(f"gold-session span            = {dict(sorted(span_sessions.items()))}")
    print(f"mean gold recall by BM25@{topk}   = {statistics.mean(frac_gold_in_topk):.3f} over {len(frac_gold_in_topk)} q")
    print(f"  all gold reachable (no bridge needed) = {all_reachable}")
    print(f"  UNREACHABLE but entity-linked (HEADROOM)= {unreachable_linked}")
    print(f"  unreachable, NO entity edge (dense/other's job) = {no_bridge}")
    if has_gold:
        print(f"HEADROOM fraction (entity-bridge can help) = {unreachable_linked/has_gold:.3f}")
    for q, ng, nr, sh, mt in examples:
        print("-" * 60)
        print("Q:", q[:160])
        print(f"   gold={ng} reached@{topk}={nr} shared_ent={sh}")
        for t in mt:
            print("   MISS:", t.replace(chr(10), " "))
    return unreachable_linked, has_gold


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", default="multi_session_reasoning")
    ap.add_argument("--topk", type=int, default=10)
    a = ap.parse_args()
    analyze(a.cat, a.topk)
