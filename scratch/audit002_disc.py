"""Per-discordant-item evidence-location analysis for AF-READ-002."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(r'C:\Users\muzaf\PycharmProjects\contextDecayWindow')
AR = ROOT / 'experiments/probes/anchor_reader'
AF1 = AR / 'artifacts'
AF2 = AF1 / 'af_read002'
LOCOMO = Path(r'C:\Users\muzaf\Downloads\locomo10.json')


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


disc = load(ROOT / 'scratch/audit002_disc_items.json')
ctx2 = load(AF2 / 'contexts.json')
ctx1 = load(AF1 / 'contexts.json')
items2 = {it['qid']: it for it in ctx2['items']}
a_prompt = {it['qid']: it['a_prompt'] for it in ctx1['items']}

srcs = {c['sample_id']: c for c in json.load(open(LOCOMO, encoding='utf-8'))}


def turns(cid):
    out = []
    for k, v in srcs[cid]['conversation'].items():
        if k.startswith('session_') and isinstance(v, list):
            date = srcs[cid]['conversation'].get(f'{k}_date_time', '')
            out += [dict(id=t['dia_id'], text=t['text'], speaker=t.get('speaker', '?'),
                         session=k, date=date) for t in v]
    return out


def norm(s):
    return re.sub(r'\W+', ' ', s.lower()).strip()


def dia_ids(block):
    ids = set()
    for m in re.finditer(r'dialogue_ids="([^"]*)"', block):
        ids.update(m.group(1).split())
    return ids


out = {}
for d in disc:
    qid = d['qid']
    cid, sidx = qid.split(':')[0], int(qid.split(':')[1])
    qa = srcs[cid]['qa'][sidx]
    T = turns(cid)
    tmap = {t['id']: t for t in T}
    ev = [e for e in qa.get('evidence', []) if e in tmap]
    it = items2[qid]
    bb_ids = dia_ids(it['block_b'])
    bc_ids = dia_ids(it['block_c'])
    seed = it['seed_turn']
    ap = a_prompt[qid]
    gold = d['gold']
    gold_n = norm(gold)
    # token-level presence: content tokens of gold (len>=3) found in block/prompt?
    def cover(text):
        tn = set(re.findall(r'[a-z0-9]+', norm(text)))
        gt = {w for w in re.findall(r'[a-z0-9]+', gold_n) if len(w) >= 3}
        return (round(len(gt & tn) / max(1, len(gt)), 2), sorted(gt - tn))
    rec = dict(
        qid=qid, cat=d['cat'], seed_src=d['seed_src'], seed_turn=seed,
        seed_session=tmap.get(seed, {}).get('session'),
        seed_text=tmap.get(seed, {}).get('text', '')[:200],
        n_anchor=it['n_anchor'], n_cc80=it['n_cc80'], n_dropped=it['n_cc80_dropped'],
        anchor_lo=it['anchor_lo'], anchor_hi=it['anchor_hi'],
        evidence=[dict(id=e, session=tmap[e]['session'], text=tmap[e]['text'][:250],
                       in_b=e in bb_ids, in_c=e in bc_ids) for e in ev],
        ev_sessions=sorted({tmap[e]['session'] for e in ev}),
        gold_in_b=gold_n in norm(it['block_b']),
        gold_in_c=gold_n in norm(it['block_c']),
        gold_in_A=gold_n in norm(ap),
        cover_b=cover(it['block_b']), cover_c=cover(it['block_c']), cover_A=cover(ap),
    )
    out[qid] = rec

Path(ROOT / 'scratch/audit002_disc_evidence.json').write_text(
    json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
for q, r in out.items():
    print('====', q, 'cat', r['cat'], r['seed_src'], '| seed', r['seed_turn'], r['seed_session'])
    print('  seed text:', r['seed_text'])
    print('  ev sessions:', r['ev_sessions'], '| n_anchor', r['n_anchor'],
          'n_cc80', r['n_cc80'], 'dropped', r['n_dropped'])
    for e in r['evidence']:
        print(f"   ev {e['id']} [{e['session']}] in_b={e['in_b']} in_c={e['in_c']} :: {e['text'][:150]}")
    print('  gold_in_b', r['gold_in_b'], 'gold_in_c', r['gold_in_c'], 'gold_in_A', r['gold_in_A'],
          '| cover b/c/A:', r['cover_b'][0], r['cover_c'][0], r['cover_A'][0])
    print('  missing tokens C:', r['cover_c'][1], ' A:', r['cover_A'][1])
