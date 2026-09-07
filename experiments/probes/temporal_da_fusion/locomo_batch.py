"""Matched real-prompt throughput diagnostic; no scoring."""
import concurrent.futures as cf
import gzip,json,os,socket,subprocess,time
from pathlib import Path
import batch_capacity as b
P=b.P; OUT=P/'locomo_batch_artifacts'; b.OUT=OUT
SOURCE=b.ROOT/'experiments/components/live_validation_009/artifacts/part1/prompts.jsonl.gz'
def commit(name):
    subprocess.run(['git','add',str(OUT/name)],check=True)
    subprocess.run(['git','commit','-m','Gate LoCoMo batch '+name],check=True)
def gate():
    b.committed(OUT/'input_gate.json')
    assert json.loads((OUT/'input_gate.json').read_text())['code']==b.sha(__file__)
def native(text):
    return b.req('apply-template',dict(messages=[dict(role='user',content=text)],add_generation_prompt=True,chat_template_kwargs={'enable_thinking':False},reasoning_effort='none'))['prompt']
def main():
    assert not OUT.exists(); OUT.mkdir()
    b.committed(__file__);b.committed(SOURCE)
    try:gate()
    except subprocess.CalledProcessError:pass
    else:raise AssertionError('missing gate passed')
    rows=[]
    with gzip.open(SOURCE,'rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line)
            if r['category'] not in [1,2,3,4]:continue
            a=r['arms']['PAIRWISE'];text=a['prompt']
            assert b.hashlib.sha256(text.encode()).hexdigest()==a['prompt_sha256']
            rows.append(dict(key=r['comparison_key'],question=r['question'],text=text,sha=a['prompt_sha256']))
            if len(rows)==9:break
    assert len(rows)==9
    pins=json.loads((b.OLD/'runtime_pins.json').read_text())
    for pin in pins:assert b.sha(pin['path'])==pin['sha256']
    b.save('input_gate.json',dict(code=b.sha(__file__),source_sha=b.sha(SOURCE),pins=pins,rows=rows,negative_gate=True))
    commit('input_gate.json');all_native=None
    base=dict(seed=5005,temperature=.6,top_p=.95,top_k=20,min_p=0,repeat_penalty=1,presence_penalty=0,cache_prompt=False,reasoning_format='none',n_predict=4096)
    for n in [1,9]:
        gate()
        with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8098))!=0
        cmd=json.loads((b.OLD/'launch.json').read_text())['command']
        for flag,val in [('--port','8098'),('--parallel',str(n)),('--ctx-size',str(n*32768))]:cmd[cmd.index(flag)+1]=val
        assert cmd[cmd.index('--reasoning')+1]=='off' and cmd[cmd.index('--reasoning-budget')+1]=='0'
        cmd+=['--verbosity','5']
        env=os.environ.copy();env['PATH']='C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;'+env['PATH']
        proc=subprocess.Popen(cmd,env=env,stdout=(OUT/f'server_{n}.out').open('xb'),stderr=(OUT/f'server_{n}.err').open('xb'),creationflags=subprocess.CREATE_NO_WINDOW)
        result=dict(slots=n,command=cmd,pid=proc.pid)
        try:
            for _ in range(180):
                assert proc.poll() is None
                try:props=b.req('props');break
                except OSError:time.sleep(1)
            else:raise RuntimeError('startup timeout')
            assert props['total_slots']==n
            assert 'offloaded 66/66 layers to GPU' in (OUT/f'server_{n}.err').read_text(errors='replace')
            prompts=[native(r['text']) for r in rows]
            assert all('<think>\n\n</think>' in p for p in prompts)
            if all_native is not None:assert prompts==all_native
            all_native=prompts
            lengths=[len(b.req('tokenize',dict(content=p,add_special=False))['tokens']) for p in prompts]
            assert max(lengths)+4096<=32768
            cp=native('What is 17 + 28? Answer only the number.')
            cal=[b.req('completion',dict(base,prompt=cp,n_predict=64,id_slot=0)) for _ in range(2)]
            assert cal[0]['content']==cal[1]['content'] and cal[0]['content'].strip()=='45'
            assert b.allowed(b.gpu())
            b.save(f'gate_{n}.json',dict(props=props,prompts=prompts,lengths=lengths,calibration=cal,command=cmd,pid=proc.pid))
            commit(f'gate_{n}.json');b.committed(OUT/f'gate_{n}.json')
            start=time.perf_counter();samples=[]
            def call(i):
                t=time.perf_counter()
                response=b.req('completion',dict(base,prompt=prompts[i],id_slot=i if n==9 else 0))
                item=dict(key=rows[i]['key'],seconds=time.perf_counter()-t,response=response)
                b.save(f'answer_{n}_{i}.json',item)
                return item
            with cf.ThreadPoolExecutor(max_workers=n) as pool:
                fs=[pool.submit(call,i) for i in range(9)]
                while not all(f.done() for f in fs):samples.append(b.gpu());time.sleep(.2)
                answers=[f.result() for f in fs]
            result.update(seconds=time.perf_counter()-start,samples=samples,answers=answers,lengths=lengths)
            assert all(not a['response'].get('truncated') and a['response']['stop_type']=='eos' for a in answers)
            assert min(s['free'] for s in samples)>=1536
            result['status']='PASS';print(json.dumps(dict(slots=n,seconds=result['seconds'],output_tokens=sum(a['response']['tokens_predicted'] for a in answers))),flush=True)
        finally:
            proc.terminate()
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            b.save(f'arm_{n}.json',result)
    assert b.sha(__file__)==json.loads((OUT/'input_gate.json').read_text())['code']
    b.save('complete.json',dict(status='PASS',gpu=b.gpu()))
if __name__=='__main__':main()
