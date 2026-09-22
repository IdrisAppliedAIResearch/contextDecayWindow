"""Judge votes + A-prompt content checks for AF-READ-002 discordants."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(r'C:\Users\muzaf\PycharmProjects\contextDecayWindow')
sys.path.insert(0, str(ROOT / 'src'))
from analysis.hh001_prompt import parse_judge_verdict  # noqa: E402

AR = ROOT / 'experiments/probes/anchor_reader'
AF1 = AR / 'artifacts'
AF2 = AF1 / 'af_read002'
LOCOMO = Path(r'C:\Users\muzaf\Downloads\locomo10.json')


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def final_text(r):
    return (r.get('content') or '').strip()


disc = load(ROOT / 'scratch/audit002_disc_items.json')
qids = [d['qid'] for d in disc]

surf1 = load(AF1 / 'blind_surface.json'); map1 = load(AF1 / 'blind_map.json')
surf2 = load(AF2 / 'blind_surface.json'); map2 = load(AF2 / 'blind_map.json')
s1 = {x['blind_id']: x for x in surf1}; s2 = {x['blind_id']: x for x in surf2}

votes = {}
for folder, mp in ((AF1 / 'judges', map1), (AF2 / 'judges', map2)):
    for p in Path(folder).glob('*.json'):
        rec = load(p)
        if 'blind_id' in rec:
            v, r = parse_judge_verdict(final_text(rec['response']))
            m = mp[rec['blind_id']]
            votes.setdefault((m['arm'], m['comparison_key'], rec['seed']), (v, r))

print('== judge votes (V/I per seed 9100/9101/9102) ==')
for d in disc:
    q = d['qid']
    line = f"{q} A[{d['A']}]: "
    for seed in (9100, 9101, 9102):
        v, r = votes.get(('A_DEPLOYED', q, seed), (None, ''))
        line += ('V' if v else 'I' if v is not None else '?')
    line += f"  reasonA[{9100}]={votes.get(('A_DEPLOYED', q, 9100), ('', ''))[1][:70]}"
    line += f" || C[{d['C']}]: "
    for seed in (9100, 9101, 9102):
        v, r = votes.get(('C_ANCHOR8K_CC80', q, seed), (None, ''))
        line += ('V' if v else 'I' if v is not None else '?')
    line += f"  reasonC[9101]={votes.get(('C_ANCHOR8K_CC80', q, 9101), ('', ''))[1][:70]}"
    print(line)

print()
print('== session dates ==')
srcs = {c['sample_id']: c for c in json.load(open(LOCOMO, encoding='utf-8'))}
for cid, keys in (('conv-26', ['session_7']), ('conv-41', ['session_10', 'session_29'])):
    for k in keys:
        print(cid, k, '=', srcs[cid]['conversation'].get(f'{k}_date_time'))

print()
print('== A-prompt content probes (deployed timeline, af1 contexts a_prompt) ==')
ctx1 = load(AF1 / 'contexts.json')
ap = {it['qid']: it['a_prompt'] for it in ctx1['items']}
probes = {
    'conv-41:56': ['5K', 'charity run', 'August'],
    'conv-43:11': ['surf', 'Surf'],
    'conv-43:52': ['yoga', 'Yoga'],
    'conv-30:57': ['relationship', 'brand', 'positive'],
    'conv-44:15': ['pet-friendly', 'pet friendly'],
    'conv-49:112': ['physical therapy', 'low-impact'],
    'conv-41:75': ['divorce', 'homeless'],
    'conv-26:19': ['dinosaur'],
    'conv-44:51': ['bed', 'collar', 'tag', 'toy'],
    'conv-48:8': ['rose', 'dahlia', 'photo', 'nature'],
}
for q, terms in probes.items():
    t = ap[q]
    print(q, {term: (t.lower().count(term.lower())) for term in terms})

print()
print('== C block spans around evidence (quotes) ==')
ctx2 = load(AF2 / 'contexts.json')
items2 = {it['qid']: it for it in ctx2['items']}
for q in ['conv-44:15', 'conv-44:51', 'conv-26:19', 'conv-41:56', 'conv-48:8']:
    bc = items2[q]['block_c']
    print('----', q, 'len block_c', len(bc))
    for m in re.finditer(r'.{80}(pet-friendly|beds|dinosaur|5K|roses).{80}', bc, re.I):
        print('  ...', m.group(0).replace('\n', ' ')[:190])

print()
print('== cross-session flag (seed session vs evidence sessions) ==')
for d in disc:
    q = d['qid']
    cid = q.split(':')[0]
    conv = srcs[cid]['conversation']
    qa = srcs[cid]['qa'][int(q.split(':')[1])]
    sess = {}
    for k, v in conv.items():
        if k.startswith('session_') and isinstance(v, list):
            for t in v:
                sess[t['dia_id']] = k
    seed_s = sess.get(items2[q]['seed_turn'])
    ev_s = sorted({sess.get(e, '?') for e in qa.get('evidence', []) if sess.get(e)})
    print(f"{q} seed@{seed_s} evidence_sessions={ev_s} "
          f"seed_on_evidence={seed_s in ev_s}")
