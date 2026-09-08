"""Owned-server GPU allocation and concurrent synthetic load diagnostic."""
import concurrent.futures as cf
import hashlib,json,os,socket,subprocess,time,urllib.request
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
OUT=P/'batch_capacity_artifacts_retry'
OLD=ROOT/'experiments/study_E/artifacts/confirmation/restart005'
def save(name,value):
    with (OUT/name).open('x',encoding='utf8') as f: json.dump(value,f,indent=2)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def committed(p):subprocess.run(['git','ls-files','--error-unmatch',str(p)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
def req(route,value=None):
    r=urllib.request.Request('http://127.0.0.1:8098/'+route,data=None if value is None else json.dumps(value).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(r,timeout=900) as f:return json.load(f)
def gpu():
    r=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True)
    return dict(zip(['used','free','util'],map(int,r.strip().split(','))))
def allowed(m):return m['free']>=1536
def gate():
    committed(OUT/'input_gate.json')
    assert json.loads((OUT/'input_gate.json').read_text())['code']==sha(__file__)
def main():
    committed(__file__);committed(P/'BATCH_CAPACITY_PLAN.md')
    assert not OUT.exists();OUT.mkdir()
    pins=json.loads((OLD/'runtime_pins.json').read_text())
    for pin in pins:assert sha(pin['path'])==pin['sha256']
    assert allowed({'free':1536}) and not allowed({'free':1535})
    try:gate()
    except subprocess.CalledProcessError:pass
    else:raise AssertionError('missing gate accepted')
    save('input_gate.json',dict(status='PASS',pins=pins,code=sha(__file__),baseline_gpu=gpu(),negative_gate=True))
    subprocess.run(['git','add',str(OUT/'input_gate.json')],cwd=ROOT,check=True)
    subprocess.run(['git','commit','-m','Gate pinned GPU capacity inputs before allocation and stress'],cwd=ROOT,check=True)
    command=json.loads((OLD/'launch.json').read_text())['command']
    env=os.environ.copy();env['PATH']='C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;'+env['PATH']
    with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8098))!=0
    results=[]
    # Increasing integers characterize the exact boundary without unsafe jumps.
    for n in range(1,17):
        gate();cmd=command.copy()
        for flag,value in [('--port','8098'),('--parallel',str(n)),('--ctx-size',str(n*32768))]:cmd[cmd.index(flag)+1]=value
        cmd+=['--verbosity','5']
        process=subprocess.Popen(cmd,env=env,stdout=(OUT/f'server_{n}.out').open('xb'),stderr=(OUT/f'server_{n}.err').open('xb'),creationflags=subprocess.CREATE_NO_WINDOW)
        row=dict(slots=n,command=cmd,pid=process.pid)
        try:
            for _ in range(180):
                if process.poll() is not None:raise RuntimeError('server exited')
                try:props=req('props');break
                except OSError:time.sleep(1)
            else:raise RuntimeError('startup timeout')
            row['props']=props;row['idle_gpu']=gpu();assert props['total_slots']==n
            print(json.dumps(dict(slots=n,idle_gpu=row['idle_gpu'])),flush=True)
            if not allowed(row['idle_gpu']):row['status']='BELOW_HEADROOM';break
            log=(OUT/f'server_{n}.err').read_text(errors='replace')
            assert 'offloaded' in log, 'ALLOCATION_LOG_MISSING'
            # Native template and short seeded reproduction before concurrent stress.
            template=req('apply-template',dict(messages=[dict(role='user',content='What is 17 + 28? Answer only the number.')],add_generation_prompt=True,chat_template_kwargs={'enable_thinking':False},reasoning_effort='none'))['prompt']
            assert '<think>\n\n</think>' in template
            base=dict(seed=5005,temperature=.6,top_p=.95,top_k=20,min_p=0,repeat_penalty=1,presence_penalty=0,cache_prompt=False,reasoning_format='none')
            cal=[req('completion',dict(base,prompt=template,n_predict=64,id_slot=0)) for _ in range(2)]
            row['calibration']=cal;assert cal[0]['content']==cal[1]['content'] and cal[0]['content'].strip()=='45'
            prompt=req('apply-template',dict(messages=[dict(role='user',content=('The archive contains routine entries about rain and wind.\n'*3500)+'\nWrite a list of numbers.')],add_generation_prompt=True,chat_template_kwargs={'enable_thinking':False},reasoning_effort='none'))['prompt']
            tokens=req('tokenize',dict(content=prompt))['tokens']
            # Token-array input isolates capacity from tokenizer length estimates.
            tokens=tokens[:27900]+req('tokenize',dict(content='\nContinue listing numbers.\n<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n'))['tokens']
            row['input_tokens']=len(tokens);assert 27000<len(tokens)<28672
            row['waves']=[]
            for wave in range(2):
                start=time.time();samples=[]
                with cf.ThreadPoolExecutor(max_workers=n) as pool:
                    fs=[pool.submit(req,'completion',dict(base,prompt=[tokens[0]]+req('tokenize',dict(content=f'Unique request {i}.'))['tokens']+tokens[1:],n_predict=64,ignore_eos=True,id_slot=i)) for i in range(n)]
                    while not all(f.done() for f in fs):samples.append(dict(time=time.time(),**gpu()));time.sleep(.5)
                    responses=[f.result() for f in fs]
                row['waves'].append(dict(seconds=time.time()-start,samples=samples,responses=responses))
                assert all(not r.get('truncated') and r['tokens_evaluated']>=27000 and r['tokens_predicted']==64 for r in responses)
                assert min(s['free'] for s in samples)>=1536
            row['status']='STRESS_PASS'
            print(json.dumps(dict(slots=n,status=row['status'],seconds=[w['seconds'] for w in row['waves']])),flush=True)
        except Exception as e:row['status']='ERROR';row['error']=repr(e);print(repr(e),flush=True)
        finally:
            process.terminate()
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            row['stopped']=True;save(f'configuration_{n}.json',row);results.append({k:row[k] for k in ['slots','status']})
        if row['status']!='STRESS_PASS':break
    save('complete.json',dict(results=results,gpu_after=gpu()))
if __name__=='__main__':main()
