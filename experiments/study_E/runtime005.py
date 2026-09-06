"""Thinking-off native-template runtime; immutable captures and bounded waves."""
import concurrent.futures as cf
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.request
import reader_confirmation as base

ROOT = base.ROOT
STUDY = base.STUDY
OUT = STUDY/'artifacts/confirmation/restart005'
PROBE = STUDY/'artifacts/amendment005'
CAP = 16384
SLOT_CONTEXT = 32768
AMENDMENT = '6603aca3'
SUFFIX = '\n<think>\n</think>\n'

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())

def request(route, value=None):
    req = urllib.request.Request('http://127.0.0.1:8097/'+route,
        data=None if value is None else json.dumps(value).encode(),
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=600) as f: return json.load(f)

def render(prompt, thinking=False):
    assert prompt.endswith(SUFFIX)
    user = prompt[:-len(SUFFIX)]
    result = request('apply-template', dict(messages=[dict(role='user', content=user)],
        add_generation_prompt=True, chat_template_kwargs={'enable_thinking':thinking},
        reasoning_effort='none' if not thinking else 'high'))['prompt']
    assert user in result
    return result

def start(slots, directory):
    # Only start when this study's dedicated port is free.
    import socket
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1',8097)) != 0, 'PORT_IN_USE'
    directory.mkdir(parents=True, exist_ok=True)
    command = list(base.read(base.O.parent/'continuation004/launch.json')['command'])
    command[command.index('--ctx-size')+1] = str(slots*SLOT_CONTEXT)
    command[command.index('--parallel')+1] = str(slots)
    command += ['--reasoning','off','--reasoning-budget','0','--cont-batching']
    env = os.environ.copy()
    env['PATH'] = ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;'
                   'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;'+env['PATH'])
    stdout = (directory/'server_stdout.txt').open('xb')
    stderr = (directory/'server_stderr.txt').open('xb')
    process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    save(directory/'launch.json',dict(pid=process.pid,command=command,slots=slots,started=time.time()))
    deadline = time.monotonic()+180
    while time.monotonic()<deadline:
        if process.poll() is not None: raise RuntimeError('SERVER_START_FAILED')
        try:
            props=request('props'); save(directory/'props.json',props)
            assert props['total_slots']==slots
            return process
        except (urllib.error.URLError,TimeoutError): time.sleep(1)
    process.terminate(); process.wait(); raise RuntimeError('SERVER_START_TIMEOUT')

def valid(response):
    return bool(response.get('content','').strip()) and not response.get('truncated',False) and \
        response.get('stop_type')=='eos' and '<think>' not in response.get('content','')

def capture_wave(rows, store, directory, slots, filename='responses.jsonl'):
    """Each response is fsynced before its future completes; drain on any failure."""
    lock = threading.Lock()
    def one(pair):
        slot,row=pair
        journal=directory/('pending_'+str(slot)+'.json')
        save(journal, row)
        started=time.monotonic()
        response=request('completion',dict(prompt=store[row['prompt_sha256']],seed=row['seed'],
            temperature=.6,top_p=.95,top_k=20,min_p=0,repeat_penalty=1,presence_penalty=0,
            n_predict=CAP,cache_prompt=False,stream=False,reasoning_format='none',id_slot=slot))
        item=dict(row=row,response=response,latency_seconds=time.monotonic()-started,slot=slot)
        with lock:
            with (directory/filename).open('a',encoding='utf-8') as f:
                f.write(json.dumps(item)+'\n'); f.flush(); os.fsync(f.fileno())
        journal.unlink()
        return item
    assert len(rows)<=slots
    with cf.ThreadPoolExecutor(max_workers=slots) as executor:
        futures=[executor.submit(one,pair) for pair in enumerate(rows)]
        results=[];errors=[]
        for future in futures:
            try:results.append(future.result())
            except Exception as error:errors.append(repr(error))
    if errors: raise RuntimeError('UNCERTAIN_CALL: '+repr(errors))
    assert all(valid(r['response']) for r in results), 'INSTRUMENT_FAILURE'
    return results

def telemetry(stop, rows):
    while not stop.is_set():
        try:
            line=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu,utilization.memory,power.draw',
                '--format=csv,noheader,nounits'],text=True,creationflags=subprocess.CREATE_NO_WINDOW).strip()
            rows.append(dict(time=time.time(),values=line))
        except Exception as e:rows.append(dict(error=repr(e)))
        stop.wait(2)

def eligible(row, serial):
    return row['complete'] and row['repeat_equal'] and row['contents']==serial['contents'] and \
        (row['slots']==1 or row['wall_seconds']<=serial['wall_seconds']*.9)

def fixtures():
    a=dict(complete=True,repeat_equal=True,contents=['x'],slots=1,wall_seconds=10)
    b=dict(a,slots=2,wall_seconds=8)
    assert eligible(a,a) and eligible(b,a)
    for bad in [dict(b,complete=False),dict(b,repeat_equal=False),dict(b,contents=['y']),dict(b,wall_seconds=9.1)]:
        assert not eligible(bad,a)
    assert valid(dict(content='office',stop_type='eos',truncated=False))
    for response in [dict(content='',stop_type='eos'),dict(content='x',stop_type='limit'),dict(content='<think>x',stop_type='eos'),dict(content='x',stop_type='eos',truncated=True)]:
        assert not valid(response)
    return dict(status='PASS',reachable_selection_branches=6,completion_branches=5)

def probe():
    base.prereqs()
    base.committed(STUDY/'amendments/AMENDMENT_005_thinking_off_restart.md')
    base.committed(Path(__file__).resolve())
    save(PROBE/'fixtures.json',fixtures())
    source=STUDY/'artifacts/amendment003/development/prompts.json'
    rows=base.read(source); group=min(r['session'] for r in rows)
    chosen=[next(r for r in rows if r['session']==group and r['type']==kind and r['arm']==arm)
            for kind in base.KINDS[:4] for arm in ['C0','C1']]
    save(PROBE/'input_manifest.json',dict(source_sha256=base.sha(source),count=8,
        runner_sha256=base.sha(Path(__file__)),selected=[dict(id=r['id'],arm=r['arm'],prompt_sha256=hashlib.sha256(r['prompt'].encode()).hexdigest()) for r in chosen]))
    summaries=[]
    for slots in [1,2,4]:
        directory=PROBE/('slots'+str(slots));process=None
        stop=threading.Event();gpu=[];thread=None
        try:
            process=start(slots,directory)
            store={};schedule=[]
            for i,row in enumerate(chosen):
                prompt=render(row['prompt']); key=hashlib.sha256(prompt.encode()).hexdigest();store[key]=prompt
                n=len(request('tokenize',dict(content=prompt,add_special=False))['tokens'])
                assert n+CAP<=SLOT_CONTEXT
                schedule.append(dict(physical_id=str(i),prompt_sha256=key,seed=5005,stage='probe'))
            off=render(chosen[0]['prompt']);on=render(chosen[0]['prompt'],True)
            assert off!=on, 'THINKING_CONTROL_INERT'
            save(directory/'templates.json',dict(off=off,on=on))
            save(directory/'prompt_store.json',store);save(directory/'schedule.json',schedule)
            thread=threading.Thread(target=telemetry,args=(stop,gpu));thread.start()
            begin=time.monotonic();passes=[]
            for repeat in range(2):
                items=[]
                for i in range(0,8,slots):items+=capture_wave(schedule[i:i+slots],store,directory,slots)
                passes.append(items)
            elapsed=time.monotonic()-begin
            contents=[[i['response']['content'] for i in p] for p in passes]
            summary=dict(slots=slots,complete=True,repeat_equal=contents[0]==contents[1],
                contents=contents[0],wall_seconds=elapsed,
                tokens=[i['response']['tokens_predicted'] for p in passes for i in p],
                latency_seconds=[i['latency_seconds'] for p in passes for i in p])
            save(directory/'result.json',summary);summaries.append(summary)
            print(json.dumps({k:v for k,v in summary.items() if k not in ['contents','latency_seconds']}),flush=True)
        except Exception as error:
            save(directory/'failure.json',dict(error=repr(error),retry_authorized=False))
            if slots==1:raise
        finally:
            stop.set()
            if thread:thread.join()
            save(directory/'gpu.json',gpu)
            if process and process.poll() is None:process.terminate();process.wait()
    serial=summaries[0]
    assert serial['slots']==1 and serial['complete'] and serial['repeat_equal'],'SERIAL_NOT_REPRODUCIBLE'
    candidates=[s for s in summaries if eligible(s,serial)]
    selected=min(candidates,key=lambda s:(s['wall_seconds'],s['slots']))
    save(PROBE/'selection.json',dict(status='PASS',selected_slots=selected['slots'],
        candidates=[dict(slots=s['slots'],eligible=eligible(s,serial),wall_seconds=s['wall_seconds'],
                         repeat_equal=s['repeat_equal'],serial_equal=s['contents']==serial['contents']) for s in summaries]))
    print('SELECTED '+str(selected['slots']),flush=True)

if __name__=='__main__':
    try:probe()
    except Exception as error:
        save(PROBE/'failure.json',dict(error=repr(error),retry_authorized=False));raise
