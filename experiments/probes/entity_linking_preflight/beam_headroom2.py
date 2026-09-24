"""BEAM cross-session headroom, tightened (zero API, zero LLM).

Fixes the first probe's proxy inflation: capitalization artifacts and generic
tokens counted as "entities." Here a gold mention's reach is decomposed:

  lexical    : shares a content word with the question  (BM25 AND dense can both reach)
  entity-only: shares a PROPER-NOUN entity but NO content word (a real nominal/
               proper-noun bridge; lexical misses it)
  none       : shares neither a content word nor an entity (dense semantic or a
               trained coref resolver's job -- NOT a surface entity bridge)

A proper noun here = a token whose surface form is capitalized in-sentence and is
not a stopword, appearing as a name-like token (also lowercased for matching).
The decisive number for entity-linking headroom:
  gold mentions that are (not reached by BM25@K) AND (entity-only-linked to the
  question). Dense will absorb most; this probe reports the lexical+entity view,
  then dense is measured on a sample separately.
"""
from __future__ import annotations
import argparse, collections, gzip, json, math, os, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.abspath(os.path.join(HERE, "..", "..", "comparisons", "beam_001", "artifacts", "corpus"))
MECH = os.path.join(CORPUS, "mechanism_surface.jsonl.gz")
OUT = os.path.join(CORPUS, "outcome_surface.sealed.jsonl.gz")

WORD = re.compile(r"[a-z0-9]+")
CAP = re.compile(r"[A-Z][A-Za-z0-9]{1,}")  # capitalized, >=2 chars
STOP = set("""a about above after again against all also am an and any are as at be because been before being
below between both but by can cannot could did do does doing down during each few for from further had has have
having he her here hers him his how i if in into is it its just me more most my no nor not now of off on once only
or other our out over own same she should so some such than that the their them then there these they this those
through to too under until up very was we were what when where which while who whom why will with you your
hmm okay ok yes yeah great thanks thank sure""".split())


def content_words(s):
    return set(w for w in WORD.findall(s.lower()) if w not in STOP and len(w) > 2)


def entities(s):
    """Capitalized name-like tokens (proper nouns). Lowercased for matching.
    A capitalized token is treated as a proper noun (BEAM messages are mid-thread,
    sentence starts are usually preceded by punctuation but we accept some noise)."""
    return set(m.lower() for m in CAP.findall(s))


def load():
    mech = [json.loads(l) for l in gzip.open(MECH, "rt", encoding="utf-8")]
    out = {r["question_key"]: r["official_fields"]
           for r in (json.loads(l) for l in gzip.open(OUT, "rt", encoding="utf-8"))}
    return mech, out


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.doc_t = []
        self.df = Counter()
        for _id, text in docs:
            tf = Counter(content_words(text))
            self.doc_t.append((_id, tf, sum(tf.values())))
            for t in tf:
                self.df[t] += 1
        self.N = len(docs)
        self.avgdl = (sum(d[2] for d in self.doc_t) / self.N) if self.N else 1.0

    def rank(self, query):
        q = content_words(query)
        sc = []
        for _id, tf, dl in self.doc_t:
            s = 0.0
            for t in q & set(tf):
                n = self.df[t]
                idf = math.log(1 + (self.N - n + 0.5) / (n + 0.5))
                f = tf[t]
                s += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            sc.append((_id, s))
        return [i for i, _ in sorted(sc, key=lambda x: -x[1])]


def run(topk=10):
    mech, out = load()
    m = dict(q=0, gold=0, mentions=0, reached=0, miss_lex=0, miss_ent_only=0, miss_none=0,
             ent_q_linked_q=0)
    ex_ent = []
    for c in mech:
        id2m = {}
        for b in c["chat_batches"]:
            for msg in b:
                id2m.setdefault(msg["id"], msg)
        user_docs = [(msg["id"], msg["content"]) for b in c["chat_batches"] for msg in b if msg.get("role") == "user"]
        if not user_docs:
            continue
        bm = BM25(user_docs)
        for q in c["questions"]:
            if q["category"] != "multi_session_reasoning":
                continue
            m["q"] += 1
            sc = out[q["question_key"]].get("source_chat_ids")
            if not isinstance(sc, list) or not sc:
                continue
            m["gold"] += 1
            ranked = bm.rank(q["question"])
            rank = {i: r for r, i in enumerate(ranked)}
            qc, qe = content_words(q["question"]), entities(q["question"])
            for i in sc:
                msg = id2m.get(i)
                if not msg:
                    continue
                m["mentions"] += 1
                reached = rank.get(i, 10**9) < topk
                if reached:
                    m["reached"] += 1
                    continue
                mc, me = content_words(msg["content"]), entities(msg["content"])
                if qc & mc:
                    m["miss_lex"] += 1
                elif qe & me:
                    m["miss_ent_only"] += 1
                    if len(ex_ent) < 8:
                        ex_ent.append((q["question"], (qe & me), msg["content"]))
                else:
                    m["miss_none"] += 1
    print(f"=== BEAM tightened headroom (multi_session_reasoning, BM25@{topk}) ===")
    print(f"questions={m['q']} with_gold={m['gold']} gold_mentions={m['mentions']}")
    print(f"reached by BM25@{topk}                 = {m['reached']} ({m['reached']/max(1,m['mentions']):.1%})")
    miss = m['mentions'] - m['reached']
    print(f"MISSED total                           = {miss}")
    print(f"  missed BUT shares content word (lexical -> dense likely reaches) = {m['miss_lex']} ({m['miss_lex']/max(1,miss):.1%} of miss)")
    print(f"  missed, ENTITY-ONLY link (proper-noun bridge, lexical fails)     = {m['miss_ent_only']} ({m['miss_ent_only']/max(1,miss):.1%} of miss)")
    print(f"  missed, NO lexical or entity surface link (dense-semantic/coref) = {m['miss_none']} ({m['miss_none']/max(1,miss):.1%} of miss)")
    print(f"ENTITY-ONLY miss as fraction of ALL gold = {m['miss_ent_only']/max(1,m['mentions']):.3f}")
    print("\n--- entity-only-bridged misses (candidate real headroom) ---")
    for q, sh, txt in ex_ent:
        print("-" * 60)
        print("Q:", q[:150])
        print("shared_ent:", sorted(sh))
        print("MISS:", txt[:160].replace("\n", " "))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=10)
    run(ap.parse_args().topk)
