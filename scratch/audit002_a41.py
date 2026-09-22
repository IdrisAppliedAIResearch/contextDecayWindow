import json
import re
from pathlib import Path

ROOT = Path(r'C:\Users\muzaf\PycharmProjects\contextDecayWindow')
AF1 = ROOT / 'experiments/probes/anchor_reader/artifacts'
ctx1 = json.loads((AF1 / 'contexts.json').read_text(encoding='utf-8'))
ap = {it['qid']: it['a_prompt'] for it in ctx1['items']}
t = ap['conv-41:56']
for m in re.finditer(r'.{140}5K.{140}', t, re.S):
    print('---', m.group(0).replace('\n', ' ')[:340])
    print()
print('len A prompt', len(t))
for m in re.finditer(r'August 2023|first weekend', t, re.I):
    s = max(0, m.start() - 100)
    print('AUG-CTX:', t[s:m.end() + 60].replace('\n', ' '))
