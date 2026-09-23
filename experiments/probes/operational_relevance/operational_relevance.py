"""AF-PRE-010: does an AF-PRE-009 anchor miss cost the deployed pack delivered evidence?

Zero model calls, zero reader calls. Reads only committed artifacts:
  - miss_audit/artifacts/e5_subpartition.json  (AF-PRE-009 items, 120/56 hits)
  - hh_003 A_EPISODIC/contexts.json            (D-product, 32k, 120/120)
  - nf_004 g6_holdout_outcomes.json            (D-ranked, 63/120)
  - hh_004 A_DA098_ARCH32_DECODED/contexts.json (identity-recovery gate only)

Gate first (PF3): delivered-turn identity recovery must reproduce D-comp's units_delivered.
"""
import json
import re
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
AUDIT = ROOT / 'experiments/probes/miss_audit/artifacts/e5_subpartition.json'
DPROD = ROOT / 'experiments/comparisons/hh_003/artifacts/run/A_EPISODIC/contexts.json'
DRANK = ROOT / 'experiments/components/biological_memory/nf_004/artifacts/g6_holdout_outcomes.json'
DCOMP = ROOT / ('experiments/comparisons/hh_004/artifacts/run/'
                'A_DA098_ARCH32_DECODED/contexts.json')
PF4 = ROOT / 'experiments/probes/miss_audit/PF4_deployed_coverage.json'

STOP = set('the a an and or of to in on at for with that this it is was were are be been as by '
           'from his her their our your my its do does did when where what who which how why '
           'then than but so not no yes have has had will would can could about into over after '
           'before he she they we you i s t'.split())


def norm(s):
    return re.sub(r'[^a-z0-9 ]', ' ', str(s).lower())


def present(ans, text):
    """AF-PRE-009 frozen answer-presence rule (verbatim)."""
    a, t = norm(ans), norm(text)
    if a.strip() and a.strip() in t:
        return True
    ct = [w for w in a.split() if len(w) > 2 and w not in STOP]
    if not ct:
        return False
    tt = set(t.split())
    return all(w in tt for w in ct)


def fisher(a, b, c, d):
    from math import comb
    r1, c1, N = a + b, a + c, a + b + c + d
    lo, hi = max(0, c1 - (N - r1)), min(r1, c1)

    def pr(x):
        return comb(c1, x) * comb(N - c1, r1 - x) / comb(N, r1)
    po = pr(a)
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= po * 1.0000001))


def main():
    ART.mkdir(exist_ok=True)
    audit = json.load(open(AUDIT, encoding='utf-8'))['items']
    assert len(audit) == 120, len(audit)
    assert sum(1 for r in audit if r['hit']) == 56, sum(1 for r in audit if r['hit'])

    raw = json.load(open(ft_pipeline.LOCOMO, encoding='utf-8'))
    qas = {c['sample_id']: c['qa'] for c in raw}
    convs = arms.load_conversations(ft_pipeline.LOCOMO)
    spkmap = {}
    for c in raw:
        for s in [k for k in c['conversation'] if k.startswith('session_')
                  and not k.endswith('_date_time')]:
            for t in c['conversation'][s]:
                spkmap[(c['sample_id'], t['dia_id'])] = t['speaker']

    def recover(ctx, cid):
        out = set()
        for dia, text in convs[cid]:
            r = f"{spkmap[(cid, dia)]}: {text}"
            if len(text) >= 25:
                if r in ctx:
                    out.add(dia)
            elif re.search(r'(^|\n|>| )' + re.escape(r) + r'($|\n|<)', ctx, re.M):
                out.add(dia)
        return out

    # ---- identity-recovery gate (runs before any reported measure) ----
    dcomp = json.load(open(DCOMP, encoding='utf-8'))['items']
    dcomp = {(str(v['sample_id']), int(v['source_index'])): v for v in dcomp.values()}
    mism = []
    for k, v in dcomp.items():
        found = recover(v['context'], k[0])
        mism.append(abs(len(found) - int(v['units_delivered'])))
    gate = dict(items=len(mism), absmax_mismatch=max(mism),
                items_within_1=sum(1 for m in mism if m <= 1))
    if gate['absmax_mismatch'] > 1:
        (ART / 'gate_failed.json').write_text(json.dumps(gate, indent=1), encoding='utf-8')
        raise SystemExit(f"identity recovery gate FAILED: {gate}")

    # ---- PF6 anchors ----
    pf4 = json.load(open(PF4, encoding='utf-8'))
    drank = json.load(open(DRANK, encoding='utf-8'))
    rk = {(str(r['sample_id']), int(r['source_index'])): r for r in drank['rows']}
    qerr = [(r['qid'].split(':')[0], int(r['qid'].split(':')[1]))
            for r in audit if not r['hit']]
    chk = {f'miss_{m}_P_PAIR_RANK': sum(1 for k in qerr if k in rk and rk[k]['arms']['P_PAIR_RANK'][m])
           for m in ('any_evidence', 'all_evidence')}
    if chk['miss_any_evidence_P_PAIR_RANK'] != pf4['miss_any_evidence_P_PAIR_RANK']:
        raise SystemExit(f"D-ranked join changed: {chk}")

    dprod = json.load(open(DPROD, encoding='utf-8'))['items']
    dprod = {(str(v['sample_id']), int(v['source_index'])): v for v in dprod.values()}

    items = []
    for r in audit:
        cid = r['qid'].split(':')[0]
        idx = int(r['qid'].split(':')[1])
        key = (cid, idx)
        qa = qas[cid][idx]
        ev = set(qa['evidence'])
        ans = str(qa.get('answer'))
        texts = {d: t for d, t in convs[cid]}
        rec = dict(qid=r['qid'], hit=r['hit'], cat=r['cat'], gold=r['gold'], pred=r['pred'],
                   n_evidence=len(ev), x=r.get('x'), rank_covered=False,
                   rank16_any_ev=None, rank16_all_ev=None, rank32_any_ev=None,
                   rank32_all_ev=None, src_any_ev=None, src_all_ev=None)
        dl = recover(dprod[key]['context'], cid) if key in dprod else None
        rec['product_covered'] = dl is not None
        rec['product_delivered_n'] = len(dl) if dl is not None else None
        rec['product_any_ev'] = bool(dl & ev) if dl is not None else None
        rec['product_all_ev'] = bool(ev) and ev <= dl if dl is not None else None
        rec['product_gold_delivered'] = r['gold'] in dl if dl is not None else None
        rec['product_answer_bearing'] = (any(present(ans, texts[d]) for d in dl)
                                         if dl is not None else None)
        rec['product_pred_delivered'] = r['pred'] in dl if dl is not None else None
        if key in rk:
            for arm, tag in (('P_PAIR_RANK', 'rank16'), ('P_PAIR_RANK_32K', 'rank32'),
                             ('SOURCE_ORDER', 'src')):
                a = rk[key]['arms'][arm]
                rec[f'{tag}_any_ev'] = a['any_evidence']
                rec[f'{tag}_all_ev'] = a['all_evidence']
            rec['rank_covered'] = True
        items.append(rec)

    def rate(sub, field):
        v = [x[field] for x in sub if x[field] is not None]
        return (sum(1 for z in v if z), len(v))

    def block(sel):
        m = [x for x in items if sel(x)]
        out = {}
        for f in ('product_any_ev', 'product_all_ev', 'product_answer_bearing',
                  'product_gold_delivered', 'product_pred_delivered'):
            n, d = rate(m, f)
            out[f] = f'{n}/{d}'
        for f in ('rank16_all_ev', 'rank32_all_ev', 'src_all_ev'):
            n, d = rate(m, f)
            out[f] = f'{n}/{d}' if d else None
        silent = [x for x in m if x['product_all_ev'] or x['product_answer_bearing']]
        cost = [x for x in m if not x['product_all_ev'] and not x['product_answer_bearing']]
        out['silent_or'] = f"{len(silent)}/{len(m)}"
        out['cost_set'] = len(cost)
        return out, [x['qid'] for x in cost]

    miss_block, cost_q = block(lambda x: not x['hit'])
    hit_block, _ = block(lambda x: x['hit'])

    def frac(s):
        n, d = s.split('/')
        return int(n) / int(d) if int(d) else 0.0

    delta = (frac(hit_block['silent_or']) - frac(miss_block['silent_or']))
    sm = frac(miss_block['silent_or'])
    disp = ('OPERATIONAL_SILENT' if sm >= .80 else
            'OPERATIONAL_COST' if sm < .50 else 'MIXED')
    pilot = disp == 'OPERATIONAL_COST' or (disp == 'MIXED' and len(cost_q) >= 10)

    def tab(field, sel_hit):
        n, d = rate([x for x in items if sel_hit(x)], field)
        return n, d

    pvals = {}
    for f in ('product_any_ev', 'product_all_ev', 'product_answer_bearing'):
        hn, hd = tab(f, lambda x: x['hit'])
        mn, md = tab(f, lambda x: not x['hit'])
        pvals[f] = round(fisher(hn, hd - hn, mn, md - mn), 4)

    res = dict(gate_identity_recovery=gate, pf6_drank_check=chk,
               fisher_hits_vs_misses=pvals,
               misses=miss_block, hits=hit_block,
               silent_rate_misses=round(sm, 4), hits_minus_misses_pp=round(100 * delta, 1),
               disposition=disp, reader_pilot_registerable=pilot,
               cost_set_qids=cost_q,
               cost_by_cat={c: sum(1 for q in cost_q if next(i for i in items if i['qid'] == q)['cat'] == c)
                            for c in ('1', '2', '3', '4')})
    (ART / 'results.json').write_text(json.dumps(dict(items=items, summary=res), indent=1),
                                      encoding='utf-8')
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
