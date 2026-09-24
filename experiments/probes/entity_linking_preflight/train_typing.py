"""CoNLL-2003 entity-typing pipeline (Track A: proves the training rig).

Self-contained: parses the local CoNLL-2003 IOB files, fine-tunes a token
classifier (default bert-small) under a hard VRAM cap, and reports entity-level
P/R/F1 on dev and test. Subword alignment keeps the gold label on the first
subword and masks continuations (label -100), so loss/eval run on words only.

VRAM discipline: refuses to start if free VRAM is below --min-vram (default 1.2 GB)
so it will not OOM the colocated LLM server; a tiny model + short length keeps it
~1-1.5 GB. No HF token needed (model is cached; data is local).
"""
import argparse, os, random, re, subprocess, sys, time

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, AutoModelForTokenClassification

LABELS = ["O", "B-PER", "I-PER", "B-LOC", "I-LOC", "B-ORG", "I-ORG", "B-MISC", "I-MISC"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for i, l in enumerate(LABELS)}


def read_conll(path):
    sents, toks, tags = [], [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                if toks:
                    sents.append((toks, tags)); toks, tags = [], []
                continue
            parts = line.split()
            if parts[0] == "-DOCSTART-":
                continue
            toks.append(parts[0]); tags.append(parts[-1])
    if toks:
        sents.append((toks, tags))
    return sents


def align_features(tok, toks, tags, max_len):
    enc = tok(toks, is_split_into_words=True, max_length=max_len,
              truncation=True, padding="max_length", return_offsets_mapping=True)
    # Gold label on the FIRST subword of each word; mask special + continuation subwords.
    labels = [-100] * len(enc["input_ids"])
    seen = set()
    for idx, wi in enumerate(enc.word_ids()):
        if wi is None:
            continue
        if wi in seen:
            labels[idx] = -100
        else:
            labels[idx] = LABEL2ID.get(tags[wi], 0); seen.add(wi)
    enc["labels"] = labels
    return {k: enc[k] for k in ("input_ids", "attention_mask", "token_type_ids", "labels")
            if k in enc}


def extract_entities(ids, ignore=-100):
    ents, cur, start = [], None, 0
    for i, lab in enumerate(ids):
        if lab in (ignore, "O"):
            if cur:
                ents.append(tuple(cur)); cur = None
            continue
        typ = lab[2:]
        if lab[0] == "B":
            if cur:
                ents.append(tuple(cur))
            cur = [typ, start]; start = i
        elif lab[0] == "I" and cur and cur[0] == typ:
            start = i
        else:
            if cur:
                ents.append(tuple(cur)); cur = None
    if cur:
        ents.append(tuple(cur))
    return set(ents)


def prf(golds, preds):
    tp = sum(len(p & g) for p, g in zip(preds, golds))
    sn = sum(len(g) for g in golds); pn = sum(len(p) for p in preds)
    pr = tp / sn if sn else 0.0; rc = tp / pn if pn else 0.0
    f1 = 2 * pr * rc / (pr + rc) if (pr + rc) else 0.0
    return dict(P=round(pr, 4), R=round(rc, 4), F1=round(f1, 4), gold=sn, pred=pn, tp=tp)


def free_vram_mb():
    """OS truth via nvidia-smi; torch.cuda.mem_get_info over-reports on this host."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=r"experiments/probes/entity_linking_preflight/data")
    ap.add_argument("--model", default="bert-base-uncased")
    ap.add_argument("--full", action="store_true", help="use all train sentences")
    ap.add_argument("--max-train-sent", type=int, default=3000)
    ap.add_argument("--max-len", type=int, default=96)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--min-vram", type=float, default=1.4, help="GB free (nvidia-smi) to use CUDA")
    ap.add_argument("--device", default="auto")
    args = ap.parse_args()

    torch.manual_seed(args.seed); random.seed(args.seed)
    if args.device == "auto":
        free = free_vram_mb() / 1000.0
        print(f"nvidia-smi free {free:.2f} GB")
        device = "cuda" if (torch.cuda.is_available() and free >= args.min_vram) else "cpu"
    else:
        device = args.device
    print(f"device={device} model={args.model} max_len={args.max_len} bs={args.bs} full={args.full}")

    tok = AutoTokenizer.from_pretrained(args.model)
    train = read_conll(os.path.join(args.data, "train.txt"))
    dev = read_conll(os.path.join(args.data, "valid.txt"))
    test = read_conll(os.path.join(args.data, "test.txt"))
    if not args.full:
        train = train[: args.max_train_sent]
    print(f"sents train={len(train)} dev={len(dev)} test={len(test)}")

    t0 = time.time()
    print("aligning..."); tr_f = [align_features(tok, w, g, args.max_len) for w, g in train]
    de_f = [align_features(tok, w, g, args.max_len) for w, g in dev]
    te_f = [align_features(tok, w, g, args.max_len) for w, g in test]
    print(f"aligned in {time.time()-t0:.1f}s")

    model = AutoModelForTokenClassification.from_pretrained(args.model, num_labels=len(LABELS))
    device = move(model, device); print("model on", device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    n = len(tr_f); steps_per = max(1, n // args.bs); steps = int(steps_per * args.epochs)
    print(f"steps={steps}")
    model.train()
    for st in range(steps):
        idx = [random.randrange(n) for _ in range(args.bs)]
        batch = [tr_f[i] for i in idx]
        try:
            enc = {k: torch.tensor([f[k] for f in batch], device=device) for k in batch[0]}
            loss = model(**enc).loss
        except torch.cuda.OutOfMemoryError:
            device = move(model, "cpu"); print("OOM on cuda -> CPU")
            opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
            enc = {k: torch.tensor([f[k] for f in batch], device=device) for k in batch[0]}
            loss = model(**enc).loss
        opt.zero_grad(); loss.backward(); opt.step()
        if st % 20 == 0 or st == steps - 1:
            print(f"  step {st}/{steps} loss {loss.item():.4f}")

    dg, dp = _collect(model, tok, de_f, device, args.bs)
    tg, tp_ = _collect(model, tok, te_f, device, args.bs)
    print("dev ", prf(dg, dp))
    print("test", prf(tg, tp_))


def _collect(model, tok, feats, device, bs):
    model.eval(); golds, preds = [], []
    with torch.no_grad():
        for i in range(0, len(feats), bs):
            batch = feats[i:i + bs]
            enc = {k: torch.tensor([f[k] for f in batch], device=device) for k in batch[0]}
            out = model(**enc).logits.argmax(-1).tolist()
            for f, o in zip(batch, out):
                g = [ID2LABEL[l] for l in f["labels"] if l != -100]
                p = [ID2LABEL[o[j]] for j, l in enumerate(f["labels"]) if l != -100]
                golds.append(extract_entities(g)); preds.append(extract_entities(p))
    return golds, preds


if __name__ == "__main__":
    main()
