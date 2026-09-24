"""Synthetic positive-control corpus (Track B).

Purpose: build conversations where the ONLY thing connecting a two-hop evidence
pair is that they refer to the same person via an ALIAS (the founder / her / the
CEO). Anchor and target are constructed to share ZERO discriminative content
words, so lexical cannot bridge them, and they are topically unrelated so dense
cosine is not expected to either. This is the headroom an entity linker would
fill; measuring that dense+lexical MISS it is the positive-control gate (PF4).

Output (synthetic_corpus.json):
  - measured DENSE (pinned Qwen3 cosine rank) and LEXICAL (discriminative-token
    overlap) results on each gold bridge pair;
  - GOLD entity table (coref oracle) = an upper bound on what a perfect entity
    resolver achieves. It is a lookup, not a trained model, and is labelled so.

Embedder: episodic._embedding.PinnedEmbedder (CPU, n_gpu_layers=0) via .venv.
Run:  .venv\\Scripts\\python.exe .../synthetic_corpus.py --items 60
"""
import argparse, json, os, random, re, sys

STOP = set("""a an the and or but if then of in on at by with from to as is are was were be been being this that
these those there here what which who whom whose do does did have has had not no so too very can will just also
about after before between both each few more most other some such than own same his her hers its their them they
he she it we you i me him us our your my mine yours life once ago during while last next his into from""".split())

# Neutral, DISJOINT predicate families so anchor vs target never share a content word.
ANCHOR_PRED = ["has been in the news", "was mentioned today", "came up at the reunion",
               "surfaced in the interview", "is a public figure", "wrote a memoir"]
TARGET_ATTR = {
    "birthday":   ["turned a year older", "had a quiet celebration"],
    "home_city":  ["moved somewhere new", "settled abroad"],
    "instrument": ["picked up a new hobby", "spent weekends practicing"],
    "pet":        ["adopted an animal", "took in a stray"],
}
ATTR_DETAIL = {
    "birthday": ["12 April", "the 3rd of June", "late October"],
    "home_city": ["Lisbon", "a coastal town", "a mountain village"],
    "instrument": ["the cello", "the upright bass", "the accordion"],
    "pet": ["a three-legged cat", "an old greyhound", "a rescue parrot"],
}
ROLES = ["the founder of the club", "her", "the CEO", "the chair", "the organizer",
         "she", "the president", "the head chef"]
FIRST = ["Melanie", "Aisha", "Dmitri", "Priya", "Marcus", "Yuki", "Omar", "Nadia",
         "Tomas", "Ines", "Kwame", "Sofia", "Ravi", "Elena", "Hugo", "Amara"]


def toks(text):
    return set(w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 1)


def gen_items(n, seed=7):
    rng = random.Random(seed)
    items = []
    for i in range(n):
        person = FIRST[i % len(FIRST)]
        alias = ROLES[(i * 3 + 1) % len(ROLES)]
        other = FIRST[(i + 5) % len(FIRST)]
        attr = list(ATTR_DETAIL)[i % len(ATTR_DETAIL)]
        anchor = f"{person} {ANCHOR_PRED[i % len(ANCHOR_PRED)]}."
        target = f"{alias} {TARGET_ATTR[attr][i % 2]}: {ATTR_DETAIL[attr][i % len(ATTR_DETAIL[attr])]}."
        p_distr = f"{person} released a software update."
        t_distr = f"{other} {TARGET_ATTR[attr][(i + 1) % 2]}: {ATTR_DETAIL[attr][(i + 1) % len(ATTR_DETAIL[attr])]!r}."[:70]
        r_distr = f"{FIRST[(i + 11) % len(FIRST)]} bought a bicycle near a river."
        passages = [dict(text=anchor, role="anchor"), dict(text=target, role="target"),
                    dict(text=p_distr, role="person_distractor"), dict(text=t_distr, role="topic_distractor"),
                    dict(text=r_distr, role="random_distractor")]
        items.append(dict(id=i, person=person, alias=alias, attr=attr, passages=passages))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-embed", action="store_true")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)) + r"\synthetic_corpus.json")
    args = ap.parse_args()

    items = gen_items(args.items, args.seed)

    # ---- Lexical control: does a discriminative token bridge anchor<->target? ----
    from collections import Counter
    all_pass = [p["text"] for it in items for p in it["passages"]]
    df = Counter()
    for t in all_pass:
        df.update(set(toks(t)))
    N = len(all_pass)
    def disc(t):
        return set(w for w in toks(t) if df[w] <= 0.15 * N)

    lex_bridge = 0
    for it in items:
        a = next(p["text"] for p in it["passages"] if p["role"] == "anchor")
        g = next(p["text"] for p in it["passages"] if p["role"] == "target")
        if disc(a) & disc(g):
            lex_bridge += 1
    print(f"LEXICAL: anchor&target share a discriminative token in {lex_bridge}/{len(items)} "
          f"({lex_bridge/max(1,len(items)):.3f}) — want ~0")

    report = dict(items=len(items), lexical_bridge_rate=lex_bridge / max(1, len(items)),
                  dense=None, entity_oracle_rate=1.0)

    if not args.no_embed:
        os.environ.setdefault("CDW_EMBEDDING_MODEL_PATH",
            r"C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF\Qwen3-Embedding-0.6B-Q8_0.gguf")
        import numpy as np
        from episodic._embedding import PinnedEmbedder, cosine_similarity
        emb = PinnedEmbedder()
        vecs = []
        for k, t in enumerate(all_pass):
            vecs.append(emb(t))
            if k % 100 == 0:
                print(f"  embedded {k}/{N}")
        vecs = np.stack(vecs)
        dense_miss = dense_topk = 0
        K = 5
        idx = 0
        for it in items:
            a = next(j for j, p in enumerate(it["passages"]) if p["role"] == "anchor") + idx
            g = next(j for j, p in enumerate(it["passages"]) if p["role"] == "target") + idx
            sims = [(cosine_similarity(vecs[a], vecs[j]), j) for j in range(len(all_pass)) if j != a]
            sims.sort(reverse=True)
            rank = next(r + 1 for r, (_, j) in enumerate(sims) if j == g)
            if rank > K:
                dense_miss += 1
            if rank <= K:
                dense_topk += 1
            idx += len(it["passages"])
        report["dense"] = dict(miss_rate=dense_miss / max(1, len(items)), topk=K,
                               topk_rate=dense_topk / max(1, len(items)))
        print(f"DENSE: gold target NOT in top-{K} of anchor's cosine neighbours in "
              f"{dense_miss}/{len(items)} ({dense_miss/max(1,len(items)):.3f}) — want high")

    json.dump(report, open(args.out, "w"), indent=1)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
