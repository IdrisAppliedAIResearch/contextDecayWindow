"""AF-PRE-011: anchor-centered packs vs broad-budget packs (zero inference calls).

Reuses arms.BM25 (the arc's lexical scorer) and the committed ckpt2 anchor from AF-PRE-009.
Gate first (PF3): the 120/56 item split must match the audit, and the ORACLE_EVIDENCE positive
control must deliver all evidence on every item it fits.
"""
import json
import sys
from pathlib import Path

ROOT = Path(r'C:\Users\muzaf\PycharmProjects\ContextDecayWindow')
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms  # noqa: E402
import ft_pipeline  # noqa: E402

HERE = Path(__file__).resolve().parent
ART = HERE / 'artifacts'
BUDGETS = (500, 1000, 2000, 4000, 8000)
CROSSOVER_TARGET = 70

STOP = set('the a an and or of to in on at for with that this it is was were are be been as by '
           'from his her their our your my its do does did when where what who which how why '
           'then than but so not no yes have has had will would can could about into over after '
           'before he she they we you i s t'.split())


def norm(s):
    import re
    return re.sub(r'[^a-z0-9 ]', ' ', str(s).lower())


def present(ans, text):
    a, t = norm(ans), norm(text)
    if a.strip() and a.strip() in t:
        return True
    ct = [w for w in a.split() if len(w) > 2 and w not in STOP]
    if not ct:
        return False
    tt = set(t.split())
    return all(w in tt for w in ct)


def pack(idxs, render):
    """Chronological rendered pack over the given turn positions; returns (set, chars)."""
    uniq = sorted(set(idxs))
    return set(uniq), len('\n'.join(render[i] for i in uniq))


def main():
    ART.mkdir(exist_ok=True)
    s2 = json.load(open(ROOT / 'experiments/probes/unified_anchor/artifacts/sample2.json',
                        encoding='utf-8'))
    audit = {r['qid']: r for r in json.load(
        open(ROOT / 'experiments/probes/miss_audit/artifacts/e5_subpartition.json',
             encoding='utf-8'))['items']}
    assert len(s2) == 120 and sum(1 for q in audit if audit[q]['hit']) == 56

    raw = json.load(open(ft_pipeline.LOCOMO, encoding='utf-8'))
    qas = {c['sample_id']: c['qa'] for c in raw}
    convs = arms.load_conversations(ft_pipeline.LOCOMO)
    spkmap, render_map, bm25 = {}, {}, {}
    for c in raw:
        cid = c['sample_id']
        for s in [k for k in c['conversation'] if k.startswith('session_')
                  and not k.endswith('_date_time')]:
            for t in c['conversation'][s]:
                spkmap[(cid, t['dia_id'])] = t['speaker']
        render_map[cid] = [f"{spkmap[(cid, d)]}: {t}" for d, t in convs[cid]]
        bm25[cid] = arms.BM25([t for _, t in convs[cid]])

    rows = []
    for e in s2:
        cid, idx = e['sample_id'], int(e['qid'].split(':')[1])
        a = audit[e['qid']]
        ids = [d for d, _ in convs[cid]]
        pos = {d: i for i, d in enumerate(ids)}
        render = render_map[cid]
        ev = set(a['ev_ids'])
        ans = str(qas[cid][idx].get('answer'))
        texts = dict(convs[cid])
        sc = bm25[cid].score(a['question'])
        order = sorted(range(len(ids)), key=lambda i: -sc[i])
        anchor = pos.get(a['pred'])
        gold = pos.get(a['gold'])
        ev_pos = {pos[d] for d in ev if d in pos}

        def seed_window(center, k):
            return range(max(0, center - k), min(len(ids), center + k + 1))

        cands = {
            'BM25': None,
            'ANCHOR': [anchor],
            'ANCHOR_W1': list(seed_window(anchor, 1)),
            'ANCHOR_W2': list(seed_window(anchor, 2)),
            'ANCHOR_W4': list(seed_window(anchor, 4)),
            'ANCHOR_FILL': None,
            'ORACLE_W2': list(seed_window(gold, 2)) if gold is not None else None,
            'ORACLE_EVIDENCE': sorted(ev_pos),
        }
        for b in BUDGETS:
            built = {}
            for name, sel in cands.items():
                if name == 'BM25':
                    take, used = [], 0
                    for i in order:
                        c = len(render[i]) + (1 if take else 0)
                        if used + c > b:
                            continue
                        take.append(i)
                        used += c
                    built[name] = pack(take, render)
                elif name == 'ANCHOR_FILL':
                    seed = list(seed_window(anchor, 1))
                    if len('\n'.join(render[i] for i in sorted(set(seed)))) > b:
                        continue
                    take, used = list(seed), len('\n'.join(render[i] for i in sorted(set(seed))))
                    for i in order:
                        if i in take:
                            continue
                        c = len(render[i]) + 1
                        if used + c > b:
                            continue
                        take.append(i)
                        used += c
                    built[name] = pack(take, render)
                elif sel is None:
                    continue
                else:
                    p, chars = pack(sel, render)
                    if chars <= b:
                        built[name] = (p, chars)

            for name, val in built.items():
                got_pos, chars = val
                got = {ids[i] for i in got_pos}
                rows.append(dict(qid=e['qid'], hit=a['hit'], cat=a['cat'], budget=b, arm=name,
                                 feasible=True, chars=chars,
                                 any_ev=bool(got & ev), all_ev=bool(ev) and ev <= got,
                                 gold_in=a['gold'] in got,
                                 ans_bearing=any(present(ans, texts[d]) for d in got)))
            for name in cands:
                if name not in built:
                    rows.append(dict(qid=e['qid'], hit=a['hit'], cat=a['cat'], budget=b, arm=name,
                                     feasible=False, chars=None, any_ev=False, all_ev=False,
                                     gold_in=False, ans_bearing=False))

    ctrl = [r for r in rows if r['arm'] == 'ORACLE_EVIDENCE' and r['feasible']]
    ctrl_by_b = {str(b): (sum(1 for r in ctrl if r['budget'] == b),
                          sum(1 for r in ctrl if r['budget'] == b and r['all_ev']))
                 for b in BUDGETS}
    if not all(n and n == k for n, k in ctrl_by_b.values()):
        raise SystemExit(f'positive control failed: {ctrl_by_b}')

    def stat(sub, f):
        return sum(1 for r in sub if r[f])

    summary = {}
    for b in BUDGETS:
        rb = [r for r in rows if r['budget'] == b]
        per = {}
        for name in cands:
            ar = [r for r in rb if r['arm'] == name]
            ok = [r for r in ar if r['feasible']]
            per[name] = dict(feasible=len(ok),
                             any_ev_120=stat(ar, 'any_ev'), all_ev_120=stat(ar, 'all_ev'),
                             any_ev_ok=stat(ok, 'any_ev'), all_ev_ok=stat(ok, 'all_ev'),
                             ans_ok=stat(ok, 'ans_bearing'), gold_ok=stat(ok, 'gold_in'),
                             median_chars=(sorted(r['chars'] for r in ok)[len(ok) // 2]
                                           if ok else None))
        deltas = {}
        for name in ('ANCHOR_W1', 'ANCHOR_W2', 'ANCHOR_W4', 'ANCHOR_FILL', 'ORACLE_W2'):
            by = {}
            for r in rb:
                if r['arm'] in (name, 'BM25') and r['feasible']:
                    by.setdefault(r['qid'], {})[r['arm']] = r
            both = [v for v in by.values() if name in v and 'BM25' in v]
            if not both:
                continue
            d = sum(1 for v in both if v[name]['all_ev']) - sum(1 for v in both if v['BM25']['all_ev'])
            a_ = sum(1 for v in both if v[name]['any_ev']) - sum(1 for v in both if v['BM25']['any_ev'])
            g = sum(1 for v in both if v[name]['all_ev'] and not v['BM25']['all_ev'])
            l = sum(1 for v in both if v['BM25']['all_ev'] and not v[name]['all_ev'])
            ag = sum(1 for v in both if v[name]['any_ev'] and not v['BM25']['any_ev'])
            al = sum(1 for v in both if v['BM25']['any_ev'] and not v[name]['any_ev'])
            deltas[name] = dict(n=len(both), delta_all_ev=d, delta_any_ev=a_,
                                gains_all=g, losses_all=l, gains_any=ag, losses_any=al)
        summary[str(b)] = dict(arms=per, matched_vs_bm25=deltas)

    def cross(name):
        for b in BUDGETS:
            if summary[str(b)]['arms'][name]['any_ev_120'] >= CROSSOVER_TARGET:
                return b
        return None

    ds = {b: summary[str(b)]['matched_vs_bm25'].get('ANCHOR_W2', {}).get('delta_all_ev')
          for b in BUDGETS}
    vals = [v for v in ds.values() if v is not None]
    disp = ('ANCHOR_GEOMETRY_CARRIES' if any(v >= 10 for v in vals) else
            'NO_GEOMETRY_BENEFIT' if vals and max(vals) <= 0 else 'MIXED')

    hits = {}
    for b in BUDGETS:
        rb = [r for r in rows if r['budget'] == b]
        hits[str(b)] = {n: dict(all_ev_hit=stat([r for r in rb if r['arm'] == n and r['hit']],
                                                'all_ev'),
                                n_hit=sum(1 for r in rb if r['arm'] == n and r['hit']),
                                all_ev_miss=stat([r for r in rb if r['arm'] == n and not r['hit']],
                                                 'all_ev'),
                                n_miss=sum(1 for r in rb if r['arm'] == n and not r['hit']))
                        for n in cands}

    out = dict(positive_control=dict(rows=len(ctrl), all_ev=sum(1 for r in ctrl if r['all_ev']),
                                     feasible_and_all_by_budget=ctrl_by_b),
               budgets=summary, disposition_anchor_w2_vs_bm25=disp, delta_all_ev_by_budget=ds,
               crossover_budget_any_ev_70={n: cross(n) for n in cands},
               hit_miss_split_by_budget=hits)
    (ART / 'results.json').write_text(json.dumps(dict(rows=rows, summary=out), indent=1),
                                      encoding='utf-8')
    print(json.dumps(dict(positive_control=out['positive_control'],
                          delta_all_ev_by_budget=ds,
                          disposition=out['disposition_anchor_w2_vs_bm25'],
                          crossover=out['crossover_budget_any_ev_70'],
                          per_arm_at_2000=summary['2000']['arms'],
                          per_arm_at_8000=summary['8000']['arms'],
                          matched_2000=summary['2000']['matched_vs_bm25']), indent=1))


if __name__ == '__main__':
    main()
