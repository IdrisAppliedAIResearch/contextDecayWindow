"""BERT-SWAP Stage 0 runner (Option 1: shadow-as-continuation).

Mechanism: per-turn MLM fine-tune warm-continued over the Study 005 user-turn
stream. Reads: script.json (stream) + probes.json (scoring only). Never reads
q_facts_key.md. CPU, deterministic. See STAGE0_SPEC.md.
"""
import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModelForMaskedLM, AutoTokenizer

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent.parent / "study_005" / "script.json"
PROBES = HERE / "probes.json"
RUNS = HERE / "runs"

SEED = 5005
LR = 2e-5
MAX_SEQ = 128
THREADS = 16
CHECKPOINTS = [10, 61, 65, 102, 121]
SLICE_TURNS = [t for t in range(2, 49, 2)]  # 24 sentences, fixed
KEY_SHA = "C1B5C9C484C1BD82A13D7B1599BFEBC78A3200FDBD684A35DBA4D3BB4731ECA7"
SCRIPT_SHA = "D8BA73FD02BFD41BEC156904FB6A3328BBED3D0DA8BFF05E4667D2E450752F01"


def get_tok(model_name):
    """prajjwal1 checkpoints ship vocab.txt only; transformers 5.x needs a fast
    tokenizer. bert-base-uncased carries the identical WordPiece tokenizer
    (vocab_size 30522), so it is the compatible fallback for the ladder."""
    try:
        return AutoTokenizer.from_pretrained(model_name), model_name
    except Exception:
        return AutoTokenizer.from_pretrained("bert-base-uncased"), "bert-base-uncased (fallback)"


def get_model(model_name):
    """prajjwal1 configs predate model_type; rebuild them as BertConfig."""
    try:
        return AutoModelForMaskedLM.from_pretrained(model_name)
    except ValueError:
        from huggingface_hub import snapshot_download
        from transformers import BertConfig
        d = json.loads((Path(snapshot_download(model_name)) / "config.json")
                       .read_text(encoding="utf-8"))
        cfg = BertConfig(**d)
        return AutoModelForMaskedLM.from_pretrained(model_name, config=cfg)


def setup():
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.set_num_threads(THREADS)
    torch.set_grad_enabled(True)
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass


def load_stream(max_turns):
    d = json.loads(SCRIPT.read_text(encoding="utf-8"))
    turns = {t["turn"]: t["user"] for t in d["turns"]}
    return {k: v for k, v in turns.items() if k <= max_turns}


def load_probes():
    return json.loads(PROBES.read_text(encoding="utf-8"))


def mlm_mask(ids, rng):
    labels = ids.clone()
    special = {0, 101, 102}
    for i in range(ids.shape[1]):
        if int(ids[0, i]) in special:
            labels[0, i] = -100
            continue
        r = rng.random()
        if r < 0.15:
            if rng.random() < 0.8:
                ids[0, i] = 103  # [MASK]
            elif rng.random() < 0.5:
                ids[0, i] = rng.randrange(104, 30522)
            # else keep token; label stays original
        else:
            labels[0, i] = -100
    return ids, labels


def train_turn(model, tok, text, turn):
    rng = random.Random(1000 + turn)
    enc = tok(text, truncation=True, max_length=MAX_SEQ, add_special_tokens=True)
    ids = torch.tensor([enc["input_ids"]])
    ids_m, labels = mlm_mask(ids.clone(), rng)
    model.train()
    out = model(input_ids=ids_m, attention_mask=ids.new_ones(ids_m.shape),
                labels=labels)
    loss = out.loss
    if loss.ndim > 0:
        loss = loss.mean()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    return float(loss)


@torch.no_grad()
def slice_loss(model, tok, texts):
    model.eval()
    rng = random.Random(777)
    total, n = 0.0, 0
    for t in texts:
        enc = tok(t, truncation=True, max_length=MAX_SEQ, add_special_tokens=True)
        ids = torch.tensor([enc["input_ids"]])
        ids_m, labels = mlm_mask(ids.clone(), rng)
        out = model(input_ids=ids_m, attention_mask=ids.new_ones(ids_m.shape),
                    labels=labels)
        l = out.loss
        if l.ndim > 0:
            l = l.mean()
        total += float(l)
        n += 1
    return total / max(n, 1)


@torch.no_grad()
def score_clozes(model, tok, probes):
    """MLM pseudo-likelihood: fill cloze, mean logP over answer-span tokens."""
    model.eval()
    results = {}
    B = 16
    for p in probes:
        scores = []
        fills = []
        spans = []
        for c in p["choices"]:
            text = p["pre"] + c + p["post"]
            fills.append(text)
            spans.append((len(p["pre"]), len(p["pre"]) + len(c)))
        for b0 in range(0, len(fills), B):
            chunk = fills[b0:b0 + B]
            sp = spans[b0:b0 + B]
            enc = tok(chunk, padding=True, add_special_tokens=True,
                      return_tensors="pt", return_offsets_mapping=True)
            om = enc.pop("offset_mapping", enc.pop("offsets_mapping", None))
            if om is None:
                raise RuntimeError("tokenizer returned no offset mapping")
            logits = model(**enc).logits
            logp = F.log_softmax(logits, dim=-1)
            for bi in range(len(chunk)):
                s, e = sp[bi]
                tot, cnt = 0.0, 0
                for i, (a, bb) in enumerate(om[bi].tolist()):
                    if a is None or bb is None or (a == bb):
                        continue
                    if a < e and bb > s:
                        tid = int(enc["input_ids"][bi, i])
                        tot += float(logp[bi, i, tid])
                        cnt += 1
                scores.append(tot / max(cnt, 1))
        best = max(range(len(scores)), key=lambda i: scores[i])
        gold = p["gold_idx"]
        best_dis = max((v for i, v in enumerate(scores) if i != gold),
                       default=float("-inf"))
        results[p["fact_id"]] = {
            "scores": [round(s, 6) for s in scores],
            "correct": best == gold,
            "margin": round(scores[gold] - best_dis, 6),
        }
    return results


@torch.no_grad()
def embed_texts(model, tok, texts, bs=16):
    model.eval()
    vecs = []
    for b0 in range(0, len(texts), bs):
        chunk = texts[b0:b0 + bs]
        enc = tok(chunk, padding=True, truncation=True, max_length=MAX_SEQ,
                  add_special_tokens=True, return_tensors="pt")
        out = model(**enc, output_hidden_states=True)
        hid = out.hidden_states[-1]
        mask = enc["attention_mask"].unsqueeze(-1).float()
        v = (hid * mask).sum(1) / mask.sum(1).clamp(min=1e-6)
        v = F.normalize(v, dim=-1)
        vecs.append(v.cpu())
    return torch.cat(vecs, 0)


def train_buffer(model, opt, tok, stream, upto, epochs):
    """Option 2: train freshly-initialized weights on turns 1..upto, past-only."""
    texts = sorted(t for t in stream if t <= upto)
    total, n = 0.0, 0
    for ep in range(epochs):
        order = texts[:]
        random.Random(SEED + upto * 100 + ep).shuffle(order)
        for t in order:
            rng = random.Random(9000 + ep * 10000 + t)
            enc = tok(stream[t], truncation=True, max_length=MAX_SEQ,
                      add_special_tokens=True)
            ids = torch.tensor([enc["input_ids"]])
            ids_m, labels = mlm_mask(ids.clone(), rng)
            model.train()
            out = model(input_ids=ids_m,
                        attention_mask=ids.new_ones(ids_m.shape), labels=labels)
            loss = out.loss
            if loss.ndim > 0:
                loss = loss.mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
            total += float(loss)
            n += 1
    return total / max(n, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--no-train", action="store_true")
    ap.add_argument("--mode", choices=["stream", "retrain"], default="stream")
    ap.add_argument("--cadence", type=int, default=10)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--max-turns", type=int, default=121)
    args = ap.parse_args()

    setup()
    RUNS.mkdir(exist_ok=True)
    stream = load_stream(args.max_turns)
    pdata = load_probes()
    probes = pdata["probes"]
    queries = {q["turn"]: q for q in pdata["queries"]}
    cps = [c for c in CHECKPOINTS if c <= args.max_turns]

    tok, tok_src = get_tok(args.model)
    model = get_model(args.model)
    model.gradient_checkpointing_disable()
    import copy as _copy
    base_state = _copy.deepcopy(model.state_dict())
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    swap_turns = set()
    if args.mode == "retrain":
        swap_turns = {u for u in stream if u % args.cadence == 0} \
            | {max(stream)}

    align_texts = [stream[t] for t in sorted(stream)[:100]]
    slice_texts = [stream[t] for t in SLICE_TURNS if t in stream]
    prev_embed = embed_texts(model, tok, align_texts)
    prev_slice = slice_loss(model, tok, slice_texts) if slice_texts else None

    meta = {"run_id": args.id, "model": args.model, "tokenizer_source": tok_src,
            "seed": SEED, "lr": LR, "mode": args.mode,
            "cadence": args.cadence if args.mode == "retrain" else None,
            "epochs": args.epochs if args.mode == "retrain" else None,
            "swap_turns": sorted(swap_turns) if swap_turns else None,
            "train": not args.no_train, "max_turns": args.max_turns,
            "script_sha256": SCRIPT_SHA, "key_sha256": KEY_SHA,
            "checkpoints": cps}
    (RUNS / f"{args.id}.meta.json").write_text(json.dumps(meta), encoding="utf-8")

    mpath = RUNS / f"{args.id}.metrics.jsonl"
    tpath = RUNS / f"{args.id}.timing.jsonl"
    q3path = RUNS / f"{args.id}.q3.jsonl"
    mpath.write_text("", encoding="utf-8")
    tpath.write_text("", encoding="utf-8")
    q3path.write_text("", encoding="utf-8")

    retrain_mode = args.mode == "retrain"
    for turn in sorted(stream):
        t0 = time.perf_counter()
        rec = {"turn": turn}
        is_swap = (not retrain_mode) or (turn in swap_turns)
        rec["swap"] = bool(is_swap and not args.no_train)
        if args.no_train:
            pass
        elif retrain_mode:
            if turn in swap_turns:
                t_r = time.perf_counter()
                model.load_state_dict(_copy.deepcopy(base_state))
                opt = torch.optim.AdamW(model.parameters(), lr=LR)
                rl = train_buffer(model, opt, tok, stream, turn, args.epochs)
                rec["train_loss"] = round(rl, 6)
                with tpath.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"turn": turn, "wall_s": None,
                                        "reembed_s": None,
                                        "retrain_s": round(
                                            time.perf_counter() - t_r, 2)}) + "\n")
        else:
            loss = train_turn(model, tok, stream[turn], turn)
            opt.step()
            opt.zero_grad(set_to_none=True)
            rec["train_loss"] = round(loss, 6)

        probes_out = score_clozes(model, tok, probes)
        rec["probes"] = probes_out

        if retrain_mode and turn in swap_turns:
            rec["swap_plant_margins"] = {
                p["fact_id"]: probes_out[p["fact_id"]]["margin"]
                for p in probes
                if p["kind"] == "planted" and p["source_turn"] <= turn}

        if is_swap:
            cur_embed = embed_texts(model, tok, align_texts)
            cos = (prev_embed * cur_embed).sum(dim=-1)
            rec["align_cos_mean"] = round(float(cos.mean()), 8)
            rec["align_cos_p10"] = round(float(torch.quantile(cos, 0.10)), 8)
            prev_embed = cur_embed
        else:
            rec["align_cos_mean"] = 1.0
            rec["align_cos_p10"] = 1.0

        if slice_texts and is_swap:
            sl = slice_loss(model, tok, slice_texts)
            rec["slice_loss"] = round(sl, 6)
            if prev_slice:
                rec["slice_delta_ratio"] = round(sl / prev_slice, 6)
            prev_slice = sl

        with mpath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        with tpath.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"turn": turn,
                                "wall_s": round(time.perf_counter() - t0, 3),
                                "reembed_s": None}) + "\n")
        print(f"[{args.id}] turn {turn} done {rec.get('train_loss')}", flush=True)

        if turn in cps:
            cand_turns = sorted(stream)
            cand_embed = embed_texts(model, tok, [stream[t] for t in cand_turns])
            t1 = time.perf_counter()
            for qturn, q in queries.items():
                if qturn not in stream:
                    continue
                if all(g > turn for g in q["gold"]):
                    continue
                qtext = stream[qturn]
                qv = embed_texts(model, tok, [qtext])
                sims = (cand_embed @ qv.T).squeeze(-1)
                order = torch.argsort(sims, descending=True)
                ranks = {g: int((order == cand_turns.index(g)).nonzero()[0])
                         for g in q["gold"]}
                row = {"checkpoint": turn, "query_turn": qturn,
                       "gold": q["gold"], "ranks": {str(g): r for g, r in ranks.items()},
                       "hit3_all": all(r < 3 for r in ranks.values()),
                       "hit5_all": all(r < 5 for r in ranks.values()),
                       "mean_rank": round(sum(ranks.values()) / len(ranks), 3)}
                with q3path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
            rec_re = {"turn": turn, "wall_s": None,
                      "reembed_s": round(time.perf_counter() - t1, 3)}
            with tpath.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec_re) + "\n")

    if not args.no_train:
        torch.save(model.state_dict(), RUNS / f"{args.id}.final.pt")
    print(f"[{args.id}] DONE", flush=True)


if __name__ == "__main__":
    main()
