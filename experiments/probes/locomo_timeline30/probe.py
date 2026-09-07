"""Frozen chronological LoCoMo reader sample; judges isolated after raw commit."""
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'locomo_relevance_timeline'))
import runtime as r
import prepare as p
from analysis.hh001_prompt import render_judge_prompt,parse_judge_verdict
P=Path(__file__).resolve().parent
OUT=P/'artifacts'

def gate(calibrated=False):
    p.committed(OUT/'input_gate.json')
    g=p.read(OUT/'input_gate.json')
    assert g['status']=='PASS'
    for path,h in g['hashes'].items():assert p.sha(path)==h
    if calibrated:
        p.committed(OUT/'calibration.json')
        assert p.read(OUT/'calibration.json')['status']=='PASS'

def main():
    p.committed(__file__);p.committed(P/'PLAN.md');assert not OUT.exists();OUT.mkdir()
    network=[]
    with patch.object(p,'committed',lambda x:None),patch.object(p,'read',lambda x:dict(status='FAIL')),patch.object(r,'req',lambda *a,**k:network.append(a)):
        for cal in [False,True]:
            try:gate(cal)
            except AssertionError:pass
            else:raise AssertionError('failed gate accepted')
    assert not network
    try:gate()
    except Exception:pass
    else:raise AssertionError('missing gate accepted')
    part=p.read(p.OUT/'part1.json');fit=p.read(r.FIT)
    assert fit['status']=='PASS' and part['routes']=={'unsupported':1986}
    assert p.sha(p.OUT/'native_prompts.jsonl.gz')==fit['native_prompts_sha256']
    for name,h in part['outputs'].items():assert p.sha(p.OUT/name)==h
    primary=[x for x in r.rows('native_prompts.jsonl.gz') if x['category'] in [1,2,3,4]]
    broad=[];temporal=[]
    for conv in sorted({x['conversation'] for x in primary}):
        cs=sorted([x for x in primary if x['conversation']==conv],key=lambda x:x['key'])
        broad.extend([dict(x,group='broad20') for x in cs[:2]])
        excluded={x['key'] for x in cs[:2]}
        temporal.append(dict(next(x for x in cs if x['category']==2 and x['key'] not in excluded),group='temporal10'))
    schedule=broad+temporal
    assert len(schedule)==len({x['key'] for x in schedule})==30
    pins=p.read(r.OLD/'runtime_pins.json')
    for pin in pins:assert p.sha(pin['path'])==pin['sha256']
    paths=[Path(__file__),P/'PLAN.md',Path(r.__file__),Path(p.__file__),p.OUT/'native_prompts.jsonl.gz',r.FIT]
    p.save(OUT/'schedule.json',schedule)
    paths.append(OUT/'schedule.json')
    p.save(OUT/'input_gate.json',dict(status='PASS',hashes={str(x):p.sha(x) for x in paths},pins=pins,negative_gate_network_calls=0,source_prompts_exact=True))
    r.commit([OUT], 'Freeze thirty LoCoMo questions and exact current-arm prompts')
    gate();process=r.launch(OUT/'runtime')
    try:
        for x in schedule:
            assert r.native(x['text'])==x['prompt']
            assert x['tokens']+4096<=r.CONTEXT
        r.calibration(OUT)
        r.commit([OUT], 'Gate native-off reader and semantic judge calibration')
        gate(True)
        for i,x in enumerate(schedule):
            path=OUT/'reader'/x['key']
            p.save(path.with_suffix('.pending.json'),dict(key=x['key'],prompt_sha256=x['prompt_sha256'],started=time.time()))
            start=time.time();response=r.req('completion',dict(r.BASE,prompt=x['prompt']))
            p.save(path.with_suffix('.json'),dict(key=x['key'],seconds=time.time()-start,response=response))
            r.final(response)
            print(f'Reader {i+1}/30',flush=True)
        p.save(OUT/'reader_complete.json',dict(status='PASS',hashes={x['key']:p.sha(OUT/'reader'/(x['key']+'.json')) for x in schedule}))
        r.commit([OUT], 'Preserve all thirty reader answers before opening gold for evaluation')
        p.committed(OUT/'reader_complete.json')
        # Only evaluation now opens answer labels. No path back to reader inputs.
        source={x['sample_id']:x for x in p.read(p.prior.DATASET_PATH)}
        packet=[]
        for x in schedule:
            qa=source[x['conversation']]['qa'][x['source_index']]
            assert qa['question']==x['question']
            packet.append(dict(blind_id=p.digest('timeline30\0'+x['key']),question=x['question'],gold=str(qa['answer']),answer=r.final(p.read(OUT/'reader'/(x['key']+'.json'))['response'])))
        p.save(OUT/'blind_surface.json',sorted(packet,key=lambda x:x['blind_id']))
        r.commit([OUT/'blind_surface.json'], 'Freeze blind question-reference-answer evaluation surface')
        for seed in [9100,9101,9102]:
            for i,x in enumerate(sorted(packet,key=lambda x:p.digest(str(seed)+x['blind_id']))):
                prompt=r.native(render_judge_prompt(x['question'],x['gold'],x['answer']))
                path=OUT/'judges'/(x['blind_id']+'_'+str(seed))
                p.save(path.with_suffix('.pending.json'),dict(prompt_sha256=p.digest(prompt),started=time.time()))
                start=time.time();response=r.req('completion',dict(r.BASE,prompt=prompt,seed=seed,temperature=.2,top_p=.9))
                p.save(path.with_suffix('.json'),dict(blind_id=x['blind_id'],seed=seed,response=response,seconds=time.time()-start))
                r.final(response)
            print(f'Judge pass {seed} captured',flush=True)
        gate(True)
        p.save(OUT/'judge_complete.json',dict(status='PASS',calls=90,hashes={x.name:p.sha(x) for x in (OUT/'judges').glob('*.json') if '.pending.' not in x.name}))
    finally:r.stop(process,OUT/'runtime')

def score():
    p.committed(OUT/'judge_complete.json');p.committed(OUT/'reader_complete.json')
    complete=p.read(OUT/'judge_complete.json');reader=p.read(OUT/'reader_complete.json')
    assert len(complete['hashes'])==90
    results=[]
    for x in p.read(OUT/'schedule.json'):
        blind=p.digest('timeline30\0'+x['key']);votes=[]
        for seed in [9100,9101,9102]:
            name=blind+'_'+str(seed)+'.json';path=OUT/'judges'/name
            assert p.sha(path)==complete['hashes'][name]
            verdict,reason=parse_judge_verdict(r.final(p.read(path)['response']));assert reason
            votes.append(dict(verdict=verdict,reason=reason))
        path=OUT/'reader'/(x['key']+'.json');assert p.sha(path)==reader['hashes'][x['key']]
        results.append(dict(key=x['key'],blind_id=blind,group=x['group'],votes=votes,score=int(sum(v['verdict'] for v in votes)>=2),disagreement=len({v['verdict'] for v in votes})>1))
    p.save(OUT/'blind_votes.json',results)

def summarize():
    p.committed(OUT/'blind_votes.json')
    votes={x['key']:x for x in p.read(OUT/'blind_votes.json')}
    packet={x['blind_id']:x for x in p.read(OUT/'blind_surface.json')}
    source={x['sample_id']:x for x in p.read(p.prior.DATASET_PATH)}
    selections={x['key']:x for x in r.rows('selections.jsonl.gz')}
    adapter={x['id']:x for x in r.rows('adapter.jsonl.gz')}
    result=[]
    for x in p.read(OUT/'schedule.json'):
        v=votes[x['key']];s=packet[v['blind_id']]
        ids=selections[x['key']]['selected']
        delivered={d for k in ids for d in adapter[k]['dialogue_ids']}
        evidence=set(map(str,source[x['conversation']]['qa'][x['source_index']].get('evidence',[])))
        known={d for a in adapter.values() if a['conversation']==x['conversation'] for d in a['dialogue_ids']}
        state='unannotated' if not evidence else 'unresolved' if evidence-known else 'complete' if evidence<=delivered else 'partial' if evidence&delivered else 'none'
        response=p.read(OUT/'reader'/(x['key']+'.json'))
        result.append(dict(v,conversation=x['conversation'],category=x['category'],question=s['question'],gold=s['gold'],answer=s['answer'],evidence=state,missing=sorted(evidence-delivered),input_tokens=x['tokens'],output_tokens=response['response']['tokens_predicted'],seconds=response['seconds']))
    summary={g:dict(n=len(rs),correct=sum(x['score'] for x in rs),disagreements=sum(x['disagreement'] for x in rs),evidence_complete=sum(x['evidence']=='complete' for x in rs)) for g in ['broad20','temporal10'] for rs in [[x for x in result if x['group']==g]]}
    p.save(OUT/'results.json',dict(summary=summary,rows=result))
    print(json.dumps(dict(summary=summary,rows=result),indent=2),flush=True)

if __name__=='__main__':{'run':main,'score':score,'summarize':summarize}[sys.argv[1]]()
