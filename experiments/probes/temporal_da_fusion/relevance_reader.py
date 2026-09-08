"""Paired fresh reader calls for fixed relevance timelines; no retrieval changes."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import chronology as c

BASE=c.P/'relevance_artifacts'
c.OUT=BASE/'reader';c.CAP=4096;c.ARMS=['BASELINE','RELEVANCE']
OUT=c.OUT


def ready(calibrated=False):
    c.check(calibrated)
    c.committed(Path(__file__))
    assert c.sha(Path(__file__))==c.read(OUT/'input_gate.json')['wrapper_sha256']


def prepare():
    for p in [c.P/'RELEVANCE_READER_PLAN.md',Path(__file__),BASE/'gate.json',BASE/'blind.json']:c.committed(p)
    assert not OUT.exists()
    g=c.read(BASE/'gate.json');assert g['status']=='PASS' and c.sha(BASE/'blind.json')==g['outputs_sha256']
    # Exercise the actual gate before any live calls, restoring functions afterward.
    original_read,original_committed,original_request=c.read,c.committed,c.request;network=[]
    c.read=lambda p:{'status':'FAIL'};c.committed=lambda p:None;c.request=lambda *a,**k:network.append(a)
    try:
        try:ready()
        except AssertionError:pass
        else:raise AssertionError('Failed gate accepted')
        assert not network
    finally:c.read,c.committed,c.request=original_read,original_committed,original_request
    pins=c.read(c.OLD/'runtime_pins.json')
    for p in pins:assert c.sha(Path(p['path']))==p['sha256']
    with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',8097))!=0
    previous=[r for r in c.read(c.P/'chronology_artifacts/schedule.json') if r['arm']=='CHRONO_NO_RECENT']
    candidates={r['id']:r for r in c.read(BASE/'blind.json') if r['study']=='E'}
    assert len(previous)==16
    OUT.mkdir();c.save('runtime_pins.json',pins);c.save('negative_gate_fixture.json',dict(status='PASS',network_calls=0))
    command=c.read(c.OLD/'launch.json')['command'];assert command[command.index('--reasoning')+1]=='off'
    env=os.environ.copy();env['PATH']='C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;'+env['PATH']
    proc=subprocess.Popen(command,stdout=(OUT/'server_stdout.txt').open('xb'),stderr=(OUT/'server_stderr.txt').open('xb'),env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    c.save('launch.json',dict(pid=proc.pid,command=command,started=time.time()))
    for _ in range(180):
        assert proc.poll() is None
        try:props=c.request('props');break
        except OSError:time.sleep(1)
    else:raise RuntimeError('SERVER_TIMEOUT')
    assert props['total_slots']==1;c.save('props.json',props)
    schedule=[]
    for i,old in enumerate(previous):
        for arm in c.ARMS if i%2==0 else list(reversed(c.ARMS)):
            if arm=='BASELINE':
                # Re-render the same carried payload and require exact native identity.
                oldcontext=next(r for r in c.read(c.P/'chronology_artifacts/contexts.json') if r['id']==old['id'])['contexts']['CHRONO_NO_RECENT']
                prompt=c.native(c.render_reader_prompt(old['query'],oldcontext));assert prompt==old['prompt']
            else:prompt=c.native(c.render_reader_prompt(old['query'],candidates[old['id']]['arms']['ANCHORED']['context']))
            tokens=len(c.request('tokenize',dict(content=prompt,add_special=False))['tokens'])
            assert tokens+c.CAP<=32768,'FULL_TIMELINE_DOES_NOT_FIT'
            assert prompt.endswith('<think>\n\n</think>\n\n')
            schedule.append(dict(case=f'call_{len(schedule)+1:02}',id=old['id'],history=old['history'],type=old['type'],query=old['query'],arm=arm,seed=5005,prompt=prompt,prompt_sha256=c.digest(prompt),tokens=tokens))
    c.save('schedule.json',schedule);c.save('calibration_prompt.json',dict(prompt=c.native('What is 17 plus 28? Give the final number.'),seed=5005))
    c.save('input_gate.json',dict(status='PASS',plan='860ea072',wrapper_sha256=c.sha(Path(__file__)),code_sha256=c.sha(c.P/'chronology.py'),
        calls=32,questions=16,native_thinking=False,output_cap=c.CAP,full_inputs_fit=True,
        hashes={n:c.sha(OUT/n) for n in ['schedule.json','runtime_pins.json','launch.json','props.json','calibration_prompt.json','negative_gate_fixture.json']},
        candidate_sha256=c.sha(BASE/'blind.json'),baseline_schedule_sha256=c.sha(c.P/'chronology_artifacts/schedule.json')))
    print(json.dumps(dict(prepared=32,pid=proc.pid,max_tokens=max(r['tokens'] for r in schedule),output_cap=c.CAP)))


def calibrate():
    ready();c.calibrate()


def run():
    ready(True)
    rows=c.read(OUT/'schedule.json');assert len(rows)==32
    for r in rows:c.capture(r,r['case']);print(r['case']+' captured',flush=True)
    ready(True);c.save('complete.json',dict(status='PASS',calls=32,hashes={r['case']:c.sha(OUT/(r['case']+'.json')) for r in rows}))
    print('COMPLETE',flush=True)


if __name__=='__main__':
    try:{'prepare':prepare,'calibrate':calibrate,'run':run,'score':c.score,'summarize':c.summarize}[sys.argv[1]]()
    except Exception as e:
        if OUT.exists() and not (OUT/'failure.json').exists():c.save('failure.json',dict(status='INSTRUMENT_FAILURE',phase=sys.argv[1],error=repr(e)))
        raise
