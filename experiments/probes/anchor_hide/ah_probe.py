"""AF-PRE-006: anchor-hiding auxiliary supervision. Plan: AF_PRE_006_PLAN.md (1f02b790).

AH task: given the K=10 turns preceding a gold anchor (anchor absent, no question),
pick the anchor among 8 sampled distractors. Mixed with AF-PRE-005 rows; same config.
Eval: per-item paired vs ckpt2 (AF-PRE-005 model) on sample2; E gaps; AH salience.
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms  # noqa: E402
import ft_pipeline  # noqa: E402  (reuses eligible_all, pool rule imports)
from score_sample120 import wilson, mcnemar_exact  # noqa: E402

ART = HERE / 'artifacts'
CKPT_M = ART / 'ckptM'
CKPT_005 = ROOT / 'experiments/probes/unified_anchor/artifacts/ckpt2'
UA_ART = ROOT / 'experiments/probes/unified_anchor/artifacts'
BERT_DIR = ROOT / 'experiments/probes/bert_anchor'
LOCOMO = r'C:\Users\muzaf\Downloads\locomo10.json'
SEED = 20260920
K = 10
NDIST = 8


def build():
    ART.mkdir(exist_ok=True)
    s1 = {it['qid'] for it in json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']}
    s2 = {e['qid'] for e in json.load(open(UA_ART / 'sample2.json', encoding='utf-8'))}
    rng = random.Random(SEED)
    convs = arms.load_conversations(LOCOMO)
    rows = []
    for e in ft_pipeline.eligible_all():
        if e['qid'] in s1 | s2:
            continue
        turns = convs[e['sample_id']]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        gi = ids.index(e['gold'])
        ctx = '\n'.join(texts[max(0, gi - K):gi])
        distr = rng.sample([i for i in range(len(texts)) if i != gi], NDIST)
        rows.append(dict(qid=e['qid'], q='Conversation so far:\n' + ctx,
                         pos=texts[gi], negs=[texts[i] for i in distr]))
    assert not ({r['qid'] for r in rows} & (s1 | s2))
    (ART / 'ah_pairs.json').write_text(json.dumps(rows), encoding='utf-8')
    print(dict(ah_rows=len(rows)))


def train():
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    random.seed(SEED)
    torch.manual_seed(SEED)
    p2 = json.loads((UA_ART / 'pairs2.json').read_text(encoding='utf-8'))
    ah = json.loads((ART / 'ah_pairs.json').read_text(encoding='utf-8'))
    rows = p2['e'] + p2['locomo'] + ah

    class DS:
        def __len__(self):
            return len(rows)

        def __getitem__(self, i):
            return rows[i]

    tokn = AutoTokenizer.from_pretrained(arms.CE_REPO, revision=arms.CE_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(arms.CE_REPO, revision=arms.CE_REVISION).to('cuda')
    dl = DataLoader(DS(), batch_size=16, shuffle=True, collate_fn=lambda b: b)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    steps = 3 * len(dl)
    sch = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    model.train()
    for ep in range(3):
        tot = 0.0
        for batch in dl:
            pairs, counts = [], []
            for row in batch:
                cand = [row['pos']] + row['negs']
                counts.append(len(cand))
                pairs += [(row['q'], c) for c in cand]
            enc = tokn([p[0] for p in pairs], [p[1] for p in pairs], padding=True,
                       truncation=True, max_length=512, return_tensors='pt').to('cuda')
            flat = model(**enc).logits[:, 0]
            k = max(counts)
            logits = flat.new_full((len(batch), k), float('-inf'))
            off = 0
            for bi, c in enumerate(counts):
                logits[bi, :c] = flat[off:off + c]
                off += c
            loss = torch.nn.functional.cross_entropy(logits, torch.zeros(len(batch), dtype=torch.long, device='cuda'))
            opt.zero_grad()
            loss.backward()
            opt.step()
            sch.step()
            tot += loss.item()
        print(f'epoch {ep} loss {tot / len(dl):.4f}', flush=True)
    CKPT_M.mkdir(exist_ok=True)
    model.save_pretrained(CKPT_M)
    tokn.save_pretrained(CKPT_M)
    print('saved', CKPT_M)


def evaluate():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    m_tok = AutoTokenizer.from_pretrained(CKPT_M)
    m = AutoModelForSequenceClassification.from_pretrained(CKPT_M).to('cuda').eval()
    r_tok = AutoTokenizer.from_pretrained(CKPT_005)
    r005 = AutoModelForSequenceClassification.from_pretrained(CKPT_005).to('cuda').eval()

    def sc(model, tok, q, texts):
        outs = []
        with torch.no_grad():
            for a in range(0, len(texts), 256):
                ch = texts[a:a + 256]
                enc = tok([q] * len(ch), ch, padding=True, truncation=True,
                          max_length=512, return_tensors='pt').to('cuda')
                outs += model(**enc).logits[:, 0].tolist()
        return outs

    convs = arms.load_conversations(LOCOMO)
    pool120 = json.load(open(UA_ART / 'sample2.json', encoding='utf-8'))

    def top(scores, idlist):
        return idlist[scores.index(max(scores))]

    hits = {'ref': {}, 'M': {}, 'Mg': {}}
    for it in pool120:
        turns = convs[it['sample_id']]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        bm = arms.BM25(texts)
        P, _ = ft_pipeline.pool_ids(it['question'], texts, bm)
        gold = it['gold']
        hits['ref'][it['qid']] = top(sc(r005, r_tok, it['question'], texts), ids) == gold
        hits['M'][it['qid']] = top(sc(m, m_tok, it['question'], texts), ids) == gold
        hits['Mg'][it['qid']] = top(sc(m, m_tok, it['question'], [texts[i] for i in P]), [ids[i] for i in P]) == gold

    e_items = ft_pipeline.gap_items()
    import re
    srcs = {h['id']: h for h in json.load(open(ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs/sources.json', encoding='utf-8'))}
    blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
    e_hit = e_un = 0
    for g in e_items:
        eps = srcs[g['history']]['episodes']
        texts = [e['user_message'] + '\n' + e['assistant_message'] for e in eps]
        ids = [e['id'] for e in eps]
        gold = blind[g['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
        P, _ = ft_pipeline.pool_ids(g['query'], texts, arms.BM25(texts))
        e_hit += int(top(sc(m, m_tok, g['query'], [texts[i] for i in P]), [ids[i] for i in P]) == gold)
        e_un += int(top(sc(m, m_tok, g['query'], texts), ids) == gold)

    # AH salience: context-only anchor ID on sample2 items
    rng = random.Random(SEED)
    sal = sal_n = 0
    for it in pool120:
        turns = convs[it['sample_id']]
        ids = [i for i, _ in turns]
        texts = [t for _, t in turns]
        gi = ids.index(it['gold'])
        ctx = '\n'.join(texts[max(0, gi - K):gi])
        distr = rng.sample([i for i in range(len(texts)) if i != gi], NDIST)
        cand = [texts[gi]] + [texts[i] for i in distr]
        pred = sc(m, m_tok, 'Conversation so far:\n' + ctx, cand)[0]
        sal_n += 1
        sal += int(sc(m, m_tok, 'Conversation so far:\n' + ctx, cand).index(max(sc(m, m_tok, 'Conversation so far:\n' + ctx, cand))) == 0)

    b = sum(1 for k in hits['M'] if hits['M'][k] and not hits['ref'][k])
    c = sum(1 for k in hits['M'] if not hits['M'][k] and hits['ref'][k])
    net = b - c
    p = mcnemar_exact(b, c)
    verdict = ('PASS-AH' if net >= 5 and p < .05 and e_hit == 17 else
               'SIGNAL-AH' if net > 0 and e_hit == 17 else 'DEAD-AH')
    out = dict(sample2=dict(ref_005=sum(hits['ref'].values()), M_ungated=sum(hits['M'].values()),
                            M_gated=sum(hits['Mg'].values()), n=120, net_vs_005=net, p=round(p, 6),
                            wilson_M=wilson(sum(hits['M'].values()), 120)),
               e_gaps=dict(M_gated=e_hit, M_ungated=e_un, n=17),
               ah_salience=dict(top1=f'{sal}/{sal_n}', chance='1/9',
                                wilson=wilson(sal, sal_n)),
               verdict=verdict)
    (ART / 'results.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'build': build, 'train': train, 'eval': evaluate}[sys.argv[1]]()
