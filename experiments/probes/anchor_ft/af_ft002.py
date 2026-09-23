"""AF-FT-002: V1 landscape forensics + teacher-filtered reintroduction (plan AF_FT_002_003_PLANS.md, 3f841945).

forensics        V1 vs R0 ungated top-1 landscape (BM25 rank, overlap, pool membership)
filter           champion scores the 519 excluded rows; survivors = teacher ranks gold top-1
train CFG SEED   F1 / F2 (rows per plan; generic loss margin/ls parameters)
eval             F configs x sample2 ungated/gated/E17, paired vs R0 raws; F2 null quality

Plan governs parameters; this file must not diverge from it silently.
"""
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms  # noqa: E402
import af_ft001 as F  # noqa: E402
from ft_pipeline import pool_ids, eligible_all  # noqa: E402
from score_sample120 import mcnemar_exact  # noqa: E402

ART = F.ART
ART2 = ART / 'ft002'
ART5 = F.ART5
SEEDS = F.SEEDS
EPOCHS, LR, WD, BATCH, MAXLEN = F.EPOCHS, F.LR, F.WD, F.BATCH, F.MAXLEN
MARGIN, LS = F.MARGIN, F.LS


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]


def _build():
    return json.loads((ART / 'build2.json').read_text(encoding='utf-8'))


def _pairs005():
    return json.load(open(ART5 / 'pairs2.json', encoding='utf-8'))


def _excluded_rows(b):
    """anchor_rows the champion (pairs2.json locomo 772) never trained on."""
    champ = {r['qid'] for r in _pairs005()['locomo']}
    return [r for r in b['anchor_rows'] if r['qid'] not in champ]


def _convs():
    return arms.load_conversations(F.LOCOMO)


def _items(convs, b):
    gsets = F.gold_sets()
    out = []
    for it in json.load(open(ART5 / 'sample2.json', encoding='utf-8')):
        cid = it['sample_id']
        ids = [i for i, _ in convs[cid]]
        texts = [t for _, t in convs[cid]]
        P, _s = pool_ids(it['question'], texts, arms.BM25(texts))
        out.append(dict(qid=it['qid'], q=it['question'], gold=it['gold'],
                        gset={d for d in gsets[it['qid']] if d in set(ids)},
                        texts=texts, ids=ids, pool=set(P),
                        bm_rank={i: r for r, i in enumerate(
                            sorted(range(len(texts)),
                                   key=lambda i: -_s[i]))}))
    return out


def _tok_text(q):
    import re
    return set(re.findall(r'[a-z0-9]+', q.lower()))


# ---------------------------------------------------------------- forensics

def forensics(seed=SEEDS[0]):
    import torch
    ART2.mkdir(exist_ok=True)
    convs = _convs()
    items = _items(convs, _build())
    out = {}
    for cfg in ('R0', 'V1'):
        tokn, model, _ = F._loader(cfg, seed)
        recs = []
        for it in items:
            sc = F._score(tokn, model, it['q'], it['texts'])
            order = sorted(range(len(sc)), key=lambda i: (-sc[i], i))
            pred = order[0]
            any_gold = it['ids'][pred] in it['gset']
            gj = _tok_text(it['q'])
            pj = _tok_text(it['texts'][pred])
            gold_best_rank = min(
                next(k for k, i in enumerate(order) if it['ids'][i] in it['gset'])
                for _ in [0]) if it['gset'] else None
            recs.append(dict(qid=it['qid'], miss=int(not any_gold),
                             bm_rank=it['bm_rank'][pred],
                             in_pool=int(pred in it['pool']),
                             jacc=round(len(gj & pj) / max(1, len(gj | pj)), 4),
                             gold_rank=gold_best_rank))
        out[cfg] = recs

    def stats(recs):
        def med(xs):
            xs = sorted(xs)
            return xs[len(xs) // 2] if xs else None
        sel = [r for r in recs if r['miss']]
        return dict(
            n=len(recs), n_miss=len(sel),
            pred_bm_rank_med_all=med([r['bm_rank'] for r in recs]),
            pred_bm_rank_med_miss=med([r['bm_rank'] for r in sel]),
            pred_in_pool_all=round(sum(r['in_pool'] for r in recs) / len(recs), 4),
            pred_in_pool_miss=round(sum(r['in_pool'] for r in sel) / max(1, len(sel)), 4),
            jacc_med_all=med([r['jacc'] for r in recs]),
            jacc_med_miss=med([r['jacc'] for r in sel]),
            gold_rank_med_all=med([r['gold_rank'] for r in recs]))
    summary = {cfg: stats(out[cfg]) for cfg in out}
    (ART2 / 'forensics.json').write_text(
        json.dumps(dict(seed=seed, summary=summary, raw=out), indent=1), encoding='utf-8')
    print(json.dumps(summary, indent=1))


# ---------------------------------------------------------------- filter

def filt():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    ART2.mkdir(exist_ok=True)
    b = _build()
    convs = _convs()
    gold_to_turn = {e['qid']: e['gold'] for e in eligible_all()}
    tokn = AutoTokenizer.from_pretrained(ART5 / 'ckpt2')
    teacher = AutoModelForSequenceClassification.from_pretrained(ART5 / 'ckpt2').to('cuda').eval()
    rows = []
    for r in _excluded_rows(b):
        cid = r['qid'].split(':')[0]
        texts = [t for _, t in convs[cid]]
        ids = [i for i, _ in convs[cid]]
        P, _ = pool_ids(r['q'], texts, arms.BM25(texts))
        gid = ids.index(gold_to_turn[r['qid']])
        cand_i = sorted(set(P) | {gid})
        sc = F._score(tokn, teacher, r['q'], [texts[i] for i in cand_i])
        gs = sc[cand_i.index(gid)]
        better = sum(1 for i, s in zip(cand_i, sc) if i != gid and s > gs)
        rows.append(dict(qid=r['qid'], gold_teacher_rank=better + 1,
                         survivor=int(better == 0), n_cand=len(cand_i)))
    surv = [r['qid'] for r in rows if r['survivor']]
    summary = dict(excluded=len(rows), survivors=len(surv),
                   rank_hist={}, teacher='ckpt2', teacher_sha=sha(ART5 / 'ckpt2' / 'model.safetensors'))
    for r in rows:
        k = str(r['gold_teacher_rank']) if r['gold_teacher_rank'] <= 6 else '7+'
        summary['rank_hist'][k] = summary['rank_hist'].get(k, 0) + 1
    (ART2 / 'filter.json').write_text(
        json.dumps(dict(summary=summary, survivors=sorted(surv), rows=rows), indent=1), encoding='utf-8')
    print(json.dumps(summary, indent=1))


# ---------------------------------------------------------------- rows / train

def rows_for(tag, b):
    e_rows = [(r['q'], [r['pos']] + r['negs'], {0}, False) for r in _pairs005()['e']]
    surv = set(json.loads((ART2 / 'filter.json').read_text(encoding='utf-8'))['survivors'])
    held = set(b['heldout'])
    champ = [(r['qid'], r['q'], [r['pos']] + r['negs'], {0}) for r in _pairs005()['locomo']]
    s_rows = [(r['qid'], r['q'], r['cands'], set(r['gold_idxs']))
              for r in b['anchor_rows'] if r['qid'] in surv]
    loc = champ + s_rows
    if tag == 'F1':
        return e_rows + [(q, c, g, False) for _qid, q, c, g in loc]
    if tag == 'F2':
        rows = [(q, c, g, False) for qid, q, c, g in loc if qid not in held]
        rows += [(r['q'], r['cands'], set(), True) for r in b['null_rows']]
        return rows
    raise ValueError(tag)


def train(tag, seed, margin=MARGIN, ls=LS, rows=None, use_null=None, outdir=None):
    """Generic AF-FT-001 trainer with margin/ls as explicit knobs (AF-FT-003 reuses)."""
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    if use_null is None:
        use_null = tag.endswith('2') or tag.startswith('N')
    random.seed(seed)
    torch.manual_seed(seed)
    if rows is None:
        rows = rows_for(tag, _build())

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
        opt = torch.optim.AdamW([{'params': base.parameters(), 'weight_decay': WD},
                                 {'params': [model.tau], 'weight_decay': 0.0}], lr=LR)
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
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
            logits = flat.new_full((len(batch), k + (1 if use_null else 0)), -1e9)
            off = 0
            for bi, c in enumerate(counts):
                logits[bi, :c] = flat[off:off + c]
                off += c
            if use_null:
                logits[:, -1] = model.tau
                if margin > 0:
                    anchor_mask = torch.tensor([not x[3] for x in batch], device='cuda')
                    logits[anchor_mask, -1] = logits[anchor_mask, -1] + margin
            tgt = logits.new_zeros(logits.shape)
            for bi, (q, cands, g, is_null) in enumerate(batch):
                if is_null:
                    tgt[bi, -1] = 1.0
                else:
                    real = len(cands) + 1
                    for gi in g:
                        tgt[bi, gi] = ((1 - ls) if ls > 0 else 1.0) / len(g)
                    if ls > 0:
                        tgt[bi, :len(cands)] += ls / real
                        tgt[bi, -1] += ls / real
            loss = torch.nn.functional.cross_entropy(logits, tgt)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sch.step()
            tot += loss.item()
        print(f'{tag} seed {seed} margin {margin} ls {ls} epoch {ep} loss {tot / len(dl):.4f}', flush=True)
    ck = Path(outdir) if outdir else ART / f'ckpt_{tag}_{seed}'
    ck.mkdir(parents=True, exist_ok=True)
    (base if use_null else model).save_pretrained(ck)
    tokn.save_pretrained(ck)
    if use_null:
        torch.save({'tau': float(model.tau.detach().cpu()[0])}, ck / 'null_head.pt')
    print('saved', ck)


def loader(tag, seed):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    ck = ART / f'ckpt_{tag}_{seed}'
    tokn = AutoTokenizer.from_pretrained(ck)
    model = AutoModelForSequenceClassification.from_pretrained(ck).to('cuda').eval()
    tau = float(torch.load(ck / 'null_head.pt')['tau']) if (ck / 'null_head.pt').exists() else None
    return tokn, model, tau


# ---------------------------------------------------------------- eval

def evaluate(tags=('F1', 'F2'), outpath=None):
    b = _build()
    convs = _convs()
    items = _items(convs, b)
    r0 = json.loads((ART / 'results.json').read_text(encoding='utf-8'))['raw_per_item']['R0']
    per = {}
    for tag in tags:
        per[tag] = {}
        for seed in SEEDS:
            if not (ART / f'ckpt_{tag}_{seed}').exists():
                continue
            tokn, model, tau = loader(tag, seed)
            rec = {}
            for it in items:
                sc = F._score(tokn, model, it['q'], it['texts'])
                pred = it['ids'][max(range(len(sc)), key=lambda i: (sc[i], -i))]
                gbest = max(it['pool'], key=lambda i: (sc[i], -i))
                rec[it['qid']] = dict(
                    exact=int(pred == it['gold']), any=int(pred in it['gset']),
                    gated_exact=int(it['ids'][gbest] == it['gold']),
                    gated_any=int(it['ids'][gbest] in it['gset']))
            e_hits = 0
            gsrc = {h['id']: h for h in json.load(open(ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs/sources.json', encoding='utf-8'))}
            blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
            for g in F.gap_items():
                eps = gsrc[g['history']]['episodes']
                gold = blind[g['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
                ttexts, tids = F.e_texts(eps), [e['id'] for e in eps]
                sc = F._score(tokn, model, g['query'], ttexts)
                e_hits += int(tids[max(range(len(sc)), key=lambda i: (sc[i], -i))] == gold)
            rec['_E17'] = e_hits
            if tau is not None:
                for nr in b['eval']['null']:
                    sc = F._score(tokn, model, nr['q'], nr['cands'])
                    rec[nr['qid']] = dict(pnull=F._pnull(sc, tau))
                for hr in b['anchor_rows']:
                    if not hr['in_heldout']:
                        continue
                    texts = [t for _, t in convs[hr['qid'].split(':')[0]]]
                    P, _ = pool_ids(hr['q'], texts, arms.BM25(texts))
                    sc = F._score(tokn, model, hr['q'], [texts[i] for i in P])
                    rec[hr['qid']] = dict(pnull=F._pnull(sc, tau))
            per[tag][seed] = rec
            print(tag, seed, 'E17', e_hits,
                  'exact', sum(rec[i['qid']]['exact'] for i in items),
                  'any', sum(rec[i['qid']]['any'] for i in items), flush=True)

    summary = {}
    for tag in per:
        ex = [sum(per[tag][s][i['qid']]['exact'] for i in items) for s in per[tag]]
        an = [sum(per[tag][s][i['qid']]['any'] for i in items) for s in per[tag]]
        ga = [sum(per[tag][s][i['qid']]['gated_any'] for i in items) for s in per[tag]]
        n = len(ex)
        mc = []
        for s in per[tag]:
            bb = sum(1 for i in items if per[tag][s][i['qid']]['any'] and not r0[str(s)][i['qid']]['any'])
            cc = sum(1 for i in items if not per[tag][s][i['qid']]['any'] and r0[str(s)][i['qid']]['any'])
            mx = sum(1 for i in items if per[tag][s][i['qid']]['exact'] and not r0[str(s)][i['qid']]['exact'])
            cx = sum(1 for i in items if not per[tag][s][i['qid']]['exact'] and r0[str(s)][i['qid']]['exact'])
            mc.append(dict(seed=s, net_any=bb - cc, p_any=round(mcnemar_exact(bb, cc), 5),
                           net_exact=mx - cx, p_exact=round(mcnemar_exact(mx, cx), 5)))
        summary[tag] = dict(n_seeds=n, exact_mean=round(sum(ex) / n, 2), any_mean=round(sum(an) / n, 2),
                            gated_any_mean=round(sum(ga) / n, 2),
                            e17=[per[tag][s]['_E17'] for s in per[tag]], mcnemar_vs_R0=mc)
    # null quality for null-head configs (first seed)
    for tag in per:
        s0 = sorted(per[tag])[0]
        h_a = [per[tag][s0].get(q, {}).get('pnull') for q in b['eval']['anchor']]
        h_n = [per[tag][s0].get(f'EVALNULL:{q}', {}).get('pnull') for q in b['eval']['anchor']]
        h_a = [x for x in h_a if x is not None]
        h_n = [x for x in h_n if x is not None]
        if h_a and h_n:
            wins = sum(1 for p in h_n for q in h_a if p > q) + 0.5 * sum(1 for p in h_n for q in h_a if p == q)
            tbl = [dict(threshold=t,
                        anchor_coverage=round(sum(1 for p in h_a if p < t) / len(h_a), 4),
                        null_leak=round(sum(1 for p in h_n if p < t) / len(h_n), 4))
                   for t in (0.05, 0.1, 0.2, 0.4, 0.6, 0.8)]
            summary[tag]['null_seed0'] = dict(auroc=round(wins / (len(h_n) * len(h_a)), 4),
                                              coverage_table=tbl)
    out = dict(plan='3f841945', summary=summary)
    dest = Path(outpath) if outpath else ART2 / 'results.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    cmd = sys.argv[1]
    {'forensics': forensics, 'filter': filt,
     'train': lambda: train(sys.argv[2], int(sys.argv[3])),
     'eval': evaluate}[cmd]()
