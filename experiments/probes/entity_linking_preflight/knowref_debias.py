"""knowref DEBIASED - recover a clean non-lexical signal past the saliency confound.

WHY (see memory SS23): knowref name->pronoun is first-mention biased (gold-first 0.75) and the
[ ANC ] left the gold NAME standing at subject -> positional shortcut. A 1-epoch resolver scored
0.79 overall but 0.285 on saliency-wrong docs -> SALIENCY-DOMINATED, metric was a surrogate.

FIX (this file): ANONYMISE all name mentions to [SLOT0]/[SLOT1]/... so the model cannot string-
match or lean on "the gold name is sitting right there." The pronoun is [ ANC ]. Task: does [ ANC ]
refer to the entity in slot k? Model must use SYNTAX/SEMANTICS/agreement around the anonymous slots.
Evaluate on a SALIENCY-BALANCED held-out set (gold first-slot ~50%) with name-disjoint split; report
acc on the whole balanced set vs 0.5 chance. >0.5 = genuine non-lexical linking (beyond saliency).

Still NOT a multi-sentence HEADROOM claim (knowref is single-sentence). No adoption.
Run: .venv\\Scripts\\python.exe knowref_debias.py
"""
import argparse, json, os, random, subprocess, collections
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import pyarrow.parquet as pq
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PRON = set("he him his she her hers it its they them their theirs he's she's".split())


def is_pron(w):
    return w.lower() in PRON


def load_slotdocs(parquet_path):
    """Slots = distinct name SURFACES. Anonymise ALL mentions: names->[SLOTk], pronouns->[ ANC ].
    Gold slot = the name surface that shares a chain with the pronoun. Requires >=2 distinct name
    surfaces and a unique gold surface, so it is a genuine disambiguation."""
    rows = pq.read_table(parquet_path).to_pylist()
    docs = []
    for r in rows:
        sents = r["sentences"]
        if not sents or "tokens" not in sents[0]:
            continue
        toks = [tk.get("text", "") for s in sents for tk in s.get("tokens", [])]
        offs, o = [], 0
        for s in sents:
            offs.append(o); o += len(s.get("tokens", []))
        chains = r["coref_chains"]

        def mspan(m):
            base = offs[m[0]]
            return " ".join(toks[base + m[1]: base + m[2] + 1]).strip()

        # mention -> (chain_index, global_start, global_end, is_pron)
        mems = []
        for ci, ch in enumerate(chains):
            for m in ch:
                base = offs[m[0]]; gs, ge = base + m[1], base + m[2]
                mems.append((ci, gs, ge, is_pron(mspan(m)), mspan(m)))
        name_mem = [m for m in mems if not m[3]]
        pron_mem = [m for m in mems if m[3]]
        if not pron_mem or len(name_mem) < 2:
            continue
        surfaces = sorted({m[4] for m in name_mem})
        if len(surfaces) < 2:
            continue
        # gold: name surfaces sharing a chain with any pronoun mention
        pron_cis = {m[0] for m in pron_mem}
        gold_surf = {m[4] for m in name_mem if m[0] in pron_cis}
        if len(gold_surf) != 1:
            continue
        gold_surf = next(iter(gold_surf))
        # slot order by first appearance of each surface
        first = {s: min(m[1] for m in name_mem if m[4] == s) for s in surfaces}
        order = sorted(surfaces, key=lambda s: first[s])
        slot = {s: i for i, s in enumerate(order)}
        gold_slot = slot[gold_surf]
        gold_first = (first[gold_surf] == min(first.values()))
        blank = toks[:]
        for ci, gs, ge, is_p, s in mems:
            repl = "[ ANC ]" if is_p else "[SLOT%d]" % slot[s]
            for wi in range(gs, ge + 1):
                if wi < len(blank):
                    blank[wi] = repl
        docs.append(dict(id=r["id"], ctx=" ".join(blank), slots=list(order),
                         gold_slot=gold_slot, gold_first=gold_first, genre=r.get("genre", "")))
    return docs


def pair_text(d, k):
    return (d["ctx"], f"[ ANC ] is [SLOT{k}] , i.e. {d['slots'][k]}.")


def build_pairs(docs, rng):
    X = []
    for d in docs:
        for k in range(len(d["slots"])):
            X.append((pair_text(d, k), 1 if k == d["gold_slot"] else 0))
    rng.shuffle(X)
    return X


def resolve(model, tok, docs, device, max_len):
    model.eval(); ok = 0
    with torch.no_grad():
        for d in docs:
            ts = [pair_text(d, k) for k in range(len(d["slots"]))]
            lg = model(**encode(tok, ts, device, max_len)).logits.softmax(-1)[:, 1]
            ok += (int(torch.argmax(lg).item()) == d["gold_slot"])
    return ok / max(1, len(docs))


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


def encode(tok, texts, device, max_len):
    A = [t[0] for t in texts]; B = [t[1] for t in texts]
    enc = tok(A, B, truncation=True, max_length=max_len, padding="max_length", return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="bert-base-uncased")
    ap.add_argument("--train-docs", type=int, default=4000)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-len", type=int, default=96)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(HERE, "knowref_debias_result.json"))
    args = ap.parse_args()
    rng = random.Random(args.seed)

    pool = load_slotdocs(os.path.join(DATA, "knowref_train.parquet"))
    print("slot docs (2 names + 1 pronoun):", len(pool))
    alln = sorted({s for d in pool for s in d["slots"]}); rng.shuffle(alln)
    hold = set(alln[:int(0.2 * len(alln))])
    tr = [d for d in pool if not (set(d["slots"]) & hold)]
    te = [d for d in pool if (set(d["slots"]) & hold)]
    # saliency-BALANCE both train and test: equal gold-first vs gold-not-first
    def balance(ds, n=None):
        gf = [d for d in ds if d["gold_first"]]; ng = [d for d in ds if not d["gold_first"]]
        m = min(len(gf), len(ng)); rng.shuffle(gf); rng.shuffle(ng)
        out = gf[:m] + ng[:m]; rng.shuffle(out)
        return out[:n] if n else out
    tr_bal = balance(tr, args.train_docs)
    te_bal = balance(te)
    print(f"name-disjoint hold={len(hold)} | tr_bal={len(tr_bal)} te_bal={len(te_bal)} (gold-first ~50%)")

    pairs = build_pairs(tr_bal, rng)
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2)
    device = move(model); print("device=", device, "free=", free_vram_mb())
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
        print(f"epoch {ep+1} loss {tot/nb:.4f} te_bal {resolve(model, tok, te_bal[:200], device, args.max_len):.3f}")

    acc = resolve(model, tok, te_bal, device, args.max_len)
    gf_acc = resolve(model, tok, [d for d in te_bal if d["gold_first"]], device, args.max_len)
    ng_acc = resolve(model, tok, [d for d in te_bal if not d["gold_first"]], device, args.max_len)
    golds = [d["gold_slot"] for d in te_bal]; rng.shuffle(golds)
    neg = resolve(model, tok, [dict(d, gold_slot=g) for d, g in zip(te_bal, golds)], device, args.max_len)
    print("\n=== RESULT (knowref DEBIASED: anonymised slots, saliency-balanced) ===")
    print(f"resolve acc, BALANCED held-out names = {acc:.3f}   (chance 0.500)")
    print(f"  gold-is-first-slot subset          = {gf_acc:.3f}  ({sum(1 for d in te_bal if d['gold_first'])} docs)")
    print(f"  gold-is-NOT-first subset           = {ng_acc:.3f}  ({sum(1 for d in te_bal if not d['gold_first'])} docs)")
    print(f"NEGATIVE CONTROL (gold slot shuffled) = {neg:.3f}   (must be ~0.5)")
    print("Interpret: >0.5 on the NOT-first subset = real linking past saliency; ~0.5 = shortcut only.")
    json.dump(dict(model=args.model, source="coref-data/knowref_60k_indiscrim DEBIASED",
                   mechanism="anonymised [SLOTn] + saliency-balanced eval",
                   holdout_names=len(hold), train_docs=len(tr_bal), test_docs=len(te_bal),
                   balanced_acc=acc, gold_first_acc=gf_acc, gold_notfirst_acc=ng_acc,
                   negative_control=neg, epochs=args.epochs, seed=args.seed),
              open(args.out, "w"), indent=1)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
