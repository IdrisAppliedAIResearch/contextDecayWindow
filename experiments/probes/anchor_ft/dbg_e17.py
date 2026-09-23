import sys
from pathlib import Path
HERE = Path('experiments/probes/anchor_ft')
sys.path.insert(0, str(HERE)); sys.path.insert(0, 'experiments/probes/bert_anchor')
sys.path.insert(0, 'experiments/probes/unified_anchor'); sys.path.insert(0, '.')
import af_ft001 as F
import af_ft002 as F2
import json
srcs = {h['id']: h for h in json.load(open('experiments/study_E/artifacts/confirmation/development_inputs/sources.json', encoding='utf-8'))}
blind = {r['id']: r for r in json.load(open('experiments/probes/temporal_da_fusion/relevance_artifacts/blind.json', encoding='utf-8'))}
g0 = F.gap_items()[0]
eps = srcs[g0['history']]['episodes']
texts, tids = F.e_texts(eps), [e['id'] for e in eps]
gold = blind[g0['id']]['arms']['ANCHORED']['anchor_exceptions'][0]
print('n_eps', len(texts), 'gold', gold, 'gold_in_ids', gold in tids)
for tag in ('R0', 'V2', 'F1', 'F2'):
    tokn, model, tau = (F._loader(tag, 20261011) if tag in ('R0', 'V2') else F2.loader(tag, 20261011))
    sc = F._score(tokn, model, g0['query'], texts)
    top = max(range(len(sc)), key=lambda i: sc[i])
    gi = tids.index(gold) if gold in tids else None
    print(tag, 'argmax', tids[top][:8], 'score', round(sc[top], 2),
          'gold_score', round(sc[gi], 2) if gi is not None else 'ABSENT',
          'gold_rank', 1 + sum(1 for s in sc if gi is not None and s > sc[gi]))
