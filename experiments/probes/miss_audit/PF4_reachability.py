"""AF-PRE-009 PF4 reachability check (no model, no predictions): are all categories
reachable on the frozen sample2 input?"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(r'C:\Users\muzaf\PycharmProjects\ContextDecayWindow')
sys.path.insert(0, str(ROOT / 'experiments/probes/unified_anchor'))
sys.path.insert(0, str(ROOT / 'experiments/probes/bert_anchor'))
import ft_pipeline  # noqa: E402
import arms  # noqa: E402

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


raw = json.load(open(ft_pipeline.LOCOMO, encoding='utf-8'))
sample2 = json.load(open(ROOT / 'experiments/probes/unified_anchor/artifacts/sample2.json', encoding='utf-8'))
convs = arms.load_conversations(ft_pipeline.LOCOMO)
qas = {c['sample_id']: c['qa'] for c in raw}

n = multi = dup = gold_present = 0
dup_pairs = {}
for it in sample2:
    cid, idx = it['sample_id'], int(it['qid'].split(':')[1])
    qa = qas[cid][idx]
    ids = [i for i, _ in convs[cid]]
    texts = [t for _, t in convs[cid]]
    ev = [d for d in qa.get('evidence', []) if d in ids]
    gi = ids.index(sorted(ev, key=lambda d: (int(d.split(':')[0][1:]), int(d.split(':')[1])))[0])
    n += 1
    multi += len(ev) > 1
    dup_here = [j for j in range(len(texts)) if norm(texts[j]) == norm(texts[gi]) and j != gi]
    dup += bool(dup_here)
    dup_pairs[it['qid']] = len(dup_here)
    gold_present += present(qa['answer'], texts[gi])

print(json.dumps(dict(n=n, items_multi_evidence=multi, items_with_duplicate_text_of_gold=dup,
                      gold_contains_answer_value=gold_present,
                      gold_lacks_answer_value=n - gold_present), indent=1))
