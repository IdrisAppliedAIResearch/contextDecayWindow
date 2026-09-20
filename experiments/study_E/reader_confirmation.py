"""Registered confirmation: compact aliases, serial capture, lossless archive."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

from prepare_confirmation import REGISTRATION, prereqs

ROOT=Path(__file__).resolve().parents[2]
STUDY=Path(__file__).resolve().parent
P=STUDY/'artifacts/confirmation/development_inputs'
O=P.parent/'reader'
KINDS=['straight','irrelevant','future','proposal','latest','absent']


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def committed(path):
    blob=subprocess.check_output(['git','show','HEAD:'+path.relative_to(ROOT).as_posix()],cwd=ROOT)
    assert blob.replace(b'\r\n',b'\n')==path.read_bytes().replace(b'\r\n',b'\n')


def save(name,value):
    path=O/name;assert not path.exists(),path
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def req(route,obj=None):
    request=urllib.request.Request('http://127.0.0.1:8097/'+route,data=None if obj is None else json.dumps(obj).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=240) as f:return json.load(f)


def schedule(prompts):
    store={};index={}
    for row in prompts:
        key=hashlib.sha256(row['prompt'].encode()).hexdigest()
        assert key not in store or store[key]==row['prompt']
        store[key]=row['prompt'];index[(row['session'],row['type'],row['arm'])]=(key,row)
    groups=sorted({r['session'] for r in prompts})
    physical=[];logical=[];seen={}
    for group_index,group in enumerate(groups):
        arms=['C0','C1','ORACLE','NULL'];shift=group_index%4;arms=arms[shift:]+arms[:shift]
        for kind in KINDS:
            for seed in range(5005,5010):
                for arm in arms:
                    key,row=index[(group,kind,arm)];identity=(key,seed)
                    if identity not in seen:
                        pid=hashlib.sha256(f'{key}:{seed}'.encode()).hexdigest();seen[identity]=pid
                        physical.append(dict(physical_id=pid,prompt_sha256=key,seed=seed,stage='measurement'))
                    logical_id=hashlib.sha256(f"{row['id']}:{arm}:{seed}".encode()).hexdigest()
                    logical.append(dict(logical_id=logical_id,physical_id=seen[identity],prompt_sha256=key,
                        seed=seed,question_id=row['id'],session=group,history=row['history'],type=kind,
                        arm=arm,query=row['query'],reference=row['reference']))
    assert len({r['logical_id'] for r in logical})==len(logical)
    return store,physical,logical


def seal():
    prereqs();committed(P/'complete.json')
    complete=read(P/'complete.json');assert complete['status']=='PASS' and complete['registration']==REGISTRATION
    assert sha(P/'manifest.json')==complete['manifest_sha256']
    for name,digest in read(P/'manifest.json').items():assert sha(P/name)==digest,name
    assert not (O/'input_gate.json').exists()
    O.mkdir(parents=True,exist_ok=True)
    store,physical,logical=schedule(read(P/'prompts.json'))
    assert len(logical)==3840
    pins=read(STUDY.parent/'study_D/artifacts/part1/runtime_gpu/launch.json')['files']
    for pin in [pins[0],pins[2]]:assert sha(Path(pin['path']))==pin['sha256']
    save('props.json',req('props'))
    tokens={}
    for key,prompt in store.items():
        tokens[key]=len(req('tokenize',dict(content=prompt,add_special=False))['tokens'])
        assert tokens[key]+8192<=65536
    largest=max(tokens,key=tokens.get)
    short='Say exactly: ready.\nAnswer:\n<think>\n</think>\n'
    short_key=hashlib.sha256(short.encode()).hexdigest();store[short_key]=short
    calibration=[dict(physical_id=stage,prompt_sha256=largest,seed=5005,stage=stage) for stage in ['prefix1','prefix2']]
    calibration.append(dict(physical_id='short',prompt_sha256=short_key,seed=5005,stage='short'))
    save('prompt_store.json',store);save('logical_schedule.json',logical);save('physical_schedule.json',calibration+physical)
    save('token_counts.json',tokens)
    save('input_gate.json',dict(status='PASS',registration=REGISTRATION,logical_answers=len(logical),
        physical_measurement_calls=len(physical),calls=len(physical)+3,maximum_input_tokens=tokens[largest],
        inputs_manifest_sha256=sha(P/'manifest.json'),source_sha256=sha(P/'sources.json'),
        prompt_store_sha256=sha(O/'prompt_store.json'),logical_schedule_sha256=sha(O/'logical_schedule.json'),
        physical_schedule_sha256=sha(O/'physical_schedule.json'),runner_sha256=sha(Path(__file__)),
        prefix_required=True,runtime_files=[pins[0],pins[2]]))
    print(json.dumps(dict(status='PASS',logical_answers=len(logical),calls=len(physical)+3,max_tokens=tokens[largest])),flush=True)


def check_run():
    prereqs()
    for path in [O/'input_gate.json',Path(__file__).resolve()]:committed(path)
    gate=read(O/'input_gate.json');assert gate['status']=='PASS' and gate['registration']==REGISTRATION
    for field,path in [('runner_sha256',Path(__file__)),('source_sha256',P/'sources.json'),
                       ('inputs_manifest_sha256',P/'manifest.json'),('prompt_store_sha256',O/'prompt_store.json'),
                       ('logical_schedule_sha256',O/'logical_schedule.json'),('physical_schedule_sha256',O/'physical_schedule.json')]:
        assert sha(path)==gate[field],field
    assert not (O/'responses.jsonl').exists() and not (O/'pending.json').exists()
    return gate


def capture(row,store):
    save('pending.json',row)
    response=req('completion',dict(prompt=store[row['prompt_sha256']],seed=row['seed'],temperature=.6,
        top_p=.95,top_k=20,min_p=0,repeat_penalty=1,presence_penalty=0,n_predict=8192,
        cache_prompt=True,stream=False,reasoning_format='none'))
    with (O/'responses.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(dict(row=row,response=response))+'\n');stream.flush();os.fsync(stream.fileno())
    (O/'pending.json').unlink()
    assert response.get('content','').strip() and not response.get('truncated')
    assert response.get('stop_type')=='eos' and '<think>' not in response['content'],'INSTRUMENT_FAILURE'
    return response


def run():
    gate=check_run();store=read(O/'prompt_store.json');rows=read(O/'physical_schedule.json')
    a,b=capture(rows[0],store),capture(rows[1],store)
    assert a['content']==b['content'],'PREFIX_IDENTITY_FAILURE'
    save('prefix_gate.json',dict(status='PASS',equal=True))
    for index,row in enumerate(rows[2:],3):
        capture(row,store);print(f'{index}/{len(rows)}',flush=True)
    # Preserve exact raw bytes in a deterministic lossless archive for Git.
    archive=O/'responses.jsonl.gz';assert not archive.exists()
    with (O/'responses.jsonl').open('rb') as source,archive.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as target:
            while block:=source.read(1024*1024):target.write(block)
    with gzip.open(archive,'rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==sha(O/'responses.jsonl')
    save('complete.json',dict(status='PASS',registration=REGISTRATION,calls=len(rows),logical_answers=3840,
        responses_sha256=sha(O/'responses.jsonl'),archive_sha256=sha(archive),
        logical_schedule_sha256=gate['logical_schedule_sha256'],all_nonempty_eos=True))


if __name__=='__main__':
    try:{'seal':seal,'run':run}[sys.argv[1]]()
    except Exception as error:
        if sys.argv[1]=='run' and O.exists() and not (O/'failure.json').exists():
            save('failure.json',dict(status='INSTRUMENT_FAILURE',error=repr(error),pending_exists=(O/'pending.json').exists(),retry_authorized=False))
        raise
