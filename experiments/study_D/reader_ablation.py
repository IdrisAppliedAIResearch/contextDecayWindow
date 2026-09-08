"""Extension-005 sealed 35-call plus duplicate development runtime check."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
CONTROL=ROOT.parent/'contextDecayWindow-study-D-control'
sys.path[:0]=[str(CONTROL/'episodic/src'),str(CONTROL/'src')]
from temporal import build
from analysis.hh001_prompt import render_reader_prompt

OUT=ROOT/'experiments/study_D/artifacts/part1/reader_ablation'
DEV=OUT.parent/'development_opaque'

def post(path,data):
    req=urllib.request.Request('http://127.0.0.1:8097'+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=900) as response:
        return json.load(response)

def save(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'responses.jsonl').exists(),'No additional calls authorized on rerun'
    manifest=json.loads((DEV/'vector_manifest.json').read_text())
    assert hashlib.sha256((DEV/'vectors.npz').read_bytes()).hexdigest()==manifest['file_sha256']
    vectors=dict(zip(manifest['texts'],np.load(DEV/'vectors.npz')['vectors']))
    sources=json.loads((DEV/'sources.json').read_text())
    cells=[]
    for s in sources:
        es=[{**e,'embedding':vectors[e['user_message']+'\n'+e['assistant_message']]} for e in s['episodes']]
        for p in s['probes']:
            a,b,_=build(es,p['query'],vectors[p['query']])
            cells.append((p,[render_reader_prompt(p['query'],x)+'\n<think>\n</think>\n' for x in (a,b)]))
    schedule=[]
    for i in range(35):
        p,prompts=cells[i%28]
        prompt=prompts[i%2]
        tokens=len(post('/tokenize',{'content':prompt,'add_special':False})['tokens'])
        schedule.append({'index':i,'id':p['id'],'arm':'C0' if i%2==0 else 'C1','prompt':prompt,'tokens':tokens,'sha256':hashlib.sha256(prompt.encode()).hexdigest()})
    largest=max(schedule,key=lambda r:r['tokens'])
    schedule += [{**largest,'index':35},{**largest,'index':36}]
    assert all(x['tokens']+8192<65536 for x in schedule)
    save('prompt_seal.json',schedule)
    raw=[]
    for cell in schedule:
        result=post('/completion',{'prompt':cell['prompt'],'seed':5005,'temperature':.6,'top_p':.95,'top_k':20,'min_p':0.,'repeat_penalty':1.,'presence_penalty':0.,'cache_prompt':False,'n_predict':8192,'stream':False,'reasoning_format':'none'})
        with (OUT/'responses.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({'index':cell['index'],'prompt_sha256':cell['sha256'],'response':result},sort_keys=True)+'\n')
            f.flush()
        text=result.get('content','')
        complete=bool(text.strip()) and result.get('stop_type')=='eos' and result.get('tokens_predicted',8192)<8192 and not result.get('truncated',False) and '<think>' not in text
        if not complete:
            save('gate.json',{'status':'INSTRUMENT_FAILURE','index':cell['index'],'reason':'completeness','calls':cell['index']+1,'scores_opened':False})
            return
        raw.append(text)
        print(json.dumps({'completed':cell['index']+1,'total':37,'tokens':result.get('tokens_predicted')}),flush=True)
    identical=raw[35]==raw[36]
    save('gate.json',{'status':'PASS' if identical else 'INSTRUMENT_FAILURE','reason':'long-prefix identity','calls':37,'byte_identical':identical,'scores_opened':False,'max_prompt_tokens':largest['tokens']})

if __name__=='__main__':
    main()
