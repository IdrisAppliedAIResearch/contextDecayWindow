"""Full Study E single-arm reader; frozen relevance timelines."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import chronology as c

BASE=c.P/'relevance_artifacts'
c.OUT=BASE/'full_e_reader';c.CAP=4096;c.ARMS=['RELEVANCE']
OUT=c.OUT


def ready(calibrated=False):
    c.check(calibrated)
    c.committed(Path(__file__))
    assert c.sha(BASE/'blind.json')==c.read(OUT/'input_gate.json')['candidate_sha256']
    assert c.sha(Path(__file__))==c.read(OUT/'input_gate.json')['wrapper_sha256']


def prepare():
    for p in [c.P/'FULL_E_PLAN.md',Path(__file__),BASE/'gate.json',BASE/'blind.json']:c.committed(p)
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
    previous=sorted([r for r in c.read(BASE/'blind.json') if r['study']=='E'],key=lambda r:r['id'])
    replay_started=time.monotonic();replay_cpu=time.process_time()
    import relevance
    from collections import Counter
    assert Counter(r['type'] for r in previous)==dict.fromkeys(['straight','irrelevant','future','proposal','latest','absent'],32)
    for path,expected in g['inputs'].items():assert c.sha(Path(path))==expected
    histories={h['id']:h for h in c.read(c.I/'sources.json')}
    curves={r['id']:r for r in c.read(relevance.CURVES) if r['study']=='E'}
    for r in previous:
        h=histories[r['history']];by={e['id']:e for e in h['episodes']};v=curves[r['id']]
        ids=relevance.select(v['ids'],v['turns'],v['cosine'],r['anchors'])
        assert ids==r['arms']['ANCHORED']['ids']
        block=c.E.render_stm_payload([],[by[k] for k in ids])
        assert block==r['arms']['ANCHORED']['context'] and c.digest(block)==r['arms']['ANCHORED']['context_sha256']
    assert relevance.select(['b','a','c'],[2,1,3],[.48,.479,.481])==['b','c']
    assert relevance.select(['x'],[1],[0])==[] and relevance.select(['x'],[1],[0],['x'])==['x']
    assert len(relevance.select([str(i) for i in range(200)],list(range(200)),[1]*200))==200
    for bad in [dict(content='',stop_type='eos'),dict(content='x',stop_type='limit'),dict(content='<think>x</think>',stop_type='eos')]:
        try:c.final(bad)
        except AssertionError:pass
        else:raise AssertionError('parser accepted bad fixture')
    from mechanism import CONTROL,DA_ROOT
    for folder,pin in [(CONTROL,'8d18ee7c'),(DA_ROOT,'de20ac79'),(c.E.OLD,'05ef90e2'),(c.E.ENGINE,'5ebda1ef')]:
        assert subprocess.check_output(['git','-C',str(folder),'rev-parse','HEAD'],text=True).strip().startswith(pin)
        assert not subprocess.check_output(['git','-C',str(folder),'status','--porcelain'],text=True).strip()
    source=(c.P/'relevance.py').read_text(encoding='utf-8').split('def annotate():')[0]
    clean=lambda s:not any(x in s for x in ['labels.json','q_facts_key','gold_ids','sufficient_sets'])
    assert clean(source) and not clean(source+'labels.json')
    old_native={r['id']:r['prompt'] for r in c.read(BASE/'reader/schedule.json') if r['arm']=='RELEVANCE'}
    replay_stats=dict(exact=192,seconds=time.monotonic()-replay_started,cpu_seconds=time.process_time()-replay_cpu,workers=1,old_native_exact=len(old_native),leakage_sentinel=True,clean_worktrees=True)

    candidates={r['id']:r for r in c.read(BASE/'blind.json') if r['study']=='E'}
    assert len(previous)==192
    OUT.mkdir();c.save('replay.json',replay_stats);c.save('runtime_pins.json',pins);c.save('negative_gate_fixture.json',dict(status='PASS',network_calls=0))
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
            prompt=c.native(c.render_reader_prompt(old['query'],candidates[old['id']]['arms']['ANCHORED']['context']))
            if old['id'] in old_native:assert prompt==old_native[old['id']]
            tokens=len(c.request('tokenize',dict(content=prompt,add_special=False))['tokens'])
            assert tokens+c.CAP<=32768,'FULL_TIMELINE_DOES_NOT_FIT'
            assert prompt.endswith('<think>\n\n</think>\n\n')
            schedule.append(dict(case=f'call_{len(schedule)+1:02}',id=old['id'],history=old['history'],type=old['type'],query=old['query'],arm=arm,seed=5005,prompt=prompt,prompt_sha256=c.digest(prompt),tokens=tokens))
    c.save('schedule.json',schedule);c.save('calibration_prompt.json',dict(prompt=c.native('What is 17 plus 28? Give the final number.'),seed=5005))
    c.save('input_gate.json',dict(status='PASS',plan='2519aff9',wrapper_sha256=c.sha(Path(__file__)),code_sha256=c.sha(c.P/'chronology.py'),
        calls=192,questions=192,native_thinking=False,output_cap=c.CAP,full_inputs_fit=True,
        hashes={n:c.sha(OUT/n) for n in ['replay.json','schedule.json','runtime_pins.json','launch.json','props.json','calibration_prompt.json','negative_gate_fixture.json']},
        candidate_sha256=c.sha(BASE/'blind.json'),module_paths=dict(chronology=c.__file__,engine=c.E.__file__),baseline_schedule_sha256=c.sha(c.P/'chronology_artifacts/schedule.json')))
    print(json.dumps(dict(prepared=192,pid=proc.pid,max_tokens=max(r['tokens'] for r in schedule),output_cap=c.CAP)))


def calibrate():
    ready();c.calibrate()


def run():
    ready(True)
    rows=c.read(OUT/'schedule.json');assert len(rows)==192
    for r in rows:c.capture(r,r['case']);print(r['case']+' captured',flush=True)
    ready(True);c.save('complete.json',dict(status='PASS',calls=192,hashes={r['case']:c.sha(OUT/(r['case']+'.json')) for r in rows}))
    print('COMPLETE',flush=True)


if __name__=='__main__':
    try:{'prepare':prepare,'calibrate':calibrate,'run':run,'score':c.score,'summarize':c.summarize}[sys.argv[1]]()
    except Exception as e:
        if OUT.exists() and not (OUT/'failure.json').exists():c.save('failure.json',dict(status='INSTRUMENT_FAILURE',phase=sys.argv[1],error=repr(e)))
        raise
