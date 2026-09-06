"""Unseal only after committed complete blind scores; session-level reporting."""
import hashlib
import json
from pathlib import Path
import subprocess
from statistics import mean
from statistics_locked import summarize,disposition

ROOT=Path(__file__).resolve().parents[2]
STUDY=Path(__file__).parent
OUT=STUDY/'artifacts/confirmation'

def read(name):
    return json.loads((OUT/name).read_text())

def main():
    scoring=read('resolved_scoring_gate.json')
    assert scoring['status']=='PASS','Do not unseal outcomes while adjudication is pending'
    raw=(OUT/'resolved_scores.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==scoring['blind_scores_sha256']
    rel=(OUT/'resolved_scores.json').relative_to(ROOT).as_posix()
    assert subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT).replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n')
    scores={r['blind_id']:r['score'] for r in json.loads(raw)}
    assert all(v in (0,1) for v in scores.values())
    mapping=read('mapping.json')
    aliases=read('score_aliases.json')
    traces={r['id']:r for r in read('mechanism_sealed.json')}
    for r in mapping:
        r['score']=scores[aliases[r['item']+':'+r['call_key']]]
    sessions=sorted({r['session'] for r in mapping})
    types=['T1','T2','T3','T4','M1','M2','N1']
    arms=['C0','C1','ORACLE','NULL']
    def rate(arm,ts,session=None):
        rows=[r for r in mapping if r['arm']==arm and r['type'] in ts and (session is None or r['session']==session)]
        return mean(r['score'] for r in rows)
    differences=[rate('C1',['T1','T2'],s)-rate('C0',['T1','T2'],s) for s in sessions]
    primary=summarize(differences)
    primary['C0_accuracy']=rate('C0',['T1','T2'])
    primary['C1_accuracy']=rate('C1',['T1','T2'])
    primary['correct_samples']={a:sum(r['score'] for r in mapping if r['arm']==a and r['type'] in ('T1','T2')) for a in arms}
    primary['samples_per_arm']=320
    guard_other=rate('C1',['T3','T4','M1','M2'])-rate('C0',['T3','T4','M1','M2'])
    guard_absence=rate('C1',['N1'])-rate('C0',['N1'])
    primary_traces=[t for t in traces.values() if t['type'] in ('T1','T2')]
    delivery=mean(int(t['availability']['C1']['complete'])-int(t['availability']['C0']['complete']) for t in primary_traces)
    by_type={}
    for typ in types:
        subset=[t for t in traces.values() if t['type']==typ]
        type_d=[rate('C1',[typ],s)-rate('C0',[typ],s) for s in sessions]
        by_type[typ]={'queries':32,'accuracy':{a:rate(a,[typ]) for a in arms},'reader_difference_ci95':summarize(type_d)['ci95'],'complete_evidence':None if typ=='N1' else {a:sum(t['availability'][a]['complete'] for t in subset) for a in arms}}
    conditional={}
    for arm in ('C0','C1'):
        ids={k for k,t in traces.items() if t['availability'][arm] and t['availability'][arm]['complete']}
        selected=[r for r in mapping if r['item'] in ids]
        conditional[arm]={'queries':len(ids),'arm_accuracy':mean(r['score'] for r in selected if r['arm']==arm) if ids else None,'same_item_oracle_accuracy':mean(r['score'] for r in selected if r['arm']=='ORACLE') if ids else None}
    common={k for k,t in traces.items() if t['availability']['C0'] and t['availability']['C0']['complete'] and t['availability']['C1']['complete']}
    conditional['common']={'queries':len(common),'accuracy':{a:mean(r['score'] for r in mapping if r['item'] in common and r['arm']==a) if common else None for a in ('C0','C1','ORACLE')}}
    result={'registration_commit':'7b7506d2aa64c86a50ec88181b72137c66b44f02','disposition':disposition(primary,delivery,guard_other,guard_absence),'primary':primary,'primary_complete_evidence_difference':delivery,'guardrail_other_difference':guard_other,'guardrail_absence_difference':guard_absence,'by_type':by_type,'conditional_reader':conditional,'per_session_difference':dict(zip(sessions,differences)),'reader_calls':read('reader_gate.json')['physical_calls'],'scope':'Restricted synthetic quoted-name revision-history family, one reader; no adoption.'}
    result['scoring_deviation']='Amendment 001: eight single-agent judgments; no human or three-pass validation.'
    result['seed_primary_accuracy']={str(seed):{a:mean(r['score'] for r in mapping if r['arm']==a and r['type'] in ('T1','T2') and r['seed']==seed) for a in arms} for seed in range(5005,5010)}
    result['guardrail_other_ci95']=summarize([rate('C1',['T3','T4','M1','M2'],s)-rate('C0',['T3','T4','M1','M2'],s) for s in sessions])['ci95']
    result['guardrail_absence_ci95']=summarize([rate('C1',['N1'],s)-rate('C0',['N1'],s) for s in sessions])['ci95']
    prompts=read('prompts.json')
    result['context_cost']={a:{'mean_prompt_tokens':mean(prompts[r['prompt_sha256']]['tokens'] for r in mapping if r['arm']==a),'max_prompt_tokens':max(prompts[r['prompt_sha256']]['tokens'] for r in mapping if r['arm']==a)} for a in arms}
    (OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':
    main()
