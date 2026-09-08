"""Label-free baseline replay and fusion preflight. Measurement is a separate command."""
import os
for name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[name] = '1'
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import numpy as np
from mechanism import ROOT, CONTROL, DA_ROOT, DA_SOURCE, E, fuse, linked_order
from analysis.hh001_prompt import render_reader_prompt

P = Path(__file__).resolve().parent
I = ROOT / 'experiments/study_E/artifacts/confirmation/development_inputs'
O = P / 'artifacts'


def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def save(p, value):
    with p.open('x', encoding='utf-8') as f: json.dump(value, f, indent=2); f.write('\n')
def committed(p):
    assert subprocess.check_output(['git','show','HEAD:'+p.relative_to(ROOT).as_posix()],cwd=ROOT).replace(b'\r\n',b'\n') == p.read_bytes().replace(b'\r\n',b'\n')
def require_gate(g):
    if g.get('status') != 'PASS': raise ValueError('Structural gate has not passed')


def stable_trace(t):
    t = json.loads(json.dumps(t))
    t['prior']['baseline_report'].pop('latency_ms')
    return t


def fixtures():
    nodes = [SimpleNamespace(session_identity=s, pair_order=i) for s,i in [('a',0),('a',1),('a',2),('b',0),('b',1)]]
    order = (1,4,0,3,2)
    assert linked_order(nodes,order,'TEMPORAL',0) == (order, frozenset())
    assert linked_order(nodes,order,'TEMPORAL',1) == ((1,0,2,4,3),frozenset({0,2}))
    assert linked_order(nodes,order,'TEMPORAL',5) == ((1,0,2,4,3),frozenset({0,2,3}))
    assert linked_order(nodes,tuple(range(5)),'TEMPORAL',5)[0] == tuple(range(5))
    try: require_gate({'status':'FAIL'})
    except ValueError: pass
    else: raise AssertionError('Failed gate admitted measurement')
    # Mechanism import graph: this adapter executes a single original function,
    # imports a frozen outcome-free selector, and accepts no measurement object.
    code = (P/'mechanism.py').read_text(encoding='utf-8')
    forbidden = ['labels.json','q_facts_key','sufficient_sets','gold_ids','["answer"]']
    def clean(s): return not any(x in s for x in forbidden)
    assert clean(code) and not clean(code+'\nopen("labels.json")')
    return dict(two_session_boundary=True, active_and_inert=True, no_link_identity=True,
                failed_gate_rejected=True, planted_leak_rejected=True)


def main():
    started = time.monotonic(); cpu = time.process_time()
    assert not O.exists(), 'Never overwrite preflight artifacts'
    for p in [P/'PLAN.md',P/'mechanism.py',P/'preflight.py']: committed(p)
    pins = {CONTROL:'8d18ee7c',DA_ROOT:'de20ac79',E.OLD:'05ef90e2',E.ENGINE:'5ebda1ef'}
    for folder,pin in pins.items():
        assert subprocess.check_output(['git','-C',str(folder),'rev-parse','HEAD'],text=True).strip().startswith(pin)
        assert not subprocess.check_output(['git','-C',str(folder),'status','--porcelain'],text=True).strip()
    checks = fixtures()
    manifest = read(I/'manifest.json')
    for name in ['sources.json','vectors.npz','vector_manifest.json','traces_sealed.json','prompts.json']:
        assert sha(I/name) == manifest[name]
    vm = read(I/'vector_manifest.json'); assert sha(I/'vectors.npz') == vm['file_sha256']
    vectors = dict(zip(vm['texts'],np.load(I/'vectors.npz')['vectors']))
    histories = read(I/'sources.json')
    # Ignore and never pass outcome fields present in the historical containers.
    traces = {r['history']:r['trace'] for r in read(I/'traces_sealed.json')}
    prompts = {(r['history'],r['arm']):r['prompt'] for r in read(I/'prompts.json')}
    curves = {r['history']:r for r in read(ROOT/'experiments/probes/retrieval_score_curves/artifacts/curves.json') if r['study']=='E'}
    def one(h):
        q = h['probes'][0]
        es = [dict(e,embedding=vectors[e['user_message']+'\n'+e['assistant_message']]) for e in h['episodes']]
        _,baseline,trace = E.build(es,q['query'],vectors[q['query']])
        assert stable_trace(trace) == stable_trace(traces[h['id']])
        assert render_reader_prompt(q['query'],baseline)+'\n<think>\n</think>\n' == prompts[h['id'],'C1']
        assert list(trace['prior']['ranking']) == curves[h['id']]['order']
        neutral,_ = fuse(es,q['query'],trace,baseline,links=False)
        assert neutral == baseline
        block,t = fuse(es,q['query'],trace,baseline)
        assert (block,t) == fuse(es,q['query'],trace,baseline)
        old = trace if not trace.get('unchanged') else trace['prior']
        by = {e['id']:e for e in es}
        packed = E.render_stm_payload([], [by[k] for k in t['selected_ids']])
        assert len(packed) <= 32000 and len(set(t['selected_ids'])) == len(t['selected_ids'])
        for k in t['selected_ids']:
            fragment = E.render_stm_payload([], [by[k]])
            fragment = fragment[fragment.index('<episode '):fragment.index('</episode>')+10]
            assert fragment in block
        return dict(history=h['id'],query_sha256=digest(q['query']),id=q['id'],type=q['type'],
            source_sha256=digest(json.dumps(h['episodes'],sort_keys=True)),
            baseline=dict(selected_ids=old['selected_ids'],context_sha256=digest(baseline),
                retrieval_chars=len(E.render_stm_payload([], [by[k] for k in old['selected_ids']])),context_chars=len(baseline)),
            fusion=dict(**t,context_sha256=digest(block),context_chars=len(block)),
            context=block)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: rows = list(pool.map(one,histories))
    assert len(rows)==192 and sum(r['fusion']['active'] for r in rows)==160
    # Absence questions also contain before/anchored in Study E. Preserve them
    # under the same query rule; latest is the truly inactive guard population.
    O.mkdir()
    save(O/'blind_outputs.json',rows)
    paths = [I/n for n in ['sources.json','vectors.npz','traces_sealed.json','prompts.json','manifest.json']]
    paths += [DA_SOURCE,CONTROL/'experiments/study_E/mechanism.py',P/'mechanism.py',P/'preflight.py',P/'PLAN.md']
    gate = dict(status='PASS',baseline_contexts_exact=192,baseline_stable_traces_exact=192,no_link_contexts_exact=192,
        trace_normalization='JSON tuple/list normalization; remove only measured latency_ms',
        repeated_fusion_exact=192,fixtures=checks,outputs_sha256=sha(O/'blind_outputs.json'),
        inputs={str(p):sha(p) for p in paths},workers=4,numeric_threads=1,
        wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
        model_calls=0,embedding_calls=0,active=sum(r['fusion']['active'] for r in rows))
    save(O/'preflight.json',gate)
    print(json.dumps(gate))


if __name__ == '__main__': main()
