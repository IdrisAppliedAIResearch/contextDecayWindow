import json, sys, re, gzip
from pathlib import Path
from collections import Counter
ROOT = Path(r'C:\Users\muzaf\PycharmProjects\contextDecayWindow')
sys.path.insert(0, str(ROOT / 'experiments' / 'probes' / 'anchor_reader'))
sys.path.insert(0, str(ROOT))
import af_read001 as R
L = R.load
A2 = ROOT / 'experiments/probes/anchor_reader/artifacts/af_read002'
A1 = ROOT / 'experiments/probes/anchor_reader/artifacts'
ctx2 = {i['qid']: i for i in L(A2 / 'contexts.json')['items']}
gold = L(A2 / 'gold.json')
prim1 = {i['qid']: i for i in L(A1 / 'contexts.json')['items'] if i['kind'] == 'primary'}
surf1 = L(A1 / 'blind_surface.json'); bm1 = L(A1 / 'blind_map.json')
surf2 = L(A2 / 'blind_surface.json'); bm2 = L(A2 / 'blind_map.json')
def votes_from(folder):
    votes = {}
    for p in Path(folder).glob('*.json'):
        rec = L(p)
        if 'blind_id' in rec:
            v, _ = R.parse_judge_verdict(R.final_text(rec['response']))
            votes.setdefault(rec['blind_id'], []).append(v)
    return votes
v1, v2 = votes_from(A1 / 'judges'), votes_from(A2 / 'judges')
corrA = {bm1[x['blind_id']]['comparison_key']: int(sum(v1[x['blind_id']]) * 2 > 3)
         for x in surf1 if bm1[x['blind_id']]['arm'] == 'A_DEPLOYED' and v1.get(x['blind_id'])}
corrC = {bm2[x['blind_id']]['comparison_key']: int(sum(v2[x['blind_id']]) * 2 > 3)
         for x in surf2 if bm2[x['blind_id']]['arm'] == 'C_ANCHOR8K_CC80' and v2.get(x['blind_id'])}
ids = sorted(set(corrA) & set(corrC) & set(ctx2))
srcs = {c['sample_id']: c for c in json.load(open(R.LOCOMO, encoding='utf-8'))}
els_by_conv = {}
with gzip.open(R.T_LRT / 'adapter.jsonl.gz', 'rt', encoding='utf8') as f:
    for line in f:
        r = json.loads(line)
        els_by_conv.setdefault(r['conversation'], []).append(r)
def norm(s): return re.sub(r'\s+', ' ', s).strip().lower()
def eids(e):
    di = e['dialogue_ids']
    return re.findall(r'\S+', di.strip("[]'").replace("'", ' ').replace(',', ' ')) if isinstance(di, str) else list(di)
def turns_of(cid):
    return {t['dia_id']: t.get('text', '') for k, v in srcs[cid]['conversation'].items()
            if k.startswith('session_') and isinstance(v, list) for t in v}

# --- anatomy of A's misses: formation-miss (gold evidence absent from A prompt) vs reading ---
a_miss = [q for q in ids if not corrA[q]]
form_miss = []
for q in a_miss:
    cid, sidx = q.split(':')[0], int(q.split(':')[1])
    qa = srcs[cid]['qa'][sidx]
    tr = turns_of(cid)
    ap = norm(prim1[q]['a_prompt'])
    miss = []
    for d in qa.get('evidence', []):
        t = norm(tr.get(d, ''))
        if not t:
            continue
        els = [e for e in els_by_conv[cid] if d in eids(e)]
        present = (t in ap) or any(norm(e['element']) in ap for e in els)
        if not present:
            miss.append(d)
    if miss:
        form_miss.append((q, miss))
print('A misses', len(a_miss), 'with >=1 gold-evidence turn absent from A prompt:', len(form_miss),
      f'({len(form_miss)/len(a_miss):.0%})  reading-only: {len(a_miss)-len(form_miss)} ({1-len(form_miss)/len(a_miss):.0%})')
print('form_miss items:', [q for q, m in form_miss])

# --- C-only evidence gaps among both-wrong (class b detail): dropped at 16k vs never admitted ---
bw = [q for q in ids if not corrA[q] and not corrC[q]]
for q in bw:
    it = ctx2[q]
    cid, sidx = q.split(':')[0], int(q.split(':')[1])
    qa = srcs[cid]['qa'][sidx]
    bc = norm(it['block_c'])
    tr = turns_of(cid)
    absent = [d for d in qa.get('evidence', []) if tr.get(d) and norm(tr[d]) not in bc
              and not any(norm(e['element']) in bc for e in els_by_conv[cid] if d in eids(e))]
    if absent:
        print(f'  C-gap {q} cat{it["cat"]} dropped@16k={it["n_cc80_dropped"]} n_cc80={it["n_cc80"]} missing_evid={absent}')

# --- spot checks ---
cid = 'conv-47'
print('conv-47 session_29 date:', srcs[cid]['conversation'].get('session_29_date_time'))
it = ctx2['conv-50:88']
print('50:88 "regular walks" verbatim in C:', 'arranged with friends for regular' in norm(it['block_c']),
      '| in A:', 'arranged with friends for regular' in norm(prim1['conv-50:88']['a_prompt']))
# relative-date answers among cat2 both-wrong
for q in bw:
    if ctx2[q]['cat'] == '2':
        print('cat2 bw', q, '| A-ans:', [x for x in surf1 if bm1[x['blind_id']]['comparison_key'] == q and bm1[x['blind_id']]['arm'] == 'A_DEPLOYED'][0]['answer'][:60])
# heat table cat x conv for both-wrong
heat = Counter((q.split(':')[0], ctx2[q]['cat']) for q in bw)
cats = ['1', '2', '3', '4']
convs = sorted({q.split(':')[0] for q in ids})
print('cat\\conv', ' '.join(f'{c:>9}' for c in convs))
for c in cats:
    print(f'  cat{c}  ', ' '.join(f'{heat.get((cv, c), 0)}/{sum(1 for q in ids if q.startswith(cv) and ctx2[q]["cat"] == c)}'.rjust(9) for cv in convs))
