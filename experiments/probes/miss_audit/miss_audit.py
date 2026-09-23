"""AF-PRE-009: attribution of the 64 misses of the 56/120 run. Plan: AF_PRE_009_PLAN.md
(6aa2a019); PF4: 0e98b31d. Recompute the frozen ungated-ckpt2 arm, assert 56/120, then
assign each miss by the registered priority-ordered mechanical rules. No readers.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms  # noqa: E402
import ft_pipeline  # noqa: E402
import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

ART = HERE / 'artifacts'
CKPT = ROOT / 'experiments/probes/unified_anchor/artifacts/ckpt2'
STOP = set('the a an and or of to in on at for with that this it is was were are be been as by '
           'from his her their our your my its do does did when where what who which how why '
           'then than but so not no yes have has had will would can could about into over after '
           'before he she they we you i s t'.split())


def norm(s):
    return re.sub(r'[^a-z0-9 ]', ' ', s.lower())


def present(ans, text):
    a, t = norm(ans), norm(text)
    if a.strip() and a.strip() in t:
        return True
    ct = [w for w in a.split() if len(w) > 2 and w not in STOP]
    if not ct:
        return False
    tt = set(t.split())
    return all(w in tt for w in ct)


def jac(a, b):
    x, y = set(norm(a).split()), set(norm(b).split())
    return len(x & y) / len(x | y) if x | y else 0.0


def run():
    tok = AutoTokenizer.from_pretrained(CKPT)
    model = AutoModelForSequenceClassification.from_pretrained(CKPT).to('cuda').eval()
    raw = json.load(open(ft_pipeline.LOCOMO, encoding='utf-8'))
    qas = {c['sample_id']: c['qa'] for c in raw}
    spkmap = {}
    for c in raw:
        m = {}
        for k, v in c['conversation'].items():
            if k.startswith('session_') and isinstance(v, list):
                m.update({t['dia_id']: t.get('speaker') for t in v})
        spkmap[c['sample_id']] = m
    convs = arms.load_conversations(ft_pipeline.LOCOMO)
    sample2 = json.load(open(ROOT / 'experiments/probes/unified_anchor/artifacts/sample2.json',
                             encoding='utf-8'))

    def scores(q, texts):
        outs = []
        with torch.no_grad():
            for a in range(0, len(texts), 256):
                ch = texts[a:a + 256]
                enc = tok([q] * len(ch), ch, padding=True, truncation=True,
                          max_length=256, return_tensors='pt').to('cuda')
                outs += model(**enc).logits[:, 0].tolist()
        return outs

    recs = []
    for it in sample2:
        cid, idx = it['sample_id'], int(it['qid'].split(':')[1])
        qa = qas[cid][idx]
        spk = spkmap[cid]
        ids = [i for i, _ in convs[cid]]
        texts = [t for _, t in convs[cid]]
        bm = arms.BM25(texts)
        ev = [d for d in qa.get('evidence', []) if d in ids]
        gold = sorted(ev, key=lambda d: (int(d.split(':')[0][1:]), int(d.split(':')[1])))[0]
        gi = ids.index(gold)
        s = scores(it['question'], texts)
        order = sorted(range(len(texts)), key=lambda j: -s[j])
        pred = ids[order[0]]
        bs = bm.score(it['question'])
        P, _ = ft_pipeline.pool_ids(it['question'], texts, bm)
        recs.append(dict(qid=it['qid'], cat=str(qa.get('category')), question=it['question'],
                         answer=str(qa.get('answer')), gold=gold, pred=pred,
                         hit=pred == gold, gold_rank=1 + order.index(gi),
                         bm25_pred=ids[max(range(len(texts)), key=lambda j: (bs[j], -j))],
                         bm25_hit=ids[max(range(len(texts)), key=lambda j: (bs[j], -j))] == gold,
                         gold_in_pool=gi in P, n_evidence=len(ev),
                         ev_ids=ev,
                         gold_has_answer=present(str(qa.get('answer')), texts[gi]),
                         pred_has_answer=present(str(qa.get('answer')), texts[ids.index(pred)]),
                         pred_is_evidence=pred in ev,
                         dup_text=norm(texts[ids.index(pred)]) == norm(texts[gi]) or
                                  jac(texts[ids.index(pred)], texts[gi]) >= .90,
                         gold_speaker=spk.get(gold), pred_speaker=spk.get(pred),
                         gold_is_session_open=gold.endswith(':1'),
                         delta=ids.index(pred) - gi,
                         turns_apart=abs(ids.index(pred) - gi)))
    hit = sum(r['hit'] for r in recs)
    assert hit == 56 and len(recs) == 120, f'REPRODUCTION GATE FAILED: {hit}/120'
    return recs


def attribute(recs):
    for r in recs:
        if r['hit']:
            r['cat_err'] = None
        elif r['pred_is_evidence'] and r['pred'] != r['gold']:
            r['cat_err'] = 'E1'
        elif r['dup_text']:
            r['cat_err'] = 'E2'
        elif (not r['gold_has_answer']) and r['pred_has_answer']:
            r['cat_err'] = 'E3'
        elif r['gold_has_answer']:
            r['cat_err'] = 'E4-near' if r['gold_rank'] <= 3 else 'E4-far'
        else:
            r['cat_err'] = 'E5'
    return recs


def main():
    ART.mkdir(exist_ok=True)
    recs = attribute(run())
    errs = [r for r in recs if not r['hit']]
    counts = {}
    for r in errs:
        counts[r['cat_err']] = counts.get(r['cat_err'], 0) + 1
    ranks = sorted(r['gold_rank'] for r in errs)
    hits = [r for r in recs if r['hit']]
    apart = sorted(r['turns_apart'] for r in errs)

    def frac(xs):
        return round(sum(xs) / len(xs), 3) if xs else None
    descriptives = dict(
        errors=dict(median_turns_apart=apart[len(apart) // 2],
                    pred_same_speaker_as_gold=frac([r['gold_speaker'] == r['pred_speaker'] for r in errs]),
                    pred_after_gold=frac([r['delta'] > 0 for r in errs]),
                    median_delta=sorted(r['delta'] for r in errs)[len(errs) // 2],
                    gold_is_session_open=frac([r['gold_is_session_open'] for r in errs])),
        hits=dict(pred_same_speaker_as_gold=frac([r['gold_speaker'] == r['pred_speaker'] for r in hits]),
                  gold_is_session_open=frac([r['gold_is_session_open'] for r in hits])))
    two2 = {}
    for r in recs:
        k = f"gold_answer={'Y' if r['gold_has_answer'] else 'N'}_correct={'Y' if r['hit'] else 'N'}"
        two2[k] = two2.get(k, 0) + 1
    out = dict(
        reproduction='56/120 exact (asserted)',
        n_errors=len(errs), attribution=counts,
        gold_rank_on_errors=dict(median=ranks[len(ranks) // 2], rank2=sum(1 for x in ranks if x == 2),
                                 rank3_to_5=sum(1 for x in ranks if 3 <= x <= 5),
                                 rank6_to_20=sum(1 for x in ranks if 6 <= x <= 20),
                                 beyond20=sum(1 for x in ranks if x > 20)),
        bm25_gets_of_the_64=sum(1 for r in errs if r['bm25_hit']),
        gold_outside_pool_of_the_64=sum(1 for r in errs if not r['gold_in_pool']),
        descriptives=descriptives,
        answer_presence_2x2=two2,
        by_category={c: {k: sum(1 for r in errs if r['cat'] == c and r['cat_err'] == k)
                         for k in ('E1', 'E2', 'E3', 'E4-near', 'E4-far', 'E5')}
                     for c in ('1', '2', '3', '4')},
        ceiling_if_fixed=dict(base=56, plus_E1=56 + counts.get('E1', 0),
                              plus_E1_E2=56 + counts.get('E1', 0) + counts.get('E2', 0),
                              plus_E1_E2_E4near=56 + counts.get('E1', 0) + counts.get('E2', 0)
                              + counts.get('E4-near', 0)))
    (ART / 'per_item.json').write_text(json.dumps(recs, indent=1), encoding='utf-8')
    (ART / 'results.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
