import json, sys, re, gzip
from pathlib import Path
ROOT = Path(r'C:\Users\muzaf\PycharmProjects\contextDecayWindow')
sys.path.insert(0, str(ROOT / 'experiments' / 'probes' / 'anchor_reader'))
sys.path.insert(0, str(ROOT))
import af_read001 as R
L = R.load
A2 = ROOT / 'experiments/probes/anchor_reader/artifacts/af_read002'
A1 = ROOT / 'experiments/probes/anchor_reader/artifacts'

# ---- verdicts (mirror af_read002.score + _af1_correct_a) ----
def votes_from(folder):
    votes = {}
    for p in Path(folder).glob('*.json'):
        rec = L(p)
        if 'blind_id' in rec:
            v, _ = R.parse_judge_verdict(R.final_text(rec['response']))
            votes.setdefault(rec['blind_id'], []).append(v)
    return votes

def arm_correct(folder, surf, mapping):
    votes = votes_from(folder)
    out = {}
    for x in surf:
        m = mapping[x['blind_id']]
        vs = votes.get(x['blind_id'], [])
        if vs:
            out[(m['arm'], m['comparison_key'])] = (int(sum(vs) * 2 > len(vs)), vs)
    return out

surf2 = L(A2 / 'blind_surface.json'); bm2 = L(A2 / 'blind_map.json')
c2 = arm_correct(A2 / 'judges', surf2, bm2)
surf1 = L(A1 / 'blind_surface.json'); bm1 = L(A1 / 'blind_map.json')
c1 = arm_correct(A1 / 'judges', surf1, bm1)

gold = L(A2 / 'gold.json')
ctx2 = L(A2 / 'contexts.json')
prim1 = {i['qid']: i for i in L(A1 / 'contexts.json')['items'] if i['kind'] == 'primary'}

correct = {'A_DEPLOYED': {}, 'B_ANCHOR8K': {}, 'C_ANCHOR8K_CC80': {}}
votes_map = {}
for (arm, qid), (v, vs) in c2.items():
    if qid in gold:
        correct[arm][qid] = v; votes_map[(arm, qid)] = vs
for (arm, qid), (v, vs) in c1.items():
    if arm == 'A_DEPLOYED' and qid in gold:
        correct[arm][qid] = v; votes_map[(arm, qid)] = vs
ids = sorted(set(correct['A_DEPLOYED']) & set(correct['B_ANCHOR8K']) & set(correct['C_ANCHOR8K_CC80']))
tot = {a: sum(correct[a][q] for q in ids) for a in correct}
print('n items', len(ids), 'totals', tot)
assert tot == {'A_DEPLOYED': 85, 'B_ANCHOR8K': 59, 'C_ANCHOR8K_CC80': 81}, tot

both_wrong = [q for q in ids if not correct['A_DEPLOYED'][q] and not correct['C_ANCHOR8K_CC80'][q]]
print('both_wrong N =', len(both_wrong))

# answers: arm A answers from af1 surface, B/C from af2 surface
ansA = {x['comparison_key'] if 'comparison_key' in x else None: x for x in surf1}
# surface rows have blind_id; map via blind_map
ans1 = {}
for x in surf1:
    m = bm1[x['blind_id']]
    if m['arm'] == 'A_DEPLOYED':
        ans1[m['comparison_key']] = x['answer']
ans2 = {}
for x in surf2:
    m = bm2[x['blind_id']]
    ans2[(m['arm'], m['comparison_key'])] = x['answer']

# ---- evidence ----
srcs = {c['sample_id']: c for c in json.load(open(R.LOCOMO, encoding='utf-8'))}
els_by_conv = {}
with gzip.open(R.T_LRT / 'adapter.jsonl.gz', 'rt', encoding='utf8') as f:
    for line in f:
        r = json.loads(line)
        els_by_conv.setdefault(r['conversation'], []).append(r)

def norm(s):
    return re.sub(r'\s+', ' ', s).strip().lower()

def toks(s):
    return set(re.findall(r'[a-z0-9]+', norm(s))) - {'a', 'an', 'the', 'of', 'and', 'to', 'in', 'on', 'is', 'was', 'it', 'i', 'me', 'you', 'my', 'your', 'we', 'our', 'for', 'at', 'with', 'that', 'this', 'he', 'she', 'his', 'her', 'they', 'be', 'are', 'have', 'had', 'so', 'as', 'from', 'do', 'did', 'just', 'like', 'its'}

out = []
for qid in both_wrong:
    cid, sidx = qid.split(':')[0], int(qid.split(':')[1])
    qa = srcs[cid]['qa'][sidx]
    it2 = next(i for i in ctx2['items'] if i['qid'] == qid)
    a_prompt = prim1[qid]['a_prompt']
    ev_ids = [d for d in qa.get('evidence', []) if d]
    turns = {}
    for k, v in srcs[cid]['conversation'].items():
        if k.startswith('session_') and isinstance(v, list):
            for t in v:
                turns[t['dia_id']] = t.get('text', '')
    ev = []
    for d in ev_ids:
        txt = turns.get(d, '')
        na = norm(txt) in norm(a_prompt)
        nc = norm(txt) in norm(it2['block_c'])
        def eids(e):
            di = e['dialogue_ids']
            if isinstance(di, str):
                return re.findall(r'\S+', di.strip("[]'").replace("'", ' ').replace(',', ' '))
            return list(di)
        els = [e for e in els_by_conv[cid] if d in eids(e)]
        ev.append(dict(id=d, text=txt[:300], in_a_prompt=na, in_block_c=nc,
                       elem_ids=[e['id'] for e in els],
                       elem_in_a=all(norm(e['element']) in norm(a_prompt) for e in els),
                       elem_in_c=all(norm(e['element']) in norm(it2['block_c']) for e in els),
                       overlap_a=round(len(toks(txt) & toks(a_prompt)) / max(1, len(toks(txt))), 2),
                       overlap_c=round(len(toks(txt) & toks(it2['block_c'])) / max(1, len(toks(txt))), 2),
                       raw_turn_in_element=[norm(txt) in norm(e['text']) for e in els]))
    out.append(dict(qid=qid, cat=it2['cat'], seed_src=it2['seed_src'], gate=it2['gate'],
                    n_cc80=it2['n_cc80'], n_cc80_dropped=it2['n_cc80_dropped'],
                    question=qa['question'], gold=str(qa.get('answer')),
                    ansA=ans1.get(qid, ''), ansC=ans2.get(('C_ANCHOR8K_CC80', qid), ''),
                    votesA=votes_map.get(('A_DEPLOYED', qid)), votesC=votes_map.get(('C_ANCHOR8K_CC80', qid)),
                    evidence=ev))

Path(ROOT / 'scratch/audit002_common_bothwrong.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
print('wrote', len(out), 'items')
# quick heat summary
from collections import Counter
print('cat x bothwrong:', Counter((o['cat']) for o in out))
print('conv x bothwrong:', Counter(o['qid'].split(':')[0] for o in out))
catn = Counter((i['cat']) for i in ctx2['items'])
convn = Counter(i['qid'].split(':')[0] for i in ctx2['items'])
print('cat totals:', dict(catn))
print('conv totals:', dict(convn))
for o in out:
    allin_a = all(e['in_a_prompt'] or e['overlap_a'] >= 0.8 for e in o['evidence'])
    anyin_c = any(e['in_block_c'] or e['overlap_c'] >= 0.8 for e in o['evidence'])
    o['ev_in_a'] = allin_a
    o['ev_in_c'] = anyin_c
Path(ROOT / 'scratch/audit002_common_bothwrong.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
print('flagged. ev_in_a:', sum(o['ev_in_a'] for o in out), 'ev_in_c(any):', sum(o['ev_in_c'] for o in out))
