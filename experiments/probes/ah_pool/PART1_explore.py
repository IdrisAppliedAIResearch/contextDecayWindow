"""AF-PRE-008 Part-1 feasibility exploration (no registered claim, no sample2 access).

Question: AH-salience scored 59% top-1 at AF-PRE-006 (gold vs 8 RANDOM distractors).
Does that survive being used as a POOL rule, i.e. ranking every turn of a real
conversation? Characterized on sample-120 (dev; unseen by ckpt2 and ckptM) only.
Diagnostics: (1) reproduce 9-way discrimination on sample-120; (2) global AH rank of
gold; (3) length confound; (4) E-history transfer; (5) end-to-end pool->rerank accuracy.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(r'C:\Users\muzaf\PycharmProjects\ContextDecayWindow')
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms
import ft_pipeline
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

CKPT_M = ROOT / 'experiments/probes/anchor_hide/artifacts/ckptM'
CKPT_2 = ROOT / 'experiments/probes/unified_anchor/artifacts/ckpt2'
ART = ROOT / 'experiments/probes/ah_pool'
K = 10
MS = [5, 10, 15, 20, 30]
SEED = 20260920

tokM = AutoTokenizer.from_pretrained(CKPT_M)
mM = AutoModelForSequenceClassification.from_pretrained(CKPT_M).to('cuda').eval()
tok2 = AutoTokenizer.from_pretrained(CKPT_2)
m2 = AutoModelForSequenceClassification.from_pretrained(CKPT_2).to('cuda').eval()


def sc(model, tok, pairs, ml=512):
    outs = []
    with torch.no_grad():
        for a in range(0, len(pairs), 256):
            ch = pairs[a:a + 256]
            enc = tok([p[0] for p in ch], [p[1] for p in ch], padding=True,
                      truncation=True, max_length=ml, return_tensors='pt').to('cuda')
            outs += model(**enc).logits[:, 0].tolist()
    return outs


def ah_scores(texts):
    return sc(mM, tokM, [('Conversation so far:\n' + '\n'.join(texts[max(0, i - K):i]),
                          texts[i]) for i in range(len(texts))])


def top1(model, tok, q, texts, idxs, ml=256):
    s = sc(model, tok, [(q, texts[i]) for i in idxs], ml=ml)
    return idxs[max(range(len(idxs)), key=lambda j: s[j])]


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


pool120 = json.load(open(ROOT / 'experiments/probes/bert_anchor/part1_artifacts/part1e_locomo_pool.json',
                         encoding='utf-8'))['sample']
convs = arms.load_conversations(ft_pipeline.LOCOMO)
byconv = {}
for it in pool120:
    byconv.setdefault(it['sample_id'], []).append(it)

ahcache = {}
for cid in sorted(byconv):
    texts = [t for _, t in convs[cid]]
    ahcache[cid] = ah_scores(texts)
    print('ah scored', cid, len(texts), flush=True, file=sys.stderr)

rec = {m: dict(ah=0, bm=0) for m in MS}
acc = {m: dict(ah=0, bm=0) for m in MS}
gold_rank = []
gold_rel = []
n_turns = []
sa_n = sa_hit = 0
rng = random.Random(SEED)
for cid, items in sorted(byconv.items()):
    ids = [i for i, _ in convs[cid]]
    texts = [t for _, t in convs[cid]]
    bm = arms.BM25(texts)
    asort = sorted(range(len(texts)), key=lambda i: -ahcache[cid][i])
    for it in items:
        gi = ids.index(it['gold_anchor_earliest'])
        bs = bm.score(it['question'])
        bsort = sorted(range(len(texts)), key=lambda i: -bs[i])
        n_turns.append(len(texts))
        gold_rank.append(1 + sum(1 for j in range(len(texts)) if ahcache[cid][j] > ahcache[cid][gi]))
        gold_rel.append((1 + sum(1 for j in range(len(texts)) if ahcache[cid][j] > ahcache[cid][gi])) / len(texts))
        for m in MS:
            ap, bp = sorted(asort[:m]), sorted(bsort[:m])
            rec[m]['ah'] += gi in ap
            rec[m]['bm'] += gi in bp
            acc[m]['ah'] += top1(m2, tok2, it['question'], texts, ap) == gi
            acc[m]['bm'] += top1(m2, tok2, it['question'], texts, bp) == gi
        d = rng.sample([i for i in range(len(texts)) if i != gi], 8)
        cand = [gi] + d
        sa_n += 1
        sa_hit += top1(mM, tokM, 'Conversation so far:\n' + '\n'.join(texts[max(0, gi - K):gi]),
                       texts, cand, ml=512) == gi

srcs = {h['id']: h for h in json.load(open(ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs/sources.json', encoding='utf-8'))}
blind = {r['id']: r for r in json.load(open(ROOT / 'experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
erec = {m: dict(ah=0, bm=0) for m in MS}
erank = []
for g in ft_pipeline.gap_items():
    eps = srcs[g['history']]['episodes']
    texts = [e['user_message'] + '\n' + e['assistant_message'] for e in eps]
    ids = [e['id'] for e in eps]
    gold = blind[g['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
    ah = ah_scores(texts)
    asort = sorted(range(len(texts)), key=lambda i: -ah[i])
    bsort = sorted(range(len(texts)), key=lambda i: -arms.BM25(texts).score(g['query'])[i])
    gi_e = ids.index(gold) if gold in ids else None
    if gi_e is None:
        continue
    erank.append(1 + sum(1 for j in range(len(texts)) if ah[j] > ah[gi_e]))
    for m in MS:
        erec[m]['ah'] += gold in [ids[i] for i in asort[:m]]
        erec[m]['bm'] += gold in [ids[i] for i in bsort[:m]]

ln = []
sc_flat = []
for cid, s in ahcache.items():
    texts = [t for _, t in convs[cid]]
    ln += [len(t) for t in texts]
    sc_flat += s


def spearman(a, b):
    def rnk(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = rnk(a), rnk(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = sum((ra[i] - ma) ** 2 for i in range(n)) ** .5
    db = sum((rb[i] - mb) ** 2 for i in range(n)) ** .5
    return num / (da * db) if da * db else 0.0


out = dict(
    set='sample-120 dev (unseen by ckpt2 and ckptM); sample2 untouched',
    n_items=len(pool120), median_turns_per_conv=pct(n_turns, 50),
    ah_nine_way_reproduction=dict(top1=f'{sa_hit}/{sa_n}', af_pre_006_reported='71/120 (59%)'),
    ah_global_rank_of_gold=dict(
        median=pct(gold_rank, 50), p25=pct(gold_rank, 25), p75=pct(gold_rank, 75),
        p90=pct(gold_rank, 90),
        median_relative_position=round(pct(gold_rel, 50), 3),
        frac_top20=round(sum(1 for r in gold_rank if r <= 20) / len(gold_rank), 3),
        frac_top30=round(sum(1 for r in gold_rank if r <= 30) / len(gold_rank), 3)),
    pool_recall_at_m={str(m): rec[m] for m in MS},
    accuracy_pool_then_rerank_at_m={str(m): acc[m] for m in MS},
    e_gap_pool_recall_at_m={str(m): erec[m] for m in MS},
    e_gold_ah_rank_median=pct(erank, 50),
    spearman_ah_score_vs_turn_length=round(spearman(ln, sc_flat), 3))
ART.mkdir(parents=True, exist_ok=True)
(ART / 'PART1_results.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(out, indent=1))
