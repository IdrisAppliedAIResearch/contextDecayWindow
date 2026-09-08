"""Exact packing trace audit; no new selection policy or reader calls."""
import json
from preflight import P,I,ROOT,read,sha,committed,digest,E


def walk(es,budget):
    admitted=[];steps=[]
    for i,e in enumerate(es):
        used=len(E.render_stm_payload([],admitted))
        trial=len(E.render_stm_payload([],admitted+[e]));cost=trial-used
        steps.append(dict(id=e['id'],turn=e['turn_number'],position=i+1,used_before=used,remaining=budget-used,cost=cost,admitted=trial<=budget))
        if trial<=budget:admitted.append(e)
    expected=E.pack_stm_payload([],es,budget)
    assert [e['id'] for e in admitted]==list(expected.selected_ids)
    assert E.render_stm_payload([],admitted)==expected.payload
    return steps,admitted


def main():
    for path in [P/'MISSES_PLAN.md',P/'misses.py']:committed(path)
    paths=[P/'chronology_artifacts/result.json',P/'chronology_artifacts/contexts.json',I/'sources.json',I/'labels.json',I/'traces_sealed.json',
        ROOT/'experiments/study_E/artifacts/confirmation/restart005/diagnostics_rows_verified.json',P/'artifacts/blind_outputs.json',P/'difference_artifacts/outcomes.json']
    for path in paths:committed(path)
    result=read(paths[0]);contexts={r['id']:r for r in read(paths[1])};histories={h['id']:h for h in read(I/'sources.json')}
    traces={r['history']:r['trace'] for r in read(I/'traces_sealed.json')};labels=read(I/'labels.json')
    diags={r['history']:r for r in read(paths[5])};frozen={r['history']:r for r in read(paths[6])};variants=read(paths[7])
    cases=[r for r in result['rows'] if r['type'] not in ['latest','absent'] and not r['arms']['CHRONO_NO_RECENT']['score']]
    assert len(cases)==4;rows=[]
    for r in cases:
        context=contexts[r['id']];h=histories[context['history']];es=h['episodes'];by={e['id']:e for e in es};t=traces[h['id']]
        recent=list(E._recency_window(es,32));recent_ids={e['id'] for e in recent}
        candidates=[es[i] for i in t['eligible_after'] if es[i]['id'] not in recent_ids]
        temporal,first=walk(candidates,8000);assert [e['id'] for e in first]==t['temporal_ids']
        seen={e['id'] for e in first}|recent_ids
        merged=first+[es[i] for i in t['prior']['ranking'] if es[i]['id'] not in seen]
        final,selected=walk(merged,32000);ids=[e['id'] for e in selected];assert ids==t['selected_ids']==context['selected_ids']
        original=E.render_stm_payload(recent,selected);chrono=E.render_stm_payload([],sorted(selected,key=lambda e:e['turn_number']))
        assert digest(original)==frozen[h['id']]['baseline']['context_sha256']
        assert original==context['contexts']['ORIGINAL'] and chrono==context['contexts']['CHRONO_NO_RECENT']
        missing=set(labels[r['id']]['gold_ids'])-set(ids);assert len(missing)==1
        target=next(iter(missing));assert target in {e['id'] for e in candidates}
        carrier=next(x for x in diags[h['id']]['arms']['C1']['carriers'] if x['id']==target)
        anchor=max(es[i]['turn_number'] for i in t['route']['anchors'])
        window=[dict(turn=e['turn_number'],selected=e['id'] in ids,temporal=e['id'] in t['temporal_ids'],text=e['user_message'].split('\n')[0]) for e in es if by[target]['turn_number']-2<=e['turn_number']<=anchor]
        rows.append(dict(id=r['id'],history=h['id'],question=r['query'],gold=r['reference'],reader_answer=r['arms']['CHRONO_NO_RECENT']['answer'],
            target=by[target],anchor=anchor,carrier=carrier,temporal=next(x for x in temporal if x['id']==target),
            final=next(x for x in final if x['id']==target),temporal_selected_turns=[e['turn_number'] for e in first],
            selected_count=len(ids),final_chars=len(E.render_stm_payload([],selected)),window=window,
            earlier_fusion_has_target=target in frozen[h['id']]['fusion']['selected_ids'],
            existing_variants={x['mode']:x['fusion_complete'] for x in variants if x['id']==r['id']}))
    out=dict(status='PASS',plan='ba9d0dd6',exact_pack_replays=8,original_and_chrono_exact=4,candidate_presence=4,
        no_new_reader_calls=True,inputs={str(p):sha(p) for p in paths},rows=rows)
    path=P/'chronology_artifacts/misses_audit.json';assert not path.exists();path.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(q=r['question'],gold=r['gold'],answer=r['reader_answer'],temporal=r['temporal'],final=r['final'],turns=r['temporal_selected_turns'],window=r['window'],variants=r['existing_variants']) for r in rows],indent=2))


if __name__=='__main__':main()
