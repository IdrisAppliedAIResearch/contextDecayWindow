"""AF-PRE-011 preflight (PF4 reachability, no model, no reader calls):
how much conversation does an anchor-centered pack consume, and can local geometry cover the
evidence at all? Distances between evidence turns decide whether anchor +/- k windows can ever
reach all_evidence; char costs decide which budgets any pack can fit.
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

HERE = Path(__file__).resolve().parent
s2 = json.load(open(ROOT / 'experiments/probes/unified_anchor/artifacts/sample2.json',
                    encoding='utf-8'))
audit = {r['qid']: r for r in json.load(
    open(ROOT / 'experiments/probes/miss_audit/artifacts/e5_subpartition.json',
         encoding='utf-8'))['items']}
convs = arms.load_conversations(ft_pipeline.LOCOMO)

turn_chars = []
pack_chars = Counter()
cov = {k: 0 for k in (0, 1, 2, 4)}
multi = 0
span_chars = []
for e in s2:
    cid = e['sample_id']
    turns = convs[cid]
    ids = [d for d, _ in turns]
    ev = audit[e['qid']]['ev_ids']
    pos = [ids.index(d) for d in ev]
    a = ids.index(e['gold'])
    for _, t in turns:
        turn_chars.append(len(t))
    for k in cov:
        cover = set(range(max(0, a - k), min(len(ids), a + k + 1)))
        if all(p in cover for p in pos):
            cov[k] += 1
    if len(ev) > 1:
        multi += 1
        span_chars.append(sum(len(turns[i][1]) for i in range(min(pos), max(pos) + 1)))

turn_chars.sort()
span_chars.sort()
out = {
    'items': len(s2), 'items_multi_evidence': multi,
    'turn_chars_median': turn_chars[len(turn_chars) // 2],
    'turn_chars_p90': turn_chars[int(.9 * len(turn_chars))],
    'turns_fitting_budget': {str(b): int(b // (turn_chars[len(turn_chars) // 2] + 12))
                             for b in (500, 1000, 2000, 4000, 8000, 16000)},
    'gold_window_k_covers_all_evidence': {f'+/-{k}': f'{cov[k]}/120' for k in sorted(cov)},
    'evidence_span_chars_median_if_single_session': (span_chars[len(span_chars) // 2]
                                                     if span_chars else None),
    'evidence_span_chars_p90': (span_chars[int(.9 * len(span_chars))] if span_chars else None),
}
anchor_cost = [len(dict(convs[e['sample_id']])[e['gold']]) for e in s2]
anchor_cost.sort()
out['anchor_turn_chars_median'] = anchor_cost[len(anchor_cost) // 2]
out['anchor_alone_fits_500'] = sum(1 for e in s2
                                   if len(dict(convs[e['sample_id']])[e['gold']]) <= 500)
out['anchor_alone_any_evidence'] = sum(1 for e in s2 if audit[e['qid']]['n_evidence'] == 1)
Path(HERE / 'PF4_anchor_geometry.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(out, indent=1))
