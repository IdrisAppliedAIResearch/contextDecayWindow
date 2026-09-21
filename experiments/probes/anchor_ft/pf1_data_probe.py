"""AF-FT-001 PF Part 1: data characterization before any registration.

Read-only probe over locomo10.json + AF-PRE-005 frozen artifacts. Records, for the
proposed multi-positive + null-class retrain: category counts, evidence-set sizes,
how much any-gold headroom exists on the frozen eval, null population sizes, and
the gold-in-pool training-row counts under the frozen pool builder. No training,
no writes outside this script's stdout.
"""
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/event_lexicon'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms  # noqa: E402
from ft_pipeline import pool_ids, eligible_all, LOCOMO, BERT_DIR  # noqa: E402
ART5 = ROOT / 'experiments/probes/unified_anchor/artifacts'

raw = json.load(open(LOCOMO, encoding='utf-8'))
convs = arms.load_conversations(LOCOMO)

print('== categories and evidence ==')
cat_counts = Counter()
cat5 = []
multi = Counter()
for conv in raw:
    cid = conv['sample_id']
    ids = {i for i, _ in convs[cid]}
    for i, q in enumerate(conv['qa']):
        cat = str(q.get('category'))
        cat_counts[cat] += 1
        ev = [d for d in q.get('evidence', []) if d in ids]
        if cat == '5':
            cat5.append((f'{cid}:{i}', len(ev), bool(q.get('answer'))))
        elif ev:
            multi[len(ev)] += 1
print('cat counts:', dict(sorted(cat_counts.items())))
print('cat5 items:', len(cat5), 'with evidence:', sum(1 for x in cat5 if x[1] > 0),
      'with answer field:', sum(1 for x in cat5 if x[2]))
print('cats1-4 evidence-set sizes:', dict(sorted(multi.items())),
      'items with >1 gold:', sum(v for k, v in multi.items() if k > 1))

print()
print('== frozen eval: any-gold headroom ==')
sample2 = json.load(open(ART5 / 'sample2.json', encoding='utf-8'))
by_qid = {}
for conv in raw:
    cid = conv['sample_id']
    ids = {i for i, _ in convs[cid]}
    for i, q in enumerate(conv['qa']):
        by_qid[f'{cid}:{i}'] = [d for d in q.get('evidence', []) if d in ids]
n_multi = 0
sizes = []
for it in sample2:
    ev = by_qit = by_qid[it['qid']]
    sizes.append(len(ev))
    if len(ev) > 1:
        n_multi += 1
print(f'sample2 n={len(sample2)} items with >1 gold: {n_multi}, gold-set sizes: {dict(Counter(sizes))}')

pool120 = json.load(open(BERT_DIR / 'part1_artifacts/part1e_locomo_pool.json', encoding='utf-8'))['sample']
print(f'sample1 n={len(pool120)}')

print()
print('== null population: cat5 by conversation ==')
c5_by_conv = Counter(q.split(':')[0] for q, _, _ in cat5)
print(dict(sorted(c5_by_conv.items())), 'total', sum(c5_by_conv.values()))

print()
print('== training rows under frozen pool builder (gold-in-pool, single vs multi) ==')
elig = eligible_all()
s1_ids = {it['qid'] for it in pool120}
s2_ids = {it['qid'] for it in sample2}
train_pool = [e for e in elig if e['qid'] not in s1_ids and e['qid'] not in s2_ids]
print('eligible total:', len(elig), 'train pool (minus samples):', len(train_pool))
kept = skip = multi_row = 0
for e in train_pool:
    turns = convs[e['sample_id']]
    ids = [i for i, _ in turns]
    texts = [t for _, t in turns]
    bm = arms.BM25(texts)
    P, _ = pool_ids(e['question'], texts, bm)
    golds_in = [d for d in by_qid[e['qid']] if d in set(ids)]
    gi = ids.index(e['gold'])
    if gi not in P:
        skip += 1
        continue
    kept += 1
    if sum(1 for d in golds_in if d in {ids[j] for j in P}) > 1:
        multi_row += 1
print(f'train rows kept {kept}, skipped (gold out of pool) {skip}, rows with >1 gold IN pool {multi_row}')
