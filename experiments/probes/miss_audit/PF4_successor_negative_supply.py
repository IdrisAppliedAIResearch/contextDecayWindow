"""AF-PRE-009 successor feasibility (PF4 for a hypothetical contract probe, no model):
on the AF-PRE-005 TRAINING items, how many have a non-gold turn whose text contains the
answer value? That is the hard-negative supply a contract probe would need. If thin, no such
probe should be registered.
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


raw = json.load(open(ft_pipeline.LOCOMO, encoding='utf-8'))
qas = {c['sample_id']: c['qa'] for c in raw}
sample1 = {it['qid'] for it in json.load(open(ROOT / 'experiments/pibes/bert_anchor/part1_artifacts/part1e_locomo_pool.json'.replace('pibes', 'probes'), encoding='utf-8'))['sample']}
s2 = {e['qid'] for e in json.load(open(ROOT / 'experiments/probes/unified_anchor/artifacts/sample2.json', encoding='utf-8'))}
convs = arms.load_conversations(ft_pipeline.LOCOMO)

n = has_neg = 0
tot_neg_turns = []
for e in ft_pipeline.eligible_all():
    if e['qid'] in sample1 | s2:
        continue
    cid = e['sample_id']
    idx = int(e['qid'].split(':')[1])
    ans = str(qas[cid][idx].get('answer'))
    ids = [i for i, _ in convs[cid]]
    texts = [t for _, t in convs[cid]]
    gi = ids.index(e['gold'])
    k = sum(1 for j, t in enumerate(texts) if j != gi and present(ans, t))
    n += 1
    has_neg += k > 0
    tot_neg_turns.append(k)

tot_neg_turns.sort()
print(json.dumps(dict(train_items=n, items_with_answer_bearing_non_gold_turn=has_neg,
                      pct=round(100 * has_neg / n, 1),
                      median_negatives_per_item=tot_neg_turns[len(tot_neg_turns) // 2],
                      p90=tot_neg_turns[int(.9 * len(tot_neg_turns))]), indent=1))
