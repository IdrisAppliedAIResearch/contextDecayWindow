"""AF-FT-001: retrain the anchor cross-encoder (plan AF_FT_001_PLAN.md, f9e75e9c).

build                 build2.json (frozen splits, gold-in-pool rows, nulls; asserts)
train CONFIG SEED     one checkpoint (R0 V1 V1H V2), prints per-epoch loss
eval                  all checkpoints x sample2(ungated/gated) x E-17, paired stats,
                      V2 calibration + null slices; writes results.json

Plan governs parameters; this file must not diverge from it silently.
"""
import hashlib
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/event_lexicon'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms  # noqa: E402
from ft_pipeline import pool_ids, eligible_all, gap_items, e_texts, LOCOMO, BERT_DIR  # noqa: E402
from score_sample120 import wilson, mcnemar_exact  # noqa: E402

ART5 = ROOT / 'experiments/probes/unified_anchor/artifacts'
ART = HERE / 'artifacts'
SEEDS = [20261011, 20261012, 20261013, 20261014, 20261015]
RNG_NULL, RNG_HOLD, RNG_EVAL = 20261002, 20261003, 20261003
NULL_ROWS, HELDOUT_N, CAT5_N = 800, 120, 50
MARGIN, LS, EPOCHS, LR, WD, BATCH = 0.5, 0.05, 3, 2e-5, 0.01, 16
MAXLEN = 256
CONFIGS = ('R0', 'V1', 'V1H', 'V2')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]


def gold_sets():
    """qid -> ALL in-conversation evidence turn ids (cats1-4 eligible universe)."""
    raw = json.load(open(LOCOMO, encoding='utf-8'))
    convs = arms.load_conversations(LOCOMO)
    out = {}
    for conv in raw:
        cid = conv['sample_id']
        ids = set(i for i, _ in convs[cid])
        for i, q in enumerate(conv['qa']):
            out[f'{cid}:{i}'] = [d for d in q.get('evidence', []) if d in ids]
    return out


def build():
    ART.mkdir(exist_ok=True)
    raw = json.load(open(LOCOMO, encoding='utf-8'))
    convs = arms.load_conversations(LOCOMO)
    gsets = gold_sets()
    sample2 = json.load(open(ART5 / 'sample2.json', encoding='utf-8'))
    pool120 = json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']
    pairs005 = json.load(open(ART5 / 'pairs2.json', encoding='utf-8'))
    s1 = {it['qid'] for it in pool120}
    s2 = {it['qid'] for it in sample2}
    train005_qids = {r['qid'] for r in pairs005['locomo']}

    elig = eligible_all()
    train_pool = [e for e in elig if e['qid'] not in s1 and e['qid'] not in s2]
    assert len(train_pool) == 1291, f'train universe drift {len(train_pool)}'
    assert {r['qid'] for r in pairs005['locomo']} <= {e['qid'] for e in train_pool}

    rng_hold = random.Random(RNG_HOLD)
    heldout = sorted(rng_hold.sample(sorted(e['qid'] for e in train_pool), HELDOUT_N))
    held_set = set(heldout)

    bm_cache = {}
    def bm(cid):
        if cid not in bm_cache:
            bm_cache[cid] = arms.BM25([t for _, t in convs[cid]])
        return bm_cache[cid]

    anchor_rows = []
    n_skipped_now_zero = 0
    for e in train_pool:
        cid = e['sample_id']
        ids = [i for i, _ in convs[cid]]
        texts = [t for _, t in convs[cid]]
        idset = set(ids)
        gi = ids.index(e['gold'])
        gold_idxs = sorted({ids.index(d) for d in gsets[e['qid']] if d in idset})
        P0, s = pool_ids(e['question'], texts, bm(cid))
        if gi not in P0:
            n_skipped_now_zero += 1  # champion would have dropped this row
        P = sorted(set(P0) | {gi})  # gold-in-pool insertion replaces 005's skip
        negs = sorted([i for i in P if i not in gold_idxs], key=lambda i: -s[i])[:6]
        cands = gold_idxs + negs
        anchor_rows.append(dict(qid=e['qid'], cat=e['cat'], q=e['question'],
                                gold_idx=cands.index(gi),
                                gold_idxs=[cands.index(g) for g in gold_idxs],
                                n_pool=len(P),
                                cands=[texts[i] for i in cands],
                                in_heldout=e['qid'] in held_set))
    assert len(anchor_rows) == 1291

    cids = sorted(convs)
    rng_null = random.Random(RNG_NULL)
    srcs = [e for e in train_pool if e['qid'] not in held_set]
    null_rows = []
    for k in range(NULL_ROWS):
        e = rng_null.choice(srcs)
        other = rng_null.choice([c for c in cids if c != e['sample_id']])
        texts = [t for _, t in convs[other]]
        P, s = pool_ids(e['question'], texts, bm(other))
        null_rows.append(dict(qid=f'NULL:{e["qid"]}', q=e['question'],
                              cands=[texts[i] for i in P]))
    assert len(null_rows) == NULL_ROWS

    rng_ev = random.Random(RNG_EVAL)
    held_rows = [r for r in anchor_rows if r['in_heldout']]
    ev = dict()
    ev['anchor'] = [r['qid'] for r in held_rows]
    ev['null'] = []
    for r in held_rows:
        other = rng_ev.choice([c for c in cids if c != r['qid'].split(':')[0]])
        texts = [t for _, t in convs[other]]
        P, _ = pool_ids(r['q'], texts, bm(other))
        ev['null'].append(dict(qid=f'EVALNULL:{r["qid"]}', q=r['q'],
                               cands=[texts[i] for i in P]))
    calib = set(sorted(rng_ev.sample([r['qid'] for r in held_rows], HELDOUT_N // 2)))
    ev['calib_anchor'] = sorted(calib)
    cat5 = []
    for conv in raw:
        cid = conv['sample_id']
        for i, q in enumerate(conv['qa']):
            if str(q.get('category')) == '5':
                cat5.append(dict(qid=f'{cid}:{i}', q=q['question']))
    ev['cat5'] = sorted(cat5, key=lambda d: d['qid'])[:CAT5_N]
    for r in ev['cat5']:
        cid = r['qid'].split(':')[0]
        texts = [t for _, t in convs[cid]]
        P, _ = pool_ids(r['q'], texts, bm(cid))
        r['cands'] = [texts[i] for i in P]

    out = dict(
        inputs=dict(locomo=sha(LOCOMO), sample2=sha(ART5 / 'sample2.json'),
                    pairs2=sha(ART5 / 'pairs2.json')),
        asserts=dict(train_universe=1291, overlap_sample1=0, overlap_sample2=0,
                     n005_recoverable=n_skipped_now_zero),
        heldout=heldout, anchor_rows=anchor_rows, null_rows=null_rows, eval=ev)
    tid = {r['qid'] for r in anchor_rows}
    assert not (tid & s1) and not (tid & s2)
    assert not ({r['qid'] for r in null_rows} & (s1 | s2))
    (ART / 'build2.json').write_text(json.dumps(out), encoding='utf-8')
    print(json.dumps(dict(anchor=len(anchor_rows),
                          multi_gold=sum(1 for r in anchor_rows if len(r['gold_idxs']) > 1),
                          heldout=len(heldout), nulls=NULL_ROWS,
                          eval_null=len(ev['null']), calib_anchor=len(ev['calib_anchor']),
                          cat5=len(ev['cat5']), inputs=out['inputs']), indent=1))


def _rows_for(cfg, b):
    """Training rows: (q, cands, gold_slot_set, is_null)."""
    anchor = b['anchor_rows']
    pairs005 = json.load(open(ART5 / 'pairs2.json', encoding='utf-8'))
    e_rows = [(r['q'], [r['pos']] + r['negs'], {0}, False) for r in pairs005['e']]
    if cfg == 'R0':
        l_rows = [(r['q'], [r['pos']] + r['negs'], {0}, False) for r in pairs005['locomo']]
        return e_rows + l_rows
    if cfg in ('V1', 'V1H', 'V2'):
        sub = [r for r in anchor if not (cfg != 'V1' and r['in_heldout'])]
        a_rows = [(r['q'], r['cands'], set(r['gold_idxs']), False) for r in sub]
        if cfg == 'V2':
            a_rows += [(r['q'], r['cands'], set(), True) for r in b['null_rows']]
        return e_rows + a_rows
    raise ValueError(cfg)


def train(cfg, seed):
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    assert cfg in CONFIGS
    random.seed(seed)
    torch.manual_seed(seed)
    b = json.loads((ART / 'build2.json').read_text(encoding='utf-8'))
    rows = _rows_for(cfg, b)
    use_null = cfg == 'V2'

    class NullHead(torch.nn.Module):
        def __init__(self, base):
            super().__init__()
            self.base = base
            self.tau = torch.nn.Parameter(torch.zeros(1, device='cuda'))

        def scores(self, enc):
            return self.base(**enc).logits[:, 0]

    tokn = AutoTokenizer.from_pretrained(arms.CE_REPO, revision=arms.CE_REVISION)
    base = AutoModelForSequenceClassification.from_pretrained(arms.CE_REPO, revision=arms.CE_REVISION).to('cuda')
    model = NullHead(base) if use_null else base
    dl = DataLoader(rows, batch_size=BATCH, shuffle=True, collate_fn=lambda x: x)
    if use_null:
        # champion wd on the transformer, none on the learned null logit
        opt = torch.optim.AdamW([{'params': base.parameters(), 'weight_decay': WD},
                                 {'params': [model.tau], 'weight_decay': 0.0}], lr=LR)
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)  # champion regime
    steps = EPOCHS * len(dl)
    sch = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    model.train()
    for ep in range(EPOCHS):
        tot = 0.0
        for batch in dl:
            pairs, counts = [], []
            for q, cands, _g, _n in batch:
                counts.append(len(cands))
                pairs += [(q, c) for c in cands]
            enc = tokn([p[0] for p in pairs], [p[1] for p in pairs], padding=True,
                       truncation=True, max_length=MAXLEN, return_tensors='pt').to('cuda')
            flat = model.scores(enc) if use_null else model(**enc).logits[:, 0]
            k = max(counts)
            # -1e9, NOT -inf: soft-target CE gives 0 * -inf = NaN on pad slots
            logits = flat.new_full((len(batch), k + (1 if use_null else 0)), -1e9)
            off = 0
            for bi, c in enumerate(counts):
                logits[bi, :c] = flat[off:off + c]
                off += c
            if use_null:
                logits[:, -1] = model.tau
                anchor_mask = torch.tensor([not x[3] for x in batch], device='cuda')
                logits[anchor_mask, -1] = logits[anchor_mask, -1] + MARGIN  # reject margin on null slot
            tgt = logits.new_zeros(logits.shape)
            for bi, (q, cands, g, is_null) in enumerate(batch):
                if is_null:
                    tgt[bi, -1] = 1.0
                else:
                    # real slots for this row = its own candidates (+ null slot when V2);
                    # smoothing must never touch pad columns
                    real = len(cands) + (1 if use_null else 0)
                    for gi in g:
                        tgt[bi, gi] = (1 - LS if LS > 0 and use_null else 1.0) / len(g)
                    if LS > 0 and use_null:
                        tgt[bi, :len(cands)] += LS / real
                        tgt[bi, -1] += LS / real
            loss = torch.nn.functional.cross_entropy(logits, tgt)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sch.step()
            tot += loss.item()
        print(f'{cfg} seed {seed} epoch {ep} loss {tot / len(dl):.4f}', flush=True)
    ck = ART / f'ckpt_{cfg}_{seed}'
    ck.mkdir(exist_ok=True)
    (base if use_null else model).save_pretrained(ck)
    tokn.save_pretrained(ck)
    if use_null:
        torch.save({'tau': float(model.tau.detach().cpu()[0])}, ck / 'null_head.pt')
    print('saved', ck)


def _loader(cfg, seed):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    ck = ART / f'ckpt_{cfg}_{seed}'
    tokn = AutoTokenizer.from_pretrained(ck)
    model = AutoModelForSequenceClassification.from_pretrained(ck).to('cuda').eval()
    tau = None
    if cfg == 'V2':
        tau = float(torch.load(ck / 'null_head.pt')['tau'])
    return tokn, model, tau


def _score(tokn, model, q, texts, batch=256):
    import torch
    outs = []
    with torch.no_grad():
        for a in range(0, len(texts), batch):
            ch = texts[a:a + 256]
            enc = tokn([q] * len(ch), ch, padding=True, truncation=True,
                       max_length=MAXLEN, return_tensors='pt').to('cuda')
            outs += model(**enc).logits[:, 0].tolist()
    return outs


def _pnull(scores, tau, T=1.0):
    if tau is None:
        return 0.0
    mx = max(scores + [tau])
    ex = [math.exp((s - mx) / T) for s in scores]
    return math.exp((tau - mx) / T) / (sum(ex) + math.exp((tau - mx) / T))


def evaluate():
    import torch
    b = json.loads((ART / 'build2.json').read_text(encoding='utf-8'))
    convs = arms.load_conversations(LOCOMO)
    gsets = gold_sets()
    sample2 = json.load(open(ART5 / 'sample2.json', encoding='utf-8'))
    srcs = {h['id']: h for h in json.load(open(ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs/sources.json', encoding='utf-8'))}
    blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
    e_items = []
    for g in gap_items():
        eps = srcs[g['history']]['episodes']
        e_items.append(dict(qid='E:' + g['id'][:12], query=g['query'],
                            gold=blind[g['id']]['arms']['ANCHORED']['anchor_exceptions'][0],
                            texts=e_texts(eps), ids=[e['id'] for e in eps]))

    items = []
    for it in sample2:
        cid = it['sample_id']
        ids = [i for i, _ in convs[cid]]
        texts = [t for _, t in convs[cid]]
        bm = arms.BM25(texts)
        P, _ = pool_ids(it['question'], texts, bm)
        gset = {d for d in gsets[it['qid']] if d in set(ids)}
        items.append(dict(qid=it['qid'], q=it['question'], gold=it['gold'], gset=gset,
                          texts=texts, ids=ids, gated=P))

    per = {}
    grid = [(c, s) for c in CONFIGS for s in SEEDS if (ART / f'ckpt_{c}_{s}').exists()]
    print(f'checkpoints present: {len(grid)}/20')
    for cfg, seed in grid:
            key = f'{cfg}_{seed}'
            tokn, model, tau = _loader(cfg, seed)
            rec = {}
            for it in items:
                sc = _score(tokn, model, it['q'], it['texts'])
                pred = it['ids'][max(range(len(sc)), key=lambda i: (sc[i], -i))]
                gidx = it['gated']
                gbest = max(gidx, key=lambda i: (sc[i], -i))
                gpred = it['ids'][gbest]
                rec[it['qid']] = dict(exact=int(pred == it['gold']),
                                      any=int(pred in it['gset']),
                                      pnull=_pnull(sc, tau) if tau is not None else None,
                                      gated_exact=int(gpred == it['gold']),
                                      gated_any=int(gpred in it['gset']))
            e_hits = e_un = 0
            for e in e_items:
                sc = _score(tokn, model, e['query'], e['texts'])
                pred = e['ids'][max(range(len(sc)), key=lambda i: (sc[i], -i))]
                e_hits += int(pred == e['gold'])
            rec['_E17'] = e_hits
            for nr in b['eval']['null']:
                sc = _score(tokn, model, nr['q'], nr['cands'])
                rec[nr['qid']] = dict(pnull=_pnull(sc, tau) if tau is not None else None)
            # H120 anchor side: same frozen pool builder as the null side (comparable K)
            for hr in b['anchor_rows']:
                if not hr['in_heldout']:
                    continue
                cid = hr['qid'].split(':')[0]
                texts = [t for _, t in convs[cid]]
                P, _ = pool_ids(hr['q'], texts, arms.BM25(texts))
                sc = _score(tokn, model, hr['q'], [texts[i] for i in P])
                rec[hr['qid']] = dict(pnull=_pnull(sc, tau) if tau is not None else None)
            for cr in b['eval']['cat5']:
                sc = _score(tokn, model, cr['q'], cr['cands'])
                rec[cr['qid']] = dict(pnull=_pnull(sc, tau) if tau is not None else None)
            per[cfg] = per.get(cfg, {})
            per[cfg][seed] = rec
            print(key, 'E17', e_hits,
                  'exact', sum(rec[i['qid']]['exact'] for i in items),
                  'any', sum(rec[i['qid']]['any'] for i in items), flush=True)

    def means(cfg, f):
        return [sum(per[cfg][s][i['qid']][f] for i in items) for s in per[cfg]]

    summary = {}
    for cfg in CONFIGS:
        if cfg not in per:
            continue
        ex, an = means(cfg, 'exact'), means(cfg, 'any')
        n = len(ex)
        summary[cfg] = dict(
            n_seeds=n,
            exact_mean=round(sum(ex) / n, 2), exact_sd=round((sum((x - sum(ex) / n) ** 2 for x in ex) / max(1, n - 1)) ** .5, 2),
            any_mean=round(sum(an) / n, 2), any_sd=round((sum((x - sum(an) / n) ** 2 for x in an) / max(1, n - 1)) ** .5, 2),
            e17=[per[cfg][s]['_E17'] for s in per[cfg]],
            gated_exact_mean=round(sum(sum(per[cfg][s][i['qid']]['gated_exact'] for i in items) for s in per[cfg]) / n, 2),
            gated_any_mean=round(sum(sum(per[cfg][s][i['qid']]['gated_any'] for i in items) for s in per[cfg]) / n, 2))
    mc = {}
    if 'R0' in per:
        for cfg in CONFIGS:
            if cfg == 'R0' or cfg not in per:
                continue
            rows = []
            for s in SEEDS:
                if s not in per[cfg] or s not in per['R0']:
                    continue
                bb = sum(1 for i in items if per[cfg][s][i['qid']]['any'] and not per['R0'][s][i['qid']]['any'])
                cc = sum(1 for i in items if not per[cfg][s][i['qid']]['any'] and per['R0'][s][i['qid']]['any'])
                rows.append(dict(seed=s, b=bb, c=cc, net=bb - cc, p=round(mcnemar_exact(bb, cc), 5)))
            mc[cfg] = rows
    summary['mcnemar_any_vs_R0_sameseed'] = mc

    v2 = per.get('V2', {}).get(SEEDS[0], {})
    calib_a = [v2.get(q, {}).get('pnull') for q in b['eval']['calib_anchor']]
    calib_n = [v2.get(f'EVALNULL:{q}', {}).get('pnull') for q in b['eval']['calib_anchor']]
    eval_a = [v2.get(q, {}).get('pnull') for q in b['eval']['anchor'] if q not in set(b['eval']['calib_anchor'])]
    eval_n = [v2.get(f'EVALNULL:{q}', {}).get('pnull') for q in b['eval']['anchor'] if q not in set(b['eval']['calib_anchor'])]
    cat5 = [v2.get(r['qid'], {}).get('pnull') for r in b['eval']['cat5']]

    def auroc(pos, neg):
        pos, neg = [x for x in pos if x is not None], [x for x in neg if x is not None]
        if not pos or not neg:
            return None
        wins = sum(1 for p in pos for n in neg if p > n) + 0.5 * sum(1 for p in pos for n in neg if p == n)
        return round(wins / (len(pos) * len(neg)), 4)

    # Selective-prediction report: raw threshold sweep on held-out items. AUROC is computed as
    # P(pnull on a true-null > pnull on an anchored question). Monotone rescaling cannot move
    # either number; calibration buys a defensible threshold, not a better ranking.
    h_a = [p for p in eval_a if p is not None]
    h_n = [p for p in eval_n if p is not None]
    table = []
    for tau_thr in (0.05, 0.1, 0.2, 0.4, 0.6, 0.8):
        if not h_a:
            break
        cov = sum(1 for p in h_a if p < tau_thr) / len(h_a)
        leak = sum(1 for p in h_n if p < tau_thr) / len(h_n) if h_n else None
        table.append(dict(threshold=tau_thr, anchor_coverage=round(cov, 4),
                          null_leak=round(leak, 4) if leak is not None else None))
    nulls = dict(
        calib_auroc=auroc([p for p in calib_n if p is not None], [p for p in calib_a if p is not None]),
        heldout_auroc=auroc(h_n, h_a),
        coverage_table=table,
        never_null = bool(h_a and all(p is not None and p < 0.02 for p in h_a + h_n)),
        always_null = bool(h_n and all(p is not None and p > 0.98 for p in h_a + h_n)),
        cat5_descriptive=dict(
            mean_pnull=(round(sum(x for x in cat5 if x is not None)
                              / max(1, sum(1 for x in cat5 if x is not None)), 4)
                        if any(x is not None for x in cat5) else None),
            n=len(cat5)))
    summary['null_head_V2_seed0'] = nulls

    out = dict(plan='f9e75e9c', grid_present=[f'{c}_{s}' for c, s in grid],
               summary=summary,
               raw_per_item={cfg: {str(s): {k: v for k, v in per[cfg][s].items() if not k.startswith('_')}
                                   for s in per[cfg]} for cfg in per})
    (ART / 'results.json').write_text(json.dumps(out), encoding='utf-8')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    {'build': build, 'train': lambda: train(sys.argv[2], int(sys.argv[3])),
     'eval': evaluate}[sys.argv[1]]()
