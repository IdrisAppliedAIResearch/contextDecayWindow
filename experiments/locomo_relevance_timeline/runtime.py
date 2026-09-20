"""Serial owned reader runtime, persistent requests, and local health events."""
import gzip
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import prepare as p

OUT = p.OUT
CONTEXT = 40960
FIT = OUT/'fit40960/fit.json'
OLD = p.ROOT/'experiments/study_E/artifacts/confirmation/restart005'
BASE = dict(seed=5005, temperature=.6, top_p=.95, top_k=20, min_p=0, repeat_penalty=1, presence_penalty=0, cache_prompt=False, reasoning_format='none', n_predict=4096, id_slot=0)


def req(route, data=None):
    request = urllib.request.Request('http://127.0.0.1:8099/'+route, data=None if data is None else json.dumps(data).encode('utf8'), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=600) as f:
        return json.load(f)


def rows(name):
    with gzip.open(OUT/name, 'rt', encoding='utf8') as f:
        return [json.loads(line) for line in f]


def commit(paths, message):
    subprocess.run(['git','add',*[str(v) for v in paths]], cwd=p.ROOT, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['git','commit','-m',message], cwd=p.ROOT, check=True)


def native(text):
    prompt = req('apply-template', dict(messages=[dict(role='user',content=text)], add_generation_prompt=True, chat_template_kwargs={'enable_thinking':False}, reasoning_effort='none'))['prompt']
    assert prompt.endswith('<think>\n\n</think>\n\n')
    return prompt


def final(response):
    assert not response.get('truncated') and response['stop_type']=='eos', 'TRUNCATED_OR_NON_EOS'
    value = response['content'].strip()
    assert value and '<think>' not in value and '</think>' not in value, 'EMPTY_OR_REASONING_OUTPUT'
    return value


def gpu():
    text = subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'], text=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
    return dict(zip(['used_mib','free_mib','utilization'], map(int,text.strip().split(','))))


def launch(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with socket.socket() as s:
        assert s.connect_ex(('127.0.0.1',8099)) != 0, 'PORT_IN_USE'
    command = p.read(OLD/'launch.json')['command']
    for flag, value in [('--port','8099'),('--parallel','1'),('--ctx-size',str(CONTEXT))]:
        command[command.index(flag)+1] = value
    assert command[command.index('--reasoning')+1]=='off'
    assert command[command.index('--reasoning-budget')+1]=='0'
    command += ['--verbosity','5']
    env=os.environ.copy()
    env['PATH']='C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;'+env['PATH']
    process=subprocess.Popen(command, env=env, stdout=(folder/'server.out').open('xb'), stderr=(folder/'server.err').open('xb'), creationflags=subprocess.CREATE_NO_WINDOW)
    p.save(folder/'launch.json', dict(pid=process.pid, runner_pid=os.getpid(), command=command, started=time.time()))
    try:
        for _ in range(180):
            assert process.poll() is None, 'SERVER_EXIT'
            try:
                props=req('props')
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError('SERVER_TIMEOUT')
        assert props['total_slots']==1
        assert 'offloaded 66/66 layers to GPU' in (folder/'server.err').read_text(errors='replace')
        p.save(folder/'props.json', props)
        assert gpu()['free_mib'] >= 1536
        return process
    except BaseException:
        process.terminate(); process.wait(timeout=20)
        raise


def stop(process, folder):
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=20)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
    p.save(folder/'stopped.json', dict(pid=process.pid, exit_code=process.returncode, time=time.time()))


def fit():
    p.committed(__file__); p.committed(OUT/'part1.json')
    part=p.read(OUT/'part1.json')
    for path,h in part['hashes'].items(): assert p.sha(path)==h
    for name,h in part['outputs'].items(): assert p.sha(OUT/name)==h
    pins=p.read(OLD/'runtime_pins.json')
    for pin in pins: assert p.sha(pin['path'])==pin['sha256']
    folder=OUT/'fit40960'
    process=launch(folder)
    try:
        prompts=[]
        for r in rows('prompts.jsonl.gz'):
            prompt=native(r['text'])
            n=len(req('tokenize',dict(content=prompt,add_special=False))['tokens'])
            prompts.append(dict(r,prompt=prompt,prompt_sha256=p.digest(prompt),tokens=n))
        assert prompts == rows('native_prompts.jsonl.gz'), 'CONTEXT_CHANGE_PROMPT_DRIFT'
        lengths=sorted(r['tokens'] for r in prompts)
        p.save(folder/'fit.json',dict(status='PASS' if max(lengths)+4096<=CONTEXT else 'CAPACITY_BLOCK', tokens=lengths, max_tokens=max(lengths), context=CONTEXT, output=4096, pins=pins, native_prompts_sha256=p.sha(OUT/'native_prompts.jsonl.gz'), native_thinking=False, code=p.sha(__file__), original_prompts_exact=True))
        print(json.dumps(dict(max_tokens=max(lengths),fits=max(lengths)+4096<=CONTEXT)),flush=True)
    finally: stop(process,folder)


def gate(require_calibration=False):
    for path in [p.P/'PRE_REGISTRATION.md', OUT/'preflight.json', FIT, Path(__file__), p.P/'prepare.py']:
        p.committed(path)
    g=p.read(OUT/'preflight.json')
    assert g['status']=='PASS'
    for path,h in g['hashes'].items(): assert p.sha(path)==h, path
    assert p.read(FIT)['status']=='PASS'
    if require_calibration:
        p.committed(OUT/'reader/calibration.json')
        assert p.read(OUT/'reader/calibration.json')['status']=='PASS'


def calibration(folder):
    from analysis.hh001_prompt import render_judge_prompt, parse_judge_verdict
    prompt=native('What is 17 + 28? Answer only the number.')
    answers=[req('completion',dict(BASE,prompt=prompt,n_predict=64)) for _ in range(2)]
    assert final(answers[0])==final(answers[1])=='45' and answers[0]['content']==answers[1]['content']
    fixtures=[('Where did Jo move?', 'Paris', '', False), ('What did Jo buy?', 'a red bicycle', 'A bike that is red.', True), ('Where did Jo move?', 'Paris', 'Rome', False), ('When did Jo move?', 'May 2024', 'May 2023', False), ('Where did Jo move?', 'Paris', 'Jo moved to Rome, not Paris.', False)]
    judges=[]
    for i,(q,g,a,expected) in enumerate(fixtures):
        jp=native(render_judge_prompt(q,g,a))
        for seed in [9100,9101,9102]:
            start=time.time()
            response=req('completion',dict(BASE,prompt=jp,seed=seed,temperature=.2,top_p=.9))
            p.save(folder/f'judge_cal_{i}_{seed}.json',dict(response=response,seconds=time.time()-start,prompt=jp,expected=expected))
            verdict,reason=parse_judge_verdict(final(response))
            assert verdict==expected and reason, 'JUDGE_CALIBRATION_FAILED'
            judges.append(dict(case=i,seed=seed,verdict=verdict,seconds=time.time()-start))
    p.save(folder/'calibration.json',dict(status='PASS',arithmetic=answers,judges=judges,thinking=False,code=p.sha(__file__)))


def write_status(folder, data):
    path=folder/'status.json'; temp=folder/'status.tmp'
    temp.write_text(json.dumps(data,indent=2),encoding='utf8'); os.replace(temp,path)


def run():
    gate()
    folder=OUT/'reader'
    assert not folder.exists(), 'EXISTING_RUN_NO_SILENT_RETRY'
    process=launch(folder)
    ended=threading.Event()
    state=dict(phase='calibration',completed=0,total=1986,request_started=None,runner_pid=os.getpid(),server_pid=process.pid,started=time.time())
    durations=[]
    def watch():
        while not ended.wait(15):
            snapshot=dict(state,time=time.time())
            try: snapshot['gpu']=gpu()
            except Exception as e: snapshot['gpu_error']=repr(e)
            age=time.time()-(state.get('request_started') or time.time())
            threshold=max(180,5*statistics.median(durations[-20:])) if durations else 180
            snapshot['slow']=age>threshold
            snapshot['server_alive']=process.poll() is None
            write_status(folder,snapshot)
            with (folder/'health.jsonl').open('a',encoding='utf8') as f: f.write(json.dumps(snapshot)+'\n')
            if snapshot['slow'] or not snapshot['server_alive'] or snapshot.get('gpu',{}).get('free_mib',99999)<1536:
                with (folder/'events.jsonl').open('a',encoding='utf8') as f: f.write(json.dumps(snapshot)+'\n')
    worker=threading.Thread(target=watch,daemon=True);worker.start()
    try:
        calibration(folder)
        commit([folder], 'Gate serial native-off reader and three-pass judge calibration')
        gate(True)
        schedule=rows('native_prompts.jsonl.gz')
        state['phase']='reader'
        for i,r in enumerate(schedule):
            assert process.poll() is None,'SERVER_EXIT'
            assert gpu()['free_mib']>=1536,'LOW_VRAM'
            state.update(request_started=time.time(),current_key=r['key'])
            p.save(folder/(r['key']+'.pending.json'),dict(key=r['key'],prompt_sha256=r['prompt_sha256'],started=state['request_started']))
            response=req('completion',dict(BASE,prompt=r['prompt']))
            elapsed=time.time()-state['request_started']
            p.save(folder/(r['key']+'.json'),dict(key=r['key'],response=response,seconds=elapsed,prompt_sha256=r['prompt_sha256']))
            final(response)
            assert response['tokens_evaluated']==r['tokens'], 'INPUT_TOKEN_DRIFT'
            durations.append(elapsed)
            state.update(completed=i+1,request_started=None)
            if i==19:
                p.save(folder/'sample20.json',dict(status='PASS',n=20,seconds=sum(durations),estimated_reader_seconds=sum(durations)/20*1986,estimated_judge_seconds=statistics.mean(j['seconds'] for j in p.read(folder/'calibration.json')['judges'])*4620))
                commit([folder], 'Gate fixed twenty-question reader sample before full continuation')
                p.committed(folder/'sample20.json')
            print(f'Captured {i+1}/1986',flush=True)
        gate(True)
        p.save(folder/'complete.json',dict(status='PASS',calls=1986,seconds=sum(durations),hashes={r['key']:p.sha(folder/(r['key']+'.json')) for r in schedule}))
        state['phase']='complete'
    except BaseException as e:
        state['phase']='failure'
        p.save(folder/'failure.json',dict(error=repr(e),traceback=traceback.format_exc(),state=state))
        raise
    finally:
        ended.set();worker.join(timeout=20)
        stop(process,folder)
        write_status(folder,dict(state,time=time.time()))


if __name__=='__main__':
    {'fit':fit,'run':run}[sys.argv[1]]()
