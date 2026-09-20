"""Full fresh confirmation under the committed thinking-off runtime selection."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import runtime005 as rt

b=rt.base
O=rt.OUT

def pins():
    previous=b.read(b.O.parent/'continuation004/loaded_runtime.json')
    for item in previous:
        assert b.sha(Path(item['path']))==item['sha256'],item['path']
    model=b.read(b.O/'input_gate.json')['runtime_files']
    for item in model:assert b.sha(Path(item['path']))==item['sha256']
    return previous+model

def seal():
    b.prereqs()
    for p in [rt.PROBE/'selection.json',b.STUDY/'amendments/AMENDMENT_005_RUNTIME_LOCK.md',
              Path(__file__).resolve(),Path(rt.__file__).resolve()]:b.committed(p)
    selection=b.read(rt.PROBE/'selection.json');assert selection['status']=='PASS'
    verified=pins()
    complete=b.read(b.P/'complete.json');assert complete['status']=='PASS'
    assert b.sha(b.P/'manifest.json')==complete['manifest_sha256']
    for name,digest in b.read(b.P/'manifest.json').items():assert b.sha(b.P/name)==digest
    assert not O.exists(),'NO_OVERWRITE'
    process=rt.start(selection['selected_slots'],O)
    rt.save(O/'runtime_pins.json',verified)
    originals=b.read(b.P/'prompts.json'); transformed=[];identities=[]
    for row in originals:
        prompt=rt.render(row['prompt'])
        transformed.append(dict(row,prompt=prompt))
        identities.append(dict(id=row['id'],arm=row['arm'],old_sha256=hashlib.sha256(row['prompt'].encode()).hexdigest(),
                               new_sha256=hashlib.sha256(prompt.encode()).hexdigest(),user_payload_preserved=True))
    store,physical,logical=b.schedule(transformed)
    old_logical=b.read(b.O/'logical_schedule.json')
    remove={'physical_id','prompt_sha256'}
    assert [{k:v for k,v in r.items() if k not in remove} for r in logical]==[{k:v for k,v in r.items() if k not in remove} for r in old_logical]
    tokens={key:len(rt.request('tokenize',dict(content=prompt,add_special=False))['tokens']) for key,prompt in store.items()}
    assert max(tokens.values())+rt.CAP<=rt.SLOT_CONTEXT
    largest=max(tokens,key=tokens.get)
    short=rt.render('Say exactly: ready.\nAnswer:'+rt.SUFFIX)
    short_key=hashlib.sha256(short.encode()).hexdigest();store[short_key]=short
    calibration=[dict(physical_id=stage,prompt_sha256=largest,seed=5005,stage=stage) for stage in ['prefix1','prefix2']]
    calibration.append(dict(physical_id='short',prompt_sha256=short_key,seed=5005,stage='short'))
    rt.save(O/'prompt_store.json',store);rt.save(O/'physical_schedule.json',calibration+physical)
    rt.save(O/'logical_schedule.json',logical);rt.save(O/'token_counts.json',tokens)
    rt.save(O/'prompt_transformation.json',identities)
    rt.save(O/'input_gate.json',dict(status='PASS',registration=b.REGISTRATION,amendment=rt.AMENDMENT,
        slots=selection['selected_slots'],calls=len(physical)+3,logical_answers=len(logical),
        maximum_input_tokens=max(tokens.values()),cap=rt.CAP,context_per_slot=rt.SLOT_CONTEXT,
        runner_sha256=b.sha(Path(__file__)),runtime_sha256=b.sha(Path(rt.__file__)),
        hashes={name:b.sha(O/name) for name in ['prompt_store.json','physical_schedule.json','logical_schedule.json','runtime_pins.json','props.json','launch.json']},
        source_hashes={name:b.sha(b.P/name) for name in ['sources.json','vectors.npz','manifest.json','prompts.json']},
        all_original_logical_identities_preserved=True,old_responses_reused=0,server_pid=process.pid))
    print(json.dumps(b.read(O/'input_gate.json')),flush=True)

def check():
    b.prereqs()
    for p in [O/'input_gate.json',Path(__file__).resolve(),Path(rt.__file__).resolve()]:b.committed(p)
    gate=b.read(O/'input_gate.json');assert gate['status']=='PASS'
    assert gate['runner_sha256']==b.sha(Path(__file__)) and gate['runtime_sha256']==b.sha(Path(rt.__file__))
    for name,digest in gate['hashes'].items():assert b.sha(O/name)==digest,name
    for name,digest in gate['source_hashes'].items():assert b.sha(b.P/name)==digest,name
    pins()
    props=rt.request('props');assert props==b.read(O/'props.json'),'SERVER_PROPERTIES_CHANGED'
    assert not list(O.glob('pending_*.json')),'UNCERTAIN_CALL'
    assert not (O/'responses.jsonl').exists(),'NO_RESTART'
    return gate

def finish(gate,rows):
    raw=O/'responses.jsonl'
    received=[json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()]
    by_id={r['row']['physical_id']:r for r in received}
    assert len(by_id)==len(received)==len(rows)==gate['calls']
    assert all(by_id[r['physical_id']]['row']==r and rt.valid(by_id[r['physical_id']]['response']) for r in rows)
    assert not list(O.glob('pending_*.json'))
    assert gate['runner_sha256']==b.sha(Path(__file__)) and gate['runtime_sha256']==b.sha(Path(rt.__file__))
    for name,digest in gate['source_hashes'].items():assert b.sha(b.P/name)==digest
    for name,digest in gate['hashes'].items():assert b.sha(O/name)==digest
    pins()
    def archive(path,chunks):
        digest=hashlib.sha256()
        with path.open('xb') as f:
            with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as zipped:
                for chunk in chunks:zipped.write(chunk);digest.update(chunk)
        return digest.hexdigest()
    arrival_sha=archive(O/'arrival.jsonl.gz',[raw.read_bytes()])
    ordered_sha=archive(O/'responses.jsonl.gz',[(json.dumps(by_id[r['physical_id']])+'\n').encode() for r in rows])
    rt.save(O/'complete.json',dict(status='PASS',registration=b.REGISTRATION,amendment=rt.AMENDMENT,
        calls=len(rows),logical_answers=3840,responses_sha256=ordered_sha,archive_sha256=b.sha(O/'responses.jsonl.gz'),
        arrival_sha256=arrival_sha,arrival_archive_sha256=b.sha(O/'arrival.jsonl.gz'),
        logical_schedule_sha256=gate['hashes']['logical_schedule.json'],all_nonempty_eos=True,
        old_responses_reused=0,thinking=False,slots=gate['slots']))

def run():
    gate=check();rows=b.read(O/'physical_schedule.json');store=b.read(O/'prompt_store.json');slots=gate['slots']
    # Replay on slot 0, exactly as in the probe. No competing jobs during calibration.
    a=rt.capture_wave(rows[:1],store,O,slots)[0]['response']
    c=rt.capture_wave(rows[1:2],store,O,slots)[0]['response']
    assert a['content'].encode()==c['content'].encode(),'PREFIX_IDENTITY_FAILURE'
    rt.save(O/'prefix_gate.json',dict(status='PASS',equal=True,thinking=False))
    rt.capture_wave(rows[2:3],store,O,slots)
    for i in range(3,len(rows),slots):
        rt.capture_wave(rows[i:i+slots],store,O,slots)
        print(f'{min(i+slots,len(rows))}/{len(rows)}',flush=True)
    finish(gate,rows)

if __name__=='__main__':
    try:{'seal':seal,'check':check,'run':run}[sys.argv[1]]()
    except Exception as error:
        if sys.argv[1]=='run' and not (O/'failure.json').exists():
            rt.save(O/'failure.json',dict(status='INSTRUMENT_FAILURE',error=repr(error),retry_authorized=False,
                                        uncertain_journals=[p.name for p in O.glob('pending_*.json')]))
        raise
