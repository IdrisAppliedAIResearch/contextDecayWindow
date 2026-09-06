"""Finish pre-inference provenance/instrument checks without opening answers."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from confirmatory import OUT,ROOT,STUDY,CONTROL,read,save,digest,verify_registration
from episodic._ranking import rank_cc80

def main():
    verify_registration()
    assert not (OUT/'prefix_responses.jsonl').exists()
    assert not (OUT/'instrument_gate.json').exists()
    old=read('prompt_gate.json')
    for name,sha in old['files'].items():
        assert digest((OUT/name).read_bytes())==sha
    manifest=read('vector_manifest.json')
    vectors=dict(zip(manifest['texts'],np.load(OUT/'vectors.npz')['vectors']))
    original={t['id']:t for t in read('mechanism_sealed.json')}
    rank_rows=[]
    for s in read('sources.json'):
        es=[{**e,'embedding':vectors[e['user_message']+'\n'+e['assistant_message']]} for e in s['episodes']]
        for p in s['probes']:
            rank=rank_cc80(es,p['query'],vectors[p['query']],dense_weight=.8,bm25_k1=1.2,bm25_b=.75)
            assert list(rank.order)==original[p['id']]['ranking']
            rank_rows.append({'item':p['id'],'order_ids':[es[i]['id'] for i in rank.order],'cc80_scores':list(rank.scores),'dense_scores':list(rank.dense_scores),'bm25_scores':list(rank.bm25_scores)})
    save('rank_scores.json',rank_rows)
    tests=subprocess.run([sys.executable,'-m','pytest',str(STUDY/'test_development_contract.py'),str(STUDY/'test_confirmatory_gates.py'),'-q'],cwd=ROOT,capture_output=True,text=True)
    assert tests.returncode==0,tests.stdout+tests.stderr
    save('instrument_tests.json',{'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr})
    launch=json.loads((STUDY/'artifacts/part1/runtime_gpu/launch.json').read_text())
    gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)
    assert any(line.split(',')[0].strip()==str(launch['pid']) for line in gpu.splitlines()),gpu
    paths=list(Path(launch['command'][0]).parent.glob('*.dll'))
    cuda=Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2\bin\x64')
    paths += [p for p in cuda.glob('*.dll') if p.name.startswith(('cublas','cudart'))]
    files=[]
    for p in sorted(paths):
        with p.open('rb') as stream:
            sha=hashlib.file_digest(stream,'sha256').hexdigest()
        files.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha})
    save('runtime_dependencies.json',{'launch':launch,'gpu_processes':gpu,'dependencies':files})
    labels=read('labels.json')
    mapping=read('mapping.json')
    # Shared NULL prompts can have different golds across sessions; scores
    # must therefore key on response-call AND reference, not response alone.
    groups={}
    for cell in mapping:
        groups.setdefault(cell['call_key'],set()).add(labels[cell['item']]['answer'])
    save('alias_audit.json',{'shared_calls_with_distinct_references':sum(len(v)>1 for v in groups.values()),'score_key_contract':'SHA256(call_key + colon + reference)','physical_call_aliases_are_not_score_aliases':True})
    names=['rank_scores.json','instrument_tests.json','runtime_dependencies.json','alias_audit.json']
    save('instrument_gate.json',{'status':'PASS','implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'files':{name:digest((OUT/name).read_bytes()) for name in names},'confirmation_reader_calls':0,'scores_opened':False})
    print(json.dumps({'instrument_gate':'PASS','rank_rows':len(rank_rows),'tests':15,'confirmation_reader_calls':0}))

if __name__=='__main__':
    main()
