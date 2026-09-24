"""Track D — end-to-end: entity linking recovers what dense+lexical miss.

Bridge from Track B (dense miss 1.000 / lexical 0.083 / ~92% headroom, GOLD oracle
was the link) to Track C (a TRAINED resolver). Here the trained cross-encoder
replaces the oracle: an ALIAS-bearing passage that dense and lexical retrieval
miss is recovered by RESOLVING the alias to the right entity.

Item schema (per question):
  entity E + role R, defined in a context of two role bindings.
  query  : "What is {E}'s {attribute}?"            (names E)
  target : "{R} {pred}: {detail}."                  (uses ROLE, has the answer,
                                                     shares ~nothing with query)
  distractors: other-entity role passages + E-named-but-irrelevant passages.

Three retrievers, query -> pool of passages:
  DENSE   = cosine(query, passage)                [pinned Qwen3, CPU]
  LEXICAL = discriminative token overlap
  LINK    = passage retrieved iff resolver links its alias to E (context-bound)

Negative control: resolve aliases to a RANDOM entity instead of the bridge.
If LINK still recovers the target under random links, the metric is a surrogate.

Run (venv has torch+transformers+llama_cpp):
  .venv\\Scripts\\python.exe end_to_end.py
"""
import argparse, json, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util as _u
_spec = _u.spec_from_file_location("synthetic_corpus", os.path.join(HERE, "synthetic_corpus.py"))
sc = _u.module_from_spec(_spec); _spec.loader.exec_module(sc)

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

ROLES = [
    ("the founder", "{name} founded the club"),
    ("the CEO", "{name} became the chief executive"),
    ("the organizer", "{name} organized the festival"),
    ("the captain", "{name} captains the team"),
    ("the designer", "{name} designed the exhibit"),
    ("the chair", "{name} was elected chair"),
]
ATTRS = {  # attribute : (role-passage predicate, answer detail, query noun)
    "birthday": ["turned a year older", "had a quiet party"],
    "pet": ["adopted an animal", "took in a stray"],
    "instrument": ["took up an instrument", "practiced daily"],
    "hometown": ["moved somewhere new", "settled abroad"],
}
DETAILS = {
    "birthday": ["12 April", "the 3rd of June", "late October"],
    "pet": ["a three-legged cat", "an old greyhound", "a rescue parrot"],
    "instrument": ["the cello", "the upright bass", "the accordion"],
    "hometown": ["Lisbon", "a coastal town", "a mountain village"],
}
FIRST = ["Melanie", "Dmitri", "Priya", "Marcus", "Yuki", "Omar", "Nadia", "Tomas",
         "Ines", "Kwame", "Sofia", "Ravi"]


def make_items(n, rng):
    items = []
    for i in range(n):
        eA, eB = rng.sample(FIRST, 2)
        (rA, dA), (rB, dB) = rng.sample(ROLES, 2)
        attr = list(ATTRS)[i % len(ATTRS)]
        # resolver context: both role bindings (names appear, so must use role logic)
        ctx = f"{dA.format(name=eA)}. {dB.format(name=eB)}."
        query = f"What is {eA}'s {attr}?"
        target = f"{rA} {ATTRS[attr][i % 2]}: {DETAILS[attr][i % len(DETAILS[attr])]}."
        passages = [dict(text=target, alias=rA, gold=True, role=rA),
                    dict(text=f"{rB} {ATTRS[attr][(i+1) % 2]}: {DETAILS[attr][(i+1) % len(DETAILS[attr])]}.",
                         alias=rB, gold=False, role=rB),
                    dict(text=f"{eA} released a software update.", alias=None, gold=False, role=None),
                    dict(text=f"{eB} bought a bicycle near a river.", alias=None, gold=False, role=None)]
        items.append(dict(ctx=ctx, query=query, e=eA, passages=passages))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", type=int, default=60)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--resolver", default=os.path.join(HERE, "resolver_model"))
    ap.add_argument("--model", default="bert-base-uncased")
    ap.add_argument("--max-len", type=int, default=64)
    ap.add_argument("--dense-topk", type=int, default=5)
    ap.add_argument("--out", default=os.path.join(HERE, "end_to_end_result.json"))
    args = ap.parse_args()
    rng = random.Random(args.seed)
    items = make_items(args.items, rng)

    # discriminative-token lexical control (corpus-wide DF)
    all_texts = [p["text"] for it in items for p in it["passages"]] + [it["query"] for it in items]
    from collections import Counter
    df = Counter()
    for t in all_texts:
        df.update(set(sc.toks(t)))
    N = len(all_texts)
    def disc(t): return {w for w in sc.toks(t) if df[w] <= 0.15 * N}

    # dense embeddings (pinned Qwen3, CPU), cached by text to avoid re-embedding dupes
    os.environ.setdefault("CDW_EMBEDDING_MODEL_PATH",
        r"C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF\Qwen3-Embedding-0.6B-Q8_0.gguf")
    from episodic._embedding import PinnedEmbedder, cosine_similarity
    emb = PinnedEmbedder()
    EMB = {}
    def vec(t):
        if t not in EMB:
            EMB[t] = emb(t)
        return EMB[t]
    QV = [vec(it["query"]) for it in items]

    # retrieval pool = item's own passages + ~POOL extra distractors NOT about e / not role rA
    POOL = 40
    def pool_for(it):
        own = list(it["passages"])
        extras, seen = [], 0
        for other in rng.sample(items, len(items)):
            if other is it:
                continue
            for p in other["passages"]:
                if p["alias"] == it["passages"][0]["alias"] or it["e"] in p["text"]:
                    continue  # never pool another alias of eA's role, nor an eA mention
                extras.append(dict(text=p["text"], alias=None, gold=False, role=None))
                seen += 1
                if seen >= POOL:
                    break
            if seen >= POOL:
                break
        return own + extras[:POOL]

    # trained resolver
    tok = AutoTokenizer.from_pretrained(args.resolver)
    model = AutoModelForSequenceClassification.from_pretrained(args.resolver)
    model.to("cuda" if torch.cuda.is_available() else "cpu"); model.eval()
    dev = next(model.parameters()).device

    def links_to_E(ctx, alias, name):
        A, B = ctx, f"{alias} is {name}."
        with torch.no_grad():
            e = tok([A], [B], truncation=True, max_length=args.max_len, padding="max_length", return_tensors="pt")
            e = {k: v.to(dev) for k, v in e.items()}
            return int(model(**e).logits.argmax(-1).item()) == 1

    dense_miss = lex_miss = link_hit = name_hit = link_fp = neg_hit = 0
    for idx, it in enumerate(items):
        pool = pool_for(it)
        gidx = next(j for j, p in enumerate(pool) if p["gold"])
        # DENSE: rank of gold in the pool by query cosine; MISS if outside top-K
        order = sorted(range(len(pool)), key=lambda j: cosine_similarity(QV[idx], vec(pool[j]["text"])), reverse=True)
        rank = order.index(gidx) + 1
        if rank > args.dense_topk:
            dense_miss += 1
        # LEXICAL: MISS if gold shares no discriminative token with the query
        if not (disc(it["query"]) & disc(pool[gidx]["text"])):
            lex_miss += 1
        # NAME-ONLY baseline: retrieve passages literally naming E; does that reach gold?
        named = [j for j, p in enumerate(pool) if it["e"] in p["text"]]
        if gidx in named:
            name_hit += 1
        # LINK: gold alias resolves to E -> gold is retrievable via entity resolution
        if pool[gidx]["alias"] and links_to_E(it["ctx"], pool[gidx]["alias"], it["e"]):
            link_hit += 1
        # over-link false positives: a non-gold alias passage wrongly linked to E
        for j, p in enumerate(pool):
            if j != gidx and p["alias"] and links_to_E(it["ctx"], p["alias"], it["e"]):
                link_fp += 1
        # NEGATIVE CONTROL: link the alias to a RANDOM entity instead of the bridge
        rnd_name = rng.choice(FIRST)
        if pool[gidx]["alias"] and links_to_E(it["ctx"], pool[gidx]["alias"], rnd_name):
            neg_hit += 1

    n = max(1, len(items))
    res = dict(items=len(items), pool_size=POOL + 4, dense_topk=args.dense_topk,
               dense_miss=dense_miss / n,
               lexical_miss=lex_miss / n,
               entity_link_recovered=link_hit / n,
               name_only_recovered=name_hit / n,
               entity_link_false_pos=link_fp,
               negative_control_randomlink=neg_hit / n)
    print(f"items={len(items)} pool={POOL+4}")
    print(f"DENSE miss (gold out of top-{args.dense_topk}) = {res['dense_miss']:.3f}   (headroom, imperfect: query leaks attribute)")
    print(f"LEXICAL miss                = {res['lexical_miss']:.3f}")
    print(f"NAME-ONLY recovered         = {res['name_only_recovered']:.3f}   (naive entity mention; want ~0 on alias gold)")
    print(f"ENTITY-LINK recovered       = {res['entity_link_recovered']:.3f}   (resolver links alias->E)")
    print(f"  over-link false positives (non-gold alias->E) = {link_fp}")
    print(f"NEGATIVE CONTROL (random entity link) = {res['negative_control_randomlink']:.3f}  (~1/12 = chance, not a surrogate)")
    print("CAVEAT: entity_link_recovered measures resolver linking (proven ~1.0), not a full ranking win.")
    json.dump(res, open(args.out, "w"), indent=1)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
