"""Registered descriptive diagnostics, after committed resolved scores; no inference."""
import gzip
import json
from collections import Counter
from pathlib import Path
import numpy as np
import score_confirmation as scoring

P = Path(__file__).resolve().parent / 'artifacts/confirmation/restart005'
I = P.parent / 'development_inputs'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def distribution(values):
    return dict(n=len(values), min=min(values), median=float(np.median(values)),
                p95=float(np.quantile(values, .95)), max=max(values)) if values else dict(n=0)


def main():
    for name in ['scores_resolved.json', 'scoring_gate_resolved.json', 'complete.json']:
        scoring.committed(P / name)
    gate = read(P / 'scoring_gate_resolved.json')
    assert gate['pending'] == 0 and scoring.sha(P / 'scores_resolved.json') == gate['scores_sha256']
    # Frozen renderer only; no mechanism replay, embeddings, or model requests.
    from mechanism import render_stm_payload
    histories = {h['id']: h for h in read(I / 'sources.json')}
    labels = read(I / 'labels.json')
    prompts = read(P / 'prompt_store.json')
    logical = read(P / 'logical_schedule.json')
    by_prompt = {(r['history'], r['arm']): prompts[r['prompt_sha256']] for r in logical}
    details = []
    for row in read(I / 'traces_sealed.json'):
        h = histories[row['history']]
        episodes = h['episodes']; by_id = {e['id']: e for e in episodes}
        required = set(labels[h['probes'][0]['id']]['gold_ids'])
        t = row['trace']; prior = t['prior']
        record = dict(history=h['id'], type=row['type'], required_ids=sorted(required), arms={})
        for arm in ['C0', 'C1']:
            a = prior if arm == 'C0' or t.get('unchanged') else t
            selected = a['selected_ids']; temporal = a.get('temporal_ids', [])
            eligible = t.get('eligible_before' if arm == 'C0' else 'eligible_after', [])
            if row['type'] == 'latest':
                assert prior['route']['reason'] == 'recency'
                eligible = sorted(prior['route']['eligible'],
                                  key=lambda i: (-episodes[i]['turn_number'], episodes[i]['id']))
            candidate = [episodes[i]['id'] for i in eligible]
            ranking = [episodes[i]['id'] for i in prior['ranking']]
            full = by_prompt[h['id'], arm]
            def fragment(identity):
                rendered = render_stm_payload([], [by_id[identity]])
                return rendered[rendered.index('<episode '):rendered.index('</episode>')+10]
            rendered_ids = [k for k in selected if fragment(k) in full]
            assert rendered_ids == selected, 'Selected source missing from exact rendered prompt'
            packed = render_stm_payload([], [by_id[k] for k in selected])
            temporal_block = render_stm_payload([], [by_id[k] for k in temporal])
            assert len(packed) <= 32000 and (not temporal or len(temporal_block) <= 8000)
            def complete(ids):
                return bool(required) and required.issubset(ids)
            assert complete(rendered_ids) == row['evidence'][arm]
            carriers = []
            for k in sorted(required):
                ranks = {name: ids.index(k)+1 if k in ids else None for name, ids in
                         [('cc80_rank', ranking), ('temporal_candidate_rank', candidate),
                          ('temporal_admission_rank', temporal), ('packed_rank', selected)]}
                carriers.append(dict(id=k, turn=by_id[k]['turn_number'],
                    source_chars=len(by_id[k]['user_message'])+len(by_id[k]['assistant_message']),
                    episode_serialized_chars=len(fragment(k)), rendered=k in rendered_ids, **ranks))
            record['arms'][arm] = dict(candidate_complete=complete(candidate),
                temporal_complete=complete(temporal), packed_complete=complete(selected),
                rendered_complete=complete(rendered_ids), candidate_n=len(candidate),
                temporal_n=len(temporal), selected_n=len(selected), retrieval_chars=len(packed),
                temporal_chars=len(temporal_block) if temporal else 0,
                full_prompt_chars=len(full), carriers=carriers, selected_ids=selected)
        left = set(record['arms']['C0']['selected_ids']); right = set(record['arms']['C1']['selected_ids'])
        record['displacement'] = dict(added_ids=sorted(right-left), removed_ids=sorted(left-right),
            required_added=sorted(required & (right-left)), required_removed=sorted(required & (left-right)))
        details.append(record)
    primary = [r for r in details if r['type'] in ['straight', 'irrelevant', 'future', 'proposal']]
    assert len(primary) == 128
    summary = dict(status='PASS', scope='Registered descriptive diagnostics; no extra efficacy tests',
                   primary_questions=128, all_questions=192, by_type={})
    for kind in ['primary', 'straight', 'irrelevant', 'future', 'proposal', 'latest', 'absent']:
        subset = primary if kind == 'primary' else [r for r in details if r['type'] == kind]
        summary['by_type'][kind] = {}
        for arm in ['C0', 'C1']:
            ars = [r['arms'][arm] for r in subset]
            summary['by_type'][kind][arm] = dict(n=len(ars),
                availability_applicable=kind != 'absent',
                **{k: sum(a[k] for a in ars) for k in ['candidate_complete', 'temporal_complete', 'packed_complete', 'rendered_complete']},
                distributions={k: distribution([a[k] for a in ars]) for k in
                    ['candidate_n', 'temporal_n', 'selected_n', 'retrieval_chars', 'temporal_chars', 'full_prompt_chars']},
                carrier_ranks={k: distribution([c[k] for a in ars for c in a['carriers'] if c[k] is not None])
                    for k in ['cc80_rank', 'temporal_candidate_rank', 'temporal_admission_rank', 'packed_rank']})
    summary['primary_displacement'] = dict(
        added=distribution([len(r['displacement']['added_ids']) for r in primary]),
        removed=distribution([len(r['displacement']['removed_ids']) for r in primary]),
        required_added=sum(len(r['displacement']['required_added']) for r in primary),
        required_removed=sum(len(r['displacement']['required_removed']) for r in primary))
    summary['primary_availability_pairs'] = dict(Counter(
        f"C0_{int(r['arms']['C0']['packed_complete'])}_C1_{int(r['arms']['C1']['packed_complete'])}" for r in primary))
    scores = {r['blind_id']: r for r in read(P / 'scores_resolved.json')}
    mapping = read(P / 'mapping.json')
    summary['noncanonical_abstentions'] = dict(Counter(r['arm'] for r in mapping
        if scores[r['blind_id']]['reviewer'] != 'frozen mechanical grammar'
        and scores[r['blind_id']].get('evidence') == 'I don know.'))
    summary['opening_revisions_by_final_correctness'] = dict(Counter(
        f"{r['arm']}_{scores[r['blind_id']]['score']}" for r in mapping if scores[r['blind_id']]['corrected_wrong_opening']))
    with gzip.open(P / 'responses.jsonl.gz', 'rt', encoding='utf-8') as f:
        responses = [json.loads(line) for line in f]
    summary['runtime'] = dict(calls=len(responses),
        latency_seconds=distribution([r['latency_seconds'] for r in responses]),
        summed_request_seconds=sum(r['latency_seconds'] for r in responses),
        output_tokens=distribution([r['response']['tokens_predicted'] for r in responses]))
    summary['input_hashes'] = {str(p.relative_to(P.parent)): scoring.sha(p) for p in
        [P/'scores_resolved.json', P/'mapping.json', P/'prompt_store.json', I/'traces_sealed.json', I/'sources.json', I/'labels.json']}
    for name, data in [('diagnostics_rows_verified.json', details), ('diagnostics_verified.json', summary)]:
        dest = P / name
        assert not dest.exists()
        dest.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ['primary_availability_pairs','primary_displacement','noncanonical_abstentions','opening_revisions_by_final_correctness','runtime']}))


if __name__ == '__main__':
    main()
