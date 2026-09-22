"""Read-only audit of AF-READ-002: reconstruct per-item verdict table."""
import json
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


def final_text(response):
    return (response.get('content') or '').strip()


def votes_from(folder):
    votes = {}
    for p in Path(folder).glob('*.json'):
        rec = load(p)
        if 'blind_id' in rec:
            v, _ = parse_judge_verdict(final_text(rec['response']))
            votes.setdefault(rec['blind_id'], []).append(v)
    return votes


def arm_correct(surface, mapping, votes):
    out = {}
    for x in surface:
        m = mapping[x['blind_id']]
        vs = votes.get(x['blind_id'], [])
        if vs:
            out[(m['arm'], m['comparison_key'])] = (int(sum(vs) * 2 > len(vs)), x['answer'], len(vs))
    return out


# --- arm B/C from af_read002 judges
ctx2 = load(AF2 / 'contexts.json')
surf2 = load(AF2 / 'blind_surface.json')
map2 = load(AF2 / 'blind_map.json')
v2votes = votes_from(AF2 / 'judges')
bc = arm_correct(surf2, map2, v2votes)

# --- arm A from af_read001 judges (_af1_correct_a mirror)
surf1 = load(AF1 / 'blind_surface.json')
map1 = load(AF1 / 'blind_map.json')
v1votes = votes_from(AF1 / 'judges')
a_raw = {}
for x in surf1:
    m = map1[x['blind_id']]
    if m['arm'] == 'A_DEPLOYED' and v1votes.get(x['blind_id']):
        vs = v1votes[x['blind_id']]
        a_raw[m['comparison_key']] = (int(sum(vs) * 2 > len(vs)), x['answer'], len(vs))

correct = {'A_DEPLOYED': {}, 'B_ANCHOR8K': {}, 'C_ANCHOR8K_CC80': {}}
for (arm, q), (c, ans, n) in bc.items():
    correct[arm][q] = c
    if arm == 'B_ANCHOR8K':
        correct.setdefault('_ansB', {})[q] = ans
    else:
        correct.setdefault('_ansC', {})[q] = ans
a_map = {q: v[0] for q, v in a_raw.items()}
ids = sorted(set(a_map) & set(correct['B_ANCHOR8K']))
correct['A_DEPLOYED'] = {q: a_map[q] for q in ids}
for q in ids:
    correct.setdefault('_ansA', {})[q] = a_raw[q][1]

gold = load(AF2 / 'gold.json')
qtext = {}
for c in json.load(open(LOCOMO, encoding='utf-8')):
    for i, qa in enumerate(c['qa']):
        qtext[f"{c['sample_id']}:{i}"] = qa['question']

print('n ids =', len(ids))
print('A =', sum(correct['A_DEPLOYED'].values()),
      'B =', sum(correct['B_ANCHOR8K'][q] for q in ids),
      'C =', sum(correct['C_ANCHOR8K_CC80'][q] for q in ids))

seed_src = {it['qid']: it['seed_src'] for it in ctx2['items']}
cat = {it['qid']: it['cat'] for it in ctx2['items']}
gate = {it['qid']: it['gate'] for it in ctx2['items']}

for subset_name, src in (('v2', 'v2'), ('bm25', 'bm25')):
    sub = [q for q in ids if seed_src[q] == src]
    a = sum(correct['A_DEPLOYED'][q] for q in sub)
    b = sum(correct['B_ANCHOR8K'][q] for q in sub)
    c_ = sum(correct['C_ANCHOR8K_CC80'][q] for q in sub)
    disc = [q for q in sub if correct['C_ANCHOR8K_CC80'][q] != correct['A_DEPLOYED'][q]]
    print(f'{subset_name}: n={len(sub)} A={a} B={b} C={c_} CA-discordant={len(disc)}')

disc = [q for q in ids if correct['C_ANCHOR8K_CC80'][q] != correct['A_DEPLOYED'][q]]
print('total C/A discordants =', len(disc),
      ' C-wins =', sum(1 for q in disc if correct['C_ANCHOR8K_CC80'][q]),
      ' A-wins =', sum(1 for q in disc if correct['A_DEPLOYED'][q]))

rows = []
for q in disc:
    rows.append(dict(qid=q, cat=cat[q], seed_src=seed_src[q], gate=gate[q],
                     A=correct['A_DEPLOYED'][q], B=correct['B_ANCHOR8K'][q],
                     C=correct['C_ANCHOR8K_CC80'][q],
                     question=qtext[q], gold=gold[q],
                     ansA=correct['_ansA'][q], ansB=correct['_ansB'].get(q),
                     ansC=correct['_ansC'].get(q)))

Path(ROOT / 'scratch/audit002_disc_items.json').write_text(
    json.dumps(rows, indent=1, ensure_ascii=False), encoding='utf-8')

full = [dict(qid=q, cat=cat[q], seed_src=seed_src[q],
             A=correct['A_DEPLOYED'][q], B=correct['B_ANCHOR8K'][q],
             C=correct['C_ANCHOR8K_CC80'][q]) for q in ids]
Path(ROOT / 'scratch/audit002_table.json').write_text(
    json.dumps(full, indent=1, ensure_ascii=False), encoding='utf-8')
print('wrote scratch/audit002_disc_items.json and audit002_table.json')

# vote-count sanity: how many 2-1 majorities overall for C and A on discordants
for r in rows:
    pass
