"""Same-retrieval chronology probe: prepare, calibrate, run, blind-score, summarize."""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request
from preflight import ROOT,P,I,read,sha,committed,digest,E
from analysis.hh001_prompt import render_reader_prompt

OUT=P/'chronology_artifacts'
OLD=ROOT/'experiments/study_E/artifacts/confirmation/restart005'
ARMS=['ORIGINAL','NO_RECENT','CHRONO_NO_RECENT']
CAP=16384


def save(name,v):
    with (OUT/name).open('x',encoding='utf-8') as f:
        json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def request(route,value=None):
    req=urllib.request.Request('http://127.0.0.1:8097/'+route,data=None if value is None else json.dumps(value).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=600) as f:return json.load(f)
def native(payload):
    return request('apply-template',dict(messages=[dict(role='user',content=payload)],add_generation_prompt=True,
        chat_template_kwargs={'enable_thinking':False},reasoning_effort='none'))['prompt']
def final(r):
    assert r.get('stop_type')=='eos' and not r.get('truncated') and r.get('content','').strip(),'INCOMPLETE_RESPONSE'
    assert '<think>' not in r['content'] and '</think>' not in r['content'],'UNEXPECTED_THINKING'
    return r['content'].strip()
def check(calibrated=False):
    committed(OUT/'input_gate.json');committed(P/'chronology.py')
    g=read(OUT/'input_gate.json');assert g['status']=='PASS' and g['code_sha256']==sha(P/'chronology.py')
    for n,h in g['hashes'].items():assert sha(OUT/n)==h
    assert not (OUT/'pending.json').exists(),'UNCERTAIN_CALL'
    if calibrated:
        committed(OUT/'calibration_gate.json');assert read(OUT/'calibration_gate.json')['status']=='PASS'


def prepare():
    committed(P/'CHRONOLOGY_PLAN.md');committed(P/'chronology.py');assert not OUT.exists()
    pins=read(OLD/'runtime_pins.json')
    for pin in pins:assert sha(Path(pin['path']))==pin['sha256']
    with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8097))!=0,'PORT_IN_USE'
    frozen={r['history']:r for r in read(P/'artifacts/blind_outputs.json')}
    originals={(r['history'],r['arm']):r for r in read(I/'prompts.json')}
    native_store=read(OLD/'prompt_store.json');prior_prompts=set(native_store.values())
    histories=read(I/'sources.json');rows=[]
    for h in histories:
        q=h['probes'][0];es=h['episodes'];by={e['id']:e for e in es};ids=frozen[h['id']]['baseline']['selected_ids']
        selected=[by[k] for k in ids];chronological=sorted(selected,key=lambda e:(e['turn_number'],e['id']))
        original=E.render_stm_payload(E._recency_window(es,32),selected)
        assert digest(original)==frozen[h['id']]['baseline']['context_sha256']
        contexts=dict(ORIGINAL=original,NO_RECENT=E.render_stm_payload([],selected),CHRONO_NO_RECENT=E.render_stm_payload([],chronological))
        fragments=lambda block:re.findall(r'<episode turn="\d+">.*?</episode>',block,re.S)
        retrieval=fragments(original.split('<retrieved_stm>',1)[1])
        assert sorted(retrieval)==sorted(fragments(contexts['NO_RECENT']))==sorted(fragments(contexts['CHRONO_NO_RECENT']))
        assert retrieval==fragments(contexts['NO_RECENT'])
        turns=[int(t) for t in re.findall(r'<episode turn="(\d+)">',contexts['CHRONO_NO_RECENT'])]
        assert turns==sorted(turns) and len(set(turns))==len(turns)
        assert all(c.startswith('<recent_context/>') for a,c in contexts.items() if a!='ORIGINAL')
        assert set(ids).isdisjoint(e['id'] for e in E._recency_window(es,32))
        assert render_reader_prompt(q['query'],original)+'\n<think>\n</think>\n'==originals[h['id'],'C1']['prompt']
        rows.append(dict(history=h['id'],id=q['id'],type=q['type'],query=q['query'],selected_ids=ids,contexts=contexts))
    assert len(rows)==192
    sample=[]
    for kind in ['straight','irrelevant','future','proposal','latest','absent']:
        sample.extend(sorted((r for r in rows if r['type']==kind),key=lambda r:r['id'])[:2 if kind in ['latest','absent'] else 3])
    assert len(sample)==16
    for bad in [dict(content='',stop_type='eos'),dict(content='x',stop_type='limit'),dict(content='<think>x</think>4',stop_type='eos')]:
        try:final(bad)
        except AssertionError:pass
        else:raise AssertionError('NEGATIVE_COMPLETENESS_FIXTURE')
    assert final(dict(content='45',stop_type='eos'))=='45'
    OUT.mkdir();save('contexts.json',rows);save('runtime_pins.json',pins)
    command=read(OLD/'launch.json')['command'];assert command[command.index('--reasoning')+1]=='off' and command[command.index('--reasoning-budget')+1]=='0'
    env=os.environ.copy();env['PATH']='C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;'+env['PATH']
    process=subprocess.Popen(command,stdout=(OUT/'server_stdout.txt').open('xb'),stderr=(OUT/'server_stderr.txt').open('xb'),env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    save('launch.json',dict(pid=process.pid,command=command,started=time.time()))
    for _ in range(180):
        assert process.poll() is None,'SERVER_EXITED'
        try:props=request('props');break
        except OSError:time.sleep(1)
    else:raise RuntimeError('SERVER_TIMEOUT')
    assert props['total_slots']==1;save('props.json',props)
    schedule=[]
    for i,r in enumerate(sample):
        for arm in ARMS[i%3:]+ARMS[:i%3]:
            prompt=native(render_reader_prompt(r['query'],r['contexts'][arm]))
            assert prompt.endswith('<think>\n\n</think>\n\n')
            if arm=='ORIGINAL':assert prompt in prior_prompts,'NATIVE_BASELINE_REPLAY'
            tokens=len(request('tokenize',dict(content=prompt,add_special=False))['tokens']);assert tokens+CAP<=32768
            schedule.append(dict(case=f'call_{len(schedule)+1:02}',id=r['id'],history=r['history'],type=r['type'],query=r['query'],
                arm=arm,seed=5005,prompt=prompt,prompt_sha256=digest(prompt),tokens=tokens))
    save('schedule.json',schedule);save('calibration_prompt.json',dict(prompt=native('What is 17 plus 28? Give the final number.'),seed=5005))
    save('input_gate.json',dict(status='PASS',plan='c9158936',code_sha256=sha(P/'chronology.py'),offline_exact=192,membership_equal=192,
        original_native_exact=16,questions=16,calls=48,native_thinking=False,parser_negative_fixtures=True,
        hashes={n:sha(OUT/n) for n in ['contexts.json','runtime_pins.json','launch.json','props.json','schedule.json','calibration_prompt.json']},
        inputs={str(p):sha(p) for p in [I/'sources.json',I/'traces_sealed.json',I/'prompts.json',OLD/'prompt_store.json',P/'artifacts/blind_outputs.json']}))
    print(json.dumps(dict(prepared=16,calls=48,pid=process.pid)))


def capture(row,name):
    save('pending.json',dict(case=name,seed=row['seed'],prompt_sha256=digest(row['prompt'])))
    start=time.monotonic()
    response=request('completion',dict(prompt=row['prompt'],seed=row['seed'],temperature=.6,top_p=.95,top_k=20,min_p=0,
        repeat_penalty=1,presence_penalty=0,n_predict=CAP,cache_prompt=False,stream=False,reasoning_format='none',id_slot=0))
    save(name+'.json',dict(response=response,latency_seconds=time.monotonic()-start));(OUT/'pending.json').unlink()
    final(response);return response
def calibrate():
    check();r=read(OUT/'calibration_prompt.json');a=capture(r,'calibration1');b=capture(r,'calibration2')
    assert a['content']==b['content'] and final(a)=='45'
    save('calibration_gate.json',dict(status='PASS',identical=True,thinking_off_verified=True,hashes={n:sha(OUT/n) for n in ['calibration1.json','calibration2.json']}))
    print('Calibration PASS')
def run():
    check(True)
    for r in read(OUT/'schedule.json'):
        capture(r,r['case']);print(r['case']+' captured',flush=True)
    check(True);save('complete.json',dict(status='PASS',calls=48,hashes={r['case']:sha(OUT/(r['case']+'.json')) for r in read(OUT/'schedule.json')}))
    print('COMPLETE')
def score():
    committed(OUT/'complete.json');done=read(OUT/'complete.json');assert done['status']=='PASS'
    sys.path.insert(0,str(ROOT/'experiments/study_E'));from score_amendment003 import score as canonical
    assert canonical('','office')[0]==0 and canonical('office','office')[0]==1 and canonical('depot','office')[0]==0 and canonical('office or depot','office')[0] is None
    labels=read(I/'labels.json');scores=[];mapping=[]
    for r in read(OUT/'schedule.json'):
        path=OUT/(r['case']+'.json');committed(path);assert sha(path)==done['hashes'][r['case']]
        answer=final(read(path)['response']);reference=labels[r['id']]['answer'];value,why=canonical(answer,reference)
        bid=digest(r['prompt_sha256']+str(r['seed']))
        scores.append(dict(blind_id=bid,query=r['query'],reference=reference,answer=answer,score=value,rationale=why))
        mapping.append(dict(blind_id=bid,id=r['id'],type=r['type'],arm=r['arm'],case=r['case']))
    scores.sort(key=lambda r:r['blind_id']);save('scores.json',scores);save('mapping.json',mapping)
    save('scoring_gate.json',dict(status='PENDING' if any(r['score'] is None for r in scores) else 'PASS',pending=sum(r['score'] is None for r in scores)))
    print(json.dumps([r for r in scores if r['score'] is None],indent=2))
def summarize():
    committed(OUT/'scores.json');assert read(OUT/'scoring_gate.json')['status']=='PASS'
    scores={r['blind_id']:r for r in read(OUT/'scores.json')};mapping=read(OUT/'mapping.json');rows=[]
    for qid in dict.fromkeys(r['id'] for r in mapping):
        rs=[r for r in mapping if r['id']==qid];first=scores[rs[0]['blind_id']]
        rows.append(dict(id=qid,type=rs[0]['type'],query=first['query'],reference=first['reference'],arms={r['arm']:dict(answer=scores[r['blind_id']]['answer'],score=scores[r['blind_id']]['score']) for r in rs}))
    totals={}
    for group in ['primary','latest','absent']:
        rs=[r for r in rows if (r['type'] not in ['latest','absent'] if group=='primary' else r['type']==group)]
        totals[group]=dict(n=len(rs),scores={a:sum(r['arms'][a]['score'] for r in rs) for a in ARMS},pairs={})
        for a,b in zip(ARMS,ARMS[1:]):
            totals[group]['pairs'][a+'→'+b]=dict(gains=sum(r['arms'][b]['score']>r['arms'][a]['score'] for r in rs),losses=sum(r['arms'][b]['score']<r['arms'][a]['score'] for r in rs))
    save('result.json',dict(scope='Exploratory native-thinking-off reader probe',totals=totals,rows=rows))
    print(json.dumps(totals,indent=2))


if __name__=='__main__':
    try:{'prepare':prepare,'calibrate':calibrate,'run':run,'score':score,'summarize':summarize}[sys.argv[1]]()
    except Exception as e:
        if OUT.exists() and not (OUT/'failure.json').exists():save('failure.json',dict(phase=sys.argv[1],error=repr(e),status='INSTRUMENT_FAILURE'))
        raise
