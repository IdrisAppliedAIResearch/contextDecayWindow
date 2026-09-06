"""Offline source-to-final-prompt audit; no reader calls or score changes."""
import re,json
from pathlib import Path
from preflight import P,I,ROOT,read,sha,committed,E,save
from analysis.hh001_prompt import render_reader_prompt
O=P/'relevance_artifacts/full_e_reader'
def main():
    paths=[O/n for n in ['result.json','scores_resolved.json','schedule.json','complete.json']]+[P/'FULL_E_MISSES_PLAN.md',Path(__file__),I/'sources.json',I/'labels.json']
    for p in paths:committed(p)
    histories={h['probes'][0]['id']:h for h in read(I/'sources.json')}
    labels=read(I/'labels.json');schedule={r['id']:r for r in read(O/'schedule.json')}
    candidates={r['id']:r for r in read(P/'relevance_artifacts/blind.json') if r['study']=='E'}
    curves={r['id']:r for r in read(ROOT/'experiments/probes/retrieval_score_curves/artifacts/curves.json') if r['study']=='E'}
    gate=read(P/'relevance_artifacts/gate.json');assert sha(P/'relevance_artifacts/blind.json')==gate['outputs_sha256']
    def supported(parts,prompt):return all(x in prompt for x in parts)
    assert supported(['alpha','beta'],'alpha beta') and not supported(['alpha','beta'],'alpha')
    rows=[]
    for r in read(O/'result.json')['rows']:
        if r['score']:continue
        h=histories[r['id']];lab=labels[r['id']];s=schedule[r['id']];by={e['id']:e for e in h['episodes']}
        a=candidates[r['id']]['arms']['ANCHORED']
        context=E.render_stm_payload([],[by[k] for k in a['ids']])
        assert context==a['context'] and render_reader_prompt(r['query'],context) in s['prompt']
        assert set(lab['gold_ids']).issubset(a['ids'])
        assert all(supported(parts,s['prompt']) for parts in lab['sufficient_sets'])
        assert all(by[k]['user_message'] in s['prompt'] for k in lab['gold_ids'])
        raw=O/(r['case']+'.json');assert sha(raw)==read(O/'complete.json')['hashes'][r['case']]
        assert read(raw)['response']['content'].strip()==r['answer']
        anchor=lab['rationale']['anchor'];target=lab['rationale']['target']
        updates=[]
        for e in h['episodes']:
            m=re.match(r'The delivery location for "[^"]+" is now the (\w+)\.',e['user_message'])
            if m:updates.append(dict(turn=e['turn_number'],value=m[1],text=e['user_message'].splitlines()[0]))
        before=[e for e in updates if e['turn']<anchor];gold=before[-1]
        assert gold['turn']==target and gold['value']==r['reference']
        prior=[e for e in updates if e['turn']<target][-1]
        later=next(e for e in updates if e['turn']>anchor)
        values=re.findall(r'\b(office|warehouse|studio|depot|workshop|laboratory|annex|hangar)\b',r['answer'].lower())
        assert values and len(set(values))==1
        wrong=values[-1]
        near=next(e for e in h['episodes'] if e['turn_number']==lab['rationale']['near'])
        v=curves[r['id']];ti=v['turns'].index(target)
        between=[dict(turn=e['turn_number'],statement=e['user_message'].splitlines()[0]) for e in h['episodes'] if target<e['turn_number']<anchor]
        rows.append(dict(id=r['id'],query=r['query'],type=r['type'],gold=r['reference'],wrong=wrong,target=target,anchor=anchor,target_cosine=v['cosine'][ti],
            previous=prior,first_later=later,near=near['user_message'].splitlines()[0],intervening=between,
            matches_previous=wrong==prior['value'],matches_first_later=wrong==later['value'],
            matches_near=bool(re.search(r'\b'+wrong+r'\b',near['user_message'].splitlines()[0])),
            matching_update_turns=[e['turn'] for e in updates if e['value']==wrong],
            target_filler_mentions_wrong=wrong in h['episodes'][target-1]['user_message'].split('\n',1)[-1],
            complete_literal_support=True))
    assert len(rows)==22
    counts={k:sum(r[k] for r in rows) for k in ['matches_previous','matches_first_later','matches_near','target_filler_mentions_wrong']}
    save(O/'misses_audit.json',dict(plan='16f1820b',status='PASS',inputs={str(p):sha(p) for p in paths},exact_prompt_replays=22,independent_gold_reconstructions=22,negative_support_fixture=True,counts=counts,rows=rows))
    print(json.dumps(dict(counts=counts,cases=[{k:r[k] for k in ['query','gold','wrong','target','anchor','matches_previous','matches_first_later','matches_near']} for r in rows]),indent=2))
if __name__=='__main__':main()
