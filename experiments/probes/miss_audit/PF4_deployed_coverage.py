"""AF-PRE-010 preflight (PF4 reachability, no model, no reader calls):
can the deployed-pack artifacts answer "was answer-bearing content delivered?" for the
AF-PRE-009 items? Measures coverage of the deployed population and the reliability of
recovering delivered turn identities from rendered context text.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r'C:\Users\muzaf\PycharmProjects\ContextDecayWindow')
for p in (str(ROOT), str(ROOT / 'experiments/probes/bert_anchor'),
          str(ROOT / 'experiments/probes/unified_anchor')):
    sys.path.insert(0, p)
import arms  # noqa: E402
import ft_pipeline  # noqa: E402

NF = ROOT / 'experiments/components/biological_memory/nf_004/artifacts/g6_holdout_outcomes.json'
HH = ROOT / ('experiments/comparisons/hh_004/artifacts/run/A_DA098_ARCH32_DECODED/'
             'contexts.json')

miss = json.load(open(ROOT / 'experiments/probes/miss_audit/artifacts/e5_subpartition.json',
                      encoding='utf-8'))['items']
errs = [r for r in miss if not r['hit']]
s2 = json.load(open(ROOT / 'experiments/probes/unified_anchor/artifacts/sample2.json',
                    encoding='utf-8'))

nf = json.load(open(NF, encoding='utf-8'))
nfk = {(str(r['sample_id']), int(r['source_index'])): r for r in nf['rows']}
hh = json.load(open(HH, encoding='utf-8'))['items']
hhk = {(str(v['sample_id']), int(v['source_index'])): v for v in hh.values()}

k2s = [(e['sample_id'], int(e['qid'].split(':')[1])) for e in s2]
e2s = [(e['qid'].split(':')[0], int(e['qid'].split(':')[1])) for e in errs]
out = {}
out['nf_rows'] = len(nfk)
out['nf_conversations'] = sorted({k[0] for k in nfk})
out['sample2_in_nf'] = sum(1 for k in k2s if k in nfk)
out['sample2_in_hh'] = sum(1 for k in k2s if k in hhk)
out['misses_in_nf'] = sum(1 for k in e2s if k in nfk)
out['misses_in_hh'] = sum(1 for k in e2s if k in hhk)
out['misses_in_both'] = sum(1 for k in e2s if k in nfk and k in hhk)
out['nf_arms'] = sorted(next(iter(nfk.values()))['arms'])
out['nf_budget'] = [nf['budget'], nf['secondary_budget']]

# reliability: does rendered-context containment recover exactly `units_delivered` turns?
convs = arms.load_conversations(ft_pipeline.LOCOMO)
raw = json.load(open(ft_pipeline.LOCOMO, encoding='utf-8'))
spk = {}
for c in raw:
    for s in [k for k in c['conversation'] if k.startswith('session_')
              and not k.endswith('_date_time')]:
        for t in c['conversation'][s]:
            spk[(c['sample_id'], t['dia_id'])] = t['speaker']
diff = []
dup = 0
for k, v in hhk.items():
    cid = k[0]
    ctx = v['context']
    ids = [i for i, _ in convs[cid]]
    found = sum(1 for i, t in convs[cid]
                if f"{spk[(cid, i)]}: {t}" in ctx or t in ctx)
    diff.append(found - v['units_delivered'])
    dup += sum(1 for i, t in convs[cid]
               if sum(1 for i2, t2 in convs[cid] if t2 == t) > 1)
out['hh_unitsdelivered_minus_textcontained_median'] = sorted(diff)[len(diff) // 2]
out['hh_unitsdelivered_minus_textcontained_absmax'] = max(abs(x) for x in diff)
out['hh_items_with_any_recovery_mismatch'] = sum(1 for x in diff if x != 0)
out['locomo_items_with_duplicate_turn_texts'] = dup

# annotated-evidence delivery on the covered misses (the arc's deployed measure)
for arm in out['nf_arms']:
    out[f'miss_any_evidence_{arm}'] = sum(
        1 for k in e2s if k in nfk and nfk[k]['arms'][arm]['any_evidence'])
    out[f'miss_all_evidence_{arm}'] = sum(
        1 for k in e2s if k in nfk and nfk[k]['arms'][arm]['all_evidence'])

Path(ROOT / 'experiments/probes/miss_audit/PF4_deployed_coverage.json').write_text(
    json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(out, indent=1))
