"""AF-PRE-008 Part-1 addendum: is any SOFT use of AH-salience feasible?

The hard-pool design is dead (PART1_results.json). The only remaining question a
successor could ask is whether AH-salience adds candidates the registered pool rule
misses. Measure gold-in-pool recall of pool_ids (AF-PRE-005 rule) and pool_ids UNION
AH-top-m on sample-120. If the union adds no gold, no fusion probe has a reachable bar.
"""
import json
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
K = 10
MS = [10, 20, 30, 50]

tokM = AutoTokenizer.from_pretrained(CKPT_M)
mM = AutoModelForSequenceClassification.from_pretrained(CKPT_M).to('cuda').eval()


def ah_scores(texts):
    outs = []
    with torch.no_grad():
        pairs = [('Conversation so far:\n' + '\n'.join(texts[max(0, i - K):i]), texts[i])
                 for i in range(len(texts))]
        for a in range(0, len(pairs), 256):
            ch = pairs[a:a + 256]
            enc = tokM([p[0] for p in ch], [p[1] for p in ch], padding=True,
                       truncation=True, max_length=512, return_tensors='pt').to('cuda')
            outs += mM(**enc).logits[:, 0].tolist()
    return outs


pool120 = json.load(open(ROOT / 'experiments/probes/bert_anchor/part1_artifacts/part1e_locomo_pool.json',
                         encoding='utf-8'))['sample']
convs = arms.load_conversations(ft_pipeline.LOCOMO)
byconv = {}
for it in pool120:
    byconv.setdefault(it['sample_id'], []).append(it)

ref = un = 0
per_m = {m: 0 for m in MS}
n = 0
for cid, items in sorted(byconv.items()):
    ids = [i for i, _ in convs[cid]]
    texts = [t for _, t in convs[cid]]
    bm = arms.BM25(texts)
    ah = ah_scores(texts)
    asort = sorted(range(len(texts)), key=lambda i: -ah[i])
    for it in items:
        gi = ids.index(it['gold_anchor_earliest'])
        P, _ = ft_pipeline.pool_ids(it['question'], texts, bm)
        n += 1
        ref += gi in P
        for m in MS:
            per_m[m] += gi in (set(P) | set(asort[:m]))
print(json.dumps(dict(n=n, pool_ids_recall=ref,
                      union_recall={str(m): per_m[m] for m in MS},
                      added_by_union={str(m): per_m[m] - ref for m in MS}), indent=1))
