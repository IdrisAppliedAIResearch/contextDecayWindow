"""Trained entity resolver (minimal honest mechanism) — Track C.

Claim under test (narrow, stated up front):
  A BERT cross-encoder fine-tuned on planted synthetic role chains can resolve
  an anaphoric ALIAS ("the founder", "the CEO") to the correct named entity
  using ONLY the bridging context, and it generalises to entity NAMES never
  seen in training. This is a REAL trained mechanism, not a lookup table.

Task (schema learning, name generalisation):
  context : one bridge sentence, e.g. "Elena founded the company in 2004."
  query   : an alias for one role, e.g. "the founder"
  pair    : pair A = context, pair B = "the founder is Elena."  (sequence pair)
  label   : 1 iff the named candidate is the entity the bridge says fills that
            role. Distractors are entities the bridge ties to a DIFFERENT role.
  resolve : score gold + each distractor, argmax == gold?

What it does NOT claim:
  - aliases are a CLOSED 6-role schema (founder/CEO/organizer/chair/captain/
    designer). Open-world appositional aliases ("Apple, the iPhone maker, ...")
    are untested.
  - trained and evaluated on OUR synthetic template. Held-out NAMES test name
    generalisation, NOT domain generalisation. Real data needs OntoNotes.

Negative control (AGENTS.md §3 — show the metric can fail when the certified
property is false): shuffle bridges so the context no longer supports the gold
answer; resolve accuracy must collapse to chance or the metric is a surrogate.

Run (.venv has torch+transformers+llama_cpp):
  .venv\\Scripts\\python.exe coref_resolver.py
"""
import argparse, json, os, random, subprocess
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

HERE = os.path.dirname(os.path.abspath(__file__))

# (alias, bridge template). The alias refers to whoever the bridge makes the {role}.
BRIDGES = [
    ("the founder", "{name} founded the company in {yr}."),
    ("the CEO", "{name} became the chief executive last spring."),
    ("the organizer", "{name} organized the annual festival."),
    ("the chair", "{name} was elected the chair of the board."),
    ("the captain", "{name} leads the team as its captain."),
    ("the designer", "{name} designed the winning entry."),
]
TRAIN_NAMES = ["Melanie", "Dmitri", "Priya", "Marcus", "Yuki", "Omar", "Nadia", "Tomas",
               "Ines", "Kwame", "Sofia", "Ravi"]
TEST_NAMES = ["Elena", "Hugo", "Amara", "Felix", "Noor", "Diego", "Lucia", "Mateo"]


def gen_docs(names, n, rng):
    """Each example: one gold entity+role, one distractor entity+role, query=gold alias."""
    docs = []
    for _ in range(n):
        gold, distract = rng.sample(names, 2)
        (g_alias, g_bridge), (_, d_bridge) = rng.sample(BRIDGES, 2)
        ctx = [g_bridge.format(name=gold, yr=rng.randint(1990, 2019)),
               d_bridge.format(name=distract, yr=rng.randint(1990, 2019))]
        rng.shuffle(ctx)
        docs.append(dict(ctx=" ".join(ctx), alias=g_alias, gold=gold, cands=[gold, distract]))
    return docs


def pair_text(d, cand):
    # BERT inserts [SEP] between the two sentences of a sequence pair.
    return (d["ctx"], f"{d['alias']} is {cand}.")


def build_pairs(docs, rng):
    X = []
    for d in docs:
        for c in d["cands"]:
            X.append((pair_text(d, c), 1 if c == d["gold"] else 0))
    rng.shuffle(X)
    return X


def shuffle_bridges(docs, rng):
    """Negative control: detach each context from its answer by swapping contexts."""
    ctxs = [d["ctx"] for d in docs]
    rng.shuffle(ctxs)
    out = [dict(d, ctx=ctxs[i]) for i, d in enumerate(docs)]
    return out


def free_vram_mb():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return min(int(x) for x in out.splitlines() if x.strip().isdigit())
    except Exception:
        return 0


def move(model, device):
    for t in ["cuda:0", "cuda", "cpu"]:
        try:
            model.to(t); return t
        except Exception:
            continue
    return "cpu"


def encode(tok, texts, device, max_len):
    """texts: list of (A, B) pairs -> tokenized as a proper sequence pair."""
    A = [t[0] for t in texts]; B = [t[1] for t in texts]
    enc = tok(A, B, truncation=True, max_length=max_len, padding="max_length", return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def resolve(model, tok, docs, device, max_len):
    """Highest-scoring candidate wins; return (frac_gold, ranked_correct list)."""
    model.eval()
    ok, detail = 0, []
    with torch.no_grad():
        for d in docs:
            texts = [pair_text(d, c) for c in d["cands"]]
            logits = model(**encode(tok, texts, device, max_len)).logits.softmax(-1)[:, 1]
            best = int(torch.argmax(logits).item())
            hit = d["cands"][best] == d["gold"]
            ok += hit; detail.append(hit)
    return ok / max(1, len(docs)), detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="bert-base-uncased")
    ap.add_argument("--docs-train", type=int, default=1500)
    ap.add_argument("--docs-test", type=int, default=400)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-len", type=int, default=64)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--save", default=os.path.join(HERE, "resolver_model"))
    ap.add_argument("--out", default=os.path.join(HERE, "resolver_result.json"))
    args = ap.parse_args()
    rng = random.Random(args.seed)

    tok = AutoTokenizer.from_pretrained(args.model)
    tr_docs = gen_docs(TRAIN_NAMES, args.docs_train, rng)
    te_docs = gen_docs(TEST_NAMES, args.docs_test, rng)
    te_neg = shuffle_bridges(te_docs, rng)
    tr_pairs = build_pairs(tr_docs, rng)
    print(f"train docs={len(tr_docs)} pairs={len(tr_pairs)}  test docs={len(te_docs)} (HELD-OUT names)")

    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=2)
    device = move(model, "cpu") if free_vram_mb() > 1400 else "cpu"
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
            y = torch.tensor([lab for _, lab in batch], device=device)
            loss = model(**enc, labels=y).loss
            opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item()
        tracc, _ = resolve(model, tok, tr_docs[:300], device, args.max_len)
        teacc, _ = resolve(model, tok, te_docs, device, args.max_len)
        print(f"epoch {ep+1}/{args.epochs} loss {tot/nb:.4f} train {tracc:.3f} "
              f"test(held-out names) {teacc:.3f}")
    os.makedirs(args.save, exist_ok=True)
    model.save_pretrained(args.save); tok.save_pretrained(args.save)

    teacc, _ = resolve(model, tok, te_docs, device, args.max_len)
    negacc, _ = resolve(model, tok, te_neg, device, args.max_len)
    rnd = sum(1 for d in te_docs if rng.choice(d["cands"]) == d["gold"]) / max(1, len(te_docs))
    lex = sum(1 for d in te_docs if d["gold"] in d["alias"]) / max(1, len(te_docs))
    print(f"\n=== RESULT (held-out names) ===")
    print(f"resolver resolve acc        = {teacc:.3f}")
    print(f"random-candidate baseline    = {rnd:.3f}   (2-way chance)")
    print(f"NEGATIVE CONTROL bridges shuffled = {negacc:.3f}   (must be ~chance: metric is not a surrogate)")
    print(f"lexical(name-in-alias shortcut)   = {lex:.3f}   (~0: the bridge is not a lexical match)")
    print("NOTE: synthetic template, CLOSED 6-role alias schema. Name-generalisation only; NOT a real-data result.")
    json.dump(dict(model=args.model, docs_train=len(tr_docs), docs_test=len(te_docs),
                   test_heldout_names=TEST_NAMES, resolve_acc=teacc, random_baseline=rnd,
                   negative_control_shuffled=negacc, lexical_shortcut=lex, epochs=args.epochs),
              open(args.out, "w"), indent=1)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
