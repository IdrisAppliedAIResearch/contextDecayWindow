"""Prepare registered Study E inputs without any reader calls."""
import concurrent.futures
import hashlib
import html
import json
import subprocess
import sys
import time
from pathlib import Path
import numpy as np

from prepare_amendment003 import generate
from prepare_dev import init, emb
from mechanism import build
from analysis.hh001_prompt import render_reader_prompt
from episodic._render import render_stm_payload

ROOT=Path(__file__).resolve().parents[2]
STUDY=Path(__file__).resolve().parent
P=STUDY/'artifacts/confirmation/development_inputs'
REGISTRATION='2e047c41c80748b16f0e6df15dcc70ac54145598'
PINS={'corpus.py':'53abd4e029790576e3df09e7d17259d179d32e183bd884c888f010a1017fc7af',
      'prepare_amendment003.py':'70eebdd24e6e3a2efc2fb7af963dc63dca69feb062ca310b9882f9a2e602cccf',
      'mechanism.py':'cd04f01e35904405bd67fd98f3b1bf4689c00182a767fb297eafe415a2b476c5'}


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save(name,value):
    path=P/name;assert not path.exists(),path
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def prereqs():
    path='experiments/study_E/PRE_REGISTRATION.md'
    assert subprocess.check_output(['git','show',REGISTRATION+':'+path],cwd=ROOT).replace(b'\r\n',b'\n')==(ROOT/path).read_bytes().replace(b'\r\n',b'\n')
    assert subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r',REGISTRATION],text=True,cwd=ROOT).splitlines()==[path]
    assert sys.version_info[:3]==(3,13,13) and np.__version__=='2.4.6'
    for name,digest in PINS.items():assert sha(STUDY/name)==digest
    for folder,pin in [('contextDecayWindow-study-E-control','05ef90e29b849196515cf39f52ba09754656c599'),('contextDecayWindow-study-D-control','5ebda1ef4510c1806709039aeb66e6d79cedbbd8')]:
        location=ROOT.parent/folder
        assert subprocess.check_output(['git','-C',str(location),'rev-parse','HEAD'],text=True).strip()==pin
        assert not subprocess.check_output(['git','-C',str(location),'status','--porcelain'],text=True).strip()
    # Exact regeneration of all previously committed development source objects.
    replay=[]
    for seed in range(93201,93205):replay.extend(generate(seed)[0])
    previous=STUDY/'artifacts/amendment003/development/sources.json'
    assert json.loads(previous.read_text())==replay
    assert (json.dumps(replay,indent=2)+'\n').encode()==previous.read_bytes().replace(b'\r\n',b'\n')
    model=Path(r'C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF\Qwen3-Embedding-0.6B-Q8_0.gguf')
    assert sha(model)=='06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439'


def main():
    prereqs()
    assert not P.exists(),'No overwrite or implicit resume.'
    histories,labels,ledger=[],{},[]
    for seed in range(94001,94033):
        hs,ls,lg=generate(seed);histories.extend(hs);labels.update(ls);ledger.extend(lg)
    assert len(histories)==len(labels)==192 and sum(len(h['episodes']) for h in histories)==26880
    assert len({h['id'] for h in histories})==192
    P.mkdir(parents=True)
    save('sources.json',histories);save('labels.json',labels);save('ledger.json',ledger)
    save('source_gate.json',dict(status='PASS',registration=REGISTRATION,groups=32,histories=192,source_records=26880,
         questions=192,references_checked=192,required_before_109=True,development_regeneration_exact=True,
         generator_pins=PINS,python=sys.version,numpy=np.__version__,confirmation_outcome_filter=False))
    texts=sorted({e['user_message']+'\n'+e['assistant_message'] for h in histories for e in h['episodes']}
                 |{q['query'] for h in histories for q in h['probes']})
    started=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=8,initializer=init) as pool:
        results=list(pool.map(emb,texts))
    assert len({r[2] for r in results})==1
    vectors=np.vstack([r[1] for r in results]);np.savez_compressed(P/'vectors.npz',vectors=vectors)
    save('vector_manifest.json',dict(texts=texts,file_sha256=sha(P/'vectors.npz'),sentinel=results[0][2],
         calls=len(texts)+8,pids=sorted({r[3] for r in results}),cpu_seconds=sum(r[4] for r in results),wall_seconds=time.monotonic()-started))
    by_text=dict(zip(texts,vectors));prompts=[];traces=[]
    for history in histories:
        query=history['probes'][0];label=labels[query['id']]
        episodes=[dict(e,embedding=by_text[e['user_message']+'\n'+e['assistant_message']]) for e in history['episodes']]
        original_ids=[e['id'] for e in episodes]
        c0,c1,trace=build(episodes,query['query'],by_text[query['query']])
        assert (c0,c1)==build(episodes,query['query'],by_text[query['query']])[:2]
        assert original_ids==[e['id'] for e in episodes]
        if query['type']=='latest':assert c0==c1
        else:
            assert trace['route']['reason']=='anchored'
            assert set(trace['eligible_before'])==set(trace['eligible_after'])
        by_id={e['id']:e for e in episodes}
        for selected in [trace['prior']['selected_ids'],trace.get('selected_ids',trace['prior']['selected_ids'])]:
            assert len(render_stm_payload([],[by_id[x] for x in selected]))<=32000
        ordered_gold=sorted((by_id[x] for x in label['gold_ids']),key=lambda e:e['turn_number'])
        oracle=render_stm_payload([],ordered_gold) if ordered_gold else ''
        for arm,block in [('C0',c0),('C1',c1),('ORACLE',oracle),('NULL','')]:
            prompts.append(dict(id=query['id'],session=history['group'],history=history['id'],type=query['type'],arm=arm,
                 query=query['query'],reference=label['answer'],prompt=render_reader_prompt(query['query'],block)+'\n<think>\n</think>\n'))
        evidence={}
        for arm,selected,block in [('C0',trace['prior']['selected_ids'],c0),('C1',trace.get('selected_ids',trace['prior']['selected_ids']),c1)]:
            required=set(label['gold_ids']);complete=bool(required) and required.issubset(selected)
            if complete:assert any(all(html.escape(t,quote=False) in block for t in group) for group in label['sufficient_sets'])
            evidence[arm]=complete
        traces.append(dict(history=history['id'],session=history['group'],type=query['type'],evidence=evidence,trace=trace))
    save('prompts.json',prompts)
    # Do not inspect confirmation mechanism/evidence aggregates before scoring.
    save('traces_sealed.json',traces)
    manifest={f.name:sha(f) for f in sorted(P.iterdir()) if f.is_file()}
    save('manifest.json',manifest)
    save('complete.json',dict(status='PASS',registration=REGISTRATION,groups=32,histories=192,questions=192,
         arm_prompts=len(prompts),logical_answers=len(prompts)*5,manifest_sha256=sha(P/'manifest.json'),
         vector_workers=8,repeat_identity=True,source_gate='PASS',outcomes_opened=False))
    print(json.dumps(dict(status='PASS',histories=192,arm_prompts=len(prompts),logical_answers=len(prompts)*5)),flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:
        if P.exists() and not (P/'failure.json').exists():save('failure.json',dict(status='INSTRUMENT_FAILURE',error=repr(error)))
        raise
