import json, sys, re, gzip
from pathlib import Path
ROOT = Path(r'C:\Users\muzaf\PycharmProjects\contextDecayWindow')
sys.path.insert(0, str(ROOT / 'experiments' / 'probes' / 'anchor_reader'))
sys.path.insert(0, str(ROOT))
import af_read001 as R
L = R.load
A2 = ROOT / 'experiments/probes/anchor_reader/artifacts/af_read002'
A1 = ROOT / 'experiments/probes/anchor_reader/artifacts'
ctx2 = {i['qid']: i for i in L(A2 / 'contexts.json')['items']}
prim1 = {i['qid']: i for i in L(A1 / 'contexts.json')['items'] if i['kind'] == 'primary'}
srcs = {c['sample_id']: c for c in json.load(open(R.LOCOMO, encoding='utf-8'))}
def norm(s): return re.sub(r'\s+', ' ', s).strip().lower()

def convtext(cid, needle):
    hits = []
    for k, v in srcs[cid]['conversation'].items():
        if k.startswith('session_') and isinstance(v, list):
            for t in v:
                if needle.lower() in t.get('text', '').lower():
                    hits.append((t['dia_id'], t['text'][:140]))
    return hits

checks = [
    ('conv-41:69', 'session D2 date:', 'D2'),
    ('conv-49:108', 'sunset/ocean in conv-49:', None),
    ('conv-49:140', 'bird in conv-49:', None),
    ('conv-43:113', 'wolves in conv-43:', None),
    ('conv-47:16', 'uno in conv-47:', None),
    ('conv-30:73', 'air/magical in conv-30:', None),
    ('conv-50:88', 'regular walk in conv-50:', None),
    ('conv-48:87', 'thailand in conv-48:', None),
    ('conv-26:7', 'single in conv-26:', None),
    ('conv-42:73', 'indiana in conv-42:', None),
]
for qid, label, _ in checks:
    cid = qid.split(':')[0]
    needle = {'conv-41:69': '', 'conv-49:108': 'sunset', 'conv-49:140': 'bird',
              'conv-43:113': 'wolves', 'conv-47:16': 'uno', 'conv-30:73': 'air',
              'conv-50:88': 'regular walk', 'conv-48:87': 'thailand',
              'conv-26:7': 'single', 'conv-42:73': 'indiana'}[qid]
    print('---', qid, label)
    if qid == 'conv-41:69':
        c = srcs[cid]['conversation']
        print('D2 date:', c.get('session_2_date_time'), '| D1:', c.get('session_1_date_time'))
    for h in convtext(cid, needle)[:6]:
        print('   ', h)

# date headers present in C blocks and A prompts?
for qid in ['conv-49:23', 'conv-26:35', 'conv-42:72']:
    b = ctx2[qid]['block_c']; ap = prim1[qid]['a_prompt']
    print(qid, 'date= in C:', b.count('date="'), 'date= in A:', ap.count('date="'))

# session dates for relative-date items
for qid, sess in [('conv-26:35', 'session_9'), ('conv-26:49', 'session_12'),
                  ('conv-49:23', 'session_4'), ('conv-43:56', 'session_21'),
                  ('conv-42:72', 'session_28'), ('conv-50:51', 'session_24')]:
    cid = qid.split(':')[0]
    print(qid, sess, '=', srcs[cid]['conversation'].get(sess + '_date_time'))
    d = sess.replace('session_', 'D')
    inb = f'{d}"' in ctx2[qid]['block_c'] or f'session_{sess[-1] if sess[-1].isdigit() else ""}' in ctx2[qid]['block_c']
# explicit: is the dated header for the evidence session inside block_c?
for qid, sess in [('conv-26:35', 'session_9'), ('conv-49:23', 'session_4'), ('conv-43:56', 'session_21')]:
    cid = qid.split(':')[0]
    dt = srcs[cid]['conversation'].get(sess + '_date_time')
    print(qid, 'header in C?', f'session="{sess}"' in ctx2[qid]['block_c'],
          '| date in C?', dt[:14] in ctx2[qid]['block_c'], '| date in A?', dt[:14] in prim1[qid]['a_prompt'], '|', dt)

# judge rationales for e-candidates
import glob
surf1 = L(A1 / 'blind_surface.json'); bm1 = L(A1 / 'blind_map.json')
surf2 = L(A2 / 'blind_surface.json'); bm2 = L(A2 / 'blind_map.json')
want = {'conv-26:41': 'A', 'conv-42:72': 'C', 'conv-49:132': 'A', 'conv-50:51': 'C', 'conv-44:12': 'C'}
for qid, arm in want.items():
    if arm == 'A':
        bid = [x['blind_id'] for x in surf1 if bm1[x['blind_id']]['comparison_key'] == qid and bm1[x['blind_id']]['arm'] == 'A_DEPLOYED'][0]
        folder = A1 / 'judges'
    else:
        bid = [x['blind_id'] for x in surf2 if bm2[x['blind_id']]['comparison_key'] == qid and bm2[x['blind_id']]['arm'] != 'A_DEPLOYED' and 'C' in bm2[x['blind_id']]['arm']][0]
        folder = A2 / 'judges'
    for s in (9100, 9101, 9102):
        rec = L(folder / f'{bid}_{s}.json')
        v, r = R.parse_judge_verdict(R.final_text(rec['response']))
        print(qid, arm, s, v, (r or '')[:160])
