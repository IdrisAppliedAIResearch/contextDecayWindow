"""Execute the fixed extension-003 development population; no reader calls."""
import concurrent.futures
import hashlib
import html
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
CONTROL=ROOT.parent/'contextDecayWindow-study-D-control'
sys.path[:0]=[str(CONTROL/'episodic/src'),str(CONTROL/'src')]
import numpy as np
if '--dense' in sys.argv:
    from corpus_dense import make_session
else:
    from corpus import make_session
from temporal import build

OUT=ROOT/'experiments/study_D/artifacts/part1'/('development_dense' if '--dense' in sys.argv else 'development')
MODEL=Path(r'C:\Users\muzaf\.cache\huggingface\hub\Qwen3-Embedding-0.6B-GGUF\Qwen3-Embedding-0.6B-Q8_0.gguf')

def save(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def worker_init():
    global EMBEDDER,SENTINEL
    from episodic._embedding import PinnedEmbedder
    EMBEDDER=PinnedEmbedder(MODEL)
    SENTINEL=hashlib.sha256(EMBEDDER('episodic call-shape sentinel: one text per call').tobytes()).hexdigest()

def embed(text):
    start=time.process_time()
    v=EMBEDDER(text)
    return text,v,os.getpid(),SENTINEL,time.process_time()-start

def tokenize(prompt):
    req=urllib.request.Request('http://127.0.0.1:8097/tokenize',data=json.dumps({'content':prompt,'add_special':False}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as response:
        return len(json.load(response)['tokens'])

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert subprocess.check_output(['git','status','--porcelain'],cwd=CONTROL).strip()==b''
    sessions=[]
    labels={}
    for seed in range(91001,91005):
        s,l=make_session(seed)
        sessions.append(s)
        labels.update(l)
    save('sources.json',sessions)
    save('labels.json',labels)
    ids=[e['id'] for s in sessions for e in s['episodes']]
    assert len(ids)==560 and len(set(ids))==560 and len(labels)==28
    for s in sessions:
        for p in s['probes']:
            for sufficient in labels[p['id']]['sufficient_sets']:
                for span in sufficient:
                    assert any(span in e['user_message'] and e['turn_number']<p['probe_turn'] for e in s['episodes'])
    save('input_seal.json',{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ('sources.json','labels.json')})
    texts=sorted(set([e['user_message']+'\n'+e['assistant_message'] for s in sessions for e in s['episodes']]+[p['query'] for s in sessions for p in s['probes']]))
    path=OUT/'vectors.npz'
    if path.exists():
        prior=json.loads((OUT/'vector_manifest.json').read_text())
        assert prior['texts']==texts
        assert prior['file_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
        array=np.load(path)['vectors']
    else:
        started=time.monotonic()
        entries=[]
        workers=min(8,os.cpu_count() or 1)
        # Each worker uses the carried one-text, one-thread call shape.
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers,initializer=worker_init) as pool:
            for n,result in enumerate(pool.map(embed,texts),1):
                entries.append(result)
                if n%50==0:
                    print(json.dumps({'embedded':n,'total':len(texts),'seconds':round(time.monotonic()-started,1)}),flush=True)
        assert len({x[3] for x in entries})==1
        array=np.stack([x[1] for x in entries])
        np.savez_compressed(path,vectors=array)
        save('vector_manifest.json',{'texts':texts,'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'canonical_sha256':hashlib.sha256(array.astype(np.float32).tobytes()).hexdigest(),'worker_pids':sorted({x[2] for x in entries}),'workers_requested':workers,'sentinel_sha256':entries[0][3],'wall_seconds':time.monotonic()-started,'worker_cpu_seconds':sum(x[4] for x in entries),'calls':len(texts)+len({x[2] for x in entries})})
    vectors=dict(zip(texts,array))
    rows=[]
    for s in sessions:
        episodes=[{**e,'embedding':vectors[e['user_message']+'\n'+e['assistant_message']]} for e in s['episodes']]
        for p in s['probes']:
            baseline,treatment,trace=build(episodes,p['query'],vectors[p['query']])
            a2,b2,_=build(episodes,p['query'],vectors[p['query']])
            assert baseline==a2 and treatment==b2
            label=labels[p['id']]
            def availability(text):
                sets=label['sufficient_sets']
                return {'any':any(html.escape(span,quote=False) in text for group in sets for span in group),'complete':any(all(html.escape(span,quote=False) in text for span in group) for group in sets)} if sets else None
            rows.append({'id':p['id'],'session':s['id'],'type':p['type'],'changed':baseline!=treatment,'C0':availability(baseline),'C1':availability(treatment),'C0_chars':len(baseline),'C1_chars':len(treatment),'C0_tokens':tokenize(baseline),'C1_tokens':tokenize(treatment),'C0_sha256':hashlib.sha256(baseline.encode()).hexdigest(),'C1_sha256':hashlib.sha256(treatment.encode()).hexdigest(),'trace':trace})
    save('development_trace.json',rows)
    summary={'status':'CHARACTERIZED','items':len(rows),'source_episodes':len(ids),'changed':sum(r['changed'] for r in rows),'by_type':{},'max_context_tokens':max(max(r['C0_tokens'],r['C1_tokens']) for r in rows),'reader_calls':0}
    for typ in ('T1','T2','T3','T4','M1','M2','N1'):
        subset=[r for r in rows if r['type']==typ]
        summary['by_type'][typ]={'n':len(subset),'changed':sum(r['changed'] for r in subset),'C0_complete':sum(bool(r['C0'] and r['C0']['complete']) for r in subset),'C1_complete':sum(bool(r['C1'] and r['C1']['complete']) for r in subset)}
    save('summary.json',summary)
    print(json.dumps(summary),flush=True)

if __name__=='__main__':
    multiprocessing.freeze_support()
    main()
