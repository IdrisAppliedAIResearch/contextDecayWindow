"""Exposed-data availability diagnostics, strictly after committed preflight."""
import html
import json
from pathlib import Path
import numpy as np
from preflight import P, I, O, read, sha, save, committed, require_gate, E


def dist(values):
    return dict(n=len(values),min=min(values),median=float(np.median(values)),
                p95=float(np.quantile(values,.95)),max=max(values)) if values else dict(n=0)


def compare(required,left,right):
    a = bool(required) and required.issubset(left)
    b = bool(required) and required.issubset(right)
    return dict(baseline_complete=a,fusion_complete=b,gain=b and not a,loss=a and not b)


def main():
    for p in [P/'analyze.py',O/'preflight.json',O/'blind_outputs.json']: committed(p)
    gate = read(O/'preflight.json'); require_gate(gate)
    assert sha(O/'blind_outputs.json') == gate['outputs_sha256']
    assert compare({'a'},{'b'},{'a'})['gain']
    assert compare({'a'},{'a'},{'b'})['loss']
    assert not compare(set(),set(),set())['fusion_complete']
    labels = read(I/'labels.json'); histories = {h['id']:h for h in read(I/'sources.json')}
    prior = {r['history']:r['evidence']['C1'] for r in read(I/'traces_sealed.json')}
    rows = []
    for r in read(O/'blind_outputs.json'):
        left = set(r['baseline']['selected_ids']); right = set(r['fusion']['selected_ids'])
        label = labels[r['id']]; required = set(label['gold_ids'])
        c = compare(required,left,right); assert c['baseline_complete'] == prior[r['history']]
        if c['fusion_complete']:
            assert any(all(html.escape(s,quote=False) in r['context'] for s in group) for group in label['sufficient_sets'])
        by = {e['id']:e for e in histories[r['history']]['episodes']}
        def detail(k):
            return dict(id=k,turn=by[k]['turn_number'],text=by[k]['user_message'],
                        parents=[by[e['seed']]['turn_number'] for e in r['fusion']['links'] if e['child']==k])
        rows.append(dict(history=r['history'],id=r['id'],type=r['type'],**c,
            required_added=sorted(required & (right-left)),required_removed=sorted(required & (left-right)),
            added_ids=sorted(right-left),removed_ids=sorted(left-right),
            baseline_n=len(left),fusion_n=len(right),baseline_chars=r['baseline']['retrieval_chars'],
            fusion_chars=len(E.render_stm_payload([], [by[k] for k in r['fusion']['selected_ids']])),
            baseline_context_chars=r['baseline']['context_chars'],fusion_context_chars=r['fusion']['context_chars'],
            context_changed=r['baseline']['context_sha256']!=r['fusion']['context_sha256'],
            linked_n=len(r['fusion'].get('linked_selected_ids',[])),
            added_linked_n=len(set(r['fusion'].get('linked_selected_ids',[])) & (right-left)),
            question=histories[r['history']]['probes'][0]['query'],
            required_details=[dict(**detail(k),baseline=k in left,fusion=k in right) for k in sorted(required)]))
    summary = {}
    for kind in ['primary','straight','irrelevant','future','proposal','latest','absent']:
        rs = [r for r in rows if (r['type'] in ['straight','irrelevant','future','proposal'] if kind=='primary' else r['type']==kind)]
        summary[kind] = dict(n=len(rs),availability_applicable=kind!='absent',
            **{k:sum(r[k] for r in rs) for k in ['baseline_complete','fusion_complete','gain','loss','context_changed']},
            required_added=sum(len(r['required_added']) for r in rs),required_removed=sum(len(r['required_removed']) for r in rs),
            same_record_count=sum(r['baseline_n']==r['fusion_n'] for r in rs),
            distributions={k:dist([r[k] for r in rs]) for k in ['baseline_n','fusion_n','baseline_chars','fusion_chars','linked_n','added_linked_n','baseline_context_chars','fusion_context_chars']},
            added_records=dist([len(r['added_ids']) for r in rs]),removed_records=dist([len(r['removed_ids']) for r in rs]))
    summary['scope'] = 'Exploratory availability only; no reader scores or efficacy disposition'
    summary['provenance'] = dict(preflight_sha256=sha(O/'preflight.json'),labels_sha256=sha(I/'labels.json'),
                                analysis_sha256=sha(P/'analyze.py'),measurement_gain_loss_fixtures=True)
    save(O/'diagnostic_rows.json',rows);save(O/'diagnostics.json',summary)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__': main()
