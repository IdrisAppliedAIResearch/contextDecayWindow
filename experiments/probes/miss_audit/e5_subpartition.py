"""AF-PRE-009 Amendment 001: sub-partition the misses by where the answer value lives
(X1 nowhere / X2 session-header only / X3 other turn text / X4 at gold) plus Fisher exact
on the registered answer-presence 2x2. No model, no readers.
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'experiments/probes/bert_anchor'))
sys.path.insert(0, str(ROOT / 'experiments/probes/unified_anchor'))
import arms  # noqa: E402
import ft_pipeline  # noqa: E402

STOP = set('the a an and or of to in on at for with that this it is was were are be been as by '
           'from his her their our your my its do does did when where what who which how why '
           'then than but so not no yes have has had will would can could about into over after '
           'before he she they we you i s t'.split())


def norm(s):
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


def fisher(a, b, c, d):
    from math import comb
    r1, r2, c1 = a + b, c + d, a + c
    N = a + b + c + d
    lo, hi = max(0, c1 - r2), min(r1, c1)

    def pr(x1):
        return comb(c1, x1) * comb(N - c1, r1 - x1) / comb(N, r1)
    p_obs = pr(a)
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= p_obs * 1.0000001))


def main():
    per = json.load(open(HERE / 'artifacts/per_item.json', encoding='utf-8'))
    raw = json.load(open(ft_pipeline.LOCOMO, encoding='utf-8'))
    qas = {c['sample_id']: c['qa'] for c in raw}
    convs = arms.load_conversations(ft_pipeline.LOCOMO)
    hdr = {}
    for c in raw:
        hs = [v for k, v in c['conversation'].items() if k.endswith('_date_time')]
        hdr[c['sample_id']] = ' | '.join(str(h) for h in hs)

    errs = [r for r in per if not r['hit']]
    sub = {}
    for r in per:
        cid = r['qid'].split(':')[0]
        idx = int(r['qid'].split(':')[1])
        ans = str(qas[cid][idx].get('answer'))
        texts = [t for _, t in convs[cid]]
        if r['gold_has_answer']:
            k = 'X4_answer_at_gold'
        elif any(present(ans, t) for t in texts):
            k = 'X3_answer_elsewhere_in_turn_text'
        elif present(ans, hdr[cid]):
            k = 'X2_session_header_only'
        else:
            k = 'X1_answer_nowhere'
        r['x'] = k
        if not r['hit']:
            sub[k] = sub.get(k, 0) + 1
    acc_by_x = {k: f"{sum(1 for r in per if r['x'] == k and r['hit'])}/{sum(1 for r in per if r['x'] == k)}"
                for k in ('X4_answer_at_gold', 'X3_answer_elsewhere_in_turn_text',
                          'X2_session_header_only', 'X1_answer_nowhere')}

    a = sum(1 for r in per if r['gold_has_answer'] and r['hit'])
    b = sum(1 for r in per if r['gold_has_answer'] and not r['hit'])
    c = sum(1 for r in per if not r['gold_has_answer'] and r['hit'])
    d = sum(1 for r in per if not r['gold_has_answer'] and not r['hit'])
    out = dict(subpartition_of_64=sub, accuracy_by_answer_location_all_120=acc_by_x,
               fisher_2x2=dict(gold_answer_present=f'{a}/{a + b}',
                               gold_answer_absent=f'{c}/{c + d}',
                               odds_ratio=round((a * d) / (b * c), 3) if b * c else None,
                               p_two_sided=round(fisher(a, b, c, d), 5)),
               x_by_cat={cc: {k: sum(1 for r in errs if r['cat'] == cc and r.get('x') == k)
                              for k in sub} for cc in ('1', '2', '3', '4')})
    (HERE / 'artifacts/e5_subpartition.json').write_text(json.dumps(dict(items=per, summary=out),
                                                                    indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
