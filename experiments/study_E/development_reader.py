import json,hashlib,urllib.request,os,subprocess,sys
from pathlib import Path
P=Path(__file__).parent/'artifacts/part1/development_dense'
O=Path(__file__).parent/'artifacts/part1/reader'
O.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(O/n).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def req(route,obj=None):
    r=urllib.request.Request('http://127.0.0.1:8097/'+route,data=None if obj is None else json.dumps(obj).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(r,timeout=240) as f:return json.load(f)
def committed(p):
    assert subprocess.check_output(['git','show','HEAD:'+p.relative_to(Path.cwd()).as_posix()]).replace(b'\r\n',b'\n')==p.read_bytes().replace(b'\r\n',b'\n')
def call(row):
    save('pending.json',row)
    r=req('completion',dict(prompt=row['prompt'],seed=5005,temperature=.6,top_p=.95,top_k=20,min_p=0,repeat_penalty=1,presence_penalty=0,n_predict=8192,cache_prompt=True,stream=False,reasoning_format='none'))
    with (O/'responses.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps(dict(row=row,response=r))+'\n');f.flush();os.fsync(f.fileno())
    (O/'pending.json').unlink()
    assert r.get('content','').strip() and not r.get('truncated') and r.get('stop_type')=='eos' and '<think>' not in r.get('content',''), 'INSTRUMENT_FAILURE'
    return r
if sys.argv[1]=='seal':
    assert not (O/'input_gate.json').exists()
    prompts=json.loads((P/'prompts.json').read_text());rows=[]
    for x in prompts:
        if (x['session'] in ['session-93001','session-93002','session-93003'] and x['type'] in ['straight','irrelevant','future','proposal'] and x['arm'] in ['C0','C1']) or (x['type'] in ['latest','absent'] and x['arm']=='C1'):rows.append(x)
    assert len(rows)==32
    save('props.json',req('props'))
    pins=json.loads(Path('experiments/study_D/artifacts/part1/runtime_gpu/launch.json').read_text())
    checked=[]
    for x in (pins['files'][0],pins['files'][2]):
        with open(x['path'],'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==x['sha256']
        checked.append(x)
    for row in rows:
        row['tokens']=len(req('tokenize',dict(content=row['prompt'],add_special=False))['tokens'])
        assert row['tokens']+8192<=65536
    largest=max(rows,key=lambda x:x['tokens'])
    schedule=[dict(largest,stage='prefix1'),dict(largest,stage='prefix2'),dict(prompt='Say exactly: ready.\nAnswer:\n<think>\n</think>\n',stage='short')]+rows
    save('schedule.json',schedule)
    save('input_gate.json',dict(status='PASS',calls=35,max_tokens=largest['tokens'],schedule_sha256=sha(O/'schedule.json'),source_sha256=sha(P/'sources.json'),prompts_sha256=sha(P/'prompts.json'),verified=checked))
    print(json.dumps(dict(calls=35,max_tokens=largest['tokens'])))
else:
    committed(O/'input_gate.json')
    gate=json.loads((O/'input_gate.json').read_text())
    assert gate['schedule_sha256']==sha(O/'schedule.json')
    assert not (O/'responses.jsonl').exists()
    schedule=json.loads((O/'schedule.json').read_text())
    a=call(schedule[0]);b=call(schedule[1]);assert a['content']==b['content']
    save('prefix_gate.json',dict(status='PASS',equal=True))
    for i,row in enumerate(schedule[2:],3):call(row);print(f'{i}/35',flush=True)
    save('complete.json',dict(status='PASS',calls=35,responses_sha256=sha(O/'responses.jsonl')))
