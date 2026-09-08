"""Authorized single capped-response repair, then original unissued schedule."""
import gzip,hashlib,json,os,subprocess,sys,urllib.request
from pathlib import Path
import reader_confirmation as base

OLD=base.O
O=OLD.parent/'continuation004'
AMENDMENT='1019f3e2a68d64b3e45077ef85cc50226a3302bc'
CAP=16384

def save(name,value):
    path=O/name;assert not path.exists(),path
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def old_rows():
    audit=base.read(OLD/'stop_audit.json')
    assert base.sha(OLD/'responses_stopped.jsonl.gz')==audit['archive_sha256']
    with gzip.open(OLD/'responses_stopped.jsonl.gz','rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==audit['raw_sha256']
    with gzip.open(OLD/'responses_stopped.jsonl.gz','rt',encoding='utf-8') as stream:
        rows=[json.loads(line) for line in stream]
    schedule=base.read(OLD/'physical_schedule.json')
    assert len(rows)==456 and all(r['row']==schedule[i] for i,r in enumerate(rows))
    assert all(r['response']['stop_type']=='eos' for r in rows[:-1])
    assert rows[-1]['response']['stop_type']=='limit' and rows[-1]['response']['tokens_predicted']==8192
    return rows

def seal():
    base.prereqs()
    path=base.STUDY/'amendments/AMENDMENT_004_output_cap_continuation.md'
    expected=subprocess.check_output(['git','show',AMENDMENT+':'+path.relative_to(base.ROOT).as_posix()])
    assert expected.replace(b'\r\n',b'\n')==path.read_bytes().replace(b'\r\n',b'\n')
    base.committed(OLD/'stop_audit.json')
    rows=old_rows();original=base.read(OLD/'physical_schedule.json');gate=base.read(OLD/'input_gate.json')
    for name,field in [('prompt_store.json','prompt_store_sha256'),('logical_schedule.json','logical_schedule_sha256'),('physical_schedule.json','physical_schedule_sha256')]:
        assert base.sha(OLD/name)==gate[field]
    for pin in gate['runtime_files']:assert base.sha(Path(pin['path']))==pin['sha256']
    assert base.sha(base.P/'sources.json')==gate['source_sha256']
    O.mkdir(parents=True,exist_ok=True)
    store=base.read(OLD/'prompt_store.json');tokens={}
    previous=base.read(OLD/'token_counts.json')
    for key,prompt in store.items():
        tokens[key]=len(base.req('tokenize',dict(content=prompt,add_special=False))['tokens'])
        assert tokens[key]+CAP<=65536
        if key in previous:assert tokens[key]==previous[key]
    save('props.json',base.req('props'));save('token_counts.json',tokens)
    schedule=original[:2]+original[455:]
    assert len(schedule)==3055
    save('schedule.json',schedule)
    save('provenance_plan.json',dict(reused_measurement_ids=[r['row']['physical_id'] for r in rows[3:-1]],
         repaired_id=rows[-1]['row']['physical_id'],unissued_ids=[r['physical_id'] for r in original[456:]],
         original_archive_sha256=base.sha(OLD/'responses_stopped.jsonl.gz'),logical_answers=3840))
    (O/'logical_schedule.json').write_bytes((OLD/'logical_schedule.json').read_bytes())
    save('input_gate.json',dict(status='PASS',amendment=AMENDMENT,cap=CAP,calls=3055,
         runner_sha256=base.sha(Path(__file__)),schedule_sha256=base.sha(O/'schedule.json'),
         original_prompt_sha256=base.sha(OLD/'prompt_store.json'),logical_schedule_sha256=base.sha(O/'logical_schedule.json'),
         original_archive_sha256=base.sha(OLD/'responses_stopped.jsonl.gz'),max_input_tokens=max(tokens.values()),
         transport_timeout_seconds=600))
    print('Continuation input PASS: two calibration calls, one repair, 3052 unissued calls.',flush=True)

def check():
    base.prereqs();base.committed(O/'input_gate.json');base.committed(Path(__file__).resolve())
    gate=base.read(O/'input_gate.json');assert gate['status']=='PASS' and gate['amendment']==AMENDMENT
    for path,key in [(Path(__file__),'runner_sha256'),(O/'schedule.json','schedule_sha256'),
                     (OLD/'prompt_store.json','original_prompt_sha256'),(OLD/'responses_stopped.jsonl.gz','original_archive_sha256'),
                     (O/'logical_schedule.json','logical_schedule_sha256')]:assert base.sha(path)==gate[key]
    assert not (O/'pending.json').exists()
    return base.read(O/'schedule.json'),base.read(OLD/'prompt_store.json')

def call(row,store):
    save('pending.json',row)
    payload=dict(prompt=store[row['prompt_sha256']],seed=row['seed'],temperature=.6,top_p=.95,top_k=20,
        min_p=0,repeat_penalty=1,presence_penalty=0,n_predict=CAP,cache_prompt=True,stream=False,reasoning_format='none')
    request=urllib.request.Request('http://127.0.0.1:8097/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    # One request, no retries. Accommodates the doubled decoding allowance.
    with urllib.request.urlopen(request,timeout=600) as stream:response=json.load(stream)
    with (O/'capture.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(dict(row=row,response=response))+'\n');stream.flush();os.fsync(stream.fileno())
    (O/'pending.json').unlink()
    assert response.get('content','').strip() and not response.get('truncated')
    assert response.get('stop_type')=='eos' and '<think>' not in response['content'],'INSTRUMENT_FAILURE'
    return response

def prefix():
    schedule,store=check();assert not (O/'capture.jsonl').exists()
    original=old_rows()
    a,b=call(schedule[0],store),call(schedule[1],store)
    assert a['content'].encode()==b['content'].encode()==original[0]['response']['content'].encode(),'CALIBRATION_IDENTITY_FAILURE'
    save('calibration_gate.json',dict(status='PASS',original_and_new_identical=True))
    response=call(schedule[2],store)
    original_prefix=original[-1]['response']['content'].encode('utf-8')
    assert response['content'].encode('utf-8').startswith(original_prefix),'REPAIR_PREFIX_IDENTITY_FAILURE'
    save('repair_gate.json',dict(status='PASS',prefix_bytes=len(original_prefix),repaired_id=schedule[2]['physical_id'],
         capture_prefix_sha256=base.sha(O/'capture.jsonl'),repair_tokens=response['tokens_predicted']))
    print('PASS: calibration identity and capped-response prefix identity; repair reached EOS.',flush=True)

def archive(source,target):
    assert not target.exists()
    with source.open('rb') as inp,target.open('wb') as out:
        with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0) as zipped:
            while chunk:=inp.read(1024*1024):zipped.write(chunk)

def resume():
    schedule,store=check();base.committed(O/'repair_gate.json');gate=base.read(O/'repair_gate.json')
    assert gate['status']=='PASS' and base.sha(O/'capture.jsonl')==gate['capture_prefix_sha256']
    initial=[json.loads(line) for line in (O/'capture.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(initial)==3
    for index,row in enumerate(schedule[3:],4):call(row,store);print(f'{index}/3055',flush=True)
    archive(O/'capture.jsonl',O/'capture.jsonl.gz')
    original=old_rows();new=[json.loads(line) for line in (O/'capture.jsonl').read_text(encoding='utf-8').splitlines()]
    combined=original[:-1]+new[2:];expected=base.read(OLD/'physical_schedule.json')
    assert len(combined)==3508 and all(r['row']==expected[i] and r['response']['stop_type']=='eos' for i,r in enumerate(combined))
    digest=hashlib.sha256();target=O/'responses.jsonl.gz';assert not target.exists()
    with target.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
            for row in combined:
                chunk=(json.dumps(row)+'\n').encode();digest.update(chunk);zipped.write(chunk)
    save('combined_index.json',[dict(physical_id=r['row']['physical_id'],source='original' if i<455 else 'continuation004',
         source_line=i+1 if i<455 else i-452) for i,r in enumerate(combined)])
    save('complete.json',dict(status='PASS',registration=base.REGISTRATION,amendment=AMENDMENT,calls=3508,actual_calls=3511,
         logical_answers=3840,responses_sha256=digest.hexdigest(),archive_sha256=base.sha(target),
         logical_schedule_sha256=base.sha(O/'logical_schedule.json'),all_nonempty_eos=True,reused_eos_measurements=452))

if __name__=='__main__':
    try:{'seal':seal,'prefix':prefix,'resume':resume}[sys.argv[1]]()
    except Exception as error:
        if sys.argv[1] in ['prefix','resume'] and O.exists() and not (O/'failure.json').exists():
            save('failure.json',dict(status='INSTRUMENT_FAILURE',phase=sys.argv[1],error=repr(error),pending_exists=(O/'pending.json').exists(),retry_authorized=False))
        raise
