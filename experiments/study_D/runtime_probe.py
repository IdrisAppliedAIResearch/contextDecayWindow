"""Six-call development runtime gate specified in Part 1 extension 001."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
GPU = '--gpu' in sys.argv
OUT = ROOT / 'experiments/study_D/artifacts/part1' / ('runtime_gpu' if GPU else 'runtime')
CONTROL = ROOT.parent / 'contextDecayWindow-study-D-control'
SERVER = 'http://127.0.0.1:8097'

def request(path, data=None):
    req = urllib.request.Request(SERVER+path, data=None if data is None else json.dumps(data).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as response:
        return json.load(response)

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def save(name, obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'responses.jsonl').exists():
        raise RuntimeError('Persisted calls exist: no rerun authorized')
    files = json.loads((OUT.parent/'runtime_files.json').read_text(encoding='utf-8-sig'))
    binary = files[0]['path']
    model = files[2]['path']
    command = [binary,'--model',model,'--host','127.0.0.1','--port','8097','--ctx-size','65536','--parallel','1','--n-gpu-layers','999','--cache-type-k','q8_0','--cache-type-v','q8_0','--flash-attn','on','--no-context-shift','--seed','5005']
    child_env = os.environ.copy()
    if GPU:
        added = [r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2\bin\x64', r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin']
        child_env['PATH'] = ';'.join(added) + ';' + child_env['PATH']
        devices = subprocess.check_output([binary,'--list-devices'],env=child_env,stderr=subprocess.STDOUT,text=True)
        assert 'CUDA0' in devices
        save('devices.json',{'listing':devices,'path_additions':added})
        command += ['--device','CUDA0']
    stdout = (OUT/'server_stdout.txt').open('w',encoding='utf-8')
    stderr = (OUT/'server_stderr.txt').open('w',encoding='utf-8')
    process = subprocess.Popen(command,stdout=stdout,stderr=stderr,env=child_env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    save('launch.json',{'command':command,'pid':process.pid,'files':files})
    ready = False
    for _ in range(120):
        if process.poll() is not None:
            save('gate.json',{'status':'INSTRUMENT_FAILURE','reason':'server exited before readiness','exit':process.returncode})
            return
        try:
            if request('/health').get('status')=='ok':
                ready=True
                break
        except Exception:
            pass
        time.sleep(1)
    if not ready:
        save('gate.json',{'status':'INSTRUMENT_FAILURE','reason':'readiness timeout'})
        return
    props=request('/props')
    save('props.json',props)
    if GPU:
        memory=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True)
        save('gpu_memory.json',{'used_mib':memory})
        assert int(memory.strip().splitlines()[0]) > 17000
    # Guard the actual runtime before generating, not only the requested flags.
    params=props.get('default_generation_settings',{}).get('params',{})
    save('readiness.json',{'health':request('/health'),'total_slots':props.get('total_slots'),'params':params})
    if props.get('total_slots') != 1:
        save('gate.json',{'status':'INSTRUMENT_FAILURE','reason':'slot count not one'})
        return
    sys.path.insert(0,str(CONTROL/'src'))
    from analysis.hh001_prompt import render_reader_prompt
    fixtures=[('code','The assigned access code for Project Maple is VEL-742.','What is the assigned access code for Project Maple?'),('duration','We chose the design on 2026-01-03 and dropped it on 2026-01-08.','How many days elapsed between choosing and dropping the design?'),('absent','Project Maple has a blue cover.','What is the access code for Project Birch?')]
    rows=[]
    for name,source,query in fixtures:
        prompt=render_reader_prompt(query,source)+'\n<think>\n</think>\n'
        tokens=len(request('/tokenize',{'content':prompt,'add_special':False})['tokens'])
        for repeat in range(2):
            response=request('/completion',{'prompt':prompt,'seed':5005,'temperature':.6,'top_p':.95,'top_k':20,'min_p':0.,'repeat_penalty':1.,'presence_penalty':0.,'cache_prompt':False,'n_predict':512,'stream':False,'reasoning_format':'none'})
            row={'fixture':name,'repeat':repeat,'prompt':prompt,'prompt_sha256':sha(prompt),'token_count':tokens,'response':response}
            with (OUT/'responses.jsonl').open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(row,sort_keys=True)+'\n')
                stream.flush()
            rows.append(row)
            print(json.dumps({'fixture':name,'repeat':repeat,'stop':response.get('stop_type'),'tokens':response.get('tokens_predicted')}),flush=True)
    pairs=[rows[i]['response'].get('content')==rows[i+1]['response'].get('content') for i in range(0,6,2)]
    complete=all(str(row['response'].get('content','')).strip() and row['response'].get('stop_type')=='eos' and row['response'].get('tokens_predicted',512)<512 for row in rows)
    save('gate.json',{'status':'PASS' if all(pairs) and complete else 'INSTRUMENT_FAILURE','paired_byte_identity':pairs,'complete':complete,'calls':len(rows),'reader_accuracy_evaluated':False})
    print((OUT/'gate.json').read_text(),flush=True)

if __name__=='__main__':
    main()
