import json, sys, re
from pathlib import Path
ROOT = Path(r'C:\Users\muzaf\PycharmProjects\contextDecayWindow')
sys.path.insert(0, str(ROOT / 'experiments' / 'probes' / 'anchor_reader'))
A2 = ROOT / 'experiments/probes/anchor_reader/artifacts/af_read002'
A1 = ROOT / 'experiments/probes/anchor_reader/artifacts'
L = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))

ctx2 = L(A2 / 'contexts.json')
print('ctx2 keys', list(ctx2.keys()))
it = ctx2['items'][0]
print('item keys', list(it.keys()))
print('sample', {k: (v[:80] if isinstance(v, str) else v) for k, v in it.items() if k not in ('block_b', 'block_c')})
res = L(A2 / 'results.json')
print('results summary keys', list(res['summary'].keys()))
print(json.dumps(res['summary']['correct'], indent=0))
print(json.dumps(res['summary'].get('by_category'), indent=0))
gold = L(A2 / 'gold.json')
print('gold n', len(gold))
surf2 = L(A2 / 'blind_surface.json')
print('surf2[0]', surf2[0])
bm2 = L(A2 / 'blind_map.json')
k0 = list(bm2)[0]
print('map0', k0, bm2[k0])
ctx1 = L(A1 / 'contexts.json')
i1 = [i for i in ctx1['items'] if i['kind'] == 'primary']
print('af1 primary n', len(i1), 'keys', list(i1[0].keys()))
surf1 = L(A1 / 'blind_surface.json')
print('surf1[0]', {k: (v[:60] if isinstance(v, str) else v) for k, v in surf1[0].items()})
bm1 = L(A1 / 'blind_map.json')
print('bm1 sample', bm1[list(bm1)[0]])
import gzip
r = json.loads(gzip.open(ROOT / 'experiments/locomo_relevance_timeline/artifacts/adapter.jsonl.gz', 'rt', encoding='utf8').readline())
print('adapter keys', list(r.keys()))
print({k: (str(v)[:100]) for k, v in r.items()})
