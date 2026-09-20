"""Bounded, gated Amendment 003 reader capture; preserves uncertain calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
P = Path(__file__).resolve().parent/'artifacts/amendment003/development'
O = P.parent/'reader'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(name, value):
    path = O/name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def committed(path):
    blob = subprocess.check_output(['git', 'show', 'HEAD:'+path.relative_to(ROOT).as_posix()], cwd=ROOT)
    assert blob.replace(b'\r\n',b'\n') == path.read_bytes().replace(b'\r\n',b'\n')


def req(route, obj=None):
    request = urllib.request.Request('http://127.0.0.1:8097/'+route,
        data=None if obj is None else json.dumps(obj).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.load(response)


def call(row):
    save('pending.json', row)
    response = req('completion', dict(prompt=row['prompt'], seed=5005, temperature=.6,
        top_p=.95, top_k=20, min_p=0, repeat_penalty=1, presence_penalty=0,
        n_predict=8192, cache_prompt=True, stream=False, reasoning_format='none'))
    with (O/'responses.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(row=row,response=response))+'\n'); stream.flush(); os.fsync(stream.fileno())
    (O/'pending.json').unlink()
    assert response.get('content','').strip() and not response.get('truncated')
    assert response.get('stop_type')=='eos' and '<think>' not in response['content'], 'INSTRUMENT_FAILURE'
    return response


def seal():
    committed(P/'readiness_gate_exact.json')
    gate = read(P/'readiness_gate_exact.json')
    assert gate['status']=='PASS' and gate['reader_authorized']
    assert sha(P/'sources.json')==gate['source_sha256']
    assert sha(P/'prompts.json')==gate['prompts_sha256']
    O.mkdir(parents=True, exist_ok=True)
    assert not (O/'input_gate.json').exists()
    prompts = read(P/'prompts.json')
    rows = [r for r in prompts if r['arm'] in ['C0','C1'] and
            ((r['type'] not in ['latest','absent'] and r['session'] in ['session-93201','session-93202','session-93203'])
             or r['type'] in ['latest','absent'])]
    assert len(rows)==40
    pins = read(ROOT/'experiments/study_D/artifacts/part1/runtime_gpu/launch.json')
    checked = []
    for pin in [pins['files'][0], pins['files'][2]]:
        assert sha(Path(pin['path']))==pin['sha256']
        checked.append(pin)
    props = req('props'); save('props.json', props)
    for row in rows:
        row['tokens'] = len(req('tokenize',dict(content=row['prompt'],add_special=False))['tokens'])
        assert row['tokens']+8192<=65536
    largest = max(rows,key=lambda r:r['tokens'])
    schedule = [dict(largest,stage='prefix1'),dict(largest,stage='prefix2'),
                dict(prompt='Say exactly: ready.\nAnswer:\n<think>\n</think>\n',stage='short')]+rows
    save('schedule.json',schedule)
    save('input_gate.json',dict(status='PASS',calls=43,max_tokens=largest['tokens'],
         readiness_sha256=sha(P/'readiness_gate_exact.json'),schedule_sha256=sha(O/'schedule.json'),
         source_sha256=sha(P/'sources.json'),prompts_sha256=sha(P/'prompts.json'),
         runner_sha256=sha(Path(__file__)),verified=checked))
    print(json.dumps(dict(calls=43,max_tokens=largest['tokens'])),flush=True)


def run():
    for path in [P/'readiness_gate_exact.json',O/'input_gate.json',Path(__file__).resolve()]:
        committed(path)
    gate = read(O/'input_gate.json')
    assert gate['status']=='PASS' and gate['runner_sha256']==sha(Path(__file__))
    assert gate['schedule_sha256']==sha(O/'schedule.json')
    assert gate['readiness_sha256']==sha(P/'readiness_gate_exact.json')
    assert gate['source_sha256']==sha(P/'sources.json') and gate['prompts_sha256']==sha(P/'prompts.json')
    assert not (O/'responses.jsonl').exists() and not (O/'pending.json').exists()
    schedule = read(O/'schedule.json')
    a,b = call(schedule[0]),call(schedule[1])
    assert a['content']==b['content'], 'PREFIX_IDENTITY_FAILURE'
    save('prefix_gate.json',dict(status='PASS',equal=True))
    for index,row in enumerate(schedule[2:],3):
        call(row); print(f'{index}/43',flush=True)
    save('complete.json',dict(status='PASS',calls=43,responses_sha256=sha(O/'responses.jsonl')))


if __name__=='__main__':
    try:
        {'seal':seal,'run':run}[sys.argv[1]]()
    except Exception as error:
        if sys.argv[1]=='run' and O.exists() and not (O/'failure.json').exists():
            save('failure.json',dict(status='INSTRUMENT_FAILURE',error=repr(error),
                pending_exists=(O/'pending.json').exists(),retry_authorized=False))
        raise
