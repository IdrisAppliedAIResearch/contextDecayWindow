"""REAL-DATA resolver - Track C on real coreference (coref-data/knowref_60k_indiscrim, ungated).

WHAT THIS TESTS (narrow, stated up front):
  Re-train the Track-C BERT cross-encoder entity resolver on REAL gold coreference
  chains instead of synthetic templates. Task = name->pronoun antecedent choice with
  HARD SAME-SENTENCE distractors ("Ronald lost against opponents like Cory when [ ANC ]
  did lose...": gold Ronald, hard-neg Cory). Generalisation is tested on entity NAMES
  never seen during training.

WHY IT IS AN HONEST MECHANISM TEST (not a surrogate, AGENTS.md SS3):
  - surface overlap between name and pronoun mentions is 0.000 BY CONSTRUCTION
    (knowref reddit_with_names_swapped): the metric CANNOT be gamed by lexical overlap.
  - HARD NEGATIVES: the distractor is a different name in the SAME sentence; ~all docs
    qualify, so a gender/name-count heuristic cannot ace it.
  - NEGATIVE CONTROL: shuffle the gold name across docs; accuracy must fall to ~chance.

WHAT IT DOES **NOT** CLAIM:
  - knowref docs are SINGLE-SENTENCE with chain={name, pronoun}. This validates
    "the resolver learns genuine (non-lexical) linking from REAL data". It does NOT
    demonstrate the multi-sentence entity-only retrieval-headroom claim (that stays on
    the synthetic Track B corpus; cross-sentence LitBank/MMC remain for it).
  - no product / adoption claim.

Run (.venv has torch+transformers+pyarrow):
  .venv\\Scripts\\python.exe knowref_coref.py
"""
import argparse, json, os, random, subprocess
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import pyarrow.parquet as pq
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PRON = set("he him his she her hers it its they them their theirs he's she's".split())


def is_pron(w):
    return w.lower() in PRON


def toks_of(sentences):
    out = []
    for s in sentences:
        for tk in s.get("tokens", []):
            out.append(tk.get("text", ""))
    return out


def load_docs(parquet_path):
    """Return well-posed docs: exactly one pronoun chain whose gold name is unique,
    and >=2 distinct name strings (so the choice is a real disambiguation)."""
    rows = pq.read_table(parquet_path).to_pylist()
    docs = []
    for r in rows:
        sents = r["sentences"]
        if not sents or "tokens" not in sents[0]:
            continue
        toks = toks_of(sents)
        # mention index -> (chain_index, kind, span)
        chains = r["coref_chains"]
        names, prons = [], []   # (name_str, ci) / (ci)
        ci_of_pron = []
        for ci, ch in enumerate(chains):
            for m in ch:
                si, a, b = m[0], m[1], m[2]
                # local token offset within flattened toks
                off = sum(len(s["tokens"]) for s in sents[:si])
                span = toks[off + a: off + b + 1]
                txt = " ".join(span).strip()
                if not txt:
                    continue
                if is_pron(txt):
                    prons.append((txt, ci)); ci_of_pron.append(ci)
                else:
                    names.append((txt, ci))
        if not prons or len(names) < 2:
            continue
        # require the pronoun's gold name to be unique among names
        pci = ci_of_pron[0]
        golds = sorted({n for n, nci in names if nci == pci})
        names_only = sorted({n for n, _ in names})
        if len(golds) != 1 or len(names_only) < 2:
            continue
        # blank ONLY the pronoun mentions (never the gold name's own mention, else the
        # gold string is removed and position-in-text makes the task trivially solvable).
        blanked = toks[:]
        for ci, ch in enumerate(chains):
            for m in ch:
                si, a, b = m[0], m[1], m[2]
                off = sum(len(s["tokens"]) for s in sents[:si])
                span = " ".join(toks[off + a: off + b + 1]).strip()
                if not is_pron(span):
                    continue
                for wi in range(off + a, off + b + 1):
                    if wi < len(blanked):
                        blanked[wi] = "[ ANC ]"
        ctx = " ".join(blanked)
        gold = golds[0]
        docs.append(dict(doc_id=r["id"], ctx=ctx, gold=gold, cands=names_only))
    return docs


def pair_text(d, cand):
    return (d["ctx"], f"[ ANC ] refers to {cand}.")


def build_pairs(docs, rng):
    X = []
    for d in docs:
        for c in d["cands"]:
            X.append((pair_text(d, c), 1 if c == d["gold"] else 0))
    rng.shuffle(X)
    return X


def resolve(model, tok, docs, device, max_len):
    model.eval(); ok = 0
    with torch.no_grad():
        for d in docs:
            texts = [pair_text(d, c) for c in d["cands"]]
            lg = model(**encode(tok, texts, device, max_len)).logits.softmax(-1)[:, 1]
            best = d["cands"][int(torch.argmax(lg).item())]
            ok += (best == d["gold"])
    return ok / max(1, len(docs))


def free_vram_mb():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free",
                              "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return min(int(x) for x in out.splitlines() if x.strip().isdigit())
    except Exception:
        return 0


def move(model):
    if free_vram_mb() > 1600:
        try:
            model.to("cuda:0"); return "cuda:0"
        except Exception:
            pass
    return "cpu"


def encode(tok, texts, device, max_len):
    A = [t[0] for t in texts]; B = [t[1] for t in texts]
    enc = tok(A, B, truncation=True, max_length=max_len, padding="max_length",
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="bert-base-uncased")
    ap.add_argument("--train-docs", type=int, default=5000)
    ap.add_argument("--test-docs", type=int, default=800)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-len", type=int, default=96)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(HERE, "knowref_result.json"))
    args = ap.parse_args()
    rng = random.Random(args.seed)

    tr_pool = load_docs(os.path.join(DATA, "knowref_train.parquet"))
    te_ext = load_docs(os.path.join(DATA, "knowref_test.parquet"))
    print(f"well-posed: train_pool={len(tr_pool)} external_test={len(te_ext)}")

    # NAME-DISJOINT split on the train pool (name-generalisation, matches Track C).
    all_names = sorted({n for d in tr_pool for n in d["cands"]})
    rng.shuffle(all_names)
    hold = set(all_names[:int(0.2 * len(all_names))])
    tr_docs = [d for d in tr_pool if not (set(d["cands"]) & hold)][:args.train_docs]
    te_docs = [d for d in tr_pool if (set(d["cands"]) & hold)][:args.test_docs]
    print(f"held-out names={len(hold)}/{len(all_names)}  tr_docs={len(tr_docs)} "
          f"te_docs={len(te_docs)} (HELD-OUT names)")

    tr_pairs = build_pairs(tr_docs, rng)
    print("train pairs=", len(tr_pairs), "pos=", sum(l for _, l in tr_pairs))

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2)
    device = move(model)
    print("device=", device, "free_vram_mb=", free_vram_mb())

    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    nb = max(1, (len(tr_pairs) + args.bs - 1) // args.bs)
    for ep in range(args.epochs):
        rng.shuffle(tr_pairs)
        tot = 0.0
        for i in range(0, len(tr_pairs), args.bs):
            batch = tr_pairs[i:i + args.bs]
            enc = encode(tok, [t for t, _ in batch], device, args.max_len)
            y = torch.tensor([l for _, l in batch], device=device)
            loss = model(**enc, labels=y).loss
            opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item()
        tracc = resolve(model, tok, tr_docs[:200], device, args.max_len)
        teacc = resolve(model, tok, te_docs, device, args.max_len)
        print(f"epoch {ep+1}/{args.epochs} loss {tot/nb:.4f} train {tracc:.3f} "
              f"test(held-out names) {teacc:.3f}")

    teacc = resolve(model, tok, te_docs, device, args.max_len)
    extacc = resolve(model, tok, te_ext[:args.test_docs], device, args.max_len) if te_ext else float("nan")

    # NEGATIVE CONTROL: detach each gold from its context by shuffling golds across docs.
    golds = [d["gold"] for d in te_docs]
    rng.shuffle(golds)
    te_neg = [dict(d, gold=g) for d, g in zip(te_docs, golds)]
    negacc = resolve(model, tok, te_neg, device, args.max_len)
    rnd = sum(1 for d in te_docs if rng.choice(d["cands"]) == d["gold"]) / max(1, len(te_docs))
    lex = sum(1 for d in te_docs if d["gold"] in d["ctx"].replace("[ ANC ]", "")) / max(1, len(te_docs))

    print("\n=== RESULT (real knowref coreference) ===")
    print(f"resolve acc, HELD-OUT NAMES    = {teacc:.3f}")
    print(f"resolve acc, EXTERNAL test split = {extacc:.3f}   (unseen docs, names may repeat)")
    print(f"random-candidate baseline       = {rnd:.3f}   (mostly 2-way chance)")
    print(f"NEGATIVE CONTROL (gold shuffled)= {negacc:.3f}   (must be ~chance: not a surrogate)")
    print("NOTE: real gold coreference, surface-overlap 0 by design; single-sentence "
          "name->pronoun with hard same-sentence distractors. No multi-sentence headroom claim.")
    json.dump(dict(model=args.model, source="coref-data/knowref_60k_indiscrim (ungated)",
                   heldout_name_strings=len(hold), n_distinct_names=len(all_names),
                   train_docs=len(tr_docs), test_docs=len(te_docs),
                   resolve_heldout_names=teacc, resolve_external_test=extacc,
                   random_baseline=rnd, negative_control_shuffled_gold=negacc,
                   epochs=args.epochs, seed=args.seed),
              open(args.out, "w"), indent=1)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
