import json, sys, re, gzip
from pathlib import Path
ROOT = Path(r'C:\Users\muzaf\PycharmProjects\contextDecayWindow')
sys.path.insert(0, str(ROOT / 'experiments' / 'probes' / 'anchor_reader'))
sys.path.insert(0, str(ROOT))
import af_read001 as R
L = R.load
A2 = ROOT / 'experiments/probes/anchor_reader/artifacts/af_read002'
A1 = ROOT / 'experiments/probes/anchor_reader/artifacts'
gold = L(A2 / 'gold.json'); ctx2 = L(A2 / 'contexts.json')
prim1 = {i['qid']: i for i in L(A1 / 'contexts.json')['items'] if i['kind'] == 'primary'}
items = json.loads((ROOT / 'scratch/audit002_common_bothwrong.json').read_text(encoding='utf-8'))
srcs = {c['sample_id']: c for c in json.load(open(R.LOCOMO, encoding='utf-8'))}
els_by_conv = {}
with gzip.open(R.T_LRT / 'adapter.jsonl.gz', 'rt', encoding='utf8') as f:
    for line in f:
        r = json.loads(line)
        els_by_conv.setdefault(r['conversation'], []).append(r)
def norm(s): return re.sub(r'\s+', ' ', s).strip().lower()
def toks(s): return set(re.findall(r"[a-z0-9']+", norm(s)))
STOP = set('a an the of and to in on is was it i me you my your we our for at with that this he she his her they be are have had so as from do did just like its not but was were what when where who how'.split())
def overlap(a, b):
    ta, tb = toks(a) - STOP, toks(b) - STOP
    return len(ta & tb) / max(1, len(ta))
def eids(e):
    di = e['dialogue_ids']
    if isinstance(di, str):
        return re.findall(r'\S+', di.strip("[]'").replace("'", ' ').replace(',', ' '))
    return list(di)
lines = []
for o in items:
    cid, sidx = o['qid'].split(':')[0], int(o['qid'].split(':')[1])
    a_prompt = norm(prim1[o['qid']]['a_prompt'])
    it2 = next(i for i in ctx2['items'] if i['qid'] == o['qid'])
    bc = norm(it2['block_c']); bb = norm(it2['block_b'])
    lines.append('=' * 100)
    lines.append(f"{o['qid']} cat{o['cat']} seed={o['seed_src']} gate={o['gate']} dropped={o['n_cc80_dropped']}")
    lines.append(f"Q: {o['question']}\nGOLD: {o['gold']}")
    lines.append(f"A({o['votesA']}): {o['ansA'][:260]}")
    lines.append(f"C({o['votesC']}): {o['ansC'][:260]}")
    for e in o['evidence']:
        d = e['id']
        els = [x for x in els_by_conv[cid] if d in eids(x)]
        for x in els:
            et = norm(x['text'])
            lines.append(f"  ev {d}: {e['text'][:150]}")
            lines.append(f"    elem_verbatim_raw={norm(e['text']) in et or norm(e['text']) in norm(x['element'])} "
                         f"tok_ov_raw_vs_elem={overlap(e['text'], x['text']):.2f} "
                         f"elem_in_A={et[:200] in a_prompt or norm(x['element']) in a_prompt} "
                         f"elem_in_C={norm(x['element']) in bc} elem_in_B={norm(x['element']) in bb} "
                         f"tok_ov_elem_vs_Aprompt={overlap(x['text'], a_prompt):.2f} "
                         f"tok_ov_elem_vs_C={overlap(x['text'], bc):.2f}")
            if norm(x['element']) not in bc:
                lines.append(f"    ELEM_TEXT_MISSING_IN_C: {x['text'][:220]}")
Path(ROOT / 'scratch/audit002_common_digest.txt').write_text('\n'.join(lines), encoding='utf-8')
print('digest lines', len(lines))
