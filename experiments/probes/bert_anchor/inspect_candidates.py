"""Fixture inspection aid: print gold anchor + top lexical competitors for sample items."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads(Path(r'C:\Users\muzaf\Downloads\locomo10.json').read_text(encoding='utf-8'))
pool = json.loads((HERE / 'part1_artifacts/part1e_locomo_pool.json').read_text(encoding='utf-8'))
convs = {c['sample_id']: c for c in data}


def turns(cid):
    out = []
    for k, v in convs[cid]['conversation'].items():
        if k.startswith('session_') and isinstance(v, list):
            out += [(t['dia_id'], t['text']) for t in v]
    return out


def toks(s):
    return set(w.lower().strip('.,!?()"') for w in s.split())


import sys
cats = sys.argv[1] if len(sys.argv) > 1 else '4'
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 4
shown = 0
for item in pool['sample']:
    if item['cat'] != cats or shown >= limit:
        continue
    ts = turns(item['sample_id'])
    gold = item['gold_anchor_earliest']
    gtext = [x for x in ts if x[0] == gold][0]
    q = toks(item['question'])
    scored = sorted(((len(q & toks(t[1])), t) for t in ts if t[0] != gold), key=lambda x: -x[0])[:3]
    print('=' * 100)
    print(item['sample_id'], item['qid'], '|', item['question'])
    print('GOLD', gtext[0], '|', gtext[1][:200])
    for n, t in scored:
        print('  NEG', n, t[0], '|', t[1][:170])
    shown += 1
