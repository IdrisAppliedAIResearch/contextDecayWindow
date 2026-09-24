"""Cross-sentence real-data resolver - LitBank (coref-data/litbank_indiscrim, ungated).

WHY (memory SS23-24): knowref name->pronoun is single-sentence and first-mention/surface-copy
dominated: debiased (anonymised slots + saliency-balanced) it fell to 0.50 chance. It cannot
certify non-lexical linking. LitBank has MULTI-SENTENCE chains (e.g. England ... her ... Great
Britain): resolving a later mention to an EARLIER antecedent in another sentence, with no lexical
bridge, is exactly the entity-linking operation at issue.

TASK (mention->antecedent resolution, standard coref formulation):
  target    : an anaphoric mention (later than its chain head) in sentence s.
  context A : a window of sentences around the target, target mention blanked to [ TGT ].
  candidate B: "{surface} is who [ TGT ] refers to."  (candidate surface = an earlier chain head)
  label      : 1 iff candidate chain == target chain. Resolve = argmax over candidates (gold + distractors).

CONTROLS (AGENTS.md SS3), all reported:
  - OVERLAP SPLIT: Jaccard surface overlap of target vs gold candidate. The HEADLINE is the
    ZERO-OVERLAP subset (e.g. pronoun vs name): a lexical copier scores chance there; >0.5 = real linking.
  - DISTANCE CONTROL: accuracy on cases where the gold chain is NOT the nearest-mention candidate
    (a proximity/saliency heuristic fails there).
  - NEGATIVE CONTROL: shuffle gold across targets -> must fall to chance.
This is single-corpus, exploratory, no adoption; a positive here is REAL-DATA evidence past saliency/lexical.
Run: .venv\\Scripts\\python.exe litbank_crosssentence.py
"""
import argparse, json, os, random, subprocess, re
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import pyarrow.parquet as pq
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
STOP = set("a an the of to in on at by for and or is was were be been being he she it they them him her his its their this that as with from".split())


def norm_tokens(s):
    return [w for w in re.findall(r"[a-z0-9']+", s.lower()) if w not in STOP]


def jaccard(a, b):
    A, B = set(norm_tokens(a)), set(norm_tokens(b))
    if not A | B:
        return 0.0
    return len(A & B) / len(A | B)


def load_docs(path):
    rows = pq.read_table(path).to_pylist()
    docs = []
    for r in rows:
        sents = r["sentences"]
        if not sents or "tokens" not in sents[0]:
            continue
        toks, offs, o = [], [], 0
        for s in sents:
            offs.append(o)
            ts = [tk.get("text", "") for tk in s.get("tokens", [])]
            toks += ts; o += len(ts)
        cl = [sorted(ch, key=lambda m: (m[0], m[1])) for ch in r["coref_chains"] if ch]
        docs.append(dict(id=r["id"], genre=r.get("genre", ""), toks=toks, offs=offs,
                         nsent=len(sents), chains=cl))
    return docs


def mention_text(doc, m):
    base = doc["offs"][m[0]]
    return " ".join(doc["toks"][base + m[1]: base + m[2] + 1]).strip()


def make_examples(doc, rng, max_targets=6, max_cands=5, window=35):
    """Yield resolution problems: target = a non-head mention later than its chain head; gold = its
    chain head; distractors = heads of other multi-mention chains. Context = flat-token window with
    the target span blanked to [ TGT ]."""
    chains = [c for c in doc["chains"] if len(c) >= 2]
    if len(chains) < 2:
        return []
    toks = doc["toks"]
    exs = []
    for ci, ch in enumerate(chains):
        hsi, ha, hb = ch[0]
        targets = [m for m in ch[1:] if m[0] > hsi]  # true cross-sentence
        rng.shuffle(targets)
        per = max(1, max_targets // len(chains))
        for t in targets[:per]:
            tsi = t[0]
            base = doc["offs"][tsi]
            gs, ge = base + t[1], base + t[2]
            tsurf = " ".join(toks[gs:ge + 1]).strip()
            gold_surf = mention_text(doc, ch[0])
            if not tsurf or not gold_surf or tsurf.lower() == gold_surf.lower():
                continue
            di = [j for j in range(len(chains)) if j != ci]
            rng.shuffle(di)
            cands = [ch[0]] + [chains[j][0] for j in di[:max_cands - 1]]
            lo, hi = max(0, gs - window), min(len(toks), ge + 1 + window)
            wtoks = toks[lo:hi]
            for wi in range(gs, ge + 1):
                if lo <= wi < hi:
                    wtoks[wi - lo] = "[ TGT ]"
            # distance control: is the gold chain's head the nearest mention to the target?
            def dist(m):
                mb = doc["offs"][m[0]] + m[1]
                return abs(mb - gs)
            gold_d = dist(ch[0])
            near_d = min(dist(c) for c in cands)
            gold_nearest = (gold_d <= near_d)
            exs.append(dict(ctx=" ".join(wtoks), cands=[mention_text(doc, m) for m in cands],
                            gold_idx=0, overlap=jaccard(tsurf, gold_surf),
                            tgt=tsurf, gold=gold_surf, gold_nearest=gold_nearest))
    rng.shuffle(exs)
    return exs


def pair_text(ex, cand):
    return (ex["ctx"], f"{cand} is who [ TGT ] refers to.")


def encode(tok, texts, device, max_len):
    A = [t[0] for t in texts]; B = [t[1] for t in texts]
    enc = tok(A, B, truncation=True, max_length=max_len, padding="max_length", return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def build_pairs(exs, rng):
    X = []
    for ex in exs:
        idx = list(range(len(ex["cands"]))); rng.shuffle(idx)
        for pos, k in enumerate(idx):
            X.append((pair_text(ex, ex["cands"][k]), 1 if k == ex["gold_idx"] else 0))
    rng.shuffle(X)
    return X


def resolve(model, tok, exs, device, max_len):
    """Shuffle candidate order (gold never fixed at index 0) then argmax must hit gold."""
    model.eval(); ok = 0
    random.seed(0)
    with torch.no_grad():
        for ex in exs:
            idx = list(range(len(ex["cands"]))); random.shuffle(idx)
            gpos = idx.index(ex["gold_idx"])
            ts = [pair_text(ex, ex["cands"][k]) for k in idx]
            lg = model(**encode(tok, ts, device, max_len)).logits.softmax(-1)[:, 1]
            ok += (int(torch.argmax(lg).item()) == gpos)
    return ok / max(1, len(exs))


def free_vram_mb():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
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


def acc(model, tok, exs, device, max_len, seed=0):
    model.eval(); ok = 0; random.seed(seed)
    with torch.no_grad():
        for ex in exs:
            idx = list(range(len(ex["cands"]))); random.shuffle(idx)
            g = idx.index(ex["gold_idx"])
            ts = [pair_text(ex, ex["cands"][k]) for k in idx]
            lg = model(**encode(tok, ts, device, max_len)).logits.softmax(-1)[:, 1]
            ok += (int(torch.argmax(lg).item()) == g)
    return ok / max(1, len(exs))


def train_once(args, tre, tok, rng):
    pairs = build_pairs(tre, rng)
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2)
    device = move(model)
    model.train(); opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    nb = max(1, (len(pairs) + args.bs - 1) // args.bs)
    for ep in range(args.epochs):
        rng.shuffle(pairs); tot = 0.0
        for i in range(0, len(pairs), args.bs):
            b = pairs[i:i + args.bs]
            enc = encode(tok, [t for t, _ in b], device, args.max_len)
            y = torch.tensor([l for _, l in b], device=device)
            loss = model(**enc, labels=y).loss
            opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item()
    return model, device, tot / nb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="bert-base-uncased")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-len", type=int, default=128)
    ap.add_argument("--max-ex-doc", type=int, default=15)
    ap.add_argument("--seeds", default="7,11,23")
    ap.add_argument("--out", default=os.path.join(HERE, "litbank_result.json"))
    args = ap.parse_args()

    tr_docs = load_docs(os.path.join(DATA, "litbank_train.parquet"))
    te_docs = load_docs(os.path.join(DATA, "litbank_validation.parquet"))
    rng0 = random.Random(7)
    tre = [e for d in tr_docs for e in make_examples(d, rng0, max_targets=args.max_ex_doc)]
    tee = [e for d in te_docs for e in make_examples(d, rng0, max_targets=args.max_ex_doc * 4)]
    chance = sum(1.0 / len(e["cands"]) for e in tee) / max(1, len(tee))
    # context-shuffled NEGATIVE control set (severs context<->answer).
    ctxs = [e["ctx"] for e in tee]; rng0.shuffle(ctxs)
    tee_neg = [dict(e, ctx=c) for e, c in zip(tee, ctxs)]
    zero = [e for e in tee if e["overlap"] < 1e-6]
    notnear = [e for e in tee if not e["gold_nearest"]]
    print(f"train docs={len(tr_docs)} ex={len(tre)} | val docs={len(te_docs)} ex={len(tee)} "
          f"zero-overlap={len(zero)} gold-not-nearest={len(notnear)}")
    tok = AutoTokenizer.from_pretrained(args.model)
    seeds = [int(s) for s in args.seeds.split(",")]
    res = {"all": [], "zero": [], "notnear": [], "neg": []}
    for sd in seeds:
        rng = random.Random(sd)
        model, device, lastloss = train_once(args, tre, tok, rng)
        a_all = acc(model, tok, tee, device, args.max_len, seed=sd)
        a_zero = acc(model, tok, zero, device, args.max_len, seed=sd)
        a_nn = acc(model, tok, notnear, device, args.max_len, seed=sd)
        a_neg = acc(model, tok, tee_neg, device, args.max_len, seed=sd)
        res["all"].append(a_all); res["zero"].append(a_zero)
        res["notnear"].append(a_nn); res["neg"].append(a_neg)
        print(f"seed {sd} (dev={device} loss {lastloss:.3f}) all={a_all:.3f} zero={a_zero:.3f} "
              f"notnearest={a_nn:.3f} NEG-ctxshuf={a_neg:.3f}")

    def mean(v): return sum(v) / len(v)
    def sd(v):
        if len(v) < 2: return 0.0
        m = mean(v); return (sum((x - m) ** 2 for x in (v)) / (len(v) - 1)) ** 0.5
    print("\n=== RESULT (LitBank cross-sentence mention->antecedent, %d seeds) ===" % len(seeds))
    print(f"acc ALL           = {mean(res['all']):.3f} +/- {sd(res['all']):.3f}  (chance {chance:.3f})")
    print(f"acc ZERO-OVERLAP  = {mean(res['zero']):.3f} +/- {sd(res['zero']):.3f}  ({len(zero)} ex)  HEADLINE")
    print(f"acc GOLD-NOT-NEAREST = {mean(res['notnear']):.3f} +/- {sd(res['notnear']):.3f}  ({len(notnear) if False else len(notnear)} ex)  distance-control")
    print(f"NEG ctx-shuffled  = {mean(res['neg']):.3f}  (must be ~chance {chance:.3f})")
    print("If zero-overlap and gold-not-nearest both clearly > chance AND ctx-shuffled is ~chance,")
    print("the resolver does genuine non-lexical, non-salient cross-sentence linking on REAL coref.")
    json.dump(dict(model=args.model, source="coref-data/litbank_indiscrim (ungated)",
                   seeds=seeds, train_ex=len(tre), test_ex=len(tee), chance=chance,
                   acc_all_mean=mean(res['all']), acc_all_sd=sd(res['all']),
                   acc_zero_overlap_mean=mean(res['zero']), acc_zero_overlap_sd=sd(res['zero']),
                   n_zero=len(zero), acc_notnearest_mean=mean(res['notnear']),
                   n_notnearest=len(notnear),
                   neg_ctxshuffled_mean=mean(res['neg']), epochs=args.epochs),
              open(args.out, "w"), indent=1)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
