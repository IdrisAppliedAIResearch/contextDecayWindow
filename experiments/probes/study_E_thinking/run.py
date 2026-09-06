"""Frozen twelve-case thinking-on probe; raw traces retained, no retries."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
P = Path(__file__).resolve().parent
O = P / 'artifacts'
OLD = ROOT / 'experiments/study_E/artifacts/confirmation/restart005'
I = OLD.parent / 'development_inputs'
CAP = 16384
PLAN = 'c6b955d3'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(name, obj):
    O.mkdir(exist_ok=True)
    with (O/name).open('x', encoding='utf-8') as f:
        json.dump(obj, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())


def committed(path):
    prior = subprocess.check_output(['git', 'show', 'HEAD:'+path.relative_to(ROOT).as_posix()], cwd=ROOT)
    assert prior.replace(b'\r\n', b'\n') == path.read_bytes().replace(b'\r\n', b'\n')


def request(route, data=None):
    req = urllib.request.Request('http://127.0.0.1:8097/'+route,
        data=None if data is None else json.dumps(data).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=600) as f:
        return json.load(f)


def render(payload, thinking):
    return request('apply-template', dict(messages=[dict(role='user', content=payload)],
        add_generation_prompt=True, chat_template_kwargs={'enable_thinking':thinking},
        reasoning_effort='high' if thinking else 'none'))['prompt']


def final(response):
    # Native prompt already opens <think>; completion must close it.
    content = response.get('content', '')
    assert response.get('stop_type') == 'eos' and not response.get('truncated'), 'NONCOMPLETE_RESPONSE'
    assert content.count('</think>') == 1, 'MISSING_OR_AMBIGUOUS_THINKING_CLOSE'
    thoughts, answer = content.split('</think>')
    assert thoughts.strip() and answer.strip() and '<think>' not in answer, 'MISSING_THOUGHT_OR_FINAL'
    return answer.strip()


def fixtures():
    good = dict(content='Checking 2+2.\n</think>\n4', stop_type='eos', truncated=False)
    assert final(good) == '4'
    for bad in [dict(good, content='reasoning only'), dict(good, content='x</think>'),
                dict(good, stop_type='limit'), dict(good, truncated=True)]:
        try:
            final(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError('NEGATIVE_PARSER_FIXTURE_PASSED')
    assert not (O/'calibration_gate.json').exists(), 'NO_RERUN'
    return dict(status='PASS', positive_final=True, four_negative_cases=True)


def prepare():
    committed(P/'PLAN.md'); committed(Path(__file__).resolve())
    assert not O.exists(), 'NO_OVERWRITE'
    assert subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r',PLAN], cwd=ROOT, text=True).splitlines() == [str((P/'PLAN.md').relative_to(ROOT)).replace('\\','/')]
    scores = {r['blind_id']:r for r in read(OLD/'scores_resolved.json')}
    traces = {r['history']:r for r in read(I/'traces_sealed.json')}
    inventory = [r for r in read(OLD/'mapping.json') if r['arm']=='C1'
        and r['type'] in ['straight','irrelevant','future','proposal']
        and traces[r['history']]['evidence']['C1'] and scores[r['blind_id']]['score']==0]
    assert len(inventory)==243 and len({r['question_id'] for r in inventory})==97
    selected=[]
    for kind in ['straight','irrelevant','future','proposal']:
        rows=[r for r in inventory if r['type']==kind]
        for qid in sorted({r['question_id'] for r in rows})[:3]:
            selected.append(min((r for r in rows if r['question_id']==qid), key=lambda r:r['seed']))
    assert len(selected)==12
    pins=read(OLD/'runtime_pins.json')
    for pin in pins:
        assert sha(Path(pin['path']))==pin['sha256'], pin['path']
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1',8097))!=0, 'PORT_IN_USE'
    O.mkdir()
    save('parser_fixtures.json', fixtures())
    save('inventory.json', inventory)
    save('runtime_pins.json', pins)
    command=read(OLD/'launch.json')['command']
    command[command.index('--reasoning')+1]='on'
    command[command.index('--reasoning-budget')+1]='-1'
    env=os.environ.copy()
    env['PATH']='C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;'+env['PATH']
    process=subprocess.Popen(command, stdout=(O/'server_stdout.txt').open('xb'),
        stderr=(O/'server_stderr.txt').open('xb'), env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    save('launch.json', dict(command=command,pid=process.pid,started=time.time()))
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError('SERVER_START_FAILED')
        try:
            props=request('props'); break
        except (OSError, TimeoutError):
            time.sleep(1)
    else:
        raise RuntimeError('SERVER_START_TIMEOUT')
    assert props['total_slots']==1
    save('props.json', props)
    logical={r['logical_id']:r for r in read(OLD/'logical_schedule.json')}
    prior_store=read(OLD/'prompt_store.json')
    originals={(r['history'],r['arm']):r for r in read(I/'prompts.json')}
    histories={h['id']:h for h in read(I/'sources.json')}
    labels=read(I/'labels.json')
    import html
    for index,row in enumerate(selected):
        old=logical[row['blind_id']] if row['blind_id'] in logical else next(r for r in logical.values() if r['physical_id']==row['physical_id'] and r['arm']=='C1')
        original=originals[row['history'],'C1']['prompt']
        suffix='\n<think>\n</think>\n'
        assert original.endswith(suffix)
        payload=original[:-len(suffix)]
        off=render(payload,False); on=render(payload,True)
        assert off==prior_store[old['prompt_sha256']], 'OFF_TEMPLATE_REPLAY_MISMATCH'
        assert on.endswith('<think>\n') and off==on+'\n</think>\n\n', 'UNEXPECTED_TEMPLATE_CHANGE'
        h=histories[row['history']]; by_id={e['id']:e for e in h['episodes']}
        required=labels[row['question_id']]['gold_ids']
        for identity in required:
            e=by_id[identity]
            fragment=f'<episode turn="{e["turn_number"]}">\n<user>{html.escape(e["user_message"],quote=False)}</user>\n<assistant>{html.escape(e["assistant_message"],quote=False)}</assistant>\n</episode>'
            assert fragment in on, 'REQUIRED_SOURCE_NOT_RENDERED'
        tokens=len(request('tokenize',dict(content=on,add_special=False))['tokens'])
        assert tokens+CAP<=32768
        row.update(case=f'case_{index+1:02d}',prompt=on,prompt_sha256=hashlib.sha256(on.encode()).hexdigest(),
            original_prompt_sha256=old['prompt_sha256'],query=old['query'],reference=old['reference'],tokens=tokens,
            old_response=scores[row['blind_id']].get('evidence'),required_ids=required)
    save('selection.json', selected)
    calibration=render('What is 17 plus 28? Give the final number.',True)
    save('calibration_prompt.json',dict(prompt=calibration,seed=5005))
    files=['selection.json','inventory.json','runtime_pins.json','launch.json','props.json','calibration_prompt.json','parser_fixtures.json']
    save('input_gate.json',dict(status='PASS',plan=PLAN,count=12,eligible_logical=243,eligible_questions=97,
        runner_sha256=sha(Path(__file__)),input_hashes={f:sha(O/f) for f in files},
        old_hashes={str(p.relative_to(ROOT)):sha(p) for p in [OLD/'scores_resolved.json',OLD/'logical_schedule.json',OLD/'prompt_store.json',I/'sources.json',I/'labels.json',I/'traces_sealed.json']},
        off_template_replay_exact=True,only_assistant_thinking_boundary_changed=True,required_source_fragments_verified=True))
    print(json.dumps(dict(prepared=12,server_pid=process.pid)),flush=True)


def check(calibrated=False):
    committed(P/'PLAN.md'); committed(Path(__file__).resolve()); committed(O/'input_gate.json')
    gate=read(O/'input_gate.json')
    assert sha(Path(__file__))==gate['runner_sha256']
    for f,digest in gate['input_hashes'].items():
        assert sha(O/f)==digest
    for f,digest in gate['old_hashes'].items():
        assert sha(ROOT/f)==digest
    assert not (O/'pending.json').exists(), 'UNCERTAIN_CALL'
    if calibrated:
        committed(O/'calibration_gate.json')
        assert read(O/'calibration_gate.json')['status']=='PASS'


def capture(row,name):
    save('pending.json',dict(case=name,seed=row['seed'],prompt_sha256=hashlib.sha256(row['prompt'].encode()).hexdigest()))
    start=time.monotonic()
    response=request('completion',dict(prompt=row['prompt'],seed=row['seed'],temperature=.6,top_p=.95,
        top_k=20,min_p=0,repeat_penalty=1,presence_penalty=0,n_predict=CAP,cache_prompt=False,
        stream=False,reasoning_format='none',id_slot=0))
    save(name+'.json',dict(response=response,latency_seconds=time.monotonic()-start))
    (O/'pending.json').unlink()
    answer=final(response)
    return response,answer


def calibrate():
    check()
    row=read(O/'calibration_prompt.json')
    a,_=capture(row,'calibration1'); b,_=capture(row,'calibration2')
    assert a['content']==b['content'], 'PREFIX_NOT_IDENTICAL'
    save('calibration_gate.json',dict(status='PASS',native_thinking_captured=True,identical=True,
        hashes={f:sha(O/f) for f in ['calibration1.json','calibration2.json']}))
    print('Calibration PASS',flush=True)


def run():
    check(True)
    rows=read(O/'selection.json')
    for row in rows:
        capture(row,row['case'])
        print(row['case']+' captured',flush=True)
    check(True)
    save('complete.json',dict(status='PASS',plan=PLAN,count=12,thinking=True,
        hashes={r['case']:sha(O/(r['case']+'.json')) for r in rows}))
    print('COMPLETE',flush=True)


if __name__=='__main__':
    try:
        {'prepare':prepare,'calibrate':calibrate,'run':run}[sys.argv[1]]()
    except Exception as error:
        if O.exists() and not (O/'failure.json').exists():
            save('failure.json',dict(status='INSTRUMENT_FAILURE',error=repr(error),phase=sys.argv[1],retry=False))
        raise
