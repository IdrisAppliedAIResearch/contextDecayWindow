import json
import sys
sys.path.insert(0, 'experiments/probes/bert_anchor')
sys.path.insert(0, 'experiments/probes/unified_anchor')
from score_sample120 import mcnemar_exact

r = json.load(open('experiments/probes/anchor_ft/artifacts/results.json', encoding='utf-8'))
raw = r['raw_per_item']
seeds = ['20261011', '20261012', '20261013', '20261014', '20261015']
q2 = [it['qid'] for it in json.load(open('experiments/probes/unified_anchor/artifacts/sample2.json', encoding='utf-8'))]
print(f'{len(q2)} eval items')
for cfg in ('V1', 'V1H', 'V2'):
    nets, ps, netsx, psx = [], [], [], []
    for s in seeds:
        for field, N, P in (('any', nets, ps), ('exact', netsx, psx)):
            b = sum(1 for q in q2 if raw[cfg][s][q][field] and not raw['R0'][s][q][field])
            c = sum(1 for q in q2 if not raw[cfg][s][q][field] and raw['R0'][s][q][field])
            N.append(b - c)
            P.append(round(mcnemar_exact(b, c), 5))
    print(f'{cfg:4} any-net {nets}  exact-net {netsx} exact-p {psx}')
# gated paired
for cfg in ('V1', 'V1H', 'V2'):
    nets = []
    for s in seeds:
        b = sum(1 for q in q2 if raw[cfg][s][q]['gated_any'] and not raw['R0'][s][q]['gated_any'])
        c = sum(1 for q in q2 if not raw[cfg][s][q]['gated_any'] and raw['R0'][s][q]['gated_any'])
        nets.append(b - c)
    print(f'{cfg:4} gated-any-net {nets}')
