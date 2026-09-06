"""Locked Study D input/prompt gates and serial persisted reader schedule."""
import argparse
import concurrent.futures
import hashlib
import html
import json
import multiprocessing
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
STUDY=Path(__file__).resolve().parent
CONTROL=ROOT.parent/'contextDecayWindow-study-D-control'
OUT=STUDY/'artifacts/confirmation'
ANCHOR='7b7506d2aa64c86a50ec88181b72137c66b44f02'
sys.path[:0]=[str(CONTROL/'episodic/src'),str(CONTROL/'src')]
import numpy as np
from corpus_opaque import make_session
from temporal import build
from develop import worker_init,embed
from statistics_locked import reachability
from analysis.hh001_prompt import render_reader_prompt
from episodic._render import render_stm_payload

def digest(data):
    return hashlib.sha256(data if isinstance(data,bytes) else data.encode()).hexdigest()

def save(name,obj):
    path=OUT/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n',encoding='utf-8')

def read(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))

def verify_registration():
    subprocess.run(['git','merge-base','--is-ancestor',ANCHOR,'HEAD'],cwd=ROOT,check=True)
    original=subprocess.check_output(['git','show',ANCHOR+':experiments/study_D/PRE_REGISTRATION.md'],cwd=ROOT)
    assert original.replace(b'\r\n',b'\n')==(STUDY/'PRE_REGISTRATION.md').read_bytes().replace(b'\r\n',b'\n')
    for row in json.loads((STUDY/'registration_inputs.json').read_text(encoding='utf-8-sig')):
        assert digest((ROOT/row['path']).read_bytes())==row['sha256'],row['path']
    assert subprocess.check_output(['git','status','--porcelain'],cwd=CONTROL).strip()==b''

def post(path,data=None):
    req=urllib.request.Request('http://127.0.0.1:8097'+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=900) as response:
        return json.load(response)

def complete(prompt,seed):
    return post('/completion',{'prompt':prompt,'seed':seed,'temperature':.6,'top_p':.95,'top_k':20,'min_p':0.,'repeat_penalty':1.,'presence_penalty':0.,'cache_prompt':True,'n_predict':8192,'stream':False,'reasoning_format':'none'})

def is_complete(result):
    text=result.get('content','')
    return bool(text.strip()) and '<think>' not in text and result.get('stop_type')=='eos' and result.get('tokens_predicted',8192)<8192 and not result.get('truncated',False)

def append(name,obj):
    with (OUT/name).open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(obj,sort_keys=True)+'\n')
        stream.flush()
        os.fsync(stream.fileno())

def committed(name):
    rel=(OUT/name).relative_to(ROOT).as_posix()
    raw=subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)
    assert raw.replace(b'\r\n',b'\n')==(OUT/name).read_bytes().replace(b'\r\n',b'\n')

def prepare():
    verify_registration()
    assert not (OUT/'prompt_gate.json').exists(),'Prepared artifacts already sealed'
    OUT.mkdir(parents=True,exist_ok=True)
    sessions=[]
    labels={}
    for seed in range(92001,92033):
        s,l=make_session(seed)
        sessions.append(s)
        labels.update(l)
    save('sources.json',sessions)
    save('labels.json',labels)
    ids=[e['id'] for s in sessions for e in s['episodes']]
    assert len(ids)==len(set(ids))==4480 and len(labels)==224
    for s in sessions:
        for p in s['probes']:
            label=labels[p['id']]
            for group in label['sufficient_sets']:
                for span in group:
                    carriers=[e for e in s['episodes'] if span in e['user_message']]
                    assert len(carriers)==1 and carriers[0]['turn_number']<141
            if p['type'] in ('T1','T2'):
                target=44 if p['type']=='T1' else 100
                assert label['gold_ids'][0]==s['episodes'][target-1]['id']
    save('input_seal.json',{name:digest((OUT/name).read_bytes()) for name in ('sources.json','labels.json')})
    texts=sorted(set([e['user_message']+'\n'+e['assistant_message'] for s in sessions for e in s['episodes']]+[p['query'] for s in sessions for p in s['probes']]))
    if (OUT/'vectors.npz').exists():
        manifest=read('vector_manifest.json')
        assert manifest['texts']==texts and manifest['file_sha256']==digest((OUT/'vectors.npz').read_bytes())
        array=np.load(OUT/'vectors.npz')['vectors']
    else:
        start=time.monotonic()
        entries=[]
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(8,os.cpu_count() or 1),initializer=worker_init) as pool:
            for n,row in enumerate(pool.map(embed,texts),1):
                entries.append(row)
                if n%250==0:
                    print(json.dumps({'stage':'embeddings','done':n,'total':len(texts)}),flush=True)
        assert len({x[3] for x in entries})==1
        array=np.stack([x[1] for x in entries])
        np.savez_compressed(OUT/'vectors.npz',vectors=array)
        save('vector_manifest.json',{'texts':texts,'file_sha256':digest((OUT/'vectors.npz').read_bytes()),'content_sha256':digest(array.astype(np.float32).tobytes()),'worker_pids':sorted({x[2] for x in entries}),'sentinel_sha256':entries[0][3],'wall_seconds':time.monotonic()-start,'worker_cpu_seconds':sum(x[4] for x in entries),'calls':len(texts)+len({x[2] for x in entries})})
    vectors=dict(zip(texts,array))
    prompts={}
    logical=[]
    traces=[]
    changed_sets=0
    arms=['C0','C1','ORACLE','NULL']
    for si,s in enumerate(sessions):
        es=[{**e,'embedding':vectors[e['user_message']+'\n'+e['assistant_message']]} for e in s['episodes']]
        by_id={e['id']:e for e in es}
        arm_order=arms[si%4:]+arms[:si%4]
        for p in s['probes']:
            start=time.perf_counter()
            a,b,trace=build(es,p['query'],vectors[p['query']])
            latency=time.perf_counter()-start
            # Gold enters only this reference construction/measurement block.
            label=labels[p['id']]
            oracle=render_stm_payload([],sorted([by_id[x] for x in label['gold_ids']],key=lambda e:e['turn_number'])) if label['gold_ids'] else ''
            blocks={'C0':a,'C1':b,'ORACLE':oracle,'NULL':''}
            delivered={arm:re.findall(r'<episode turn="(\d+)">',text) for arm,text in blocks.items()}
            changed_sets+=set(delivered['C0'])!=set(delivered['C1'])
            availability={}
            for arm,text in blocks.items():
                sets=label['sufficient_sets']
                availability[arm]=None if not sets else {'any':any(html.escape(span,quote=False) in text for group in sets for span in group),'complete':any(all(html.escape(span,quote=False) in text for span in group) for group in sets)}
            trace.update({'id':p['id'],'session':s['id'],'type':p['type'],'availability':availability,'delivered_turns':delivered,'latency_seconds':latency,'chars':{k:len(v) for k,v in blocks.items()}})
            traces.append(trace)
            for arm in arm_order:
                prompt=render_reader_prompt(p['query'],blocks[arm])+'\n<think>\n</think>\n'
                ph=digest(prompt)
                if ph not in prompts:
                    tokens=len(post('/tokenize',{'content':prompt,'add_special':False})['tokens'])
                    assert tokens+8192<65536
                    prompts[ph]={'prompt':prompt,'tokens':tokens}
                for seed in range(5005,5010):
                    call_key=digest(ph+':'+str(seed))
                    logical.append({'item':p['id'],'session':s['id'],'type':p['type'],'arm':arm,'seed':seed,'prompt_sha256':ph,'call_key':call_key,'query':p['query']})
        print(json.dumps({'stage':'prompts','sessions':si+1,'total':32}),flush=True)
    assert len(logical)==4480 and changed_sets>0
    save('prompts.json',prompts)
    save('mapping.json',logical)
    save('mechanism_sealed.json',traces)
    save('reachability.json',reachability())
    checks=subprocess.run([sys.executable,'-m','pytest',str(STUDY/'test_development_contract.py'),'-q'],cwd=ROOT,capture_output=True,text=True)
    save('tests.json',{'returncode':checks.returncode,'output':checks.stdout,'stderr':checks.stderr})
    assert checks.returncode==0
    props=post('/props')
    assert props.get('total_slots')==1
    spec=props.get('default_generation_settings',{}).get('params',{}).get('speculative',{})
    assert spec.get('types') in (None,[],['none'],'none'),spec
    save('runtime_props.json',props)
    seal={name:digest((OUT/name).read_bytes()) for name in ('sources.json','labels.json','vectors.npz','vector_manifest.json','prompts.json','mapping.json','mechanism_sealed.json','reachability.json','tests.json')}
    save('prompt_gate.json',{'status':'PASS','registration_commit':ANCHOR,'files':seal,'logical_cells':len(logical),'unique_calls':len({x['call_key'] for x in logical}),'changed_selection_sets':changed_sets,'max_tokens':max(x['tokens'] for x in prompts.values()),'control_path':str(CONTROL)})
    print(json.dumps({'stage':'prepared','logical_cells':4480,'unique_calls':len({x['call_key'] for x in logical})}),flush=True)

def validate_gate():
    verify_registration()
    gate=read('prompt_gate.json')
    assert gate['status']=='PASS'
    committed('prompt_gate.json')
    for name,sha in gate['files'].items():
        assert digest((OUT/name).read_bytes())==sha,name

def prefix():
    validate_gate()
    assert not (OUT/'prefix_responses.jsonl').exists(),'No extra prefix calls allowed'
    prompts=read('prompts.json')
    ph=max(prompts,key=lambda x:prompts[x]['tokens'])
    responses=[]
    for repeat in range(2):
        r=complete(prompts[ph]['prompt'],5005)
        append('prefix_responses.jsonl',{'repeat':repeat,'prompt_sha256':ph,'response':r})
        responses.append(r)
    passed=all(is_complete(r) for r in responses) and responses[0]['content']==responses[1]['content']
    save('prefix_gate.json',{'status':'PASS' if passed else 'INSTRUMENT_FAILURE','calls':2,'response_sha256':[digest(r.get('content','')) for r in responses]})
    print(json.dumps({'prefix_gate':'PASS' if passed else 'INSTRUMENT_FAILURE'}))

def run():
    validate_gate()
    assert read('prefix_gate.json')['status']=='PASS'
    committed('prefix_gate.json')
    assert not (OUT/'reader_gate.json').exists(),'Run already terminated'
    # No retry after an uncertain call: operator must resolve pending journal.
    assert not (OUT/'pending_call.json').exists(),'Uncertain prior call requires explicit repair'
    prompts=read('prompts.json')
    mapping=read('mapping.json')
    done={}
    if (OUT/'responses.jsonl').exists():
        for line in (OUT/'responses.jsonl').read_text().splitlines():
            row=json.loads(line)
            assert row['call_key'] not in done
            done[row['call_key']]=row
    total=len({x['call_key'] for x in mapping})
    for cell in mapping:
        k=cell['call_key']
        if k in done:
            continue
        save('pending_call.json',{'call_key':k,'prompt_sha256':cell['prompt_sha256'],'seed':cell['seed']})
        r=complete(prompts[cell['prompt_sha256']]['prompt'],cell['seed'])
        row={'call_key':k,'prompt_sha256':cell['prompt_sha256'],'seed':cell['seed'],'response':r}
        append('responses.jsonl',row)
        (OUT/'pending_call.json').unlink()
        done[k]=row
        if not is_complete(r):
            save('reader_gate.json',{'status':'INSTRUMENT_FAILURE','call_key':k,'completed_calls':len(done),'reason':'incomplete_final_or_truncation'})
            print(json.dumps({'stage':'reader','status':'INSTRUMENT_FAILURE','completed':len(done)}),flush=True)
            return
        if len(done)%25==0:
            print(json.dumps({'stage':'reader','completed':len(done),'total':total}),flush=True)
    # Blind surface contains no arm or retrieval data.
    labels=read('labels.json')
    surface=[]
    seen=set()
    for cell in mapping:
        k=cell['call_key']
        if k in seen:
            continue
        seen.add(k)
        surface.append({'blind_id':k,'query':cell['query'],'type':cell['type'],'reference':labels[cell['item']]['answer'],'response':done[k]['response']['content'],'complete':True})
    surface.sort(key=lambda x:digest('study-D-blind-order:'+x['blind_id']))
    save('blind_surface.json',surface)
    save('reader_gate.json',{'status':'PASS','physical_calls':len(done),'logical_cells':len(mapping),'responses_sha256':digest((OUT/'responses.jsonl').read_bytes()),'blind_surface_sha256':digest((OUT/'blind_surface.json').read_bytes())})
    print(json.dumps({'stage':'reader','status':'PASS','physical_calls':len(done)}),flush=True)

if __name__=='__main__':
    multiprocessing.freeze_support()
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','prefix','run'])
    args=parser.parse_args()
    {'prepare':prepare,'prefix':prefix,'run':run}[args.stage]()
